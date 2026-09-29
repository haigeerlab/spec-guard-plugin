---
description: 校验已落地的产物是否符合约定（能力图结构、模块 spec 与能力图对应、根目录 spec 漂移）
allowed-tools: Bash
---

阶段交接、确认或停止前，读取并遵循 `spec-guard-ops` 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问。

跑一次产物落地校验：

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
CLAUDE_PROJECT_DIR="$PROJECT" bash "$ROOT/hooks/verify-artifacts.sh"
```

脚本输出已经是给人看的格式，**原样转述**，然后：

- **有 ❌** —— 逐条说明「为什么这是问题」和「怎么改」，**得到确认后再动手**。
  违规可能是用户故意的，不要自作主张补齐。
- **有 ⚠️** —— 提一句即可，不必追着修。
- **「未验证」不等于通过** —— python3 不可用或能力图解析器没有正常运行时，对应检查整段跳过，
  要明确告诉用户「这部分没验，不是验过了」。
- **退出码 2** —— 项目目录无法进入。没有能力图只会给出 ⚠️，不影响退出码。

当前检查的是：能力图存在并通过与 Proposal 相同的严格解析（唯一模块表、Build order、依赖）；
`spec/` 下每个模块 spec 都是能力图中的模块；项目根目录没有 `SPEC*.md`。它不校验 plan、todo 的内容，也不检查
分支或远端 Issue；对 plan 与 todo 只做下面这条存在性汇总。

能力图通过解析后，若有模块有 `tasks/<id>/plan.md` 却没有 `tasks/<id>/todo.md`，会多一条汇总 ⚠️：`N 个模块有 Plan 但没有 todo.md，按已完成计：…`（按 Build order 最多列 10 个，其余以「等 N 个」收尾）。它只是提醒，不是失败，不改变退出码：这些模块按已完成计，已交付的可以不管；仍有活要做的，补 `tasks/<id>/todo.md` 列出剩余任务。

## 和 `/spec-guard:phase` 的分工

| | `/spec-guard:phase` | `/spec-guard:verify-artifacts` |
|---|---|---|
| 问题 | 现在处在哪个阶段 | 已经落下的产物对不对 |
| 时机 | 每次发言前自动注入（hook） | 按需跑 |
| 成本 | <1s，只看文件是否存在 | 读能力图与 `spec/` 目录，只在本地 |

两边目前没有重叠的判定。以后若加入同一判据，规则必须两边一致并各有正反回归：0.6.0 改模块分支约定时
只改了 `phase-guard`，这边留在旧约定到 0.7.11 —— 模块名带数字就会报假失败。

## 什么时候该跑

- 评审能力图与模块 spec 之后：确认文件名与目录结构一致
- 新增、改名或删除模块 spec 之后：确认 `spec/` 与能力图仍然一致
- 接手别人的分支、或隔了几天回来时
