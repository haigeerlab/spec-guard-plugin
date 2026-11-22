# Todo: release-command

- [x] Task 0：提交 Plan 与 todo
- [x] Task 1：骨架、check、prepare 与测试（Codex）
- [x] Task 2：publish、install 与测试（Codex）
- [x] Task 3：smoke、evidence 与测试（Codex）
- [x] Task 4：docs/release-process.md
- [x] Checkpoint 1（report）：完整检查、变异与本仓库实跑
- [x] Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行
- [x] Task 5（返工）：`evidence` 写进证据的命令不带本机绝对路径——仓库内的脚本写相对路径，家目录下的路径写成 `~/…`；回归断言四份证据里没有仓库根与家目录的绝对路径 — 2026-11-22 v0.92.0 发版时发现（codex 证据的 smoke 命令带了本机用户名的路径，#476 手工改掉）；用户「两个都修」
- [x] Task 6（返工，发版时发现）：共用模板仓库的测试在建模板时关掉 git 后台维护（`maintenance.auto=false`、`gc.auto=0`），避免复制模板时撞上 `maintenance.lock` 消失 — #476 的 CI 因 `test_proposal_promotion_proof` 偶发失败；ecosystem-lead #22105 提供 kb-plugin 的同类做法；用户「两个都修」
- [x] Checkpoint 3（report）：完整检查与变异
- [ ] Checkpoint 4（gate）：最终验收；通过后推送并开 PR，合并由用户进行；不发版

## Checkpoint 1 记录（2026-11-22）

- 编码由 Codex 完成（三次 `/delegate:run --write`：T1 run 20261122130906.65297、T2 run 20261122132230.81116、T3 run 20261122133721.93851，
  另一次小 run 把证据里的本机绝对路径改成占位写法）。每次都只改了派活说明允许的文件。Claude 验收：读全部差异、自己重跑 `test_release.py`（43 例）通过。
- 变异（各让回归变红，均已还原）：去掉 CI 核对；`publish` 不看 `--confirm`；smoke 退出 2 一律当 waiting-on-user；Codex 配置多处 `ref` 仍替换。
- 每个提交走 verify-and-commit 完整档，全绿。T3 与 T4 一度被并进一个提交（第一次提交因工作区有未暂存的文档改动被拒，`| tail -1` 吞了退出码），未推送前已撤回、重新分开提交。
- 本仓库实跑（真 `git`、`gh`，记录目录用临时目录）：
  1. `check --pr 472` → `refused`（`main-moved`）：#472 之后 main 又合了 #473，判对了。
  2. 临时记录里手写 check 通过后 `prepare --version 0.91.3` → `ok`；与已发布的 `spec-guard-v0.91.3.tar.gz` 解压后逐文件一致（186 个文件）。
  3. `publish --version 0.91.3`（不带 `--confirm`）→ `preview`，只打印五条命令。
  4. `install --version 0.91.3`（不带 `--confirm`）→ `preview`；Codex 配置已是 v0.91.3，显示无需修改或备份。

2026-11-22 用户「验收通过」（验收前问过是否要外部审查，用户没有要求）。

<!-- spec-guard: external-review declined -->

## Checkpoint 3 记录（2026-11-22）

- Task 5、6 编码由 Codex 完成（run 20261122162918.92938、20261122163716.15987），只改了派活说明允许的文件；Claude 读全部差异、自己重跑。
- Task 5：`test_release.py` 44 例通过；变异（证据命令改回仓库绝对路径）2 例失败。
- Task 6：四个共用模板的测试用 `run_tests_parallel.py` 重跑全部通过（62／52／16／28 例）；变异（不启用 GIT_CONFIG 设置）6 例失败。
- 两个提交都走 verify-and-commit 完整档，全绿。插件本身没有改动，不发版。
