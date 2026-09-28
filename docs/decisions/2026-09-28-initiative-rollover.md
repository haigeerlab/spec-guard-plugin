# Spec: 能力图交接——结束 Proposal initiative，登记本机协作与事项

状态：已被取代（2026-09-28）。同日改为全插件一张能力图，见
[`2026-09-28-single-capability-map.md`](2026-09-28-single-capability-map.md)。本文件保留原方案作为记录。

## 背景

本仓库的 `spec/CAPABILITY-MAP.md` 只描述**当前 initiative**；每个 initiative 完成后，其能力图、模块 Spec 与
Plan 按 `capability-history.py` 的格式复制到 `spec/history/`、`tasks/history/`，并在
`spec/CAPABILITY-HISTORY.json` 记录 `created` 与 `completed` 事件。已有 12 个 initiative 按此归档。

2026-09-27 的项目审计发现三个治理问题：

1. 当前能力图是 “Candidate Proposal Pool” initiative 的图，目标只写 Proposal，却收录了与它无关的
   `collaboration-messaging`。
2. 本地事项账本已随 v0.19 交付，但只有未被接受的 Proposal（`spec/proposals/local-ticket-ledger.md`），
   不在任何能力图中。
3. 协作的 native 传输在协作 Proposal 被接受（attestation 覆盖 XATS 范围）之后才加入，未修订 Proposal。

审计把“文档治理、能力历史、本地约定没有当前 Spec”也列为问题；复核后确认这是按设计归档，不在本次范围。

## 已确认的决策（2026-09-28）

- **保持按 initiative 分图。** 不改为全产品一张图；工具只认一份 `spec/CAPABILITY-MAP.md`，不改工具。
- **协作与账本一次性人工登记进新能力图。** 它们是已交付的既有能力，不是新需求；能力图写明“既有能力登记，
  未经 Proposal 流程”。此后新需求仍走 Proposal。
- **账本保留为可选能力。** 定位改为“可选的本机事项账本，不替代、不同步 GitHub/GitLab Issue”。

## Objective

1. 把已实现的 Proposal initiative 归档为 `completed`，使历史账本记录它的能力图、7 个模块 Spec 与 Plan。
2. 以新 initiative 替换当前能力图，登记 `collaboration-messaging`（含实验性 native 传输）与
   `local-ticket-ledger`，两者都有当前模块 Spec 与 Plan。
3. 使 README、`docs/design.md`、`AGENTS.md` 的定位与现状一致。

非目标：不补写已归档 initiative 的 Spec；不改写已发布的 Proposal、acceptance attestation 或 Proposal 代码；
不伪造 accepted Issue、attestation 或“经 Proposal 流程接受”的记录。

## 步骤

1. **归档 Proposal initiative**（initiative id `proposal-lifecycle`，checkpoint `20260928T023846Z-0001`）。
   - 复制 `spec/CAPABILITY-MAP.md` 与 7 个 `spec/proposal-*.md` 模块 Spec 到
     `spec/history/proposal-lifecycle/<checkpoint>/`；复制 `tasks/proposal-*/plan.md` 到
     `tasks/history/proposal-lifecycle/<checkpoint>/<module>/plan.md`。
   - 写 `.agent/history/proposal-lifecycle/<checkpoint>/state.json`（见“未决问题 1”）。
   - 用 `capability-history.py ensure` 登记 initiative，再用 `append` 追加 `completed` 事件；各模块状态为
     `unknown`（见“已决问题 3”）。事件时间写真实 UTC 时间，不再用 `now`。
   - 从 `spec/`、`tasks/` 删除原模块 Spec 与 Plan。代码、命令与文档都不引用这些路径（已核实）。
     `spec/proposals/`、`spec/proposal-acceptances/`、`spec/proposal-mainline-policy.json` 是 Proposal
     的运行数据，保留原位。
2. **新能力图**（initiative id `local-collaboration`）。
   - `spec/CAPABILITY-MAP.md`：目标为“同一台 Mac 上 Claude Code 与 Codex 会话的可选协作邮箱与本地事项账本”；
     模块 `collaboration-messaging`（—）与 `local-ticket-ledger`（—），Build order
     `collaboration-messaging → local-ticket-ledger`；评审记录注明“既有能力登记，未经 Proposal 流程，
     2026-09-28 由用户决定”。
   - `spec/collaboration-messaging.md` 保留，补一句范围说明：已接受的 Proposal 覆盖 XATS；native 为登记时
     一并纳入的实验性范围。
   - 新写 `spec/local-ticket-ledger.md`：依据已发布 Proposal、`references/local-ticket-ledger-runtime.md`
     与现有实现（固定 `epiq@1.11.0`、显式安装与初始化、高风险工具门控、临时目录安装）。
   - 两个模块的 Plan 已存在于 `tasks/<module-id>/plan.md`，沿用。
   - 在历史账本登记 `local-collaboration` 的 `created` 事件与其初始 checkpoint，使 `active` 返回它。
3. **定位文档**：README 开头与 `docs/design.md` 写入可选协作与账本；把“不自动化 Ticket”改为“不替代、不同步
   GitHub/GitLab Issue”；删除 `AGENTS.md` 中“退役迁移正在进行”的过时表述。
4. **Proposal 池的影响**（只记录，不修改）：两份已发布 Proposal 的基线指向旧能力图，换图后 review 会报
   `stale`（目标漂移或模块已存在）。它们已是历史记录，保留文件。

## Commands

```bash
python3 plugins/spec-guard/hooks/capability-history.py ensure spec/CAPABILITY-HISTORY.json <initiative.json>
python3 plugins/spec-guard/hooks/capability-history.py append spec/CAPABILITY-HISTORY.json proposal-lifecycle <event.json>
python3 plugins/spec-guard/hooks/capability-history.py verify spec/CAPABILITY-HISTORY.json .
python3 plugins/spec-guard/hooks/capability-history.py active spec/CAPABILITY-HISTORY.json
/bin/bash plugins/spec-guard/hooks/verify-history.sh "$PWD"
CLAUDE_PROJECT_DIR="$PWD" /bin/bash plugins/spec-guard/hooks/verify-artifacts.sh
/bin/bash scripts/validate.sh
```

## Success criteria

- `capability-history.py verify` 与 `verify-history.sh` 通过；`active` 返回 `local-collaboration`。
- `proposal-lifecycle` 的 checkpoint 中每个文件的 sha256 与归档内容一致；归档前后 7 个 Spec 与 Plan 的内容
  逐字相同。
- `verify-artifacts.sh`：能力图通过严格解析，`spec/` 下只有两个模块 Spec 且都在图中，0 失败。
- phase 注入为 `SPECED`、`Module specs: 2`。
- `validate.sh` 通过；Proposal 相关测试不受影响。

## Boundaries

- Always：使用既有 capability-history 格式与校验；归档是逐字复制并记录 sha256，不改写旧内容。
- Ask first：删除或改写已发布 Proposal、attestation、mainline policy；修改任何 Proposal 代码或历史工具。
- Never：伪造 accepted Issue、attestation 或 Proposal 流程记录；把一次性登记描述为经 Proposal 接受。

## 已决问题（2026-09-28 批准时采纳）

1. **checkpoint 的 state 快照。** 两个 checkpoint 都写 `{}`：归档时本仓库不存在 `.agent/state.json`，
   不虚构 `activeModule`。
2. **initiative id。** 归档用 `proposal-lifecycle`，新图用 `local-collaboration`。
3. **模块状态。** 批准时采纳的是“记为 `completed`”；实施时发现与仓库既有规则冲突：`capability-history.py
   audit` 认定 checkpoint 与 Issue 身份不能证明模块状态，要求保留 `unknown`，已有 12 个 initiative 也全是
   `unknown`。因此两个新条目的全部模块都记为 `unknown`。`proposal-boundary-guidance` 已实现但没有接入任何
   调用方（审计 P7），记在本文件而不是状态字段里。
4. **事件时间。** 写真实 UTC 时间，而不是旧条目的 `now`。审计对任何没有外部证据的时间都报
   `timestamp-unverified`，新条目因此新增 3 条未决时间发现，与既有条目一致；需要时按 `history-integrity`
   的更正流程处理。
