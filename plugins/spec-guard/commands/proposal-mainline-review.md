---
description: 在验证后的主链模块边界提交显式 Proposal 裁决；只读且绝不写 Issue 阶段
allowed-tools: Bash
---

主链分支（policy 的 `reviewRef`）必须包含远端默认分支的最新提交。若结果是
`mainline-review-commit-not-ancestor`，说明主链分支落后：在主链 checkout 上运行
`git fetch origin && git merge --ff-only origin/<默认分支>` 后再试；不能快进时停止并报告，不要改用其他分支。

先通过 proposal-mainline-candidates 发现 Proposal，再由主链人工明确选择 decision：

~~~bash
ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
if [ -z "$ROOT" ] && command -v codex >/dev/null 2>&1; then
  ROOT="$(codex plugin list --available --json 2>/dev/null | python3 -c '
import json, sys
try:
    plugins = json.load(sys.stdin).get("installed", [])
except (TypeError, ValueError):
    plugins = []
for plugin in plugins:
    if plugin.get("name") == "spec-guard" and plugin.get("installed") and plugin.get("enabled"):
        source = plugin.get("source")
        path = source.get("path") if isinstance(source, dict) else None
        if isinstance(path, str) and path:
            print(path)
            break
')"
fi
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "spec-guard 插件未安装或未启用" >&2; exit 2; }
python3 -B "$ROOT/hooks/proposal_mainline_review.py" \
  --project . --platform "<github|gitlab>" --target "<target>" \
  --authority-id "<authority-id>" --boundary "<module-deliver|module-advance|module-interrupt>" \
  --current-module-id "<module-id>" --proposal-id "<proposal-id>" \
  --decision "<accept|needs-revision|defer|reject>" --observations-json "[]"
~~~

`--boundary` 取 `module-deliver`、`module-advance` 或 `module-interrupt`；`module-interrupt` 用于半途的当前模块被显式插队打断时（见 /spec-guard:add-module --interrupt），行为与 `module-advance` 相同。

observations 只能使用 package-boundary-conflict、public-contract-conflict、anchor-conflict、
unmerged-public-contract-change、dependency-suggestion 或 anchor-suggestion 之一；moduleIds
只能引用当前模块、Proposal 自身、其声明依赖或锚点。不能放入代码、路径、Issue 正文、token
或自由文本。accept 的结果只是 accepted-candidate。由受保护的人类流程另行写
attestation 和 accepted Issue 阶段；本命令不得写入它们。

结果为 accepted-candidate 时，输出的 JSON 额外带 `attestation`（可直接复制写入的验收记录，
七个字段）和 `attestationPath`（应写入的相对路径）；其他结果都不带这两个字段。命令仍然不写
任何文件。字段与路径的说明见
[`references/proposal-mainline-review.md`](../references/proposal-mainline-review.md#the-accepted-candidate-attestation)。
