---
description: 查看或按明确确认设置项目配置（产物语言、评审节奏），并汇总派活开关与默认事项后端的当前值和来源
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
python3 -B "$ROOT/hooks/project_config.py" show --project "$PROJECT"
```

## 配置放在哪

`.agent/config.json`，**入库**，团队与 Claude／Codex 两边读同一份。没有这个文件表示什么都没配，
插件行为与未引入配置时完全一致。`show` 发现它被 `.gitignore` 忽略时会警告：那样团队看不到这份配置。

`show` 末尾还列出本机状态根目录（`~/.spec-guard`，或环境变量 `SPEC_GUARD_STATE_DIR` 指定的位置）；若某类记录仍在
回退读取旧位置 `~/.local/state/spec-guard/…`，也逐行列出。只报告事实，不建议删除有内容的目录。

## 可配置项

| 键 | 取值 | 默认 | 作用 |
|---|---|---|---|
| `artifactLanguage` | 语言标签，如 `zh-CN`、`en`、`pt-BR` | 未设置 | 新写的 Spec、Plan、todo 正文用这种语言；结构关键字（能力图表头、`## 目标`、勾选框、`gate`／`report`、标记行）不变。已有产物不翻译 |
| `reviewCadence` | `separate`／`combined` | `separate` | `combined`：写入能力图后 Spec 与 Plan 一起给出、一次批准；出现预览时没确认过的新决策、范围不清或高风险不可逆改动时仍分两次。见共享检查点规则「评审节奏」 |

设置了的项会在每轮阶段提示里各出现一行；`separate` 与未设置不注入任何内容。

只读汇总、不在这里修改的两项：

| 项 | 存在哪 | 用什么改 |
|---|---|---|
| `dispatch`（子代理派活规则） | `CLAUDE.md`／`AGENTS.md` 约定块里的标记行 | `/spec-guard:setup-convention --replace --dispatch`（关闭用 `--no-dispatch`） |
| `trackerDefault`（默认事项后端） | `.agent/tracker.json` | `/spec-guard:tracker-default` |

## 设置或取消

先预览，用户确认后再加 `--confirm`：

```bash
python3 -B "$ROOT/hooks/project_config.py" set --project "$PROJECT" --key artifactLanguage --value zh-CN
```

```bash
python3 -B "$ROOT/hooks/project_config.py" unset --project "$PROJECT" --key reviewCadence
```

不带 `--confirm` 只打印改前／改后的差异，**什么都不写**；`--confirm` 只原子写回 `.agent/config.json`
这一个文件并读回核对。取值不合法、键不认识或属于上表"只读汇总"的两项时，退出码 2 且不写文件。

## 配置无效时

文件存在但不可用（JSON 坏、`version` 不是 1、有未知键、取值不合法）时，所有配置项按默认处理，
`show` 列出问题代码，阶段提示只注入一行 `Project config: invalid`，`verify-artifacts` 判失败。
这时 `set`／`unset` 拒绝写入：先照问题代码修好或删掉文件。问题代码是固定词表，不复述文件里的内容。
