# Todo: ci-shellcheck-pin

- [x] Task 0：提交 Plan 与 todo（2026-11-24 用户「Plan 批准」）
- [x] Task 1：回归先红后绿，改 ci.yml 与 CHANGELOG
- [x] Checkpoint 1（report）：本机完整检查与变异
- [ ] Checkpoint 2（gate）：推送、开 PR、AC4／AC5 实测、最终验收、按 F3 合并、重推 #488

## 证据
- Task 1（2026-11-24）：新回归 `test_shellcheck_is_pinned_release` 对旧 `ci.yml` 跑红（2 处：npx 调 shellcheck、没有下载发布包的一步）；改 `ci.yml` 后 `test_ci_workflow` 8 例全绿，`yaml.safe_load` 通过。
- Checkpoint 1（2026-11-24，提交 12e4935 上，macOS `/bin/bash`，完整档）：`validate.sh`「校验通过 ✅」；phase-guard「passed (541 cases)」；verify-artifacts「passed (120 cases)」。
  变异（各自还原，`git status` 干净）：版本改成 `latest` → 1 失败；删掉 `sha256sum -c` → 1 失败；检查一步改回 `npx --yes shellcheck@4.1.0` → 2 失败。
  本机跑不了 CI 里的 Linux 安装步骤，靠 Checkpoint 2 的 AC4、AC5 在 PR 上实测。
- Checkpoint 2（2026-11-24～25，PR #489，base main）：
  - AC4（9ffe74f，run 45427804626）：`validate` 日志 `shellcheck.tar.xz: OK`、`version: 0.11.0`，ShellCheck 一步通过；五项全绿，`CI required` 通过。
  - AC5（48af750，run 45428834162，校验和首位 8→9，`--no-verify` 只用于这一个故意坏的提交）：`validate` 失败于「安装 ShellCheck（官方发布包，核对 sha256）」，
    日志 `sha256sum: WARNING: 1 computed checksum did NOT match`；`CI required` 失败；其余三项通过。
  - 撤回 8b01686（run 45429495335，树与 9ffe74f 相同）：`validate` 通过，但 `python (3.9)` 失败于
    `test_proposal_promotion_proof` 的 `copytree` 撞上模板裸仓库的 `objects/maintenance.lock`（`shutil.Error`），与本模块无关，同 plugin-spec-compliance 记过的偶发失败。
- 模块外修复（2026-11-25 用户「PR 的 CI 失败了。请找出原因，修复并推送。」，越出并行边界，单列）：
  - 根因（本机 `GIT_TRACE` 实测）：本地传输推送时 git 对 `git-receive-pack` 先 `unset GIT_CONFIG_COUNT`，测试用环境变量关掉的 `maintenance.auto`／`gc.auto`
    到不了远端；远端 `receive.autogc` 默认开，每次推送都起 `git maintenance run --auto --quiet --detach`，后台建删 `maintenance.lock`，与下一个用例的 `copytree` 抢。
  - 修复：`test_proposal_promotion_proof.py`、`test_proposal_publication.py`、`test_proposal_submit.py` 的 `build()` 建完裸仓库即写 `receive.autogc false`；
    各加一条只读远端本地配置（`--local`）的回归。原有 `test_template_git_background_maintenance_is_disabled` 读到的是环境变量，所以一直是绿的。
  - 先红后绿：三条回归改前都失败（`'' != 'false'`），改后三个文件在 Python 3.10 与 `/usr/bin/python3` 3.9 下都通过。
    `GIT_TRACE` 统计 promotion_proof 整套：改前 receive-pack 45 次、maintenance 45 次；改后 45 次、0 次（publication 10／0，submit 5／0）。
