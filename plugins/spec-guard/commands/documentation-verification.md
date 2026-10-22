---
description: 只读核验模块声明的文档交付状态，不把它当作内容或代码验证
allowed-tools: Bash, Read, Write
---

先选择模块并查询：

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
FROM="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PROJECT="$(python3 -B "$ROOT/hooks/project_link.py" follow --from "$FROM" --session "${CLAUDE_CODE_SESSION_ID:-}")" || exit 2
MODULE="<module-id>"
python3 -B "$ROOT/hooks/documentation_verification.py" \
  --project "$PROJECT" --module "$MODULE" --format json
```

有项目指向时 `follow` 会跟随到被指向的项目：stderr 出现「本次操作的是被指向的项目」时，回复用户时照原文转述这一句；它退出 2 时照原文报告诊断，不要改用会话目录重试。

`absent` 表示项目未启用基线，应静默跳过；`invalid` 表示已有表格结构无效；`attention` 是提醒而非阻断，逐条列在 `attention` 里；`ready` 表示没有未收口的声明，且声明 delivered 的现状类 `update` 文档确被改过。

每个 outcome 的 `check` 说明按基线状态核到了什么（只对 `update` 且 `delivered` 的项核）：

- `changed`／`unchanged`：现状类文档（基线状态不是 `target`）自本模块 Spec 首次提交以来改过／没改过；没改过会进 `attention`；
- `target-changed`／`target-unchanged`：`target` 文档不要求改；改过时带 `added`、`removed` 行数，把这份文档的差异原样附进验收消息；有删除行会进 `attention`（删改未实现的目标即改需求，须单独交用户批准）；
- `unverified`：外部文档（`Authority` 是 URL），只要求证据非空，没有核验；
- `unknown`：git 查不了（不在仓库里、Spec 还没提交、命令失败），原因写在 `attention` 里，不能当作没改过；
- `not-checked`：`create`、`deferred`、`pending`。

不得把 `ready` 解释为文档内容正确、已对外发布或代码符合文档；外部文档始终是未核验。最终验收时把结果按上面几类写进验收结果。

根据用户提供的真实交付事实预览 `Documentation outcome` 表；只有用户明确确认后才修改 Plan 或任何业务文档。核验只用 git 看声明要更新的文档改没改过，不读文档正文、不扫描代码；不要据此或凭时间戳另行猜测文档状态。
