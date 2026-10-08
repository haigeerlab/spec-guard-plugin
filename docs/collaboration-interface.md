# Collaboration interface

The collaboration capability moved from Spec Guard into the standalone **agent-relay** plugin. Its public interface
document now lives in the agent-relay repository (`docs/collaboration-interface.md` there) and that copy is the only
authoritative one (decided in `collaboration-extraction`). This file keeps only Spec Guard's own side of the
contract; the full text as it stood at the split is in this file's git history (last full version at `fac734d`).

## Spec Guard's side (interface sections 11–12)

- **Single entry.** Spec Guard reaches collaboration only through
  `plugins/spec-guard/hooks/agent_relay_probe.py`, and agent-relay skill names written as
  `agent-relay:<skill>`. `scripts/check-collaboration-boundary.py` fails if any
  path that moved to agent-relay (or was retired with the handoff command) comes back or if Spec Guard names collaboration internals.
- **Probe.** `agent_relay_probe.py --host claude|codex` prints one JSON object
  `{"state", "interface", "required": ">=1.0,<2.0", "message"}`. It reads the host's plugin record and agent-relay's
  `interface.json` (interface `1.0`, optional `status` command), writes nothing, and reports a failed check as
  `unknown`, never `not-installed`.
- **Degradation.** No Spec Guard command, hook, or check fails because agent-relay is absent; phase injection never
  calls the probe. The not-installed message points to
  [`docs/migrations/2026-10-07-collaboration-split.md`](migrations/2026-10-07-collaboration-split.md).
- **Handoff period (ended).** The transitional handoff command shipped for the releases after the split and was
  removed in 0.54.0, as the 0.53.0 changelog announced (collaboration-command-retirement).
