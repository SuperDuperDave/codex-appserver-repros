# codex-appserver-repros

Minimal, protocol-level reproductions of `codex app-server` behaviour, with transcripts. One script, no desktop app, no config edits; it talks stdio JSON-RPC to a local `codex app-server`.

Measured on **codex-cli 0.165.0**, Linux (WSL2), 2026-11-05. Re-run on a newer version and tell us what changed.

```
cd "$(mktemp -d)"
python3 /path/to/repro/codex_appserver_repro.py resume-drift   # no model turn
python3 /path/to/repro/codex_appserver_repro.py dedupe         # two tiny model turns
```

## Findings

### 1. Cold `thread/resume` without overrides widens the sandbox
`thread/start` with `sandbox: "read-only"` reports `readOnly`. After the server is stopped and a new one resumes the thread with no overrides, the response reports `workspaceWrite` and `reasoningEffort: null`. Approval policy and reviewer are unchanged; no warning. Related upstream reports: [openai/codex#49229](https://github.com/openai/codex/issues/49229) (our 0.165.0 comment is there), #25590, #53447.

```
thread/start                                  sandbox=readOnly       effort=high
thread/resume (cold, no overrides)            sandbox=workspaceWrite effort=None
thread/resume (cold, explicit sandbox)        sandbox=readOnly       effort=None
```

### 2. An explicit sandbox on a cold resume is honoured; effort comes back only if `model` is passed
A matrix over `cwd`, `model`, `approvalsReviewer` (each combination on a fresh server): `sandbox` stayed `readOnly` in all eight; `reasoningEffort` was `null` unless `model` was in the request, in which case it was `high` ([transcripts/output-resume-matrix.txt](transcripts/output-resume-matrix.txt)). `thread/start` and `thread/resume` have no effort field; effort is set per `turn/start`.

### 3. A `thread/resume` on a thread that is already loaded ignores overrides
In one server process: cold resume without overrides (drifts to `workspaceWrite`), then `thread/resume` with `sandbox: "read-only"` on the same loaded thread: the response still says `workspaceWrite`. The same explicit request on a fresh server returns `readOnly`. So a client cannot repair a drifted loaded thread through `thread/resume`.

### 4. `clientUserMessageId` does not deduplicate `turn/start`
Two identical `turn/start` calls (same thread, same `clientUserMessageId`, same text) produce two completed turns; `thread/turns/list` shows both `userMessage` items with the same `clientId` and distinct item ids. Filed as [openai/codex#59727](https://github.com/openai/codex/issues/59727). Client-side workaround: list turns and look for the `clientId` before any retry.

## Files
- `repro/codex_appserver_repro.py`: the two repros above.
- `transcripts/`: script output, the resume matrix, and a trimmed JSON-RPC transcript of an explicit-profile cold resume followed by a deliberate replay (only `thread/start`, `thread/resume`, `turn/start`, `thread/turns/list`; paths generalised).

## Scope
Reported posture comes from the app-server's own responses; we did not attempt writes after a resume. One machine, one version. Investigation by Mainthread's team; written up with Claude and reviewed by a person.
