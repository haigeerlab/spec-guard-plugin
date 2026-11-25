# Spec: ci-shellcheck-pin

<!-- spec-guard: review approved c854fd19ba25 -->

## Objective

CI 任务 `validate` 的 ShellCheck 一步用 `npx --yes shellcheck@4.1.0` 安装。实测（2026-11-24，PR #488 的 run 45419555492 第 1、2 次）：
这个 npm 包下载二进制前，总是匿名请求 `https://api.github.com/repos/koalaman/shellcheck/releases/latest` 查最新版本号（`download.js` 调 `buildURL` 时不传版本，
`SHELLCHECKJS_RELEASE` 设了也不生效；只有环境里有 `GITHUB_TOKEN` 才带令牌）。GitHub 托管 runner 共用 IP，匿名额度常被别人用完，返回 `403 rate limit exceeded`，
这一步失败，`CI required` 随之失败，PR 合不进去。而且装的永远是最新版，`ci.yml` 里「npm 4.1.0 = 二进制 v0.11.0」的注释不成立，ShellCheck 发新版时 CI 会悄悄换版本。

本模块把 CI 改成直接下载钉住版本的官方发布包、核对 sha256 后使用，不再经过 npm 包，也不调 GitHub API。

给谁用：本仓库的 CI 与维护者。不属于用法草案，不改插件本身的任何行为、命令或输出。

登记：用户 2026-11-24 在本会话看完排查结果后回「单独 PR 钦版本下载」（选的是推荐的「单独 PR，直接下载钉住版本的二进制」）。

## Assumptions

1. **下载地址**：`https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz`。
   这是发布附件的下载地址，不走 REST API 的额度，不需要令牌。`validate` 跑在 `ubuntu-latest`（x86_64），只用这一个包。
2. **校验和**：`8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198`。2026-11-24 本机下载算出，
   与 GitHub 发布页给这个附件的官方摘要（`gh api repos/koalaman/shellcheck/releases/tags/v0.11.0` 的 `digest`）一致。校验不过就让这一步失败，不跳过。
3. **步骤写法**：`validate` 里拆成两步。
   - 「安装 ShellCheck v0.11.0」：`curl -fsSL --retry 3` 下载到 `$RUNNER_TEMP`，`sha256sum -c` 核对，解压后把目录写进 `$GITHUB_PATH`；
     版本号与校验和放在这一步的 `env` 里，各写一次。
   - 「ShellCheck（阻塞）」：先打印 `shellcheck --version`，再跑原来那条检查（范围和 `-S warning` 不变）。
   不用第三方 action，不加权限（任务仍是 `contents: read`）。
4. **回归**：`scripts/test_ci_workflow.py` 新增断言——
   - 任何 workflow 都不出现 `npx` 调用 `shellcheck`；
   - 安装步骤的下载地址里含钉死的版本号（`v` 加三段数字，不是 `latest`），`env` 里有 64 位十六进制的校验和，`run` 里有 `sha256sum -c`；
   - ShellCheck 检查那一步排在安装步骤之后。
5. **注释**：删掉 `ci.yml` 里「npm 4.1.0 = 二进制 v0.11.0」那段注释与步骤名里的说法，改为一句说明为什么不用 npm 包（匿名调 API 被限流、版本实为 latest）。
6. **本机不改**：`scripts/verify-and-commit.sh` 本机仍用 `npx shellcheck@4.1.0`（Q1 用户选 A）。
7. **模块内顺带修的偶发失败**（2026-11-25 加入）：PR #489 撤回提交那一轮 CI，`python (3.9)` 偶发失败。原因是 `test_proposal_promotion_proof` 复制模板时，
   撞上模板裸仓库的 `objects/maintenance.lock`。本机 `GIT_TRACE` 实测：往本地裸仓库推送时，git 先 `unset GIT_CONFIG_COUNT` 再启动 `git-receive-pack`，
   测试用环境变量关掉的后台维护到不了远端；远端 `receive.autogc` 默认开，每次推送都起 `git maintenance run --auto --detach`。
   三个共用模板的测试（`test_proposal_promotion_proof.py`、`test_proposal_publication.py`、`test_proposal_submit.py`）在建裸仓库时写 `receive.autogc false`，
   各加一条只读远端自身配置（`--local`）的回归。不改插件代码。登记：用户 2026-11-25「PR 的 CI 失败了。请找出原因，修复并推送。」，范围由用户回「补进 Spec 边界」。
8. **不做**：改插件代码、命令、清单版本号与 CHANGELOG 的版本段（只在「未发布」加一条）；改历史 Spec 里的旧命令；给其他平台（macOS、arm64）准备下载包。

## Contract

- **C1** `.github/workflows/ci.yml` 的 `validate` 任务（假设 1～3、5）。
- **C2** `scripts/test_ci_workflow.py`（假设 4）。
- **C3** `CHANGELOG.md` 的「未发布」一条。
- **C4** 三个 Proposal 测试的模板裸仓库配置与回归（假设 7）。

## Acceptance criteria

- **AC1** `ci.yml` 里不再有 `npx` 调 `shellcheck`；安装步骤下载 v0.11.0 的 Linux x86_64 包并用假设 2 的校验和核对。
- **AC2** `test_ci_workflow.py` 通过；把下载地址里的版本改成 `latest`、删掉 `sha256sum -c`、或改回 `npx shellcheck@4.1.0`，各自都让它变红。
- **AC3** 本机：`validate.sh`、phase-guard、verify-artifacts 全绿。
- **AC4** PR 上 `validate` 的日志里打印出 `version: 0.11.0`，ShellCheck 一步通过，`CI required` 通过。
- **AC5** 校验失败路径实测：在 PR 上推一个把校验和改错一位的临时提交，安装步骤失败、`CI required` 失败，再撤回恢复全绿。
- **AC6** 三条新回归改前红、改后绿；`GIT_TRACE` 下跑这三个测试，推送时远端不再启动 `git maintenance`；PR 上五项全绿。

## Boundaries

- **会做**：C1～C4；推送、开 PR；按 F3 问合并。合并后把 #488（merge-flow-f3）基于新的 main 重新推送，解开能力图里两个模块都插在 plugin-spec-compliance 之后的冲突。
- **先问再做**：合并；AC5 的临时提交（会让 PR 上一次 CI 故意失败）；任何超出假设 1～7 的改动。
- **不做**：假设 8 列出的事。

## 并行边界

- 独占：`spec/ci-shellcheck-pin.md`、`tasks/ci-shellcheck-pin/`、`.github/workflows/ci.yml`、`scripts/test_ci_workflow.py`、`CHANGELOG.md`、`plugins/spec-guard/hooks/test_proposal_promotion_proof.py`、`plugins/spec-guard/hooks/test_proposal_publication.py`、`plugins/spec-guard/hooks/test_proposal_submit.py`
- 公共：无

## Open questions

- **Q1 本机的 ShellCheck 要不要一起改？**（2026-11-24 用户选 A）
  - A（推荐）：不改。本机是单个开发者的 IP，匿名额度很少用完，npx 下载过一次就有缓存；本模块只修 CI。代价：本机装的仍是「最新版」，ShellCheck 发新版后本机和 CI 可能不一致。
  - B：一起改。`verify-and-commit.sh` 改为优先用 PATH 上的 `shellcheck`，并检查版本是 0.11.0，不是就报出来。代价：多改一个脚本和它的回归，本机还要先自己装好 v0.11.0。

## 文档建议

只改 CI，不影响使用者看的文档。`CONTRIBUTING.md` 第 29 行只写了 `validate` 含 ShellCheck，不用改；`docs/maintainer-workflow.md` 第 162 行说本机「再加 CI 同款 ShellCheck」，
Q1 选 A 时不改（仍是同一个检查器、同一组参数），选 B 时顺带写明本机要装 v0.11.0。项目没有文档基线。
