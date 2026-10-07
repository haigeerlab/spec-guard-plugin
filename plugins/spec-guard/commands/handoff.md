---
description: 只读的会话交接文本：从仓库文件与 git 拼出可直接粘贴到新会话的现状，末尾留“下一步”由你填写
allowed-tools: Bash
---

在已启用约定的项目里，整条提示词恰好是 `/spec-guard:handoff` 时，UserPromptSubmit hook 已在本地给出交接文本，
不会走到这里；本命令是 hook 没有拦截时（未启用约定、hook 未信任或失败）的退路，运行同一个脚本。

只读：不写文件、不联网、不读会话记录内容。

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
# 交接说的是会话所在的位置：取当前目录所在仓库，不用可能指向主检出目录的 CLAUDE_PROJECT_DIR。
PROJECT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
python3 -B "$ROOT/hooks/session_handoff.py" "$PROJECT"
```

把输出原样放进一个代码块交给用户复制，不要改写、补充或推测“下一步”——那一行留给用户填写。
