import os, time, json, importlib.util
spec = importlib.util.spec_from_file_location("r", os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex_appserver_repro.py")); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
a = r.Server()
tid = a.call("thread/start", {"sandbox": "read-only", "approvalPolicy": "on-request", "cwd": r.CWD})["thread"]["id"]
a.call("turn/start", {"threadId": tid, "input": [{"type": "text", "text": "Reply with exactly: ok"}]}); a.wait_turn()
a.stop(); time.sleep(2)
b = r.Server()
# thread/read on the unloaded thread: which fields does it return?
rd = b.call("thread/read", {"threadId": tid, "includeTurns": False})
print("thread/read keys:", sorted(rd.keys()), "| thread keys:", sorted(rd["thread"].keys()))
print("thread/read has sandbox/approval fields:", any(k in rd or k in rd["thread"] for k in ("sandbox","approvalPolicy","approvalsReviewer")))
try:
    x = b.call("turn/start", {"threadId": tid, "input": [{"type": "text", "text": "Reply with exactly: ok2"}]}, timeout=60)
    print("turn/start on UNLOADED thread, no resume:", json.dumps(x)[:300])
except Exception as e:
    print("turn/start on UNLOADED thread, no resume: exception", type(e).__name__, e)
b.stop()
