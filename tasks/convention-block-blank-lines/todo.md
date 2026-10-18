# Todo: convention-block-blank-lines

- [x] Task 0：提交已批准的 Plan 与 todo — Plan 经用户批准（2026-10-18），与本 todo 一次提交。
- [x] Task 1：回归先红 — `test-setup-teardown.sh` 新增 `blank_lines_ok`（标记前后各一个空行，本地段只查外侧），`block_is` 改为非空行逐字相同＋空行合规；新增两宿主 × 派活关／开的新建（新文件与已有文件）、标准写法再替换不变、旧写法升级预览与写入一致、本地段补外侧空行与格式化后不变共 14 例；改写本地段用例的期望。当前代码上第一条新断言即失败；另在草稿副本用旧实现跑，新段落首例失败。
- [x] Task 2：实现 — `managed-block.py` 新增 `compose`（去模板首尾空行，块标记内侧与本地段前各一个空行）与 `_blank_changes`（difflib 统计空行增删），`replace` 用 `compose` 组装，`--dry-run` 有空行变化时输出 `will adjust blank lines: add N, remove M`，新旧块逐字节相同才输出 `block content unchanged`；`setup-convention.sh` 新建块经 `compose`（输出写临时文件，失败即退出），基础模板与规则段之间空一行；两份规则段模板注释行后加空行。setup/teardown 回归 73 例全绿，往返逐字节还原。
- [x] Task 3：oxfmt 人工核对 — 2026-10-18，使用方项目已装的 oxfmt，只在临时目录跑：工作区版本新建（Claude 与 Codex × 派活关／开，再加一个本地段并 `--replace`）`--check` 退出码都是 0；0.71.0 写的旧块 `--check` 为 1，工作区版本 `--replace --dry-run` 报 `will adjust blank lines: add 2, remove 0`（派活开为 add 4），实际写入恰好新增同样多的空行、0 行删除，升级后 `--check` 为 0。临时目录已删。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无告警 — 随 e80ac7f 跑 `verify-and-commit.sh` 全档：phase-guard、verify-artifacts 68 例、repo-artifacts 5 通过、ShellCheck 无告警；setup/teardown 回归 73 例。
- [x] Task 4：CHANGELOG 与 0.71.1 版本号 — CHANGELOG `[0.71.1]`（1 个模块，修复）；两份 `plugin.json` 改为 0.71.1，中英 README 的 `--ref` 改为 v0.71.1；`commands/setup-convention.md` 预览一段补空行写法与 `will adjust blank lines` 一行。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-18 在对话里列出相对 3f4e54f 的 15 个文件（均在 Plan 范围内）、构建中纠正的两处测试代码、验证结果与未验证项（宿主安装副本放到发版后，未做独立代码评审），以及发给接入协调人的回告草稿；用户验收通过，回告草稿一并批准，确认推送与开 PR。
- [ ] 发版后的验证

## 外部审查意见

<!-- spec-guard: external-review declined -->

用户在最终验收时直接验收通过、没有要求外部审查（2026-10-18）。
