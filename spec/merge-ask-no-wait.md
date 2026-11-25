# Spec: merge-ask-no-wait

<!-- spec-guard: review approved 9b8ee2f3f650 -->

## Objective

《插件开发规范》v1.7 在 F3 上补了三件事：最终验收一结束就问合并，不等 CI；开宿主自带的 PR 监控；会话不许自己等 CI。
merge-flow-f3（#488，0.95.0 未发版）只做到 v1.5.1：共享规则写了「用户说合并后怎么合、合后核实」，但没写什么时候问、问完以后 CI 由谁盯。
实际用下来（本仓库 #489、#488、#490）：验收和合并分两轮问多一个来回；会话想等 CI 时只能自己轮询，而桌面版系统规则禁止这样做。

本模块把 v1.7 写进随插件下发的共享规则与最终验收停点，同步本仓库发版流程文档。

给谁用：所有用 spec-guard 的项目里做最终验收、决定合并的用户，以及执行合并的会话。

对外接口与用法草案一致吗：不改命令、配置键、`/map --json` 字段，不动用法草案的里程碑；只改规则文字。

登记：ecosystem-lead #22723（规范 v1.7）、#22730（第 1 步的本意）；账本 EVQX96F。需求确认：2026-11-25 用户在本会话看完需求复述后回「说全了」；Spec 交审后回「插入并批准；Q1 A」。

## Assumptions

1. **什么时候问合并**：最终验收的交审消息里就问合并，不等 CI 跑完、不等 PR 变 CLEAN；合成一问（Q1 A）：问题是「验收通过、合并吗？」，
   按钮「验收通过并合并」「只验收，先不合」；选后者时，之后照旧再问一次合并。
   验收没过就不问合并。
2. **用户说「合并」后怎么做**：沿用 merge-flow-f3 已写的一句，不改：先看 PR 状态，必需检查已全部通过直接合并（GitHub `gh pr merge`），
   没跑完用平台自动合并（`gh pr merge --auto`），CI 不过就不合。
3. **宿主的 PR 监控**：开 PR 后，宿主有 PR 监控功能（例如 Claude 桌面版的 Auto-fix）时，提议打开，用户批准才开；
   宿主没有这个功能就跳过，不用自己写的等待去代替。规则只写这一句，不写某个宿主的工具名或开关名。
4. **会话不自己等 CI**：不用后台 `--watch`、定时任务或唤醒、循环，也不反复查 `gh pr checks`。CI 结果靠用户叫或宿主通知；
   要等时告诉用户「跑完叫我」并结束本轮。
5. **下次被叫醒或用户回来时**：先核实已合并（PR 是 merged、主干指向合并提交），记下合并提交再告诉用户；没合并就照实说状态。
   这和 merge-flow-f3 的「合并后核实」是同一件事，这里只补上时机。
6. **改哪里**：
   - 共享规则 `plugins/spec-guard/references/workflow-checkpoints.md`「Plan 检查点分级」里合并那一段（merge-flow-f3 写的那句后面）补上假设 1、3、4、5；
   - 最终验收停点 `plugins/spec-guard/references/node-rules.md`「## 最终验收」：「批了会怎样」一条加上按 Q1 的合并问法；
   - `docs/release-process.md` 第 4 条加一句「不自己等 CI，等用户叫或宿主通知」；2026-10-13 的长期授权原样保留；
   - 回归：`test_workflow_checkpoints.py` 锁新短语；`test_stop_rules.py` 锁最终验收一节里的合并问法；
   - `CHANGELOG.md`「未发布」加一条。0.95.0 还没发版，本模块并进 0.95.0，不再升版本号。
7. **不变**：协调会话本地合并的唯一例外（三个条件）、接管档位 `merge: auto`、「任何 Plan 都不能代替用户这句话」。
8. **不做**：改 hub、autopilot、module-crew 的代码；S109 升钉；给某个宿主写专用的监控脚本。

## Contract

- **C1** 共享规则「Plan 检查点分级」合并段（假设 1、3、4、5）。
- **C2** `node-rules.md`「## 最终验收」的合并问法（假设 1、Q1）。
- **C3** `docs/release-process.md` 第 4 条（假设 6）。
- **C4** 两个回归文件与 CHANGELOG 一条（假设 6）。

## Acceptance criteria

- **AC1** 共享规则合并段写明：验收消息里就问合并、不等 CI；宿主有 PR 监控时提议、用户批准才开、没有就跳过；不自己等 CI（列出 `--watch`、定时、循环三种）；
  下次被叫醒或用户回来时先核实已合并再告诉用户。merge-flow-f3 那句原样还在。
- **AC2** `node-rules.md`「## 最终验收」按 Q1 写明合并怎么问；阶段提示在最终 gate 注入的停点规则里能看到这一条。
- **AC3** `docs/release-process.md` 第 4 条加上不自己等 CI 的一句，长期授权原文不变。
- **AC4** 回归锁住 AC1、AC2 的短语；删掉其中任一短语，回归变红（手工变异后还原）。
- **AC5** 本机 `validate.sh`、phase-guard、verify-artifacts 全绿；PR 上 `CI required` 通过。
- **AC6** 本模块自己的 PR 按新规则走一遍：验收消息里问合并；会话不自己等 CI；合并后被叫醒时核实再说。过程记进 todo。

## Boundaries

- **会做**：C1～C4；推送、开 PR；按新规则问合并。
- **先问再做**：合并；打开宿主的 PR 监控；任何超出假设 1～7 的改动。
- **不做**：假设 8 列出的事。

## 并行边界

- 独占：`spec/merge-ask-no-wait.md`、`tasks/merge-ask-no-wait/`、`plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/hooks/test_stop_rules.py`、`docs/release-process.md`、`CHANGELOG.md`
- 公共：无

## Open questions

- **Q1 验收和合并怎么问？**（账本 EVQX96F 写明由你在 Spec 里定；2026-11-25 用户选 A）
  - A（推荐）：合成一问。最终验收消息的问题是「验收通过、合并吗？」，按钮「验收通过并合并」「只验收，先不合」。
    代价：一次回答里有两件事；选了第二个按钮就和今天一样，要再问一次合并。
  - B：分开问，但在同一轮里。先问验收，你回「验收通过」后，同一轮里勾选、提交、推送，接着就问合并。
    代价：每个模块固定多一个来回（这次 #490 就是这样）。

## 文档建议

只改规则和本仓库发版流程文档。README 讲合并的那句（merge-flow-f3 改过）说的是「合并由用户在对话里决定」，仍然成立，不用改。项目没有文档基线。
