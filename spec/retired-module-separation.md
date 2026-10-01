# Spec: retired-module-separation

## Objective

让 `spec/CAPABILITY-MAP.md` 只列现行模块，同时保留已退役 Proposal 主链裁决与边界提醒模块的原始 Spec、Plan 和既有历史快照，供审计追溯。用户查看能力图、阶段提示或产物校验时，不再把已删除的命令和 hook 误读为现行能力。

登记：2026-10-02，基于本地 Bug `SH62J51` 的预览，经用户确认由 `module-insert.py --confirm` 追加到唯一能力图。

## Assumptions and boundary

- 退役对象仅为 `proposal-mainline-review` 与 `proposal-boundary-guidance`。`proposal-promotion-proof` 等仍有现行入口的模块保留。
- `spec/proposal-label-acceptance.md` 的 C5 曾要求将两行及其 Spec/Plan 留在原处；本模块是对此项历史保留方式的后续迁移决定。旧 Spec 保持原文，不回写历史结论。
- Proposal 的共享事实仍只来自远端默认分支固定快照。此次本地能力图变更在合并前不作为共享事实；已有快照、接受记录和 Proposal Issue 均不改写。
- 不恢复 mainline 命令、策略读取、验收记录要求或 legacy tracker bridge；不创建或修改远端 Issue、标签或 Proposal。

## Contract

### R1 当前能力图

- 从唯一模块表和 Build order 同时移除两个退役 id；不能只删行或只删顺序。
- 现行依赖不得再指向退役 id：`proposal-promotion-proof` 依赖 `proposal-review`；`audit-remediation` 与 `module-interrupt` 去掉 `proposal-mainline-review` 依赖，其余依赖顺序保持不变。
- `proposal-promotion-proof` 的职责描述改为当前按 Issue 标签与新鲜度作预检、按首个纳入提交证明的行为，不再声称需要主链验收记录或 Spec/Plan 随晋级提交落地。
- 除上述行、Build order 与必要的评审说明外，不改变其他现行模块的 id、职责、依赖或相对顺序。

### R2 历史材料

- 将两份原始 Spec 与 Plan 逐字节归档到 `docs/retirements/<module-id>/spec.md` 与 `plan.md`；使用 Git rename 保留可追溯历史，不在归档副本内改写旧设计。
- 更新 `docs/retirements/proposal-mainline-review.md`，明确归档路径及“只作历史证据”的含义。现有 `spec/history/` 快照、`tasks/history/`、`spec/CAPABILITY-HISTORY.json`、验收记录和发布证据保持原样。
- 现行 `spec/` 不留下图外模块 Spec；现行 `tasks/` 不留下这两个退役模块的 Plan。历史文档中引用旧路径的文字作为历史证据保留，由退役说明提供新入口。

### R3 消费者与错误路径

- 当前能力图经 `capability_map.parse_map` 严格解析，所有依赖存在且拓扑顺序正确。
- `verify-artifacts.sh` 不报告图外模块 Spec；`phase-guard.sh` 的模块总数和 DONE 判定只基于现行图。
- 本次迁移的验收命令须在任一归档文件缺失、依赖仍指向退役 id、或 Build order 与模块表不一致时失败或给出明确诊断；不把一次性归档核对说成通用校验器的持续承诺。
- 本次不改变解析器、阶段机或产物校验器的通用规则；若现有验证暴露出新问题，先记录证据再决定是否扩展范围。

## Verification

1. 比较四份归档文件与迁移前 `HEAD` 对应文件的 Git blob，确认内容逐字节相同。
2. 对能力图运行严格解析；断言现行模块集合不含两退役 id，现行依赖不含它们，Build order 与模块表一致。
3. 运行 `plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/hooks/test-phase-guard.sh` 和完整 `scripts/validate.sh`。
4. 只读核对远端默认分支的 Proposal 来源与本地提交边界；不把工作树内容当成已发布共享事实。

## Delivery

先提供本 Spec 供评审。评审通过后，在 `tasks/retired-module-separation/plan.md` 写正式实施顺序与回退路径，再按最小切片迁移并验证。此次改动不发布插件、不合并 PR、不关闭本地 Bug；这些动作需要各自的交付检查点。
