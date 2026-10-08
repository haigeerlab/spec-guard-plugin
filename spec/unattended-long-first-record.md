# Spec: unattended-long-first-record

## Objective

Keep the `codex exec` signal of [unattended-run-hint](unattended-run-hint.md) working when a rollout's first record is
long. `session_context.unattended()` reads the transcript's first line with `readline(65536)`. Codex writes the whole
base instructions into that first `session_meta` record; on this Mac the last 200 rollouts measured 19.2–23.6 KB
(2026-10-08), under 3× headroom. A longer project instruction set would push it past 64 KB, the read would truncate the
line, JSON parsing would fail, the run would count as attended, and `codex exec` answers would again end with the
"/compact … /clear" sentence. Found by 第二轮联调 reviewing #251; the user asked for it to be fixed before the combined
release.

Readers: maintainers of the phase hint; anyone whose agents drive `codex exec` with long project instructions.

## Assumptions

Confirmed by the user on 2026-10-08:

1. The first-record read limit becomes 1 MB (about 40× the largest measured record); the read stays bounded and still
   covers only the first record.
2. A first record longer than the limit is treated as attended (today's behaviour), never as unattended.
3. No release of its own; CHANGELOG under `## [未发布]`, shipped in the combined release.

## Requirements

1. `unattended()` reads at most 1 MB for the first record; when the read returns the full limit without a line end,
   the record counts as attended.
2. Regressions in `test_session_context.py`: a first `session_meta` record of about 100 KB with `source: "exec"` is
   unattended; a first record longer than 1 MB with `source: "exec"` is attended; existing cases unchanged.
3. Each new assertion is shown to go red by breaking the code by hand.
4. CHANGELOG entry under `## [未发布]`.

## Commands

```bash
/bin/bash scripts/validate.sh
python3 -B plugins/spec-guard/hooks/test_session_context.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
```

## Boundaries

- Always: `python3` standard library; fixtures in temporary directories; the hook stays read-only.
- Ask first: push, PR.
- Never: read beyond the first record for this signal; treat an unreadable or oversized record as unattended.

## Success criteria

1. A `codex exec` run whose first record is between 64 KB and 1 MB still drops the free-context lines.
2. Every other case behaves as today.

## Open questions

None.
