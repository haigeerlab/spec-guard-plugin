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

## phase and verify

两者均为只读：

```bash
CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/phase-guard.sh"
CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$ROOT/hooks/verify-artifacts.sh"
```

旧 remote-tracker state 按本地约定报告阶段；phase 不认证、不读取其中的映射，也不选择任务。

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
  --boundary <module-deliver|module-advance> --current-module-id <module-id>
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

历史快照与旧 state 是证据，不是恢复旧 tracker 工作流的授权。
