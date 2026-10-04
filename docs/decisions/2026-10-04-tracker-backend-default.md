# 决策：项目级默认事项后端只预填，不授权

状态：已接受（2026-10-04，用户明确决定）。

修订：[`spec/hosted-ticket-workflow.md`](../../spec/hosted-ticket-workflow.md)「项目结构与命令边界」一节
「不新增项目级 Tracker 配置」一条；该 Spec 其余条款继续有效。

## 背景

每个托管事项入口都要逐次显式传 `--platform`／`--host`／`--target`／`--visibility`，Proposal 命令要逐次传
`--platform`／`--target`。这是有意的：`hosted-ticket-workflow` 当时判断，一个项目级 Tracker 配置会成为第二个
事实源，让「代码仓库的 Git remote 决定事项目标」这类错误推断重新成为可能。

实际使用暴露了它的代价：这个选择在很长时间里是不变的。代码在 GitHub 上就一直用 GitHub，只有平台不可用时才
需要紧急切到本地。为一个几个月不变的事实逐次打四个参数，是纯粹的摩擦。

同时 `.agent/state.json` 的 `tracker` 字段正在退役（见
[退役说明](../retirements/state-tracker-field.md)）。只删不换，用户就只能永远手打参数；只换不删，那个字段
的三重职责冲突仍在。两件事是同一件事的两面。

## 决策

1. **区分「默认值」与「权威」。** 原先的否决过宽，把两者混为一谈：

   | | 默认值 | 权威 |
   | --- | --- | --- |
   | 作用 | 省去重复输入 | 代码据此自动决定并执行 |
   | 预览 | 仍完整展示后端与精确目标，并注明来源 | 可能跳过或简化 |
   | 写入 | 仍逐次授权 | 可能静默写 |
   | 对已有事项 | 零影响 | 可能改变归属 |

   被否决的始终是「权威」。「默认值」应当有。

2. **新增 `.agent/tracker.json`**，提交进仓库，单一用途：`version`、`defaultBackend`
   （`local`／`github`／`gitlab`）、`defaultTarget`。入口 `/spec-guard:tracker-default`
   （Codex：`spec-guard-ops` 的 tracker default 一节）。

3. **五条不变量**（写进 [`spec/tracker-backend-default.md`](../../spec/tracker-backend-default.md)，
   每条都有正反回归）：

   - **只预填，不决定。** 只在没有显式后端与目标时填进预览；预览必须打印来源
     （`explicit`／`project-default`／`project-default-target`）。
   - **不改变授权。** 每次外部写入仍是一次预览、一次授权；默认值不省掉任何一次确认。
   - **只对新事项生效。** 已有事项的绑定由它创建时的后端与目标固定；改默认值不移动、不复制、
     不关闭任何已有事项。
   - **冲突即停。** 已记录的绑定与当前默认不同时报 `conflict`，不静默切换。
   - **不是激活信号。** 这个文件的有无与阶段注入无关。

4. **非法绝不降级为缺席。** 文档不可解析、版本不是 1、后端未知、目标形状不符、有多余字段，一律 `invalid`
   并带 `tracker-default-invalid`，绝不读成 `absent`——否则一个拼写错误会被当成「没配过」而静默回到逐次手填。

5. **不决定共享事实。** 能力图结构、Proposal 正文与 baseline、晋级提交、Spec／Plan／todo 的位置与完成判据、
   Git 历史、CI 与发布，全都只来自远端默认分支与本地文件，与后端无关。

## 为什么 `hosted-ticket-workflow` 的那一条可以修订

它要防的是「Git remote 或旧 `.agent/state.json` 决定事项目标」。本决策没有打开这个口子：

- 目标仍然只能来自显式参数或这个**单一用途**文件，Git remote 与 `state.json` 都不参与；
- 该文件不参与任何写入决定，只参与预览的预填；
- 「后续批次改选目标不迁移已有事项」这条原则被第 3 条的第三、四款完整继承。

被修订的只是「配置文件一律不要」这个过宽的手段，不是它要保护的性质。

## 影响

- 新装项目的 `.agent/state.json` 变为 `{"activeModule":""}`；激活信号改判 `activeModule`，数量不变。
- `hosted-ticket-workflow` 的既有入口在本次不改变其必填参数；第一个程序化消费者是后续模块
  `proposal-closeout`。
- 不新增 phase 状态、后台监听、双向同步或自动迁移。
- 跨后端迁移仍走 `local-ticket-portability` 的显式逐条交接，本决策不提供新的迁移路径。
