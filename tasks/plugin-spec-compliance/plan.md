# Plan: plugin-spec-compliance

<!-- spec-guard: review pending -->

Spec：[spec/plugin-spec-compliance.md](../../spec/plugin-spec-compliance.md)（2026-11-24 批准）。

## 架构决定

- **检查名平移，不卡当前 PR**：任务 `validate` 保留单元素矩阵 `os: [ubuntu-latest]`，检查名仍是 `validate (ubuntu-latest)`；新增 `python`（矩阵 `["3.9", "3.13"]`）、`plugin`、汇总 `CI required`。
  主干保护在合并后、用户原话后才换成只要 `CI required`；之后 `validate` 改不改名都不再碰主干保护。
- **`CI required` 的判定**：`needs: [validate, python, plugin]`，`if: always()`；步骤用 `${{ toJSON(needs) }}` 交给 python 一行判断，任何一个 `result` 不是 `success` 就退出 1，并打印哪个任务是什么结果。
  不用第三方 action。
- **最小权限**：顶层 `permissions: {}`；三个检查任务各 `permissions: {contents: read}`；`CI required` 不读代码，`permissions: {}`。所有 `actions/checkout` 带 `persist-credentials: false`。
  `uses:` 一律 `owner/repo@<40 位 SHA> # vX.Y.Z`：checkout v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`、setup-python v7.1.0 `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`、
  setup-node v7.1.0 `949feb2413d6458794dcd2491c4babbbce0c15c1`（均已用 `gh api repos/<repo>/git/ref/tags/<tag>` 读到，类型 commit）。
- **`plugin` 任务**：setup-node（Node 22）后 `npx --yes @anthropic-ai/claude-code@2.1.328 plugin validate --strict plugins/spec-guard` 与 `... --strict .`；
  setup-python 3.13 后 `pip install pyyaml==6.0.3`，跑 `python3 scripts/check-frontmatter.py` 与两份带 YAML 的回归（下一条）。
- **两份新脚本**（都用 PyYAML，没有时退出 2 并说明，回归里 `skipUnless`）：
  - `scripts/check-frontmatter.py`：扫 `plugins/*/skills/*/SKILL.md`、`plugins/*/agents/*.md`（name、description）、`plugins/*/commands/*.md`（description）；frontmatter 必须是文件开头的
    `---` 块、`yaml.safe_load` 得到映射、必填项是非空字符串；问题逐条打印 `路径: 原因`，有问题退出 1。
  - `scripts/test_ci_workflow.py`：解析 `.github/workflows/*.yml`，断言 AC5（顶层 `permissions == {}`、每个任务 `permissions` 只有 `contents: read` 或为空、checkout 都有 `persist-credentials: false`、
    `uses:` 都是 40 位 SHA、`on` 里没有 `paths`／`paths-ignore`、`CI required` 的 needs 恰好是其余全部任务且 `if: always()`）。以后改 workflow 漏了哪条，它会红。
  - 两份回归登记进 `validate.sh`（本机系统 Python 没有 PyYAML 时跳过，不算失败；`plugin` 任务里装了 PyYAML 真跑）。
- **`git diff --exit-code`**：`validate`、`python` 两个任务在全部检查之后单独一步（规范 C10），`plugin` 任务同样加。
- **Python 3.9**：实测只有 `scripts/check-local-paths.py` 第 23 行的 `re.Pattern | None` 在 3.9 导入时报错（全仓库 AST 扫描只此一处），加 `from __future__ import annotations`。
- **清单**：Claude `plugin.json` 删 `requires`；`marketplace.json` 加顶层 `description`（一句中文，与 README 首句一致）。`validate.sh` 的清单一致性检查只比名字与版本，不受影响（实现时核对）。
- **dependabot**：`version: 2`，一项 `package-ecosystem: github-actions`、`directory: "/"`、`schedule.interval: monthly`、`cooldown.default-days: 7`。

## 任务

每个任务先写回归、确认失败再实现（配置文件类的由 `test_ci_workflow.py` 先红后绿）。

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**：Python 3.9 兼容（C5）。先用本机 3.9.6 复现 `test_check_local_paths` 失败，再加 `from __future__ import annotations`。验证：`PATH` 前置 3.9 的 `python3` 跑 `validate.sh` 退出 0。
- **Task 2**：`check-frontmatter.py` 与回归（C2）。回归：skill 缺 `name`、缺 `description`、YAML 写坏、没有 frontmatter、command 没有 `name` 也通过、agent 同 skill；本仓库现状通过。验证：`python3 scripts/test_check_frontmatter.py`（本机 3.10 有 PyYAML）。
- **Task 3**：清单（C3）。验证：本机 `claude plugin validate --strict plugins/spec-guard` 与 `--strict .` 都退出 0；`validate.sh` 通过。
- **Task 4**：workflow、dependabot、LICENSE（C1、C4）。先写 `test_ci_workflow.py` 对现在的 `ci.yml` 跑红，再重写 `ci.yml`、加 `dependabot.yml`、改 LICENSE 版权行。验证：`test_ci_workflow.py` 绿；`yaml.safe_load` 两个文件。
- **Task 5**：文档（C6）。`CONTRIBUTING.md` 的 CI 段落（任务构成、Python 3.9、必需检查 `CI required`、ShellCheck 仍在 `validate`）；`docs/maintainer-workflow.md` 第 172 行一带「CI 仍是合并前的必需检查」补上检查名；CHANGELOG 未发布段。验证：`validate.sh`。

## 会改哪些文件

- 新增：`tasks/plugin-spec-compliance/{plan,todo}.md`、`.github/dependabot.yml`、`scripts/check-frontmatter.py`、`scripts/test_check_frontmatter.py`、`scripts/test_ci_workflow.py`。
- 修改：`.github/workflows/ci.yml`、`scripts/check-local-paths.py`、`scripts/validate.sh`、`plugins/spec-guard/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`LICENSE`、`CONTRIBUTING.md`、`docs/maintainer-workflow.md`、`CHANGELOG.md`。
- 超出 Spec 并行边界的：`scripts/check-local-paths.py`（Task 1 实测才知道要改它）、`scripts/test_ci_workflow.py`（为 AC5 加的回归）。
- 新增依赖：CI 里装 PyYAML 6.0.3（只在 `plugin` 任务）与 npx 拉 `@anthropic-ai/claude-code@2.1.328`；仓库不加锁文件。

## 风险

- **CI 上 `claude plugin validate` 要不要登录、能不能离线跑**：本机实测不需要登录；CI 上第一次跑才知道。缓解：Checkpoint 2 推送后看 `plugin` 任务；失败就停下交用户，不改成 `|| true`。
- **3.13 上某些回归行为不同**：缓解：`python (3.13)` 首跑失败就当真问题查，不放宽。
- **汇总任务写错导致永远绿**：缓解：AC2 在 PR 上推临时提交实测失败路径；`test_ci_workflow.py` 锁 needs 与 `if: always()`。
- **主干保护切换窗口**：合并前必需检查仍是 `validate (ubuntu-latest)`，新 workflow 照样产出它，不会卡；切换在合并后单独做。

## 检查点

- Checkpoint 1（report）：本机证据——`validate.sh`（默认 Python 与 3.9.6 各一次）、phase-guard、verify-artifacts 的退出码与末行；`--strict` 两条退出 0；`check-frontmatter.py` 与两份回归；
  变异：`check-frontmatter.py` 不查 `name` → 回归变红；`ci.yml` 删掉 `if: always()` → `test_ci_workflow.py` 变红。记进 todo。
- Checkpoint 2（gate）：推送分支、开 PR（#486 合并后以 main 为基，未合并则先等）；看 CI 五个检查；按 AC2 推一个删掉某 command `description` 的临时提交，确认 `plugin` 与 `CI required` 失败，再推撤销提交恢复全绿。
  推送和临时提交要你同意后才做。
- Checkpoint 3（gate）：最终验收（AC1～AC8 证据）；合并由用户进行。合并后、`CI required` 在 main 跑绿、你说原话后，切主干保护（AC9），读回给你看。

## 预先声明

- 公共路径：无
- 外部依赖：`pyyaml@6.0.3`、`@anthropic-ai/claude-code@2.1.328`、`actions/setup-python@v7.1.0`、`actions/setup-node@v7.1.0`
- 质量与工作区配置：`.github/workflows/ci.yml`、`.github/dependabot.yml`
- 补丁：无

## 未决问题

- 无。
