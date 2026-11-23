# Plan: review-rounds-in-map

<!-- spec-guard: review approved -->

Spec：[spec/review-rounds-in-map.md](../../spec/review-rounds-in-map.md)（2026-11-23 批准）。

## 架构决定

- **一个解析、两种返回**：`module_stage` 新增 `codex_round_records(text) -> [{"round", "blocking", "sha256"}]`，用现有 `CODEX_ROUND` 正则与 `_visible_lines`；
  `codex_rounds` 改为 `[(r["round"], r["blocking"]) for r in codex_round_records(text)]`，返回值不变，`review_mark` 与 `codex_rounds_exhausted` 不改。
- **`reviewRounds` 放在 `codexRoute` 旁边**：`map_view` 新增 `_review_rounds(root, module)`，对 `spec/<id>.md`、`tasks/<id>/plan.md` 各读一次；文件不存在给 `[]`，
  读失败抛现有的 `Unreadable(path)`（与 `_review` 同样的读失败处理）。表格视图不变。
- **接口**：`interface.json` 1.17，`mapView` 加 `reviewRounds` 字段说明（每项三个键、`sha256` 是报告 sha256 的前 12 位、`[]` 的含义、按文件顺序、不随修订清空）；
  `check-interface.py` 的字段清单与 `test_map_view.py` 的字段集合同步。
- **测试**：在 `test_map_view.py` 加 `ReviewRoundsTest`，用现有 `Project` 夹具直接写轮次行，覆盖 AC1～AC3；读失败用不可读文件覆盖。

## 任务

编码由我（Claude）在本会话完成。

- **Task 0**：提交能力图新行、Spec、本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**：C1 + C2。先写 `ReviewRoundsTest`，确认失败，再实现 `codex_round_records` 与 `reviewRounds`。用例：
  - AC3 三种情形：Codex 批准且最后一轮无阻断；两轮有阻断后用户批准；只有 `codex-reviewed` 轮次、尚未批准。逐项断言 round、blocking、sha256 与文件行相同（AC1）。
  - 修订后复审（假设 5）：已批准的文件改动正文、标记变为 revised，再追加下一轮；断言旧轮次与新轮次都按文件顺序返回，不按批准标记筛选。
  - 空列表与代码块（AC2）：没有轮次行为 `[]`；Spec 文件不存在时 `reviewRounds.spec` 为 `[]`、Plan 一侧照常列出，Plan 文件不存在时反之；代码块里的示例轮次行不计入。
  - 读失败：仿照现有 `test_unreadable_todo_is_exit_4`，对 Plan 文件 `chmod(0)`（root 运行时跳过），断言 `/map --json` 的退出码与诊断与现有 `review` 读失败一致。
  - 接口边界（假设 1、3）：模块 JSON 的键集合（第 26 行的集合）只比现在多 `reviewRounds`；`reviewRounds` 只有 `spec`、`plan` 两个键，每轮只有 `round`、`blocking`、`sha256` 三个键。
  - 表格不变：在 `StatusTest` 现有夹具的 Spec、Plan 里加上轮次行，现有精确表格断言（`test_table_header_and_rows` 等）原样通过；另加一例：同一夹具带与不带轮次行，表格逐字相同。
  验证：`test_map_view`、`test_review_marker`、`test_codex_review` 全绿（AC1～AC4）。
- **Task 2**：C3。`interface.json` 1.17 与 `check-interface.py`；`docs/commands.md` 在 `codexRoute` 那句后补一句；版本号 0.93.0、CHANGELOG、README 中英 `--ref`。验证：`check-interface.py`、`validate.sh`（AC6）。

## 会改哪些文件

- 新增：`spec/review-rounds-in-map.md`、`tasks/review-rounds-in-map/{plan,todo}.md`。
- 修改：`spec/CAPABILITY-MAP.md`、`plugins/spec-guard/hooks/{module_stage,map_view,test_map_view}.py`、`plugins/spec-guard/interface.json`、`scripts/check-interface.py`、
  `docs/commands.md`、两份 `plugin.json`、`CHANGELOG.md`、`README.md`、`README.en.md`。
- 新增依赖、锁文件：无。

## 风险

- **其他读 `/map --json` 字段集合的回归**：新增字段可能让断言完整键集合的测试变红（如 `test_map_view.py` 第 26 行的集合、`check-interface.py`），Task 1、2 一并改。
- **读失败的影响面**：Spec 或 Plan 读不了时整张 `/map` 已经因 `_review` 失败，`reviewRounds` 不新增失败路径。

## 检查点

- Checkpoint 1（report）：逐项给出 AC6 的证据：`/bin/bash scripts/validate.sh`、`/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh`、`/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh`、
  `python3 scripts/check-interface.py` 各自的退出码与末行，以及 `interface.json` 的版本号；变异（`reviewRounds` 写死为 `[]`、丢掉 sha256、不跳过代码块）各让哪条回归变红；
  在本仓库实跑 `/map --json`，看本模块 Plan 的 `reviewRounds.plan` 与文件里的轮次行一致。
- Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行。
- 最终 gate 一并列出合并后要做的事，供用户一次授权：发版（`release.py publish --confirm`、`install --confirm` 都是远端或本机写入，要用户授权原话）；拟回告的对象与正文
  （autopr-design：字段名 `reviewRounds`、格式与 1.17；抄送 ecosystem-lead）。
- 合并后（不在 gate 里勾，记在 todo 的「合并后」一项）：核实已合并后按授权发 0.93.0，通知 ecosystem-lead，把字段与格式发给 autopr-design 并抄送 ecosystem-lead。
  完成证据：Release 地址、发版证据 PR 号、两条邮箱消息号；邮箱不可用时改为提醒用户转告，记下「已提醒、未确认送达」，写进 todo 那一项后再勾。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 未决问题

- 无。

## 外部审查意见

<!-- spec-guard: codex-review round=1 blocking=4 sha256=51d90b14d2df -->
<!-- spec-guard: codex-review round=2 blocking=3 sha256=73c0d0f0121f -->
