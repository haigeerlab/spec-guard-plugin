---
description: 只读的模块成本与返工报告：按 task 统计主代理与子代理的 token、主会话轮次、派活与返工信号
argument-hint: "<module-id> [更多模块] [--prices <价格文件>] [--json]"
allowed-tools: Bash
---

阶段交接、确认或停止前，读取并遵循 `spec-guard-ops` 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问。

离线读取本机 Claude Code transcript 与 Codex rollout，按 `tasks/<模块>/todo.md` 的勾选提交切出 task 时间窗，统计每个
task 的主代理与子代理 token（按模型、按类别）、主会话轮次、派活次数与覆盖率、重派、收回、交回后主代理改动的文件数。
只读：不写文件、不联网、不读 tier-guard 的数据，输出只含计数，不含 prompt 或代码。

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
python3 -B "$ROOT/hooks/module_cost_report.py" --project "$PROJECT" $ARGUMENTS
```

原样转述输出，然后：

- **「无法归属」（退出码 2）**：todo.md 没有提交历史或不在 git 里，时间窗切不出来；照实说明，不要说成用量为 0。
- **「无法统计的部分」**：逐条转述——宿主没留下记录的派活、未定价的类别、通过 shell 命令的改动都不在数字里。
- **金额**：只有用户给了 `--prices` 才有。价格文件形如
  `{"currency":"USD","per":"1M","models":{"<宿主记录里的模型名>":{"input":…,"cache_write_5m":…,"cache_write_1h":…,"cache_read":…,"output":…}}}`；
  Codex 的类别是 `input`（非缓存）、`cache_read`、`cache_write`、`output`。缺价的部分标「未定价」，不要替用户补价格。
  主会话的缓存读通常占绝大部分 token，价格表缺缓存价时金额会严重偏低，要提醒。
- **多个模块**：报告附「有派活 / 没派活」的对照，只能看趋势；派活是否省钱的结论须来自受控对照实验，不要从这里下因果结论。
