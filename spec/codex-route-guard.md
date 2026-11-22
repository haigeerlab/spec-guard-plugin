# Spec: codex-route-guard

<!-- spec-guard: review approved 6df7478e5319 -->

## Objective

把「这一步能不能由 Codex 批」的判定收回 spec-guard 一处，并让 Codex 最终验收记录在多个 worktree 之间可见：

1. **写入兜底**：`review_mark --state codex-approved` 现在只看审查报告，不看模块接管设置；能不能由 Codex 批，只靠调用方自己抄 `codex_route` 的三条规则。
   M1 沙箱里，一份 spec-guard 判为要人批的 Plan 被写上了 codex-approved（S106）。阶段提示照样当它待批准，所以没有被放行，但标记本身是错的，而且调用方抄的规则一旦和这里分叉，分叉的方向是放行。
2. **结论共享**：`/map --json` 直接给出每个模块 Spec、Plan 的 Codex 判定和原因，module-crew 改为读这个字段，不再照抄规则。
3. **验收记录跨 worktree**：autopilot 打算在检出到合并提交的 detached worktree 里记最终验收。现在的记录用 `git rev-parse --git-path` 定位，在 linked worktree 里落在 `.git/worktrees/<名>/` 下，主 checkout 读不到，删 worktree 时也会一起删掉（2026-11-22 实测）。

给谁用：autopilot 与 module-crew（调用 `review_mark`、读 `/map --json`），以及照阶段提示操作的 agent。

对外接口与用法草案一致吗：S101 的用法草案 `spec/usage/auto-takeover.md` 的 M1～M3 已确认，本模块是 S106 的后续修补，不加进那份草案的里程碑表。

登记：ecosystem-lead #22086（转 mc-coord #22083，用户在 mc-coord 会话 11-22「都按推荐」，同意由 module-crew 提出），mc-coord #22084（验收记录跨 worktree）。
需求确认：用户 2026-11-22「说完了，A」（三条一个模块、一次发版）。账本 TG2Y1YT。

## Assumptions

1. **兜底只挡 codex-approved**：`--state codex-approved` 在 `--target spec|plan` 时，先算 `module_stage.codex_route(root, module, kind)`；结果不为空就拒绝写入，预览也拒绝，退出 2，
   原因码为 `codex-route-takeover`、`codex-route-important`、`codex-route-pre-declared` 之一，并提示「改用 `--state codex-reviewed` 记下这一轮，由用户批」。
   这个检查放在读报告之前，不写轮次行。`codex-reviewed`（只记一轮、不写批准标记）不受影响；`approved`、`pending` 不受影响。
2. **已有的错标记不动**：文件里已经写着的 codex-approved，阶段提示与 `/map` 本来就按 `effective_review` 当待批准，本模块不清理、不报错。
3. **`codexRoute` 字段**：`/map --json` 每个模块加 `codexRoute: {"spec": …, "plan": …}`，值为 `null`（Codex 可以批）或 `"takeover"`、`"important"`、`"pre-declared"`，与 `codex_route` 同一函数、同一判定。
   我在 #22075 里给 mc-coord 的暂定值用的是 `""`，这里改为 `null`，与 `reviewApprovedBy` 一致；回告时一并说明。Spec 或 Plan 文件不存在时照常判定（判定不依赖文件本身的批准标记）。
4. **验收记录位置**：写入改到公共 git 目录 `$(git rev-parse --git-common-dir)/spec-guard/acceptance/<id>.json`；读取先读公共位置，没有再读旧位置（`--git-path` 算出的那个，主 checkout 里两者相同）。
   不迁移、不删除旧文件。记录对所有 worktree 可见，但阶段提示仍只在记录的 sha 是本 worktree 的 HEAD 或其祖先时才算最终 gate 已过，这条不变；`mapView.acceptance` 照旧只报 {marker, sha}。
5. **接口**：`interface.json` 升到 1.16：加 `mapView.codexRoute`，更新 `mapView.acceptance` 的记录位置说明，`reviewMark` 退出码 2 的说明加上 `codex-route-*`。`check-interface.py` 与相关回归同步。
6. **版本**：插件版本 0.92.0（新增接口字段，次版本）；CHANGELOG、README 中英文 `--ref` 随之改。合并后用 `scripts/release.py` 发版，并通知 ecosystem-lead。
7. **不做**：不改 `codex_route` 本身的三条判定规则；不改 `--target acceptance` 的三样证据要求；不替 module-crew 改它的代码。

## Contract

- **C1** `hooks/review_mark.py`：codex-approved 写入前的 `codex_route` 检查与原因码（假设 1）。
- **C2** `hooks/map_view.py`：每个模块的 `codexRoute`（假设 3）。
- **C3** `hooks/module_stage.py`：验收记录写入公共 git 目录、读取先新后旧（假设 4）。
- **C4** 接口与文档：`interface.json` 1.16、`check-interface.py`、`commands/review-mark.md`、`commands/map.md`（如提到字段）、CHANGELOG、版本号（假设 5、6）。

## Acceptance criteria

- **AC1** 模块 takeover 没把 Spec 交给 Codex 时，`review_mark --target spec --state codex-approved --review <报告>` 预览与 `--confirm` 都退出 2、输出 `codex-route-takeover`，文件字节不变；Plan 有非空预先声明时为 `codex-route-pre-declared`；Spec 判为重要需求时为 `codex-route-important`。
- **AC2** `codex_route` 为空时行为与现在一致（写轮次行与 Codex 标记）；`--state codex-reviewed` 在 `codex_route` 不为空时仍能记下一轮。
- **AC3** `/map --json` 每个模块都有 `codexRoute`，两项取值与 `codex_route` 对每个模块、每种 kind 的结果一致（回归里覆盖四种取值）。
- **AC4** 在 linked worktree 里成功记录的验收，在主 checkout 运行 `/map --json` 时 `acceptance` 读得到；主 checkout 阶段提示在记录的 sha 是 HEAD 的祖先时视最终 gate 已过，sha 不是祖先时不算。
- **AC5** 只有旧位置记录的项目（升级前在 linked worktree 里记过）照样读得到；两处都有时以公共位置为准。
- **AC6** 变异：去掉 C1 的检查、`codexRoute` 改用另一套判定、读取只读旧位置，各自让对应回归变红。
- **AC7** `validate.sh`、phase-guard、verify-artifacts 全绿；`interface.json` 为 1.16，`check-interface.py` 通过。

## Boundaries

- **会做**：C1～C4 及回归。
- **先问再做**：改 `codex_route` 的判定规则；清理或迁移已有的错标记、旧位置的验收记录；让 `codex-reviewed` 也受限。
- **不做**：假设 7 列出的事。

## 并行边界

- 独占：`spec/codex-route-guard.md`、`tasks/codex-route-guard/`、`plugins/spec-guard/hooks/review_mark.py`、`plugins/spec-guard/hooks/map_view.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test_codex_review.py`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、`plugins/spec-guard/commands/`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、`CHANGELOG.md`、`README.md`、`README.en.md`
- 公共：无

## 文档建议

`commands/review-mark.md` 写明 codex-approved 会先按接管设置判定、被拒时改用 codex-reviewed；`interface.json` 是 module-crew 读的权威说明。README 只改 `--ref`。项目没有文档基线。
