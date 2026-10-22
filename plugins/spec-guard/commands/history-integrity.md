---
description: 核对旧布局项目的能力历史证据，或只读预览旧证据的迁移
argument-hint: "[verify | migration-preview]"
allowed-tools: Bash, Read
---

能力历史只为还没迁完的旧布局项目保留（每个项目现在只有一张能力图，不再产生新归档）。两件事都只读：

- `verify`（默认）：逐个核对 `spec/CAPABILITY-HISTORY.json` 登记的归档文件的 SHA-256，并拒绝未登记的历史目录；
  没有账本时报「未验证」并以 0 退出。
- `migration-preview`：列出旧项目可导入的证据与冲突，不写任何文件。

```bash
ROOT="${CLAUDE_PLUGIN_ROOT}"
[ -n "$ROOT" ] || ROOT="${PLUGIN_ROOT:-}"
WHY="宿主没有把插件根目录代入命令，环境里也没有 CLAUDE_PLUGIN_ROOT 或 PLUGIN_ROOT"
if [ -z "$ROOT" ]; then
  if ! command -v codex >/dev/null 2>&1; then
    WHY="${WHY}；也没有 codex 可查询"
  else
    LIST="$(codex plugin list --available --json 2>/dev/null)"; RC=$?
    ROOT="$(printf '%s' "$LIST" | python3 -c '
import json, sys
try:
    plugins = json.load(sys.stdin).get("installed", [])
except (AttributeError, TypeError, ValueError):
    sys.exit(3)
for plugin in plugins:
    if isinstance(plugin, dict) and plugin.get("name") == "spec-guard" and plugin.get("installed") and plugin.get("enabled"):
        source = plugin.get("source")
        path = source.get("path") if isinstance(source, dict) else None
        if isinstance(path, str) and path:
            print(path)
            sys.exit(0)
sys.exit(4)
')"
    case $? in
      0) ;;
      4) WHY="${WHY}；codex plugin list 没有列出已启用且带路径的 spec-guard" ;;
      *) WHY="${WHY}；codex plugin list 查询失败（退出码 ${RC}）或输出无法解析" ;;
    esac
  fi
fi
[ -n "$ROOT" ] || { echo "spec-guard 无法定位插件根目录：${WHY}。这是定位失败，不代表插件未安装。" >&2; exit 2; }
[ -d "$ROOT" ] || { echo "spec-guard 插件根目录不存在：${ROOT}（插件可能刚更新或被移除，重开会话后再试）。" >&2; exit 2; }
PROJECT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
case "$ARGUMENTS" in
  ""|verify) bash "$ROOT/hooks/verify-history.sh" "$PROJECT" ;;
  migration-preview) python3 "$ROOT/hooks/history-migration.py" preview "$PROJECT" ;;
  *) echo "用法：/spec-guard:history-integrity [verify | migration-preview]" >&2; exit 2 ;;
esac
```

原样转述输出。verify 通过只说明归档文件逐字未改，不说明账本里的字段（职责、依赖、状态）都对；事件的 `at` 是迁移时抄下的原值
（可能是 `now`、`imported`），不作为时间证据。账本里已有的补正记录照常校验，但不再提供审计与追加补正。

历史快照与旧 state 是证据，不是恢复旧 tracker 工作流的授权。实际导入旧证据是维护者的内部操作，不在本命令里。
