---
description: 查看或按明确确认设置项目配置（产物语言、批准节奏、多模块并行开关），并汇总派活开关与默认事项后端的当前值和来源
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
| `artifactLanguage` | 语言标签，如 `zh-CN`、`en`、`pt-BR` | 未设置 | 新写的 Spec、Plan、todo 正文用这种语言；结构关键字（能力图表头、`## 目标`、勾选框、`gate`／`report`、标记行）不变。已有产物不翻译。恰好为 `zh-CN` 时，阶段提示的说明文字也用中文；其他值的阶段提示为英文 |
| `reviewCadence` | `separate`／`combined` | `separate` | `combined`：写入能力图后 Spec 与 Plan 一起给出、一次批准；出现预览时没确认过的新决策、范围不清或高风险不可逆改动时仍分两次。见共享检查点规则「批准节奏」 |
| `moduleConcurrency` | `off`／`on` | `off` | 多模块并行开关：`on` 时打开规划层的并行规则（并行评估、并行边界、可开工列表、角色标记）；本身不开会话、不建 worktree、不发消息、不合并，运行时归 module-crew 插件。0.67.1 及更早的 spec-guard 不认识这个键，会把整份配置判为无效（连产物语言也失效），团队成员都升级后再设置；从本版起，新版本遇到不认识的键只忽略那个键 |

设置了的项会在每轮阶段提示里各出现一行；`separate` 与未设置不注入任何内容。`moduleConcurrency` 例外：取什么值都不注入，它的效果只在相应规则的停点出现。

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

问题分两类，问题代码都是固定词表，不复述文件里的内容。

- **文件本身坏了**（读不了、JSON 坏、顶层不是对象、`version` 不是 1）：所有配置项按默认处理，`show` 列出问题代码，
  阶段提示只注入一行 `Project config: invalid`，`verify-artifacts` 判失败。这时 `set`／`unset` 拒绝写入：先照问题代码修好或删掉文件。
- **个别键有问题**（有不认识的键、某个键取值不合法）：只有那个键失效，取值不合法的键按默认处理，其余设置照常生效；
  阶段提示多一行 `Project config: ignored (<问题代码>)`。只有不认识的键时 `check` 通过（输出 `ok (ignored: unknown-key)`）、
  `verify-artifacts` 只警告——这种键多半来自更新版本的 spec-guard；有取值不合法的键时两者仍判失败。`set`／`unset` 照常可用，
  只改指定的键，不认识的键和别的键的原值原样保留。
