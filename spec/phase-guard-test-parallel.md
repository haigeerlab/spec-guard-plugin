# Spec: phase-guard-test-parallel

## Objective

`plugins/spec-guard/hooks/test-phase-guard.sh` 是 984 行的串行脚本，190 个用例。verify-and-commit 全档里它与 validate
同时跑，却比 validate 还慢（2026-10-09 全档提交：phase-guard 105 秒、validate 82 秒），成了全档提交的瓶颈；CI 里它约
44 秒，也是最慢的一步。本模块把它按互不共享夹具的段落分组并行跑，用例与断言一条不改、被测 hook 不改。来源：
validate-parallel-files 收尾列出的候选，用户 2026-10-09 选方向 A（只改测试组织；合并 hook 内 python3 进程的方向 B 另作候选）。

读者：本仓库维护者。

## 测出来的现状（2026-10-09，本机 8 核）

- 整套 56.2 秒（user 33.5、sys 15.4），负载约 11；按输出时间戳，每 10 个用例约 3 秒，分布均匀。
- 每个用例至少调一次 `phase-guard.sh`（约 0.28 秒，内含 4 个 python3 进程），这是主要耗时。
- 依赖核对（脚本扫描顶层变量、函数与 `$WORK/<目录>` 的定义行与最后使用行）：
  - 前半段只有 383、444 两处切点没有依赖跨过（只差 `$WORK/empty`，851 行还在用）；
  - 后半段（444 行起）被一组辅助函数串在一起：`run_from`、`run_input`、`context_of`、`transcript`、`mid_line`、
    `sized_boundary`、`codex_rollout` 等，以及夹具 `git_project`、`unrelated`、`plain`；
  - 前半段跨段的夹具：`stages`（123–252 行）、`local_project`／`other-state`／`crlf`／`active-pointer`（到 320 行）、
    `paused`（255–342 行）、`notodo`（323–381 行）。

## Assumptions

用户 2026-10-09 批准：

1. **入口不变、单文件**：`test-phase-guard.sh` 仍是唯一入口（CI、verify-and-commit、validate、文档都调它）。文件分三块：
   公共部分（现有的 `fail`／`run`／`injects` 等，加上挪上来的纯函数定义）、若干段函数 `part_1() { … }`（原代码按原顺序
   搬进去，不改用例与断言）、末尾的调度。不拆成多个文件。
2. **分段**：4–6 段，按用例数大致均分（每段 30–50 例），切点选在已有的段落注释处。
   - 跨段用到的**纯函数定义**挪到公共部分（只移动，不改内容）；
   - 跨段用到的**夹具**（上面列的那些）在用到它的段里按原来的建法再建一份：只复制建夹具的那几行，不复制断言；
     （2026-10-09 审查后改：几份副本容易改漏，建法改为集中在公共部分的 `build_fixture <名字>…` 里，原段落与要重建的段
     都调用它，用户选此方案；用例与断言仍不改。）
   - 实现时用脚本核对：每段只用到公共部分与本段自己定义的名字。
3. **隔离**：每段在自己的子 shell 里跑，`WORK` 指向 `$WORK/part-N`，互不共享可写目录；顶层的 EXIT trap 统一清理。
4. **输出与判定**：
   - 每段的标准输出与错误输出写进一个临时文件，按段的顺序打印：前面的段都打印完、本段也结束，就立即打印；
   - 每段把自己的通过数写进文件，汇总后最后一行仍是 `phase-guard regression passed (N cases)`，N 与改前相同（190）；
   - 任一段退出非零：照样打印它的输出（含 `❌` 那行），末尾报出第几段失败，整体退出 1；其余段照常跑完、照常打印。
5. **串行开关**：默认所有段同时跑；`SG_VALIDATE_JOBS=1`（validate 已有的开关）时逐段串行，供排查用。
6. **证明**（写进 todo）：
   - 改前、改后各跑一次，**全部 `✅` 行按顺序逐行相同**，用例数 190 不变；
   - 变异：在第一段与最后一段各把一条断言改坏，整体退出 1 并报出那一段；删掉公共部分里一个挪上来的函数，用到它的段失败；
   - `/bin/bash`（3.2）跑通；CI 同版本 ShellCheck 无告警；
   - 连跑 5 遍全绿，跑前、跑后仓库 `git status --porcelain --ignored` 不变。
7. **计时与目标**：相近负载下计时改前、改后，记下负载与 CPU（user+sys）。目标本机 20 秒以内；verify-and-commit 全档里它不再
   比 validate 慢。CI 的 phase-guard 步骤改前、改后也记下。做不到时在 todo 与 PR 里说明原因，由用户决定。
8. **范围**：只改 `test-phase-guard.sh`。它在 `plugins/spec-guard/hooks/` 下，随插件包发出，所以下次发版时包里的这个测试文件会
   变；发版证据里在安装副本上跑一遍它。不单独发版，下次发版时写进 CHANGELOG 的"维护者工具"。

## Requirements

1. `test-phase-guard.sh` 按假设 1–5 分段并行，用例、断言与被测 hook 不变。
2. 按假设 6 证明没有少跑、没有漏报，按假设 7 计时。

## Commands

```bash
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
SG_VALIDATE_JOBS=1 /bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
```

## Boundaries

- Always：每个用例照跑、按原顺序完整打印；任一段失败即整体失败。
- Ask first：推送、PR；改任何用例、断言或被测 hook；为了好切段而调换段落顺序。
- Never：为提速跳过、合并或删除用例；吞掉某一段的输出或退出码。

## Success criteria

1. 本机 20 秒以内（或说明原因），全档提交里不再是瓶颈。
2. `✅` 行序列与改前逐行相同，190 例；任一段失败整体失败并报出是哪一段。
3. 连跑 5 遍全绿、仓库不留变化；CI 绿。

## Open questions

无。
