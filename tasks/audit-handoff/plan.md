# Plan: audit-handoff

依据 [`spec/audit-handoff.md`](../../spec/audit-handoff.md) 与 Local 事项《审查批次收束与缺陷处理交接》（8C22GJK）。只补审查到整改的交接约定，复用 agent-skills 与 Spec Guard 现有入口。

## 决定与顺序

- 单一能力模块 `audit-handoff` 追加到能力图末尾，依赖 `local-convention`、`phase-and-verification`、`local-ticket-ledger`；不改其他模块或 Proposal。
- 共享行为写在现有 `workflow-checkpoints.md`，两端模板仅放发现入口，`ticket` skill 负责 Local 查重/写回。使用者文档说明审查完成与修复完成的区别，以及外部 Issue 不属当前插件原生写入。
- 多轮项目审查使用有稳定发现编号的报告；不增加状态机、自动 Issue 创建或 phase hook 分支。先以契约回归锁定规则，再做真实宿主场景测试。静态测试只能证明规则可达。

## 任务与检查点

1. **守住红态：** 在 `test_workflow_checkpoints.py` 写出双宿主发现入口和共享规则边界的契约断言；冻结后“继续”、P0/未知/重复发现等行为另外通过场景审阅。先运行并记录当前失败。验收：现有规则缺口会使测试失败。
2. **补共享交接：** 在 `workflow-checkpoints.md` 定义有限批次、报告字段、结论与优先级区分、审查收束、P0 中断、下一步与停止条件。两端项目约定模板只增加一条指向共享契约的项目审查规则。验收：审查阶段与“继续”语义对任意 Tracker 均明确，不改变现有 PR 对账或 Proposal。
3. **接入事项与用户文档：** `ticket` skill 写明审查批次中的 Local 查重/复用和失败状态；`docs/workflow.md` 给出从 agent-skills review、debugging、planning/TDD 到 Local 事项与 PR 关闭的路径。外部 Issue 只形成交接清单，当前插件不调用远端写入。验收：待调查项、无发现、重复项、Local+GitHub、未启用账本、只读审查均有准确结果。
4. **验证与真实宿主：** 跑聚焦契约测试、三条仓库最低验证和退役 bridge 扫描。用隔离消费者项目与候选约定，在真实 Codex/Claude 可用宿主执行已分级发现后重复“继续”的场景；记录成功、失败或无法验证的准确边界。验收：至少一个真实宿主证明不会无故重开深挖；另一个宿主若不可用必须标未验证，不能冒充通过。

## 验证命令

```bash
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 -B plugins/spec-guard/hooks/test_ticket_entry.py
/bin/bash plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
git diff --check
```

## 风险与回退

- **提示词规则不等于宿主行为。** 静态回归与真实宿主交互分开报告；若宿主仍继续深挖，按实测调整发现入口或缩小能力声明，不声称文本本身提供硬闸。
- **报告泄露。** 消费者报告不自动发布；项目级报告写入前检查敏感内容，Local 私有编号与标题不外传。对远端 Issue 仅准备可审阅草稿。
- **已有状态误读。** 旧 tracker 字段、Git remote、`phase DONE` 均不决定事项来源或审查完成。保持 phase hook 与能力图既有状态机不变。
- **回退。** 本分支撤销模块行、Spec/Plan 与对应契约改动即可；不触及 Local 账本之外的用户状态或远端对象。

## 完成检查点

能力图预览经确认后插入；所有任务及测试通过，真实宿主场景有可检查记录，再提交分支。PR、合并及 Local 事项关闭沿现有交付检查点分别处理。

## 验证记录（2026-10-02）

- 新增契约测试先红（4 个失败），补约定后 `test_workflow_checkpoints.py` 6/6、`test_ticket_entry.py` 9/9；退役 bridge 扫描通过。
- `scripts/validate.sh` 最终通过；`test-phase-guard.sh` 80 例、`test-verify-artifacts.sh` 18 例通过，`git diff --check` 通过。
- 临时合成消费者项目直接注入候选约定，提供已冻结的 B-1 批次（2/2 范围，已确认 P1、待调查 P2、重复项），真实 `codex exec` 连续两轮收到“继续”。两轮均维持 2/2，不泛扫、不建单；优先报告查重未知与待入账，再停在所需证据处。
- 此场景验证候选指令在 Codex 中的行为；未验证候选插件的安装/发现链路，也未实测 Claude 宿主。静态测试覆盖模板发现链路，无法保证宿主在所有审查情境都遵守提示词规则。
