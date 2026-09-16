---
description: 在验证后的主链模块边界提交显式 Proposal 裁决；只读且绝不写 Issue 阶段
allowed-tools: Bash
---

先通过 proposal-mainline-candidates 发现 Proposal，再由主链人工明确选择 decision：

~~~bash
python3 -B "${CLAUDE_PLUGIN_ROOT}/hooks/proposal_mainline_review.py" \
  --project . --platform "<github|gitlab>" --target "<target>" \
  --authority-id "<authority-id>" --boundary "<module-deliver|module-advance>" \
  --current-module-id "<module-id>" --proposal-id "<proposal-id>" \
  --decision "<accept|needs-revision|defer|reject>" --observations-json "[]"
~~~

observations 只能是受限 kind 与 moduleIds 的 JSON 数组；不能放入代码、路径、Issue 正文、
token 或自由文本。accept 的结果只是 accepted-candidate。由受保护的人类流程另行写
attestation 和 accepted Issue 阶段；本命令不得写入它们。
