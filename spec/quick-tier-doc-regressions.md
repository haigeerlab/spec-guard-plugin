# Spec: quick-tier-doc-regressions

<!-- spec-guard: review approved c5624d796ee6 -->

## 目标

只改文档的提交与推送，在本机也跑「读仓库文档」的回归测试，让改坏文档的那次提交当场被拦下，而不是推送后才在 CI 变红。

现状（2026-10-28 核对）：

- `scripts/verify-and-commit.sh` 判断暂存的全是文档类路径时走快档，只跑 `validate.sh --quick`（结构检查）、verify-artifacts 回归与
  本仓库 verify-artifacts，不跑回归测试。
- pre-push 认快档记录（`scripts/verified_trees.py` 的 `commit_basis`）：一串只改文档的提交推送时整段跳过检查。
- 至少三个回归测试读仓库的真实文档：`test_hosted_ticket_entry.py`（`docs/workflow.md`，0.03 秒）、`test_workflow_checkpoints.py`
  （`docs/workflow.md`、`docs/convention-block.md`，0.07 秒）、`test-retire-legacy-tracker-bridge.sh`（`README.md`、`docs/design.md` 等，1.2 秒）。
- CI 跑完整 `validate.sh`，是必过检查，所以坏文档合不进 `main`；损失是多一轮推送与修复。2026-10-28 user-docs-align 实际踩过一次。

给谁用：在本仓库改文档的维护者与 agent。

登记：需求来自用户本人（2026-10-28，确认需求总结「需求说完了」），不需要回告。

## 边界

**总是做**

- 先写能复现漏洞的回归（先红后绿），再改。
- 改动后按 `CLAUDE.md` 跑三条最小验证；改了 `.sh` 加跑 CI 同版 ShellCheck（`npx --yes shellcheck@4.1.0 -S warning …`）。
- 实测快档前后耗时，写进 todo。

**先问**

- 检查器在现有测试里找出更多「读仓库文档」的测试，加进快档后快档多出的耗时超过 2 秒时。
- 需要改分档规则、pre-push 逻辑或 CI 才能达到目标时。

**不做**

- 不改分档规则（只改文档照旧走快档）、不改 `scripts/verified_trees.py` 的跳过逻辑、不改 `.github/`。
- 不让快档跑整套回归；不改这三个测试本身。
- 不改 `plugins/spec-guard/` 下的任何文件，不改版本号、不发版（`scripts/` 在插件包以外，`docs/release-process.md` 只在要发版时改版本号）。

## 要你确认的假设

1. **快档记录照旧可以让 pre-push 跳过**：记录本身已包含这几个测试，跳过仍然安全，所以 pre-push 不用动。
2. **检查器只认读「仓库根」文档的写法**：例如 Python 里 `parents[N] / "docs"`、`ROOT.parents[1] / "docs/…"`，shell 里 `"$ROOT/README.md"`、
   `"$ROOT/docs/…"`；在临时目录里建 `docs/` 当夹具的测试不算。写法认不出来的漏报靠正反例约束，不追求一网打尽。
3. **快档清单放在 `validate.sh` 一处**，检查器读同一份清单，不另存一份。
4. 分支 `claude/quick-tier-doc-regressions`，从 #419 合并后的 `main`（`dcbf9da6`）开出（原 Q3，已按 A 执行）；一个 PR，按 Plan 分任务提交。

## 验收标准

- AC1：新增回归：把 `docs/workflow.md` 改坏一处（删掉 `rootCauseReviewRequired`）的副本上跑快档，修复前快档放行（测试红），修复后快档失败（测试绿）。
  放在 `scripts/test_validate_quick.py` 或 `scripts/test_verify_and_commit.py` 里，以现有写法为准。
- AC2：`validate.sh --quick` 跑上述三个测试（Q1 为 A 时）；同一台机器上快档耗时增加不超过 2 秒，前后实测写进 todo。
- AC3（Q2 为 A 时）：validate 新增一项检查：扫 `plugins/spec-guard/hooks/test*` 与 `scripts/test*`，按假设 2 的写法找出读仓库 `docs/`、
  `README*.md`、`CHANGELOG.md` 的测试，不在快档清单里就报错并给出文件名；`scripts/test-checkers.sh` 有正例（漏列被拦）与反例（夹具路径不报、
  已列入的不报）；当前仓库通过。
- AC4：检查器在现有测试里找出的其他「读仓库文档」测试，一并加进快档，或在清单旁写明不加的原因；超出 2 秒按「先问」处理。
- AC5：`scripts/verified_trees.py`、`.github/`、`plugins/spec-guard/` 无改动（`git diff --stat origin/main -- <这三处>` 为空）。
- AC6：`docs/maintainer-workflow.md`（及 `CLAUDE.md` 里讲快档的那句，若需要）写明快档也跑读仓库文档的回归，以及新增测试读仓库文档时要列入快档清单。
- AC7：`/bin/bash scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 通过；改了 `.sh` 时 CI 同版 ShellCheck 无告警。

## 未决问题

- **Q1：怎么让快档跑这些测试？** A（推荐）直接并进 `validate.sh --quick`，不论改哪个文档都跑，约多 1.3 秒；B 按暂存路径匹配才跑，要维护「测试→读哪些文件」的对照。
- **Q2：以后新增读仓库文档的测试，怎么防止忘了列进快档？** A（推荐）validate 加一项检查（AC3）；B 只在维护者文档写约定，不做自动检查（AC3 去掉）。

**已定（2026-10-28，用户）：Q1 A；Q2 A。**

（原 Q3 分支已按 A 执行。）

## 文档建议

`docs/maintainer-workflow.md` 要改（AC6）；README 不涉及（使用者不碰提交脚本）。项目没有文档基线。

## 变更记录
