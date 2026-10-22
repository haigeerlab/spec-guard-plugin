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
  做／不做（范围内与范围外）、要你确认的假设（含关键决策与取舍）、验收标准（逐条列 AC）、附带的小决定（未决问题、文档建议，细则见
  共享检查点规则「文档建议」一节）；Plan 依次给分几步（每个任务与验证方式）、会改哪些文件（影响面）、风险、中途会停下来问你的地方
  （检查点及其类型）。小项之后写“注意：”与“批了会怎样：”（这次批准授权什么）。只给链接、一句概述或任务标题不算交审。
  再列选项、各自选了会怎样（能不能撤回、还要不要另外问）和推荐理由，推荐答复（例如“批准”）放进一个独立的可复制代码块、不用行内代码；
  不需要回答的内容不用代码块；“继续”不会被记为批准，不要等用户说了“继续”再解释。所装协作插件对在哪里答复另有规定时（例如只在它的收件箱答），以它为准，复制块按它的规定放或不放。
  细则见共享检查点规则「批准标记」一节。
- **`approved`**：**只在用户明确批准这份 Spec 或 Plan 之后**。批准来源以所装协作插件的规定为准；没装只认当前对话里的明确批准；
  细则见共享检查点规则「批准标记」一节。
  “看起来可以”“继续”这类含糊的话不算，先问清楚。不得为了消除阶段提示而自行批准；标记只是让后续会话读得到的记录，不是授权来源，用户的批准原话以对话或契约消息里的「用户原话」为准。
- 用户批准后，写入 `approved` 是第一个动作，先于任何代码改动、写 Plan 或勾选 todo。
- Spec 被修订后先把修订内容交用户复审，批准后重新运行 `--state approved`，标记会带上新指纹。
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
