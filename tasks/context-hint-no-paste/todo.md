# Todo: context-hint-no-paste

- [x] Task 1: injected lines (tests first) — `test-phase-guard.sh` expectations for the unsized and sized boundary lines and the mid-module line moved to the new wording plus an assertion that none of them asks for pasted text; red (MODULE_DONE boundary line mismatch), then `module_stage.py` (shared `NO_PASTE` clause) green: phase-guard 151, test_session_context and test_session_handoff OK
- [x] Task 2: checkpoint rule and docs (tests first), CHANGELOG — contract assertions in test_workflow_checkpoints.py ("/compact", "一句话", "不贴交接文本"; old "给出 … 的交接文本" and phase.md "生成可直接粘贴的交接文本" banned) red, then workflow-checkpoints.md and commands/phase.md green. No plugin text outside the user-invoked handoff command mentions handoff text
- [x] Checkpoint 1 (report): wording changed, regressions green and red under the old wording
- [ ] Task 3: 0.51.1 and full validation
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 4: post-release evidence on the installed plugin
