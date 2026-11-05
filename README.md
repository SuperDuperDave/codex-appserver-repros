# codex-appserver-repros

Minimal, protocol-level reproductions of `codex app-server` behavior, with transcripts. One script, no desktop app, no config edits; it talks stdio JSON-RPC to a local `codex app-server`.

Measured on **codex-cli 0.165.0**, Linux (WSL2), 2026-11-05. Re-run on a newer version and tell us what changed.

```
cd "$(mktemp -d)"
python3 /path/to/repro/codex_appserver_repro.py resume-drift   # no model turn
python3 /path/to/repro/codex_appserver_repro.py dedupe         # two tiny model turns
```

## Findings

### 1. Cold `thread/resume` without overrides falls back to host defaults for a thread that has not run a turn
`thread/start` with `sandbox: "read-only"` reports `readOnly`. If the server is stopped before any turn runs and a new one resumes the thread with no overrides, the response reports `workspaceWrite` and `reasoningEffort: null`. **After one completed turn the same resume keeps the thread's settings** (`readOnly`, effort `high`; [transcripts/output-resume-after-turn.txt](transcripts/output-resume-after-turn.txt)), so the fallback applies to threads with no persisted turn context. Our first report of this (a comment on [openai/codex#49229](https://github.com/openai/codex/issues/49229)) omitted that condition; a correction is posted there. Hypothesis from reading the source (not verified by us): `TurnContextItem` in the rollout persists `sandbox_policy`, `approvals_reviewer` and `effort` per turn, and a thread with no turn has nothing to restore from. Related: #25590, #53447.

```
turn-less thread:  thread/start readOnly -> cold resume (no overrides) workspaceWrite, effort None
after one turn:    thread/start readOnly -> cold resume (no overrides) readOnly, effort high
```

### 2. An explicit sandbox on a cold resume is honoured; effort comes back only if `model` is passed
A matrix over `cwd`, `model`, `approvalsReviewer` (each combination on a fresh server): `sandbox` stayed `readOnly` in all eight; `reasoningEffort` was `null` unless `model` was in the request, in which case it was `high` ([transcripts/output-resume-matrix.txt](transcripts/output-resume-matrix.txt)). `thread/start` and `thread/resume` have no effort field; effort is set per `turn/start`.

### 3. A `thread/resume` on a thread that is already loaded ignores overrides
In one server process, `thread/resume` with an explicit `sandbox` on a thread that is already loaded leaves the thread's sandbox unchanged. This holds with and without a completed turn ([transcripts/output-loaded-override-after-turn.txt](transcripts/output-loaded-override-after-turn.txt)): after a cold resume reports `readOnly`, a second `thread/resume` with `sandbox: "workspace-write"` on the same server still reports `readOnly`, while the same request on a fresh server reports `workspaceWrite`. Filed as [openai/codex#59730](https://github.com/openai/codex/issues/59730).

### 4. `clientUserMessageId` does not deduplicate `turn/start`
Two identical `turn/start` calls (same thread, same `clientUserMessageId`, same text) produce two completed turns; `thread/turns/list` shows both `userMessage` items with the same `clientId` and distinct item ids. Filed as [openai/codex#59727](https://github.com/openai/codex/issues/59727). Client-side workaround: list turns and look for the `clientId` before any retry.

### 5. `thread/read` omits the sandbox and approval fields; `turn/start` on an unloaded thread answers "thread not found"
On a thread that completed one turn and is no longer loaded, `thread/read` returns `{readState, thread}`; `thread` carries `model` and `reasoningEffort` but no `sandbox`, `approvalPolicy` or `approvalsReviewer` (the `thread/start` and `thread/resume` responses do). `turn/start` on the same thread without a prior `thread/resume` fails with `thread not found: <id>` even though `thread/read` just found it ([transcripts/output-turn-start-unloaded.txt](transcripts/output-turn-start-unloaded.txt), `repro/turn_start_unloaded.py`). Proposals for both are filed as feature requests.

## Files
- `repro/codex_appserver_repro.py`: `resume-drift` and `dedupe`. `repro/resume_after_turn.py` and `repro/loaded_override_after_turn.py`: the controls with a completed turn (one tiny model turn each). `repro/turn_start_unloaded.py`: finding 5 (one tiny model turn).
- `transcripts/`: script output, the resume matrix, and a trimmed JSON-RPC transcript of an explicit-profile cold resume followed by a deliberate replay (only `thread/start`, `thread/resume`, `turn/start`, `thread/turns/list`; paths generalised).

## Scope
Reported posture comes from the app-server's own responses; we did not attempt writes after a resume. One machine, one version. Investigation by Mainthread's team; written up with Claude and reviewed by a person.
