# Todo: proposal-closeout

- [x] Task 1：纯状态机 `closeout_decision`（签名锁死不含 project/provider）+ tracker 读取加 `local` 与 `closed`（缺字段即 unknown）+ validate.sh 登记新测试
- [x] Task 2：github 与 gitlab 适配器——七个方法、分页不完整即 unknown、4xx 即 rejected、系统 note 不算证据、断言写入未被触发
- [ ] Task 3：local 适配器——经 mcp_tool_call、`tag_remove` 先读回 tagId 否则 unknown、runtime/worktree 未就绪即 unknown、断言未调用 epiq_sync、隔离账本可选验收
- [ ] Task 4：预览——同一次运行内重跑 prove，只有 proved 才出预览；默认值解析与来源标注；`proposal_promotion_proof.py` 零改动并加断言锁死
- [ ] Task 5：复核、写入、journal 与幂等——八项复核全部重做、每步先查重后写、读回三项、两次 confirm 第二次 already-closed、响应丢失只对账不重发
- [ ] Task 6：补 Local 链路——`proposal_submit` 与 `add-module --proposal` 的 `--platform local`；baseline/revision 与 github 路径逐字相同
- [ ] Task 7：入口与文档——命令、Codex skill、parity、`references/proposal-closeout.md`、四步表第 4 步扩写、CHANGELOG；自查文档不描述未实现的行为
- [ ] Checkpoint：两种 Python 下全部回归 + 隔离账本端到端 + 本仓库零差异 + 无 todo 模块不影响收尾判据 + 代码与安全审查（先复现再修）+ 开 PR 等 CI，不自行合并
