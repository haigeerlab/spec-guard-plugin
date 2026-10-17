---
description: 多模块并行时给这个 checkout 标角色（模块：<id> 或协调）：先预览后确认，只写本 checkout 的 git 目录里一个文件；开关 moduleConcurrency 为 on 时才用
allowed-tools: Bash
---

阶段交接、确认或停止前，读取并遵循 `spec-guard-ops` 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问。

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
python3 -B "$ROOT/hooks/checkout_role.py" show --project "$PROJECT"
```

## 做什么

项目打开了多模块并行开关（`.agent/config.json` 的 `moduleConcurrency` 为 `on`）时，同一个项目在本机有一个协调 checkout 和每个模块各一个 worktree。
给每个 checkout 标一个角色，阶段提示就知道该说什么：

- **模块 checkout**（`module <id>`）：阶段提示另报告这个模块的状态，「下一步」只指向它；做完时只提示交回协调会话，不建议切到别的模块，也不建议合并或推送。
- **协调 checkout**（`coordinator`）：阶段提示保留全局进度与评审约束，「下一步」改为统筹措辞，不建议 `/build`。
- `/spec-guard:map` 会读本机其他 worktree 的角色，给出各模块在那里的进度、有没有未提交改动、提交是否已合入。

全项目的当前模块和阶段**不受角色影响**。开关不是 `on` 时角色标记一概不读，阶段提示与 `/map` 照旧。

标记在 `git rev-parse --git-path spec-guard/role` 指向的文件里（这个 checkout 自己的 git 目录），不进版本库，也不随同步传到别的 worktree。

## 设置或清除

先预览（写明旧值 → 新值），用户确认后再加 `--confirm`：

```bash
python3 -B "$ROOT/hooks/checkout_role.py" set --module <module-id> --project "$PROJECT"
python3 -B "$ROOT/hooks/checkout_role.py" set --coordinator --project "$PROJECT"
python3 -B "$ROOT/hooks/checkout_role.py" clear --project "$PROJECT"
```

退出码：0 成功；2 不是一个非 bare 仓库的顶层、模块不在能力图、标记或它的目录是符号链接或不是普通文件；3 开关不是 `on`（只对 `set`、`clear`）；
4 写后读回与写入的不一致（另一个会话同时在改），用 `show` 看当前值，不自动重试。

通常由运行时（例如 module-crew）在开 worktree 后调用；本命令不开会话、不建 worktree、不改别的文件。
