---
description: 在模块检查点（或显式插队时），用上下文提出新模块并预览校验后插入能力图
argument-hint: "[需求上下文]"
allowed-tools: Bash
---

只在模块检查点使用：当前模块要么还没开始、要么已经完成，脚本会自己校验这一点——
当前模块做到一半（`tasks/<id>/todo.md` 既有已勾选项又有未勾选项）时会拒绝并说明先完成它（显式 `--interrupt` 插队除外，见下），不必自行判断。


**插队（`--interrupt`）**：当前模块做到一半、又在等外部条件而确需先做新模块时，才在预览命令后加 `--interrupt`，
显式跳到队前。只支持一层：已有另一个暂停中的模块时脚本会拒绝。预览会写明被暂停的模块及进度（已勾/总数），
以及插入后的当前模块——必须让用户看过并明确确认。当前模块没有做到一半时 `--interrupt` 不改变任何行为。
预览提示“插入后当前模块仍是 `<被暂停模块>`”时，提醒用户把 `.agent/state.json` 的 `activeModule` 改为新模块再开始
构建（本命令不写 state.json）。确认时同样带 `--interrupt --confirm`，会重新执行全部校验。

先读 `spec/CAPABILITY-MAP.md`。根据用户给的需求上下文，提出四项并各给一句简短理由（理由要对着能力图里的实际
模块和依赖，不要泛泛而谈）：

- **id**：kebab-case，语义稳定，以后不应改名；
- **responsibility**：单行、一句话；
- **depends-on**：逗号分隔的既有模块 id，没有则填 `—`；
- **anchor**：`after:<既有模块 id>` 或 `end`，说明为什么插在这里（例如依赖顺序、职责相邻）。

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
python3 -B "$ROOT/hooks/module-insert.py" --project "$PROJECT" \
  --id "<id>" --responsibility "<responsibility>" --depends-on "<a,b|—>" --anchor "<after:<id>|end>"
```

原样转述预览输出（新行、新 Build order、diff、当前模块会不会变、Proposal 同 id 提醒）。**被拒绝时**，原样说明
是哪一条校验失败，然后停下——不要自行改字段重试，除非那正是用户接下来要做的事。

等用户对预览结果给出明确确认后，才在同一条命令后加 `--confirm` 重新运行一次（不要跳过预览直接确认）。用户
改动了 id、responsibility、depends-on 或 anchor 中的任何一项，都要先重新跑预览，不能直接对着旧预览确认。

写入只改 `spec/CAPABILITY-MAP.md`；不创建 `spec/<id>.md`、不改 `tasks/`、`.agent/state.json` 或 Proposal 文件，
不执行任何 Git 或远端操作。成功后原样转述写入结果与阶段提示；如果新模块因此成为当前模块，阶段会是
`NEEDS_SPEC`——下一步是写并评审 `spec/<id>.md`（例如用 `/spec`），不是本命令的职责。

如果这次新增需要留下经过评审的决定记录（而不只是快速插入），改用 Proposal 九步流程（见 `docs/workflow.md`），
而不是本命令。
