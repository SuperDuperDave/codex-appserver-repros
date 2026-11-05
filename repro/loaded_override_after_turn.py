import os, time, importlib.util
spec = importlib.util.spec_from_file_location("r", os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex_appserver_repro.py")); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
a = r.Server()
t = a.call("thread/start", {"sandbox": "read-only", "approvalPolicy": "on-request", "cwd": r.CWD}); tid = t["thread"]["id"]
a.call("turn/start", {"threadId": tid, "input": [{"type": "text", "text": "Reply with exactly: ok"}]}); a.wait_turn()
a.stop(); time.sleep(2)
b = r.Server()
print("cold resume, no overrides                        ", r.posture(b.call("thread/resume", {"threadId": tid, "excludeTurns": True}))["sandbox"]["type"])
print("same server, resume sandbox=workspace-write      ", r.posture(b.call("thread/resume", {"threadId": tid, "excludeTurns": True, "sandbox": "workspace-write"}))["sandbox"]["type"])
b.stop(); time.sleep(2)
c = r.Server()
print("fresh server, cold resume sandbox=workspace-write", r.posture(c.call("thread/resume", {"threadId": tid, "excludeTurns": True, "sandbox": "workspace-write"}))["sandbox"]["type"])
c.stop()
