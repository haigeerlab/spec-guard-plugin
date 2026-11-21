---
description: 记录模块 Spec 或 Plan 的批准状态（待批准／已批准）：先预览后确认，只改一行标记；已批准只在用户明确批准后写
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
python3 -B "$ROOT/hooks/review_mark.py" --project "$PROJECT" --module <module-id> --target <spec|plan|both> --state <pending|approved>
```

有项目指向时 `follow` 会跟随到被指向的项目：stderr 出现「本次操作的是被指向的项目」时，回复用户时照原文转述这一句；它退出 2 时照原文报告诊断，不要改用会话目录重试。

## 标记是什么

`spec/<id>.md` 与 `tasks/<id>/plan.md` 各可带一行批准标记，阶段提示与 `/spec-guard:verify-artifacts` 据此报告事实：

```text
<!-- spec-guard: review pending -->                 待用户批准
<!-- spec-guard: review approved <digest> -->       Spec 已批准，digest 是批准时的内容指纹
<!-- spec-guard: review approved -->                Plan 已批准
```

- 当前模块的 Spec 或 Plan 待批准时，阶段提示报告“等待用户批准”，不建议写 Plan 或继续 build；
- Spec 在批准后内容有变，自动判为“批准后已修订”，需要用户复审后重新记录；
- 没有标记的文件不受影响，判定照旧。围栏代码块里的同样文字是示例，不算标记。

## 什么时候写

- **`pending`**：写出一份 Spec 或 Plan 交给用户审阅时。可以用本命令，也可以在写文件时直接带上这一行。
- **交审要让用户看到内容**：在对话正文里按小项给出，名称与顺序同 session-protocol 契约的交审小项，每项写全，短文件可以贴全文。Spec 依次给目标、
  边界（总是做、先问、不做三档）、要你确认的假设（含关键决策与取舍）、验收标准（逐条列 AC）、未决问题（还没定、要用户回答的事），之后是附加项文档建议
  （细则见共享检查点规则「文档建议」一节）；Plan 依次给架构决定、分几步（每个任务与验证方式）、会改哪些文件（影响面）、风险、中途会停下来问你的地方
  （检查点及其类型）、未决问题。旧名「做／不做」「附带的小决定」照认。小项之后写“注意：”与“批了会怎样：”（这次批准授权什么）。只给链接、一句概述或任务标题不算交审。
  再列选项、各自选了会怎样（能不能撤回、还要不要另外问）和推荐理由，推荐答复放进可复制代码块、不用行内代码，一块只答一件事、写最短说法（有交审号写“C16 A”，没有写“批准”或“批准；Q1 A”，
  细则见共享检查点规则「交审时说明怎么批准」）；
  不需要回答的内容不用代码块；“继续”不会被记为批准，不要等用户说了“继续”再解释。所装协作插件对在哪里答复另有规定时（例如只在它的收件箱答），以它为准，复制块按它的规定放或不放。
  细则见共享检查点规则「批准标记」一节。
- **`approved`**：**只在用户明确批准这份 Spec 或 Plan 之后**。批准来源以所装协作插件的规定为准；没装只认当前对话里的明确批准；
  细则见共享检查点规则「批准标记」一节。
  “看起来可以”“继续”这类含糊的话不算，先问清楚。不得为了消除阶段提示而自行批准；标记只是让后续会话读得到的记录，不是授权来源，用户的批准原话以对话或契约消息里的「用户原话」为准。
- 用户批准后，写入 `approved` 是第一个动作，先于任何代码改动、写 Plan 或勾选 todo。
- Spec 被修订后先把修订内容交用户复审，批准后重新运行 `--state approved`，标记会带上新指纹。
- 开工前（Spec 已批准、Plan 还没批准）的修订可以攒到 Plan 交审一次批：用户批准时用 `--target both`。Spec 读作“批准后已修订”时，
  预览先打印 Spec 相对批准基线的累计差异（基线取自 git 里指纹与标记一致的那次提交），把这段差异原样给用户看；取不到基线时预览
  写明原因，这时要把改过的 Spec 全文给用户看。所以 Spec 获批后先提交再改。只记 Plan（`--target plan`）在 Spec 已修订时照旧拒绝。
- 合并审（`reviewCadence` 为 `combined`）下用户一次批准两份时用 `--target both`。
- 既有项目里没有标记的 Spec 或 Plan 不必补标记。Spec 没有标记时可以单独记录 Plan 的批准，预览会说明本次只记录 Plan；
  要给旧的 Spec 补 `approved`，先向用户单独确认一次，不得依据此前含糊的答复补记。

## 预览与确认

默认只预览：打印每个文件的 diff、Spec 的当前指纹和写入后的批准状态；记为已批准时另给出文件行数，并提醒先确认用户已在
对话里看到这份文件的内容（只给过链接或一句概述时，先补上内容再请用户确认）。这是提醒，不是拒绝条件。把预览给用户看过并得到确认后，才在同一条命令
后加 `--confirm`；写入只改标记这一行（已有标记原地替换，没有则放在第一行标题之后）并读回核对：

```bash
python3 -B "$ROOT/hooks/review_mark.py" --project "$PROJECT" --module <module-id> --target spec --state approved --confirm
```

目标已是所求状态时说明无需改动并正常退出。拒绝（退出码 2、不写文件）：不是有效 module id、不在能力图上、目标文件
不存在或读不了、标记无效（多于一行或写法不符，需手工改正）、Spec 标着待批准、已修订或标记无效时单独把 Plan 标为已批准
（Spec 的批准需要用户针对这份 Spec 单独明确确认；Spec 没有标记时不拒绝）。
不执行任何 Git 或远端操作，不改 `.agent/state.json`、todo.md 或能力图。

## Codex 审查（接管档位）

模块档位里 Spec 或 Plan 是 codex 时（`/spec-guard:config` 的 takeover），用 /delegate:review（后端 codex）审这个文件，把它标准输出的 JSON
存成仓库外的文件（例如 `$TMPDIR` 下），再记下这一轮（一次一个文件，不用 `--target both`）：

```bash
python3 -B "$ROOT/hooks/review_mark.py" --project "$PROJECT" --module <module-id> --target <spec|plan> --state codex-approved --review <报告文件>
python3 -B "$ROOT/hooks/review_mark.py" --project "$PROJECT" --module <module-id> --target <spec|plan> --state codex-reviewed --review <报告文件>
```

只认完成且有结论的 Codex 报告；被审文件按报告 `scope.files` 的内容 sha256 与工作区核对，对不上就拒绝；缺严重程度的意见按阻断。
每次都在「外部审查意见」一节追加一行轮次；`codex-approved` 要求本轮没有阻断，并写 `<!-- spec-guard: review codex-approved <digest> -->`；
有阻断用 `codex-reviewed` 只记这一轮，改完再审。两轮仍有阻断后两种都拒绝，交用户批（`--state approved`）。Codex 的批准不是用户的批准：
档位不允许、或 Plan 的「预先声明」有内容时，阶段提示把它当作待用户批准。

## Codex 最终验收（合并：自动）

模块档位里合并是 auto 时，到最终 gate 用 /delegate:review（后端 codex）审本模块开工前的提交到 HEAD 的补丁（`--spec spec/<id>.md`），
报告存成仓库外的文件；等 autopilot 在 HEAD 上写好检查证据（`~/.autopilot/evidence/<owner>__<repo>/<HEAD>.json`），工作区干净时：

```bash
python3 -B "$ROOT/hooks/review_mark.py" --project "$PROJECT" --module <module-id> --target acceptance --state codex-approved --review <报告文件>
```

三样（审查无阻断且审到 HEAD、Spec 与工作区一致；检查由非作者在 HEAD 上跑、全部退出 0；两者都是 HEAD）缺一，或有越界文件，就拒绝并写明原因。
加 `--confirm` 才写：记录写在 git 目录的 `spec-guard/acceptance/<id>.json`（不被跟踪、不进提交），报告路径存为绝对路径。
todo 里的最终 gate 现在不勾：记录的提交是 HEAD 或其祖先时阶段提示当它已过，合并后补勾并写一句来源。拟回告写进 todo，不发出。
合并不是 auto 的模块被拒绝，最终验收照旧由用户做；本模块开工前的提交里合并还不是 auto（开工后才放宽）的也拒绝（`acceptance-not-auto-at-base`），
免得补丁靠改 `.agent/config.json` 给自己开自动合并。
