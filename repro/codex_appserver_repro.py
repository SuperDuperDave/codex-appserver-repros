#!/usr/bin/env python3
"""Two protocol-level repros for `codex app-server` (stdio), no desktop app, no config edits.

  python3 codex_appserver_repro.py resume-drift   # no model turn
  python3 codex_appserver_repro.py dedupe         # two tiny model turns

resume-drift: thread/start read-only -> stop the server -> new server -> thread/resume with no overrides.
dedupe:       turn/start twice with the same clientUserMessageId -> thread/turns/list.
Run from an empty scratch directory. Prints only protocol fields. Tested on codex-cli 0.165.0, Linux."""
import json, os, queue, subprocess, sys, threading, time, uuid

CWD = os.getcwd()

class Server:
    def __init__(self):
        self.p = subprocess.Popen(["codex", "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, cwd=CWD)
        self.q, self.n = queue.Queue(), 0
        threading.Thread(target=lambda: [self.q.put(json.loads(l)) for l in self.p.stdout], daemon=True).start()
        self.call("initialize", {"clientInfo": {"name": "repro", "title": "repro", "version": "0"}})
        self.send({"jsonrpc": "2.0", "method": "initialized"})
    def send(self, o):
        self.p.stdin.write(json.dumps(o) + "\n"); self.p.stdin.flush()
    def _decline(self, m):
        self.send({"jsonrpc": "2.0", "id": m["id"], "error": {"code": -32000, "message": "declined"}})
    def call(self, method, params, timeout=180):
        self.n += 1; rid = self.n
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        end = time.time() + timeout
        while time.time() < end:
            try: m = self.q.get(timeout=1)
            except queue.Empty: continue
            if m.get("id") == rid and ("result" in m or "error" in m): return m.get("result", m)
            if "method" in m and "id" in m: self._decline(m)
        raise TimeoutError(method)
    def wait_turn(self, timeout=240):
        end = time.time() + timeout
        while time.time() < end:
            try: m = self.q.get(timeout=1)
            except queue.Empty: continue
            if m.get("method") == "turn/completed": return
            if "method" in m and "id" in m: self._decline(m)
        raise TimeoutError("turn/completed")
    def stop(self):
        self.p.terminate(); self.p.wait(10)

def posture(r):
    return {k: r.get(k) for k in ("sandbox", "approvalPolicy", "approvalsReviewer", "reasoningEffort")}

def resume_drift():
    a = Server()
    r = a.call("thread/start", {"sandbox": "read-only", "approvalPolicy": "on-request", "cwd": CWD, "ephemeral": False})
    tid = r["thread"]["id"]; print("thread/start      ", posture(r)); a.stop(); time.sleep(2)
    b = Server()
    print("thread/resume      (cold, no overrides)         ", posture(b.call("thread/resume", {"threadId": tid, "excludeTurns": True})))
    print("thread/resume      (same server, explicit)      ", posture(b.call("thread/resume", {"threadId": tid, "excludeTurns": True,
          "sandbox": "read-only", "approvalPolicy": "on-request"})), "<- thread already loaded: override has no effect")
    b.stop(); time.sleep(2)
    c = Server()
    print("thread/resume      (cold, explicit)             ", posture(c.call("thread/resume", {"threadId": tid, "excludeTurns": True,
          "sandbox": "read-only", "approvalPolicy": "on-request"})))
    c.stop()

def dedupe():
    s = Server(); mid = "M1-" + uuid.uuid4().hex[:6]
    tid = s.call("thread/start", {"sandbox": "read-only", "approvalPolicy": "on-request", "cwd": CWD})["thread"]["id"]
    for _ in range(2):
        s.call("turn/start", {"threadId": tid, "clientUserMessageId": mid,
                              "input": [{"type": "text", "text": "Reply with exactly: ok"}]}); s.wait_turn()
    turns = s.call("thread/turns/list", {"threadId": tid})["data"]
    ids = [i.get("clientId") for t in turns for i in t["items"] if i.get("type") == "userMessage"]
    print(f"clientUserMessageId={mid}: turns={len(turns)} userMessage clientIds={ids}")
    s.stop()

if __name__ == "__main__":
    {"resume-drift": resume_drift, "dedupe": dedupe}[sys.argv[1]]()
