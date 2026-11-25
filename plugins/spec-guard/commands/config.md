---
description: 查看或按明确确认设置项目配置（产物语言、批准节奏、多模块并行开关、接管档位、按模块的接管档位），并汇总默认事项后端的当前值和来源
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
FROM="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PROJECT="$(python3 -B "$ROOT/hooks/project_link.py" follow --from "$FROM" --session "${CLAUDE_CODE_SESSION_ID:-}")" || exit 2
python3 -B "$ROOT/hooks/project_config.py" show --project "$PROJECT"
```

有项目指向时 `follow` 会跟随到被指向的项目：stderr 出现「本次操作的是被指向的项目」时，回复用户时照原文转述这一句；它退出 2 时照原文报告诊断，不要改用会话目录重试。

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
| `moduleConcurrency` | `off`／`on` | `off` | 多模块并行开关：`on` 时打开规划层的并行规则（并行评估、并行边界、可开工列表、角色标记）；本身不开会话、不建 worktree、不发消息、不合并，运行时归 module-crew 插件；不控制协调会话：协调会话由 module-crew 的 `coordinator up` 开启，与本开关无关。0.67.1 及更早的 spec-guard 不认识这个键，会把整份配置判为无效（连产物语言也失效），团队成员都升级后再设置；0.84.0 起遇到不认识的键只忽略那个键 |
| `designReview` | `off`／`on` | `off` | 技术方案审查开关：新流程里档位为普通的模块，`on` 时技术方案交第二审查者审一轮、改一轮，审过即放行；`off` 时不审。技术方案碰到老逻辑（影响面列了已有文件）或跨模块时不论开关都审；重要需求的技术方案永远由用户批。老模块与 bug、小改动不受影响。不注入阶段提示 |
| `takeover` | 预设 `none`／`design`／`merge`，或自定义对象 `{"design","merge","release"}` | `none` | 接管档位：技术方案（`human`／`reviewer`）、合并（`human`／`auto`）、发布（`human`／`prepare`／`auto-confirm`／`auto`）各由谁做；需求永远由用户确认、新流程 Plan 永远自动批准，两者不可配。`design` 让第二审查者审过即放行技术方案（重要需求仍由用户批）；`merge` 再加合并自动；发布只能用自定义打开。`none` 时每份技术方案都由用户批，不需要审的也一样。自定义里没写的项按 `human`，任何一项写错整个键失效。**旧值兼容**（只读、不再写入，`set` 拒绝并提示 `takeover-legacy`）：预设 `plan` 读作 `none`，旧 `merge` 读作新 `merge`；自定义里的 `spec`、`plan` 对新流程模块不生效。老流程模块（需求文档没有 `flow v2` 标记）仍按旧含义读谁批 Spec、Plan：`plan`、`design` 都是 Codex 批 Plan，`merge` 是 Codex 批 Spec 和 Plan。`show` 列出生效的三项与老流程两项，存的是旧值时加 `note:`；从 `plan` 改成 `design` 要用户原话。spec-guard 只存、读、报告来源，autopilot 与 module-crew 读它放行。发布为 `auto-confirm`／`auto` 时预览提示两条限制（流水线自用的四个插件最高 `prepare`；`auto` 只给能快速回滚的项目），由 autopilot 拦截。设置或取消要用户在对话里的原话，`--confirm` 前引用。0.84.0～0.94.0 的 spec-guard 把 `design` 判为取值不合法、只忽略这个键（按 `none`）；0.67.1 及更早会把含这个键的配置整份判为无效；团队都升级后再设置 |
| `moduleTakeover` | 对象：模块 id → 同 `takeover` 的值 | 未设置（`{}`） | 按模块的接管档位，没设的模块随 `takeover`。用 `--module` 一次改一个模块；任何一条写错整个键失效，旧值的读法同 `takeover`。比项目宽时只提醒、不截断。能力图上没有的模块 id 由 verify-artifacts 警告。`/map --json` 每个模块的 `takeover` 报生效的 `design`（重要需求为 `human`，`designForcedBy` 写 `important`）、`merge`、`release` 与来源，`spec`、`plan` 两项本版保留（老流程含义）、下一版删除。写入同样要用户原话 |
| `projectSections` | 对象：文档（`requirement`／`design`／`regression`）→ 章节名列表，如 `{"design": ["浏览器兼容"]}` | 未设置（`{}`） | 项目追加章节：新流程模块（需求文档带 `flow v2` 标记）的这几份文档在骨架章节之外必须带上这些章节，内容可以写「不涉及」；`bug`、`small` 只写一份需求文档，只要求 `requirement` 的追加章节；老模块不受影响。章节名非空、最多 40 个字符、不含换行和 `|`、`#`，同一份文档里不重复、不与骨架章节同名，每份最多 10 个；任何一条不对整个键失效。`set --value` 给 JSON 对象，先预览后确认，不需要用户原话（这是项目规矩，不是接管档位）。阶段提示在写到对应文档时列出这些章节。骨架见 `references/doc-skeletons.md` |
| `autonomyTier`、`moduleAutonomy` | — | — | 已退役（S101），不映射到接管档位：文件里还有时不生效，`show` 标为已退役，verify-artifacts 只警告；不能再 `set`，可以 `unset` 删除。`/map --json` 的 `autonomy` 字段本版仍按它们计算、标为 deprecated，下一版删除 |

设置了的项会在每轮阶段提示里各出现一行；`separate` 与未设置不注入任何内容。`moduleConcurrency`、`takeover`、`moduleTakeover`、`projectSections`、`designReview` 例外：取什么值都不注入，它们的效果只在相应规则的停点或读取它的插件里出现。

只读汇总、不在这里修改的一项：

| 项 | 存在哪 | 用什么改 |
|---|---|---|
| `trackerDefault`（默认事项后端） | `.agent/tracker.json` | `/spec-guard:tracker-default` |

## 设置或取消

先预览，用户确认后再加 `--confirm`：

```bash
python3 -B "$ROOT/hooks/project_config.py" set --project "$PROJECT" --key artifactLanguage --value zh-CN
```

```bash
python3 -B "$ROOT/hooks/project_config.py" unset --project "$PROJECT" --key reviewCadence
```

`takeover` 的值是预设名，或以 `{` 开头的 JSON 对象（自定义）；预览先列出三项各由谁做，再列老流程模块的 Spec、Plan 由谁批：

```bash
python3 -B "$ROOT/hooks/project_config.py" set --project "$PROJECT" --key takeover --value design
```

`moduleTakeover` 一次只改一个模块，`set` 必须带 `--module`；`unset` 带 `--module` 去掉一个模块，不带则去掉整个键：

```bash
python3 -B "$ROOT/hooks/project_config.py" set --project "$PROJECT" --key moduleTakeover --module <module-id> --value '{"design": "reviewer", "release": "prepare"}'
```

模块档位宽于项目时、发布为 `auto-confirm`／`auto` 时，预览多出 `note:` 行，照实转述；spec-guard 不截断。

**出事收窄（给 autopilot 与 module-crew 调用）**：`narrow` 往严里改一格，不需要用户原话；预设按 `merge` → `design` → `none`（旧值 `plan` 收到 `none`），
自定义按发布、合并、技术方案的顺序把一项交还给人（发布一步回到 `human`），写回新格式；已是最严时不写。从旧值 `plan` 收窄的记录，设为 `none` 或 `design` 即算恢复。带 `--module` 只收这个模块：

```bash
python3 -B "$ROOT/hooks/project_config.py" narrow --project "$PROJECT" --source autopilot --reason "自动合并 #12 被撤回" --confirm
```

它会在 `.agent/config.json` 里记下 `takeoverNarrowed`（第一次收窄前的值、谁、为什么、何时），这个文件随后要有人提交。
收窄过的范围恢复时一次只能升一格：用户说要恢复，照常 `set` 预览、引用原话后 `--confirm`；放宽超过一格会退出 2。恢复到收窄前的值后记录自动删除。
`takeoverNarrowed` 不能用 `set`／`unset` 直接改。

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
