# Spec: local-check-dedup

## Objective

本机提交与推送把同一份内容重复检查了两三遍：`verify-and-commit.sh` 跑完 validate、phase-guard、verify-artifacts
才提交，推送时 pre-push 又把这三套原样再跑一遍；`verify-and-commit` 还额外加跑 validate 已经包含的 setup/teardown 与
pre-push 回归；只改 Spec 或文档的提交也要跑全套。以 `self-report-tmpdir-independence` 为例，实际开发约 45 秒，本机等待
约 18 分钟（两次提交 286 秒、340 秒，一次推送 447 秒）。来源：第二轮联调整理、用户 2026-10-09 确认（快档记录选 A）。

读者：本仓库维护者（人或 agent）。CI 仍是必需检查，合并前一定完整跑一遍，本模块只去掉本机的重复。

## Assumptions

用户于 2026-10-09 确认（含第二轮联调审查补充的第 5 条发布证据回归与第 7 条，用户“按推荐，批准 Spec”）：

1. 本仓库改回分开审：删去 `.agent/config.json` 的 `"reviewCadence": "combined"`（默认即 `separate`）。本模块的 Plan
   起按分开审走。
2. 记录放在所有 worktree 共用的 git 目录：`$(git rev-parse --git-common-dir)/spec-guard/verified-trees`，每行
   `<tree> <full|quick>`。`verify-and-commit` 提交成功后追加当次提交的 tree 与档位。
3. pre-push 对每个要推的分支，列出远端还没有的提交（`<remote sha>..<local sha>`；新分支时取不在任何远端分支上的提交）。
   每个提交满足下列之一才算“已检查”：
   - 它的 tree 记为 `full`；
   - 它的 tree 记为 `quick`，只有一个父提交，相对父提交只改了快档路径，且父提交已在远端或本身算“已检查”（选 A）。
   所有提交都已检查、且已跟踪文件没有未提交改动时，跳过三套检查并打印原因；否则照常全跑，失败照常拦截。记录文件缺失
   或读不了时照常全跑。只删引用、只推 tag 的推送维持现有跳过规则。
4. `verify-and-commit` 按已暂存路径分档。全部路径都在快档范围内才走快档：`spec/`、`tasks/`、`docs/` 下的文件，以及
   `plugins/` 与 `.github/` 以外的 `*.md`（如 `README.md`、`CHANGELOG.md`、`CLAUDE.md`、`AGENTS.md`）。其余任何路径，
   包括拿不准的，一律走全套。
5. 快档：`validate.sh --quick`（只跑结构检查，不跑任何回归套件）+ verify-artifacts 回归 + 对本仓库本身跑一次
   `verify-artifacts.sh`（Spec、Plan 的结构问题由它直接发现）。`--quick` 的范围按实测（2026-10-09，本机）定为
   validate 的这些节，每条都在 0.4 秒以内：结构、JSON 语法、清单一致性、公开安装元数据、Shell 语法、可执行位、bash 3.2
   兼容、gh `--json` 字段、管道 + `grep -q`、命令名与命令表等 8 个检查器、指纹算法自检与单一来源、本机状态路径、README
   内嵌声明块、命令 frontmatter，以及发布证据与发布包回归（`evals/test-release-evidence.sh` 0.24 秒、
   `evals/test-release-package.sh` 0.10 秒），这样 `docs/releases/*.json` 的改动也在快档里得到检查。
6. 全套：validate、phase-guard、verify-artifacts 并行跑，暂存了 `.sh` 时再并行加 ShellCheck；每套日志分开写，退出码
   逐项判定，任一失败不提交。不再按路径加跑 setup-teardown 与 pre-push 回归（validate 第 74、151 行已包含）；
   `--suite` 仍可手动加跑。
7. 检查时工作区里有未跟踪文件（不含被忽略的）就不写记录，打印原因与文件清单，提交照常进行；推送时这个提交因此照常
   全跑。原因：检查的是工作区、提交的是暂存区，未暂存的新文件参与检查后，记成通过的 tree 会让推送跳过，缺文件要到 CI
   才发现。
8. pre-push 安装提示里的“约 50 秒”改成实测值。
9. 插件发布包与版本号不动，随下次发版。

## Requirements

1. `scripts/validate.sh` 支持 `--quick`，只跑假设 5 列出的节；不带参数时行为不变。
2. `scripts/verify-and-commit.sh`：分档（假设 4）、快档内容（假设 5）、全套并行（假设 6）、提交成功后追加记录
   （假设 2；有未跟踪文件时不写，假设 7）。屏幕摘要写明档位与每套耗时。记录写入失败只打印提醒，不影响已完成的提交。
3. `scripts/install-git-hooks.sh` 生成的 pre-push：按假设 3 判断并在跳过时说明依据（几个提交、各自依据 full / quick）；
   安装提示的耗时改为实测值。
4. 回归：
   - `test_verify_and_commit.py`：快档与全套的路径分界（含拿不准的路径走全套）；快档不跑 validate 全量；全套并行且任一
     失败不提交、逐项报出；提交成功后记录档位正确，失败时不记录，有未跟踪文件时不记录并说明；不再自动加跑
     setup-teardown 与 pre-push。
   - `test_pre_push_environment.py`（真实本地推送）：全套记录过的提交推送时跳过；快档提交在父提交已记录时跳过；以下情况
     照常全跑：记录里没有该 tree、快档提交改了快档外路径、父提交未记录、已跟踪文件有未提交改动、合并提交只有快档记录、
     记录文件缺失；照常全跑时任一检查失败仍拦截。
   - 每条新断言先在现有代码上变红，再手动改坏实现确认会变红。
5. 实测验收（写进 todo）：一个纯文档提交与一个脚本改动提交各走一遍“提交 → 推送”，前后各计时。目标：纯文档提交加推送
   30 秒以内；脚本改动提交 4 分钟以内，推送跳过全套。
6. 文档：`docs/maintainer-workflow.md`“提交前”一节、`CLAUDE.md`“最小验证”写明档位、记录与推送跳过规则。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash scripts/validate.sh --quick
python3 -B scripts/test_verify_and_commit.py
python3 -B scripts/test_pre_push_environment.py
```

## Boundaries

- Always：只依赖 `bash`、`git`、`python3`（ShellCheck 另需 `npx`）；记录只追加到 git 共用目录；拿不准一律跑全套。
- Ask first：推送、PR；重新安装本机钩子之外的本机文件改动。
- Never：缩小 CI 的检查范围；分支推送在记录不匹配时跳过；改插件发布包或版本号。

## Success criteria

1. 同一份内容在本机只完整检查一次：提交时检查过，推送就不再重跑。
2. 纯文档改动不再等全套检查。
3. 任何记录对不上的情况都照常全跑，失败照常拦截。

## Open questions

无。
