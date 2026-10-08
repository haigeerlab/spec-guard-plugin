# Todo: collaboration-command-retirement

- [x] Task 1：退役扫描加入该名字（先红） — 能力图名单与广域扫描（plugins、evals、scripts）都加入 `spec-guard:collaboration`，先红：两个检查器的注释与提示共 3 处。**补充（Spec 未写）：** 命令文件正文不含自己的名字，名字扫描拦不住「放回文件」，因此把命令文件与其回归登记进 `scripts/collaboration-owned.txt`（已移出、不得再出现的路径清单），边界检查器随即报这两个文件仍在。
- [x] Task 2：删除命令并改写现行文字 — 删除命令与回归及其在 validate.sh 的调用；README、optional-features、workflow 命令表、collaboration-interface 改为直接指向 agent-relay 并记录 0.54.0 移除；边界检查器说明与提示去掉该命令，路径失败提示改为 removed from Spec Guard。命令名检查器的 `EXTERNAL_COMMANDS` **保留**（实测：这套通用机制有两条回归在用，登记的 `/agent-relay:collaboration` 真实存在），只改注释。退役扫描、边界、命令名、命令表、README 同步检查与检查器回归 96 例通过；`test_agent_relay_probe`、`test_ticket_entry` 通过。变异：放回命令文件、能力图写回该名字，均被抓到。
- [x] Checkpoint 1（report）：validate.sh 通过，两套 hook 断言通过，ShellCheck 无警告 — 见 Checkpoint 2 的同一条验证链。
- [x] Task 3：0.54.0 版本与 CHANGELOG — 两份 plugin.json 为 0.54.0，README `--ref v0.54.0`；CHANGELOG 顶部 `[未发布]` 改为 `[0.54.0] - 2026-10-08` 并补「移除」一节（文件末尾另有一处历史遗留的 `[未发布]`，未动）。check-manifests、check-readme-sync 通过；`codex-plugin-smoke.sh --selftest` 通过。
- [x] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行；合并后一次走完发版 — macOS 15.7.3、`/bin/bash` 3.2.57 上同一条 `&&` 链：validate.sh、phase-guard、verify-artifacts、退役扫描与 ShellCheck 全部通过后才提交并推送；PR 由用户合并，发版在合并后进行。
