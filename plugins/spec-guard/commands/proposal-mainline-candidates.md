---
description: 仅在已验证主链模块边界读取远端 Proposal 候选；不接受或写入任何对象
allowed-tools: Bash
---

只有正在主链的调用者，且边界确为 module-deliver 或 module-advance，才运行：

~~~bash
python3 -B "${CLAUDE_PLUGIN_ROOT}/hooks/proposal_mainline_review.py" \
  --project . --platform "<github|gitlab>" --target "<target>" \
  --authority-id "<authority-id>" --boundary "<module-deliver|module-advance>" \
  --current-module-id "<module-id>"
~~~

原样报告 JSON。candidate-list 只是待人工审阅的排序候选，绝不等于 accepted。
若结果为 blocked、unknown、invalid 或 stale，停止，不从其他 worktree 补充事实。
本命令不会创建或修改 Issue、标签、能力图、分支、任务或 PR。

要记录主链人工裁决，追加 Proposal id、decision 和 observations JSON：

~~~bash
python3 -B "${CLAUDE_PLUGIN_ROOT}/hooks/proposal_mainline_review.py" \
  --project . --platform "<github|gitlab>" --target "<target>" \
  --authority-id "<authority-id>" --boundary "<module-deliver|module-advance>" \
  --current-module-id "<module-id>" --proposal-id "<proposal-id>" \
  --decision "<accept|needs-revision|defer|reject>" --observations-json "[]"
~~~

accept 只会产生 accepted-candidate，绝不会改写 accepted 标签或 attestation。
