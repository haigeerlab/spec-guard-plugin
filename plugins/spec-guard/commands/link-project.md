---
description: 会话目录不是项目目录时，声明这里的工作对应哪个已启用的项目：查看、建立或解除指向；先预览后确认，只写一个文件
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
python3 -B "$ROOT/hooks/project_link.py" show --from "$PROJECT"
```

这里的 `$PROJECT` 是**会话目录**（会话所在的 git 仓库根，不在仓库里时是当前目录），不是要指向的项目。

## 什么时候用

会话开在一个不是项目的目录里，实际的开发在别处的仓库：比如会话在需求文档目录，代码仓库在另一个路径。阶段钩子只看
会话目录，那里没有约定块也没有 `.agent/state.json`，所以每一轮都静默，agent 收不到任何阶段提示。

建立一次指向之后：

- 钩子在会话目录没有激活信号、但有有效指向时，改读被指向的项目，每轮输出那个项目的阶段提示；
- 注入里多一行 `Linked project`，写明项目在哪、当前会话目录指向它；位置行（分支与 worktree）也是那个项目的；
- 会话目录自己已启用 spec-guard 时不需要、也不读指向；没有指向文件的无关目录照旧静默。

钩子不推断：不看宿主的工作区设置，也不从会话记录猜你在改哪个目录。只认这个文件。

**指向按目录生效，不按会话。** 在这个目录里运行的每一个会话都会跟随它，收到同一个项目的阶段提示。多个会话共用一个目录、
各做不同项目时不要建立指向：把会话开在各自的项目目录里，或者不建立指向、运行命令时显式带上项目路径。已经建立了的，
做别的项目的会话应忽略这段阶段提示；`unset` 可以解除。

**有指向时，本插件的其他命令要显式带上被指向的项目路径**（各命令的 `--project`），它们目前不会自动跟随指向。

## 建立与解除

默认只预览：打印将写入的文件与内容、解析后的项目路径和它当前的阶段。把预览给用户看过并确认后，才加 `--confirm`：

```bash
python3 -B "$ROOT/hooks/project_link.py" set --from "$PROJECT" --project <项目路径>
python3 -B "$ROOT/hooks/project_link.py" set --from "$PROJECT" --project <项目路径> --confirm
python3 -B "$ROOT/hooks/project_link.py" unset --from "$PROJECT" --confirm
```

只写会话目录下的 `.agent/spec-guard-link.json`（`{"version": 1, "project": "<路径>"}`），不动被指向的项目，不执行 Git 或
远端操作。路径按给定的写法保存：绝对路径，或相对于会话目录的相对路径。这个文件含本机路径，除非用的是打算共享的
相对路径，否则不要入库（把 `.agent/spec-guard-link.json` 加进 `.gitignore`；命令不替你改 `.gitignore`）。
解除只删这个文件，`.agent/` 目录留着。

拒绝（退出码 2、不写文件）：项目路径不存在或不是目录；那里没有启用 spec-guard（先在那里运行 setup-convention）；
会话目录自己已启用 spec-guard；项目就是会话目录；已有的指向文件格式无效（先 `unset --confirm`）；解除时没有指向文件。

## 指向失效

指向文件在、但格式无效、目标不存在或目标没有启用 spec-guard 时，钩子不静默，每轮给一行诊断并说明是哪一种。
用 `show` 查看原因，重新 `set` 或 `unset`。这是指向失效，不是“项目未启用”。
