# Plan: plugin-interface

<!-- spec-guard: review pending -->

依据 [`spec/plugin-interface.md`](../../spec/plugin-interface.md)。本仓库评审节奏为分开审：Spec 已于 2026-10-17 单独批准（随 #339
合并），本 Plan 单独交审。分支 `claude/plugin-interface`，worktree `.claude/worktrees/current-plugin-owner-aa5b98`，从 `bda78de`
（v0.65.0 发版证据合并）开出。本模块一个 PR，含 0.66.0 版本号；合并后的发版步骤按 `docs/release-process.md` 另走。

所需工具：无 UI 改动，不需要浏览器或电脑操作。

## Overview

先把两组取值集合提成常量，让代码和接口说明能对上；再给 map-view 的 JSON 加 `externalReview`；然后写 `interface.json` 和校验它的
检查器；最后补文档、CHANGELOG 和版本号。

## Architecture Decisions

- **取值集合放在 `module_stage.py` 里作常量。** `REVIEW_STATES = ("none", "pending", "approved", "revised", "invalid")`、
  `EXTERNAL_REVIEW_STATES = ("none", "recorded", "declined")`。`review_state` 和 `external_review_state` 的返回值由测试保证
  落在集合里；检查器直接导入这两个常量对照，不另抄一份。
- **map-view 复用 `external_review_state`。** 它返回 None（文件读不出）时抛 `Unreadable`，走现有的退出码 4，与 `_review` 的
  处理一致，不输出半张图。
- **检查器单独一个文件 `scripts/check-interface.py`。** 由 `validate.sh` 调用，正反例写进 `scripts/test-checkers.sh`，与
  `check-manifests.py` 同一做法。它只读 `interface.json`，导入 `map_view` 与 `module_stage` 拿常量，不运行 map_view。
- **`interface.json` 放在插件根目录 `plugins/spec-guard/`。** git archive 打包时会自动带上，不需要改打包步骤；Codex 与 Claude
  的安装副本都在插件根下，路径一致。

## Task List

### Task 0：提交已批准的 Plan 与 todo

Plan 获批后用 `review_mark` 记批准，和 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：取值常量（先红后绿）

先在 `test_review_marker.py`（或 `test_map_view.py`）加断言：两组常量存在，并且现有各种标记、各种外部审查记录得出的值都落在
集合里。确认它们是红的，再在 `module_stage.py` 加常量，转绿。

- 验收：新断言全绿；phase-guard 回归不变（362 例）。

### Task 2：map-view 的 `externalReview`（先红后绿）

先在 `test_map_view.py` 写失败用例：
- `MODULE_KEYS` 加 `externalReview`；
- 三种取值各一例：Spec 里记录、todo 里记录、只有拒绝标记；
- 小节标题在但内容为空时为 `none`；
- todo 读不出时退出码 4。

再改 `map_view.build`，转绿。`spec/map-view.md` 的 JSON 示例和字段说明同步补上这一项。

- 验收：`test_map_view.py` 全绿；其余字段的断言不变；表格输出的用例不变。

### Task 3：`interface.json` 与检查器（先红后绿）

先在 `scripts/test-checkers.sh` 写 `check-interface.py` 的正反例，确认它们是红的：
- 反例：不是合法 JSON；`interface` 不是 `<主>.<次>`；`schemaVersion` 与代码不一致；`values.review` 少一个取值；
  `values.externalReview` 多一个取值；`command` 指向不存在的脚本；
- 正例：一份正确的副本。

再写 `scripts/check-interface.py` 和 `plugins/spec-guard/interface.json`（内容按 Spec 的 Contract），接进 `validate.sh`。

- 验收：检查器回归全绿；`validate.sh` 通过；在草稿副本上把真 `interface.json` 的 `schemaVersion` 改成 2，`validate.sh` 变红，
  复原后转绿。

### Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告

随 Task 3 的提交跑 `verify-and-commit.sh` 全档。

### Task 4：文档、CHANGELOG 与版本号

- `docs/design.md` 新增「对外接口」一小节：interface.json 管什么、版本规则、使用方怎么读，点明 spec-guard 读 agent-relay 用的
  是同一方式；部件表里 `map_view.py` 一行补一句「接口说明见 interface.json」；
- README 中英各加一句：对外只读接口见插件根目录的 `interface.json`，格式说明见 `docs/design.md`「对外接口」；
- CHANGELOG `[0.66.0]` 记一条「新增」；
- 两份 `plugin.json` 改为 0.66.0，README 中英的 `--ref` 改为 v0.66.0。

- 验收：`validate.sh` 全档通过（含 `check-readme-sync.py`）。

### Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行

在正文列出这些内容：
- 实际改动的文件，取自版本库；
- `interface.json` 全文；
- 一份 map-view JSON 里某个模块的样例（含 `externalReview`）；
- 验证结果和未验证项；
- 文档建议；
- 拟回告：对象是 spec-guard-monitor，经「Codex LIVE-SAAS 前端基础架构监测」（`local_4f410de8-418e-440c-90d8-436a73edcc6b`）
  转达，同时请它转告 decision-inbox 负责人可以改为按 interface.json 读；时机是 0.66.0 装上之后。

这是本模块的最终验收检查点。装了 delegate 时阶段提示会提议外部审查，按 0.65.0 的规则处理（只提议，用户同意才发起）。

- 验收：用户验收通过。

### 发版后的验证

- 两边升级到 0.66.0；
- 在两个安装副本里确认 `interface.json` 存在、`check-interface.py` 的判据对安装副本成立；
- 用 `interface.json` 里的 `command` 在一个临时项目上跑一次 map-view，确认输出带 `externalReview`、`schemaVersion` 为 1；
- 回告来源。

## 影响面

- 新增：`plugins/spec-guard/interface.json`、`scripts/check-interface.py`；
- 修改：`hooks/module_stage.py`（常量）、`hooks/map_view.py`、`hooks/test_map_view.py`、`test_review_marker.py`（或同类测试）、
  `scripts/test-checkers.sh`、`scripts/validate.sh`、`spec/map-view.md`、`docs/design.md`、README 中英、CHANGELOG、两份 `plugin.json`；
- 本模块的 Plan 与 todo。

## Risks and Mitigations

- **改了 map-view 的 JSON，使用方的严格解析会出问题。** 只增字段，`spec/map-view.md` 已承诺读取方忽略不认识的字段；
  `schemaVersion` 不变。
- **interface.json 和代码以后各改各的。** 由检查器在每次 `validate.sh` 时卡住。
- **`map_view` 多读一次 Spec 和 todo。** 都是本地小文件，map-view 本来就会读它们，开销可以忽略。

## Open Questions

- 无。
