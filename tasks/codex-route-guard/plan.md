# Plan: codex-route-guard

<!-- spec-guard: review approved -->

Spec：[spec/codex-route-guard.md](../../spec/codex-route-guard.md)（2026-11-22 批准）。

## 架构决定

- **判定只有一处**：兜底检查和 `codexRoute` 都直接调 `module_stage.codex_route(root, module, kind)`，不复制规则；`review_mark` 在 `_codex` 之前、读报告之前调用它，只对 `codex-approved` 生效。
  原因码 = `"codex-route-" + codex_route(...)`。
- **`codexRoute` 放在 `_approved_by` 旁边**：`map_view` 每个模块组装时加 `{"spec": codex_route(...) or None, "plan": ...}`；表格视图不变。
- **验收记录两处读、一处写**：`module_stage` 拆出 `acceptance_path`（写入位置：`--git-common-dir` 下）和旧位置（`--git-path`）；`acceptance_record` 先读新位置，读不到有效记录再读旧位置。
  `review_mark._acceptance` 写到新位置。主 checkout 里两处是同一个文件，行为不变。
- **测试**：用临时 git 仓库加 `git worktree add --detach` 覆盖跨 worktree；`codex_route` 的四种取值用现有测试里的接管配置夹具构造。

## 任务

编码任务（Task 1～3）交给 Codex（`/delegate:run --write`），我写派活说明、验收（读差异、自己重跑、变异）、提交。

- **Task 0**：提交能力图新行、Spec、本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**（Codex）：C1。`review_mark` 的 codex-approved 兜底与三个原因码，`codex-reviewed` 不受限；回归写在 `test_review_marker.py`（或 `test_codex_review.py` 里已有 codex-approved 用例的地方），先写测试确认失败（AC1、AC2）。
- **Task 2**（Codex）：C2。`map_view` 的 `codexRoute`，`interface.json` 加 `mapView.codexRoute` 并升 1.16，`scripts/check-interface.py` 与 `test_map_view.py` 同步；先写测试确认失败（AC3）。
- **Task 3**（Codex）：C3。验收记录写到公共 git 目录、读取先新后旧，`interface.json` 的 `mapView.acceptance` 与 `reviewMark` 说明同步；回归用 linked worktree（AC4、AC5）；先写测试确认失败。
- **Task 4**（我）：`commands/review-mark.md`（被拒时改用 codex-reviewed）、`reviewMark` 退出码说明加 `codex-route-*`、版本号 0.92.0、CHANGELOG、README 中英 `--ref`。

## 会改哪些文件

- 新增：`spec/codex-route-guard.md`、`tasks/codex-route-guard/{plan,todo}.md`。
- 修改：`spec/CAPABILITY-MAP.md`（新行）、`plugins/spec-guard/hooks/{review_mark,map_view,module_stage}.py` 及对应测试、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、
  `plugins/spec-guard/commands/review-mark.md`、两份 `plugin.json`、`CHANGELOG.md`、`README.md`、`README.en.md`。
- 新增依赖、锁文件：无。

## 风险

- **`codex_route` 读不到配置或 Spec 时的取值**：它现在在 `_takeover_item` 不是 codex 时返回 `takeover`，读失败也落到这里，方向是要人批，符合兜底的意图；Task 1 的用例覆盖「没有接管配置」。
- **`--git-common-dir` 的相对路径**：在主 checkout 里返回 `.git`（相对），linked worktree 里返回绝对路径；照 `acceptance_path` 现有写法按 root 补全，Task 3 两种都测。
- **`check-interface.py` 对新字段的约束**：它核对接口文件与实现常量一致，像 `reviewApprovedBy` 对 `map_view.APPROVED_BY` 那样，加字段时要在 `map_view` 加取值常量并登记到 `check-interface.py`，派活说明里写明。

## 检查点

- Checkpoint 1（report）：完整检查与变异（去掉兜底检查、`codexRoute` 写死为 null、读取只读旧位置，各让回归变红）；在临时项目实跑：未接管模块写 codex-approved 被拒、
  `/map --json` 显示 `codexRoute`、linked worktree 记的验收在主 checkout 读得到。
- Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行；合并后用 `scripts/release.py` 发 0.92.0，通知 ecosystem-lead，并回告 mc-coord 字段名与版本。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 未决问题

- 无。
