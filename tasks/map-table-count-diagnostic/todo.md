# Todo: map-table-count-diagnostic

- [x] Task 1：模块表计数报错——共用报错函数列出表头行号（≤5 个，超出以「等」结尾）、0 张单独说明；单元回归新建并登记，phase-guard 与 verify-artifacts 两边各加两张表夹具 — 单元 7 例中 5 例先红（另 2 例锁定历史模式 0 张合法与 200 字上限），phase-guard 与 verify-artifacts 新断言先红；实现后三组全绿，3.9 通过，CI 同级别 ShellCheck 无告警，validate.sh 通过
- [x] Task 2：自观测报告排除临时目录并报告排除数 — 新增 2 例先红后绿；夹具项目原在系统临时目录下会被一并排除，改用不在临时目录且 realpath 不变的假路径（macOS 的 /home 会被 realpath 改写，故不用）；共 36 例，3.9 通过。本机重跑：排除 194 段，F-1203 由 114 降为 113（少的正是那个坏能力图测试夹具）
- [ ] Checkpoint（gate）：模块评审；全量、3.9、ShellCheck、牙齿检查；Plan 获批即授权推送与开 PR，合并由用户进行，合并后通知发版会话并记入事项
