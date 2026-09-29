---
name: spec-guard-ops
description: 在 Codex 中运行 Spec Guard 的本地约定、只读验证和文档／历史工具。
---

阶段交接、确认或停止前，读取并遵循[共享检查点规则](../../references/workflow-checkpoints.md)；按实际路径预告下一步，已有授权不重复询问。

本 skill 不接管远端 tracker。GitHub/GitLab 的旧任务投影、选择、绑定和交付流程已退役；
不得从 `.agent/state.json` 恢复它们，也不得创建或修改远端对象。

## 解析环境

从当前已启用的插件安装解析根目录，不猜测缓存版本：

```bash
CODEX_PLUGINS="$(codex plugin list --available --json 2>/dev/null || true)"
ROOT="$(printf '%s' "$CODEX_PLUGINS" | python3 -c '
import json, sys
try:
    plugins = json.load(sys.stdin).get("installed", [])
except (TypeError, ValueError):
    plugins = []
for plugin in plugins:
    if plugin.get("name") == "spec-guard" and plugin.get("installed") and plugin.get("enabled"):
        print(plugin["source"]["path"])
        break
')"
PROJECT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

`ROOT` 为空时停止并说明插件未安装或未启用。

## setup

只安装本地多模块目录约定；先用 `--dry-run` 预览。用户确认后才省略它：

```bash
CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/setup-convention.sh" local --host=codex --dry-run
```

已有声明块要升级时追加 `--replace`。遗留 `.agent/state.json` 是历史记录，不得用
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

旧 remote-tracker state 按本地约定报告阶段；phase 不认证、不读取其中的映射，也不选择任务。

## add-module

只在模块检查点使用：当前模块做到一半（`tasks/<id>/todo.md` 既有已勾选项又有未勾选项）时，脚本自己会拒绝并
说明先完成它。先读 `spec/CAPABILITY-MAP.md`，根据用户给的需求上下文提出 id（kebab-case、语义稳定）、单行
responsibility、depends-on（既有模块 id，逗号分隔，没有填 `—`）、anchor（`after:<既有模块 id>` 或 `end`），
每项都给一句对着能力图实际模块的理由。

插队（`--interrupt`）：当前模块做到一半、又在等外部条件而确需先做新模块时，才在预览命令后加 `--interrupt`，
显式跳到队前。只支持一层：已有另一个暂停中的模块时脚本会拒绝。预览会写明被暂停的模块及进度（已勾/总数）与插入后的
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
并评审 `spec/<id>.md`，不是本命令的职责。需要留下经过评审的决定记录时改用 Proposal 九步流程，而不是本命令。

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
# 仅主链模块交付／推进边界：候选列表；加 --proposal-id 与 --decision 记录人工裁决
python3 -B "$ROOT/hooks/proposal_mainline_review.py" --project "$PROJECT" \
  --platform <github|gitlab> --target <target> --authority-id <id> \
  --boundary <module-deliver|module-advance|module-interrupt> --current-module-id <module-id>
# 人工写入 accepted 后：promotion 分支的基点预检；合并后加 --prove 做晋级证明
python3 -B "$ROOT/hooks/proposal_promotion_proof.py" --project "$PROJECT" \
  --proposal-id <id> --platform <github|gitlab> --target <target>
```

原样报告 JSON；除 `candidate-list`、`accepted-candidate`、`ready`、`proved` 外的状态都要停下并说明
`diagnostic`。`accepted-candidate` 不是 Issue 阶段，`ready` 不创建分支，`proved` 不回写 Issue。

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
