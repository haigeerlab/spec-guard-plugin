# Spec: phase-and-verification

## Objective

让启用了本地约定的项目在每次提交提示前看到当前阶段，并能按需只读核对已落地的产物是否符合约定。阶段注入与
产物校验都只报告事实和建议，不写文件、不改远端状态；无关项目必须静默。

登记：本模块是既有能力，由 2026-09-28 的一次性人工登记纳入能力图，未经 Proposal 流程
（`docs/decisions/2026-09-28-single-capability-map.md`）。能力图解析器 `capability_map.py`、`capability-map.py` 与
唯一的指纹算法 `spec-digest.py` 是 `proposal-contract` 模块的共享基础，本模块依赖它们。

## Contract

- **激活信号**：`CLAUDE.md` 或 `AGENTS.md` 中独占一行的受管声明块标记，或 `tracker` 为 `none`、`github`、`gitlab`
  的 `.agent/state.json`。正文里提到标记、或其他工具写的 `.agent/state.json` 都不激活。
- **项目根目录**：优先用宿主提供的 `CLAUDE_PROJECT_DIR`（Claude Code）；没有时（Codex）用 `git rev-parse --show-toplevel`，
  不在 git 仓库里才用当前目录。这样从仓库子目录启动的 Codex 会话也能看到根目录的激活信号。
- **阶段注入**（`hooks/phase-guard.sh`，经 `hooks.json` 的 UserPromptSubmit 注册，Claude 与 Codex 共用）：输出
  宿主接受的 JSON。无能力图为 `IDLE`，无模块 Spec 为 `MAP_ONLY`；否则由 `hooks/module_stage.py` 取 `activeModule` 或
  Build order 中第一个未完成的模块，按 Spec、`tasks/<id>/plan.md` 与 `tasks/<id>/todo.md` 的未勾选项报告
  `NEEDS_SPEC`、`NEEDS_PLAN`、`BUILDING` 或 `DONE`，并附全局计数；能力图无效为 `MAP_INVALID`，无法计算为
  `UNKNOWN`；`tracker` 为 `github`、`gitlab` 的旧状态文件按同样规则报告，不再有单独的迁移提示。已启用但缺 python3 时注入可
  诊断的 JSON，而不是静默成“未启用”。只依赖 `bash`、`git` 与 `python3`。
- **产物校验**（`hooks/verify-artifacts.sh`）：能力图通过与 Proposal 相同的严格解析；`spec/` 下每个模块 Spec 都是
  能力图中的模块；项目根目录没有 `SPEC*.md`。python3 不可用或解析器异常时报“未验证”，不判为违规。
- **共享检查点规则**：`references/workflow-checkpoints.md`，由 `/phase`、`/verify-artifacts` 与 `spec-guard-ops`
  引用，规定阶段交接、确认与停止时如何预告下一步。
- 入口：Claude `/spec-guard:phase`、`/spec-guard:verify-artifacts`；Codex `spec-guard-ops` 的 phase and verify 节。
  Claude Desktop MCPB 已于 2026-09-28 退役（`docs/retirements/claude-desktop-mcpb.md`）。

## Commands

```text
CLAUDE_PROJECT_DIR=<project> /bin/bash plugins/spec-guard/hooks/phase-guard.sh
CLAUDE_PROJECT_DIR=<project> /bin/bash plugins/spec-guard/hooks/verify-artifacts.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Project structure

```text
plugins/spec-guard/hooks/hooks.json            -> UserPromptSubmit 注册
plugins/spec-guard/hooks/phase-guard.sh        -> 激活判定与阶段注入
plugins/spec-guard/hooks/module_stage.py       -> 当前模块与各模块进度（只读）
plugins/spec-guard/hooks/verify-artifacts.sh   -> 只读产物校验
plugins/spec-guard/references/workflow-checkpoints.md -> 共享检查点规则
plugins/spec-guard/commands/{phase,verify-artifacts}.md
```

## Testing strategy

- `test-phase-guard.sh`：每条输出按 JSON 解析并核对事件名；覆盖无关项目、正文提及标记、CRLF、各阶段与缺 python3。
- `test-verify-artifacts.sh`：覆盖围栏与第二张表、无效能力图、缺 python3 与解析器异常。
- 两边若加入相同判据，必须一致并各有正反回归。
- 已知缺口：`hooks.json` 在插件根变量都缺失时回退执行项目内脚本（审计 P1-2）；Codex 下以当前目录而非 Git 根定位项目。

## Boundaries

- Always：无激活信号时静默退出；探测失败降级为“未验证”；输出宿主接受的 JSON；不写文件。
- Ask first：新增阶段或改变激活信号；新增共享判据。
- Never：用 `cmd | grep -q`；引入 `jq` 依赖；复制或内联指纹算法。

## Success criteria

- 启用约定的项目每轮收到正确阶段；无关项目静默；产物校验对环境故障报“未验证”，对真实违规给出 ❌ 与原因。
