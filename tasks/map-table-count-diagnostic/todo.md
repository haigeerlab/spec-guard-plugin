# Todo: map-table-count-diagnostic

- [x] Task 1：模块表计数报错——共用报错函数列出表头行号（≤5 个，超出以「等」结尾）、0 张单独说明；单元回归新建并登记，phase-guard 与 verify-artifacts 两边各加两张表夹具 — 单元 7 例中 5 例先红（另 2 例锁定历史模式 0 张合法与 200 字上限），phase-guard 与 verify-artifacts 新断言先红；实现后三组全绿，3.9 通过，CI 同级别 ShellCheck 无告警，validate.sh 通过
- [ ] Task 2：自观测报告排除临时目录并报告排除数
- [ ] Checkpoint（gate）：模块评审；全量、3.9、ShellCheck、牙齿检查；Plan 获批即授权推送与开 PR，合并由用户进行，合并后通知发版会话并记入事项
