# Spec: plugin-spec-compliance

<!-- spec-guard: review approved eec294a802a6 -->

## Objective

用户批准的《插件开发规范》v1.3（31 条，9 条卡）要求每个插件补齐。ecosystem-lead 按本仓库 GitHub 主干核出整改单（#22432、#22448、#22472），
本模块把它在 spec-guard-plugin 里做完：CI 改成规范要求的形状、清单能过 `claude plugin validate --strict`、LICENSE 版权行改为组织名，
并补上 Python 3.9、钉 SHA、dependabot、改后无残留 diff 这几条提醒项。

给谁用：维护本仓库的人和 agent；以后在 hub 接入共享检查（autopr-design 写，影子运行）的 CI；改主干保护的用户。

对外接口与用法草案一致吗：不属于用法草案（不是 S110 的模块），只是按能力图顺序插在 M2 中间；不改插件对外接口、不发版。

登记：ecosystem-lead #22432（v1.1 整改单）、#22448（v1.2 追加 5 条）、#22472（v1.3 调整）；账本 K0ZTBN0。需求确认：规范由用户在 ecosystem-lead 会话批准
（「批准，三处都同意」「对，按推荐改」「加这 5 条」「批准，升 v1.3」，经 ecosystem-lead 转来）；排序由用户 2026-11-24 在本会话定为「整改先做」。

## Assumptions

1. **一个模块、一个 PR**。改动都在 `.github/`、`scripts/`、清单与 LICENSE 上，互相牵连（检查名和主干保护要一起生效），拆开反而要多改几次主干保护。
2. **CI 的形状**（`.github/workflows/ci.yml`，workflow 名改为 `CI`，触发保持 push main、pull_request、workflow_dispatch，不加路径过滤）：
   - 顶层 `permissions: {}`，每个任务只放 `contents: read`；所有 checkout 设 `persist-credentials: false`；所有 action 钉完整提交 SHA，后面注释版本号
     （checkout v7.0.1、setup-python v7.1.0、setup-node v7.1.0，SHA 已从 GitHub 读到）。
   - 任务 `validate`：照旧跑 `validate.sh`、两条回归、ShellCheck；**保留单元素矩阵**，检查名仍是 `validate (ubuntu-latest)`——这样本 PR 不会被现在的主干保护卡住。
   - 任务 `python`：矩阵 Python 3.9 与 3.13（setup-python），跑 `scripts/validate.sh`（里面登记了全部 Python 回归）。
   - 任务 `plugin`：`npx --yes @anthropic-ai/claude-code@2.1.328 plugin validate --strict` 分别校验插件目录与 marketplace；再用新脚本 `scripts/check-frontmatter.py`
     以 PyYAML（`pip install pyyaml==6.0.3`）真正解析 frontmatter：skill 与 agent 要求 `name`、`description`，command 只要求 `description`。
   - 每个跑检查的任务最后单独一步 `git diff --exit-code`（规范 C10：不放进 `validate.sh`）。
   - 汇总任务 `CI required`：`if: always()`，needs 上面全部任务，任何一个结果不是 success（失败、取消、跳过）就失败。
3. **主干保护**：本 PR 合并、`CI required` 在 main 上跑绿之后，请用户说原话，再把必需检查从 `validate (ubuntu-latest)` 换成 `CI required`（`gh api` 改分支保护，先读回再改，改后读回）。
   换之前两边都跑，不会出现等不到的检查。这一步是改仓库设置，不在 PR 里。
4. **让 `--strict` 通过**：实测（CLI 2.1.328）插件目录与 marketplace 各报一条警告——Claude 清单的 `requires` 是 Claude Code 不认的字段（只是一句说明，没有脚本读它，
   依赖 agent-skills 已写在 README 开头），删掉；marketplace 缺 `description`，补一句。`--profile directory` 的缺图标提示不在规范要求里，不处理。插件版本不改。
5. **LICENSE**：版权行改为 `Copyright (c) 2026 haigeerlab`，其余不动。
6. **dependabot**：新增 `.github/dependabot.yml`，只开 `github-actions`，`interval: monthly`，`cooldown.default-days: 7`（字段已对照 GitHub 文档）。
7. **Python 3.9**：本机 `/usr/bin/python3` 是 3.9.6，先用它跑一遍 `validate.sh`；不兼容的地方在本模块里改掉（hook 模块已有 `test_python_compat` 保证可导入，测试与 scripts 下的脚本未必）。
8. **frontmatter 脚本的回归**：`scripts/test_check_frontmatter.py` 用临时目录造缺 `name`、缺 `description`、YAML 写坏、command 没有 `name` 也通过几种情形；
   本机没有 PyYAML 时整组跳过（系统 Python 没有），登记进 `validate.sh`。
9. **B2（`.github/autopr/interface.yml` 登记发版入口）先不做**：spec-guard 发版走 `scripts/release.py`，每一步都要用户授权，现在不接入 autopilot。用户要接入时另开模块。
10. **文档**：`CONTRIBUTING.md` 里 CI 那段改写（任务构成、Python 3.9、必需检查是 `CI required`）；`docs/maintainer-workflow.md` 如提到 CI 一并改。CHANGELOG 记在未发布段。
11. **不做**：hub 的共享检查（路径、密钥、zizmor，autopr-design 写）；改 `validate.sh` 的检查内容；发版；接入 autopilot；macOS runner。

## Contract

- **C1** `.github/workflows/ci.yml`：假设 2。
- **C2** `scripts/check-frontmatter.py` 与 `scripts/test_check_frontmatter.py`，登记进 `validate.sh`（假设 2、8）。
- **C3** `plugins/spec-guard/.claude-plugin/plugin.json` 去掉 `requires`；`.claude-plugin/marketplace.json` 加 `description`（假设 4）。
- **C4** `LICENSE`、`.github/dependabot.yml`（假设 5、6）。
- **C5** Python 3.9 兼容修正（假设 7，按实测，可能为空）。
- **C6** `CONTRIBUTING.md`、`docs/maintainer-workflow.md`、`CHANGELOG.md`（假设 10）。
- **C7** 合并后的主干保护切换（假设 3，要用户原话）。

## Acceptance criteria

- **AC1** PR 上 GitHub Actions 出现 `validate (ubuntu-latest)`、`python (3.9)`、`python (3.13)`、`plugin`、`CI required`，全部成功；`CI required` 的 needs 列全了其余任务。
- **AC2** 变异：在 PR 分支上推一个临时提交，让 `plugin` 任务失败（删掉一个 command 的 `description`），实测 `CI required` 随之失败；再推一个提交撤掉，恢复全绿。
- **AC3** `claude plugin validate --strict` 对插件目录与 marketplace 都退出 0（本机与 CI）。
- **AC4** `check-frontmatter.py` 对本仓库全部 skill、command 通过；回归覆盖假设 8 的几种情形，删掉 `name` 校验的变异让回归变红。
- **AC5** workflow 顶层 `permissions: {}`、每个任务只有 `contents: read`、每个 checkout 有 `persist-credentials: false`、每个 `uses:` 是 40 位 SHA 加版本注释；没有 `paths` 过滤。
- **AC6** 本机 `/usr/bin/python3`（3.9.6）在前、跑 `validate.sh` 退出 0；CI 的 `python (3.9)` 通过。
- **AC7** LICENSE 版权行为 `Copyright (c) 2026 haigeerlab`；`.github/dependabot.yml` 只有 github-actions 一项、monthly、cooldown 7 天。
- **AC8** `validate.sh`、phase-guard、verify-artifacts 全绿；CI 的每个检查任务末尾 `git diff --exit-code` 通过。
- **AC9** 合并后、用户说原话后，主干保护的必需检查读回为只有 `CI required`。

## Boundaries

- **会做**：C1～C6 及回归；推送、开 PR（合并由用户）；合并后在用户原话后做 C7。
- **先问再做**：改主干保护（C7）；接入 autopilot（B2）；改插件版本或发版；加 macOS runner。
- **不做**：假设 11 列出的事。

## 并行边界

- 独占：`spec/plugin-spec-compliance.md`、`tasks/plugin-spec-compliance/`、`.github/workflows/ci.yml`、`.github/dependabot.yml`、`scripts/check-frontmatter.py`、`scripts/test_check_frontmatter.py`、`scripts/validate.sh`、`plugins/spec-guard/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`LICENSE`、`CONTRIBUTING.md`、`docs/maintainer-workflow.md`、`CHANGELOG.md`
- 公共：无

## 文档建议

`CONTRIBUTING.md` 的 CI 一段按新任务构成重写，写明必需检查只有 `CI required`；`docs/maintainer-workflow.md` 有 CI 说明就同步。项目没有文档基线。
