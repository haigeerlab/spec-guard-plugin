---
description: 从远端默认分支补全 Proposal 草稿的基线与 revision 并校验，预览后确认才回写草稿
argument-hint: "<proposal-id> <github|gitlab>"
allowed-tools: Bash
---

本命令只补全并校验本地 Proposal 草稿的「基线」一节与 revision；不创建分支、提交、PR、Issue 或标签，不改能力图，
不做任何远端写操作。

**前提**：先由 agent 按 [`references/proposal-contract.md`](../references/proposal-contract.md) 的模板写好草稿
`spec/proposals/<id>.md`（模板见该文件）。草稿的 v2 标记可写 `revision=sha256:` 加 64 个 `0`，基线一节可省略，
二者由本命令按远端默认分支补全。

跑一次预览（默认，不带 `--confirm`，只读）：

```bash
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
PROJECT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
python3 -B "$ROOT/hooks/proposal_submit.py" --project "$PROJECT" \
  --draft "spec/proposals/<id>.md" --platform "<github|gitlab>"
```

原样转述预览输出：diff、revision、baseline commit、是否为已发布 Proposal 的修订，以及「下一步」清单。

**被拒绝时**，原样说明拒绝原因，然后停下。常见处理：

- 草稿路径必须是 `spec/proposals/<id>.md` 且与标记里的 id 一致；
- 远端能力图缺少 `## 目标` 一节：先在远端默认分支补上，本命令无法代写；
- 模块已在能力图中，或依赖、锚点校验失败：说明草稿的 Change 一节需要修改，改完重跑预览；
- 另一个远端文件已声明同一 id：换一个 id（同一路径上的已发布 Proposal 则视为修订，不是冲突）。

等用户对预览结果给出明确确认后，才在同一条命令后加 `--confirm` 重新运行一次（不要跳过预览直接确认）；
只有草稿文件会被重写。之后若又编辑了草稿，必须重新跑预览以重新计算 revision。

「下一步」只打印、从不执行：先经 PR 把草稿合并进默认分支；再用输出里打印的命令开 Issue（若是修订，则改已有 Issue
正文里的标记行，不要新开 Issue），标签不存在时先创建；然后运行 `/spec-guard:proposal-review`；由人把 Issue 改为
`proposal-stage:accepted`；最后用 `/spec-guard:add-module --proposal` 晋级。
