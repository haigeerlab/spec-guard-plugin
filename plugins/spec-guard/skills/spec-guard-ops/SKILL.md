---
name: spec-guard-ops
description: 在 Codex 中运行 Spec Guard 的本地约定、只读验证和文档／历史工具。
---

阶段交接、确认或停止前，读取并遵循[共享检查点规则](../../references/workflow-checkpoints.md)；按实际路径预告下一步，已有授权不重复询问。

本 skill 不接管远端 tracker。GitHub/GitLab 的旧任务投影、选择、绑定和交付流程已退役；
不得从 `.agent/state.json` 恢复它们，也不得创建或修改远端对象。

## 解析环境

与命令共用同一段规范引导：Claude 加载时代入 `${CLAUDE_PLUGIN_ROOT}`，Codex 依次回退到 `PLUGIN_ROOT` 与已启用的
插件列表。不猜测缓存版本：

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
PROJECT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

这段以退出码 2 停下时，按它给出的原因转述：那是定位失败，不代表插件未安装。

## setup

只安装本地多模块目录约定；先用 `--dry-run` 预览。用户确认后才省略它：

```bash
CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/setup-convention.sh" local --host=codex --dry-run
```

已有声明块要升级时追加 `--replace`：块内 `<!-- BEGIN:spec-guard-local -->` 与 `<!-- END:spec-guard-local -->` 之间的本地段原样保留；预览逐行列出 `will remove:` / `will add:`，标着 `[needs --accept-removals]` 的行不在模板里，原样转述，由用户决定移进本地段或同意删除后追加 `--accept-removals`。用户要求把 `/build` 的 task 交给子代理执行时加 `--dispatch`（实验性：规则默认由主代理自己做，只派预计改动 3 个以上文件、验收明确的 task；派出后 wait_agent 一次等到完成、不短间隔轮询；省钱效果未证明，预览时说明）
（默认关闭；开关存在块里，`--replace` 会保留已开启的状态，关闭须 `--no-dispatch`；转述预览中的
`build-task-dispatch rule:` 行）。Codex 段写明 tier-guard 在 Codex 上只作建议。workspace-write 沙箱不允许写 `.git`，开启后主代理每次提交都要申请提权，预览时提醒用户。遗留 `.agent/state.json` 是历史记录，不得用
setup 覆盖。

## teardown

移除本项目的 spec-guard 约定前先确认用户真的要移除，说明会发生什么：删 `AGENTS.md` 里
`BEGIN`/`END` 标记之间的内容（标记外一个字节不动）；把 `.agent/state.json` 改名为
`.agent/state.json.disabled`（这才是真正的「移除」——只删声明块留着 `state.json`，项目会变成
零足迹模式而不是约定被移除）；脚本会实际跑一遍 `phase-guard.sh` 验证，而不是让人相信
「无输出即为成功」这句话。不碰 `spec/`、`tasks/` 里的内容，也不碰远端 Issue 与本地事项账本。

先 `--dry-run` 预览，原样转述输出：

```bash
CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/teardown-convention.sh" --host=codex --dry-run
```

等用户明确确认后，才去掉 `--dry-run` 重新运行一次：

```bash
CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/teardown-convention.sh" --host=codex
```

只有用户明确要求零足迹模式（`.agent/state.json` 继续激活 hook）时才加 `--keep-state`。原样转述
结果；退出码 2 表示本项目没有启用过约定，什么都没做。

## phase and verify

两者均为只读：

```bash
CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/phase-guard.sh"
CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/verify-artifacts.sh"
```

激活信号是两个：`CLAUDE.md`／`AGENTS.md` 里独占一行的声明块，或含 `activeModule` 的
`.agent/state.json`。旧 remote-tracker state 若带 `activeModule` 仍按本地约定报告阶段；phase 不认证、
不读取其中的 Issue 映射，也不选择任务。那个文件里的 `tracker` 字段已退役，不再被读取，也不再抑制
任何提醒（`docs/retirements/state-tracker-field.md`）。

## cost report

只读的模块成本与返工报告（Claude 侧为 `/spec-guard:cost-report`）：

```bash
python3 -B "$ROOT/hooks/module_cost_report.py" --project "$PROJECT" <module-id> [更多模块] [--prices <价格文件>] [--json]
```

原样转述输出与「无法统计的部分」。退出码 2 是「无法归属」（todo.md 没有提交历史），不是用量为 0；金额只在用户给了
价格文件时出现，缺价标「未定价」，不替用户补价格；多模块对照只能看趋势，不下因果结论。

## tracker default

项目默认的事项后端与精确目标，存在 `.agent/tracker.json`。读取只读：

```bash
python3 -B "$ROOT/hooks/tracker_default.py" show --project "$PROJECT" --format json
```

`configured` 给出 `backend`（`local`／`github`／`gitlab`）与规范化目标；`absent` 表示没有默认值，
不是错误；`invalid`（诊断 `tracker-default-invalid`）表示文件不可用，**绝不当作 `absent`**，
照实报告要修哪一项，不要替用户猜一个默认值。

这个默认值**只预填预览**：没有显式后端与目标时用它，预览仍完整显示后端、精确目标与来源
（`explicit`／`project-default`／`project-default-target`），每次外部写入仍逐次授权。它不改变
已有事项的绑定（只影响此后新建的事项），不是激活信号，也不决定能力图、Proposal 基线或
Spec/Plan/todo 等共享事实。换平台要逐条显式交接，不自动迁移。

设置先预览，用户确认后才加 `--confirm`；只写 `.agent/tracker.json` 这一个文件，
不碰 `.agent/state.json`、`spec/`、`tasks/` 或 Git：

```bash
python3 -B "$ROOT/hooks/tracker_default.py" set --project "$PROJECT" \
  --backend github --host github.com --repo owner/name
python3 -B "$ROOT/hooks/tracker_default.py" set --project "$PROJECT" \
  --backend gitlab --host gitlab.example.com --project-id 17
python3 -B "$ROOT/hooks/tracker_default.py" set --project "$PROJECT" \
  --backend local --project-id 01XXXXXXXXXXXXXXXXXXXXXXXX
```

GitLab 用正整数 project id，与 Proposal 命令的 `--target` 形态一致。目标形状不合法时退出码 2
且不写文件。

## config

项目配置（Claude 侧为 `/spec-guard:config`），存在入库的 `.agent/config.json`。没有这个文件就是什么都没配，
行为不变。只读汇总，列出 `artifactLanguage`、`reviewCadence` 的生效值与来源，以及只在别处修改的
`dispatch`（约定块标记，用 setup 的 `--dispatch`／`--no-dispatch`）和 `trackerDefault`（上一节）：

```bash
python3 -B "$ROOT/hooks/project_config.py" show --project "$PROJECT"
```

`show` 末尾列出本机状态根目录（`~/.spec-guard` 或 `SPEC_GUARD_STATE_DIR`）以及仍在回退读取的旧位置，照实转述，不建议删除。

- `artifactLanguage`：语言标签（如 `zh-CN`、`en`）。新写的 Spec、Plan、todo 正文用它；结构关键字不变，已有产物不翻译。
- `reviewCadence`：`separate`（默认）或 `combined`，含义见共享检查点规则「评审节奏」。

设置或取消先预览，用户确认后才加 `--confirm`；只写 `.agent/config.json` 这一个文件并读回核对：

```bash
python3 -B "$ROOT/hooks/project_config.py" set --project "$PROJECT" --key artifactLanguage --value zh-CN
python3 -B "$ROOT/hooks/project_config.py" unset --project "$PROJECT" --key reviewCadence
```

取值不合法、键不认识或属于只读汇总的两项时，退出码 2 且不写文件。文件无效（JSON 坏、`version` 不是 1、
未知键、非法取值）时所有项按默认处理、`set`／`unset` 拒绝写入，照问题代码报告，不替用户猜值；`show` 提示
文件被 `.gitignore` 忽略时照实转述。

## module-suspend

挂起一个在等外部条件的已开工模块（Claude 侧为 `/spec-guard:module-suspend`）：在 `tasks/<id>/todo.md` 写一行
`<!-- spec-guard: suspended -->`。选当前模块时跳过它、保留 Build order 原位，阶段提示列出 `Suspended: <id>`；
它不算做到一半，随后 add-module 不需要 `--interrupt`；永不自动恢复，插件不记录原因或日期。默认只预览，用户确认后
才加 `--confirm`，只改这一行并读回：

```bash
python3 -B "$ROOT/hooks/module_suspend.py" --project "$PROJECT" --suspend <module-id>
python3 -B "$ROOT/hooks/module_suspend.py" --project "$PROJECT" --resume <module-id> --confirm
```

只能挂起有 Plan、todo 且至少一项未勾选的模块；拒绝时退出码 2 且不写文件。恢复只去掉标记、不改 `.agent/state.json`。
挂起确认后问用户要不要设提醒：时间和内容由用户说；宿主有持久的提醒或自动化能力且支持这个时间就用并读回，
否则请用户自己设。不从对话推断日期，插件不保存提醒，提醒失败不影响挂起。

## add-module

只在模块检查点使用：当前模块做到一半（`tasks/<id>/todo.md` 既有已勾选项又有未勾选项）时，脚本自己会拒绝并
说明先完成它（显式 `--interrupt` 插队除外，见下）。先读 `spec/CAPABILITY-MAP.md`，根据用户给的需求上下文提出 id（kebab-case、语义稳定）、单行
responsibility、depends-on（既有模块 id，逗号分隔，没有填 `—`）、anchor（`after:<既有模块 id>` 或 `end`），
每项都给一句对着能力图实际模块的理由。

插队（`--interrupt`）：当前模块做到一半、又在等外部条件而确需先做新模块时，才在预览命令后加 `--interrupt`，
显式跳到队前；其他模块同时做到一半（并行推进）不影响插队。预览会写明被暂停的模块及进度（已勾/总数）与插入后的
当前模块，必须让用户看过并明确确认。当前模块没有做到一半时 `--interrupt` 不改变任何行为。预览提示“插入后当前模块仍是
`<被暂停模块>`”时，提醒用户把 `.agent/state.json` 的 `activeModule` 改为新模块再开始构建（本命令不写 state.json）。
确认时同样带 `--interrupt --confirm`，会重新执行全部校验。

先预览（默认，只读）：

```bash
python3 -B "$ROOT/hooks/module-insert.py" --project "$PROJECT" \
  --id <id> --responsibility "<responsibility>" --depends-on <a,b|—> --anchor <after:<id>|end>
```

原样转述预览输出（新行、新 Build order、diff、当前模块会不会变、Proposal 同 id 提醒）；被拒绝时原样说明是哪一
条校验失败并停下。等用户明确确认后，才在同一条命令后加 `--confirm` 重新运行一次；用户改了 id、
responsibility、depends-on 或 anchor 中任何一项，都要先重新预览，不能对着旧预览直接确认。

写入只改 `spec/CAPABILITY-MAP.md`，不创建 Spec、不改 `tasks/`、`.agent/state.json` 或 Proposal 文件，不执行
Git 或远端操作。成功后原样转述写入结果与阶段提示；新模块若因此成为当前模块，阶段是 `NEEDS_SPEC`——下一步是写
并评审 `spec/<id>.md`，不是本命令的职责。需要留下经过评审的决定记录时改用 Proposal 流程；已接受的 Proposal 用下面的 `--proposal` 晋级。

从已接受的 Proposal 晋级（Issue 带 `proposal-stage:accepted` 且评审新鲜）：id、responsibility、depends-on、anchor
全部取自远端已发布的 Proposal，与 `--id`／`--responsibility`／`--depends-on`／`--anchor` 同时出现即报错；
必须给 `--platform` 与 `--target`。先预览（只读）：

```bash
python3 -B "$ROOT/hooks/module-insert.py" --project "$PROJECT" \
  --proposal <id> --platform <github|gitlab> --target <target>
```

原样转述输出（Proposal id、revision、baseCommit 与新行、Build order、diff）。命令内嵌同一预检；预检非 `ready`、
本地能力图与 baseCommit 上的不一致（提示 `git switch -c <晋级分支> <baseCommit>`）、锚点在 Build order 并行段中致使
写入结果无法被 proposal-promotion-proof 证明、当前模块做到一半（`--interrupt` 规则同上），
均原样说明并停下。`spec/<id>.md` 已存在不算拒绝：预览会提示插入后该模块阶段为 `NEEDS_PLAN`（视为已评审），
未评审先评审再 `--confirm`。等用户明确确认后才加 `--confirm` 重跑；只改 `spec/CAPABILITY-MAP.md`，不建分支、不提交、
不改 Issue 标签。正式 Spec 与 Plan 若已可评审，可与能力图放在同一个晋级 PR；
本命令仍只写能力图，且内嵌预检通常无需再单独运行。Spec 与 Plan 分别按阶段审阅，
不能因同 PR 跳过。合并后运行 proposal 一节的 `--prove`，`proved` 后按「收尾」一节预览并经授权关闭事项；只手工改标签不会关闭事项。

## documentation

文档基线、影响和验证仍是显式声明工具，不能扫描代码或 Git 历史来猜测状态：

```bash
python3 -B "$ROOT/hooks/documentation_baseline.py" --project "$PROJECT" --format json
python3 -B "$ROOT/hooks/documentation_impact.py" --project "$PROJECT" --module <module-id> --format json
python3 -B "$ROOT/hooks/documentation_verification.py" --project "$PROJECT" --module <module-id> --format json
```

只有用户确认后才修改基线、模块 Spec 或 Plan。

## proposal

Proposal 步骤均为只读：共享事实只来自远端默认分支快照与 GitHub/GitLab Proposal Issue，
不读取其他 worktree 或 `.agent/state.json`，也不写 Issue、标签、能力图、分支或任务。按需运行：

```bash
# 任何分支：单个 Proposal 的新鲜度与阶段
python3 -B "$ROOT/hooks/proposal_review.py" --project "$PROJECT" \
  --proposal-id <id> --platform <github|gitlab> --target <target>
# Issue 阶段标签 proposal-stage:accepted 加新鲜评审后：promotion 分支的基点预检；合并后加 --prove 做晋级证明
python3 -B "$ROOT/hooks/proposal_promotion_proof.py" --project "$PROJECT" \
  --proposal-id <id> --platform <github|gitlab> --target <target>
```

提交前先按 `references/proposal-contract.md` 写好草稿 `spec/proposals/<id>.md`，再补全基线与 revision 并校验（等价于 `/spec-guard:proposal-submit`）：

```bash
python3 -B "$ROOT/hooks/proposal_submit.py" --project "$PROJECT" \
  --draft spec/proposals/<id>.md --platform <github|gitlab>
```

先预览并原样转述 diff、revision、baseline commit 与下一步；用户明确确认后才加 `--confirm`（只重写草稿），
下一步只打印、不执行，本步骤不写 Issue、标签、分支或远端。

原样报告 JSON；除 `ready`、`proved` 外的状态都要停下并说明
`diagnostic`。`ready` 不创建分支，`proved` 不回写 Issue。

### 收尾（第四步的后半段）

证明通过**不等于**事项已收尾：标签还是 accepted，事项还开着。收尾是独立入口，只在同一次运行内
重新取得的 proof 为 `proved` 时才给出预览。预览只读：

```bash
python3 -B "$ROOT/hooks/proposal_closeout.py" preview --project "$PROJECT" \
  --proposal-id <id> --backend <local|github|gitlab> --target <target> \
  --output <preview.json>
```

`--target`：GitHub 是 `owner/name`（另给 `--host`），GitLab 是正整数 project id，Local 是 Epiq
`projectId`。不给 `--backend`／`--target` 时按 `.agent/tracker.json` 的项目默认值解析，预览标明
来源；解析不出即 `target-unselected`，**不要猜**。

原样转述预览，至少包含 backend、精确目标、`revision`、事项编号、当前阶段、`promotionCommit`
与**将写入的收尾记录全文**。取得用户针对**这一条 Proposal** 的明确同意后才写入：

```bash
python3 -B "$ROOT/hooks/proposal_closeout.py" close --project "$PROJECT" \
  --preview <preview.json> --confirm
```

`--confirm` 不是授权，只是执行已授权的预览。写入前所有复核都会重做；任何一项不符就停下，什么都不写。

只想知道哪些 Proposal 还欠收尾时，用只读扫描（参数与预览相同，但没有 `--proposal-id` 与 `--output`）：

```bash
python3 -B "$ROOT/hooks/proposal_closeout.py" scan --project "$PROJECT" \
  --backend <local|github|gitlab> --target <target>
```

`pending` 列出证明为 `proved` 而事项仍开着的 Proposal；对其中每一条仍要单独预览并取得授权。读不到的项是
`unknown`，不算待收尾也不算已关闭。

`verified` 才算完成。`already-closed` 是正常的重跑结果，不是失败。`partial` 与 `unknown`
**只做只读对账，绝不重发**——一次空查询不足以证明写入失败。`conflict` 需要人来判断，不要自行选一条。

关闭 Proposal 事项**不代表模块已交付**；绝不读模块 stage 或 todo 作为关闭判据。
只处理 `accepted` 与 `promoted`；`rejected`／`deferred` 的关闭是人的决定。完整契约见
`references/proposal-closeout.md`。

## history

历史验证与审计均为只读；导入或补正仍须单独确认：

```bash
/bin/bash "$ROOT/hooks/verify-history.sh" "$PROJECT"
python3 "$ROOT/hooks/capability-history.py" audit "$PROJECT/spec/CAPABILITY-HISTORY.json" "$PROJECT"
python3 "$ROOT/hooks/history-migration.py" preview "$PROJECT"
```

审计报告中的 `unknown` 不是失败时可以猜测补齐的值，不得从当前 `activeModule`、文件名或当前
时间推断责任、依赖、状态或历史时间。`correct` 是写操作，只有用户明确确认该次补正后才允许
调用；它会向账本追加 `history-correction` 记录，绝不重写 checkpoint，只会标记原值、修正值与
身份均精确匹配的 audit finding 为 `corrected`：

```bash
python3 "$ROOT/hooks/capability-history.py" correct --confirm \
  "$PROJECT/spec/CAPABILITY-HISTORY.json" <audit-report.json> <correction.json>
```

`<audit-report.json>` 与 `<correction.json>` 必须是用户审阅过的文件，补正须包含原值、修正值、
审计报告哈希、审计时间、`initiativeId`、`eventIndex`、对应的 `checkpointId`（无 checkpoint 时为
`null`）与 audit finding。没有 `--confirm`、审计报告哈希不匹配、证据矛盾，或把 `unknown` 升级
成 `completed` 的请求都会被拒绝，且不会写入。

历史快照与旧 state 是证据，不是恢复旧 tracker 工作流的授权。
