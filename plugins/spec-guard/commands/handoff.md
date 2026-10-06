---
description: 只读的会话交接文本：从仓库文件与 git 拼出可直接粘贴到新会话的现状，末尾留“下一步”由你填写
allowed-tools: Bash
---

在已启用约定的项目里，整条提示词恰好是 `/spec-guard:handoff` 时，UserPromptSubmit hook 已在本地给出交接文本，
不会走到这里；本命令是 hook 没有拦截时（未启用约定、hook 未信任或失败）的退路，运行同一个脚本。

只读：不写文件、不联网、不读会话记录内容。

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
# 交接说的是会话所在的位置：取当前目录所在仓库，不用可能指向主检出目录的 CLAUDE_PROJECT_DIR。
PROJECT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
python3 -B "$ROOT/hooks/session_handoff.py" "$PROJECT"
```

把输出原样放进一个代码块交给用户复制，不要改写、补充或推测“下一步”——那一行留给用户填写。
