# Plan: ci-shellcheck-pin

<!-- spec-guard: review approved -->

Spec：[spec/ci-shellcheck-pin.md](../../spec/ci-shellcheck-pin.md)（2026-11-24 批准，Q1 选 A；2026-11-25 用户「Spec、Plan 都批准」，加假设 7 与 Task 2）。

## 架构决定

- **`validate` 里原来的一步拆成两步**，位置不变（在 verify-artifacts 回归之后、`git diff --exit-code` 之前）：

  ```yaml
      - name: 安装 ShellCheck（官方发布包，核对 sha256）
        env:
          SHELLCHECK_VERSION: v0.11.0
          SHELLCHECK_SHA256: 8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198
        run: |
          archive="$RUNNER_TEMP/shellcheck.tar.xz"
          curl -fsSL --retry 3 -o "$archive" \
            "https://github.com/koalaman/shellcheck/releases/download/${SHELLCHECK_VERSION}/shellcheck-${SHELLCHECK_VERSION}.linux.x86_64.tar.xz"
          echo "${SHELLCHECK_SHA256}  ${archive}" | sha256sum -c -
          tar -xJf "$archive" -C "$RUNNER_TEMP"
          echo "$RUNNER_TEMP/shellcheck-${SHELLCHECK_VERSION}" >> "$GITHUB_PATH"

      - name: ShellCheck（阻塞）
        run: |
          shellcheck --version
          shellcheck -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh evals/*/*.sh
  ```

  原来那段四行注释（「npm 4.1.0 = 二进制 v0.11.0」）删掉，换成两行：为什么不用 npm 包（下载前匿名调 GitHub API 查 latest，共享 IP 被限流 403，
  `SHELLCHECKJS_RELEASE` 不生效），以及升级时版本号与校验和一起改、校验和取发布页的官方摘要。上面两行关于 `|| true` 与 evals 范围的注释保留。
- **回归**（`scripts/test_ci_workflow.py` 新增 `test_shellcheck_is_pinned_release`）：
  - 所有 workflow 的每个 `run` 都不能同时含 `npx` 与 `shellcheck`；
  - `validate` 恰好有一步的 `run` 含 `releases/download/${SHELLCHECK_VERSION}/`，它的 `env.SHELLCHECK_VERSION` 匹配 `^v\d+\.\d+\.\d+$`，
    `env.SHELLCHECK_SHA256` 匹配 64 位十六进制，`run` 含 `sha256sum -c`；
  - 跑 `shellcheck -S warning` 的那一步排在它之后。
  跟现有用例一样用 PyYAML 解析，没有 PyYAML 时跳过（CI 的 `plugin` 任务装了它，真跑）。

## 任务

- **Task 0**：提交本 Plan 与 todo。验证：`verify-and-commit` 快档。
- **Task 1**：先写回归，对现在的 `ci.yml` 跑红（`npx shellcheck` 那一条失败），再改 `ci.yml` 跑绿。CHANGELOG「未发布」加一条。
  验证：`python3 -B scripts/test_ci_workflow.py`（本机 3.10 有 PyYAML）；`verify-and-commit` 完整档。
- **Task 2**（2026-11-25 加入，Spec 假设 7）：三个 Proposal 测试的模板裸仓库写 `receive.autogc false`，各加一条只读远端 `--local` 配置的回归，先红后绿。
  验证：三个文件分别在 3.10 与 `/usr/bin/python3` 3.9 下跑；`GIT_TRACE` 统计远端 maintenance 次数；`verify-and-commit` 完整档。

## 会改哪些文件

- 新增：`tasks/ci-shellcheck-pin/{plan,todo}.md`。
- 修改：`.github/workflows/ci.yml`、`scripts/test_ci_workflow.py`、`CHANGELOG.md`；Task 2 改 `plugins/spec-guard/hooks/` 下三个 `test_proposal_*.py`。都在 Spec 的并行边界内。
- 新增依赖：ShellCheck v0.11.0 官方发布包（`shellcheck-v0.11.0.linux.x86_64.tar.xz`，sha256 `8c3be12b…7198`），替换 npm 包 `shellcheck@4.1.0`；锁文件不变。

## 风险

- **github.com 的发布附件下载也可能偶发失败**：`curl --retry 3` 缓解；它不走 REST API 的匿名额度，和这次的 403 不是一回事。真失败时日志会是 curl 的错误，不会被误认为检查失败。
- **本机看不到 CI 里的这两步**：本机的 `verify-and-commit` 仍用 npx（Q1 A），所以 CI 两步只能在 PR 上实测，靠检查点 2 的 AC4、AC5 证明。
- **#488 要跟着处理**：两个模块都插在 plugin-spec-compliance 之后，CHANGELOG「未发布」也都加了条目。本模块合并后，#488 基于新的 main 重推时会有冲突，
  按能力图顺序 plugin-spec-compliance → ci-shellcheck-pin → merge-flow-f3 解开，CHANGELOG 两条都保留。

## 检查点

- Checkpoint 1（report）：本机三套检查全绿；变异：下载地址里的版本改成 `latest`、删掉 `sha256sum -c`、把检查一步改回 `npx --yes shellcheck@4.1.0`，各自让回归变红后还原。记进 todo，不停下。
- Checkpoint 2（gate）：Plan 获批即授权推送本分支、开 PR，以及 AC5 的临时提交（把校验和改错一位，`--no-verify` 只用于这一个故意坏的提交）和撤回提交。
  看 PR 上的检查：AC4（日志里 `version: 0.11.0`、ShellCheck 通过、`CI required` 通过）、AC5（安装一步失败、`CI required` 失败、撤回后全绿）。然后交你最终验收；
  验收结束就问合并，你回「合并」后按 F3 执行并核实。之后把 #488 基于新的 main 重推。

## 预先声明

- 公共路径：无
- 外部依赖：`koalaman/shellcheck@v0.11.0`
- 质量与工作区配置：`.github/workflows/ci.yml`
- 补丁：无
