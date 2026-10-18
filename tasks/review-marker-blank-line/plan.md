# Plan: review-marker-blank-line

<!-- spec-guard: review approved -->

依据 [`spec/review-marker-blank-line.md`](../../spec/review-marker-blank-line.md)（已批准）。本仓库评审节奏为分开审：Spec 已批准，本 Plan
单独交审。分支 `claude/review-marker-blank-line`，从 `claude/record-on-receipt` 开出（能力图两行、两份 Spec 与本 Plan 已随那个 PR 提交）。
本 PR 带本模块的改动与 0.70.1 的版本号；在 `record-on-receipt` 的 PR 合并之后合并。

所需工具：无 UI 改动；格式复查用使用者前端里已装好的 `oxfmt`，只读检查临时样本，不改那个仓库。

## Overview

只改 `hooks/review_mark.py` 的 `_with_marker`：写标记时保证标记行前后都是空行（文件开头与末尾除外），已有空行不重复加，换行符沿用原文件。
approve 的指纹本来就基于写好 pending 之后的文本计算，空行在这一步补好，指纹自然一致。

## Architecture Decisions

- **只在写标记时整理。** 不扫描、不批量改已批准文件。
- **整理只限标记行两侧。** 不删多余空行，不碰文件其他部分。
- **指纹计算方式不变。** 复用 `_marked` 现有的「先写 pending 再算指纹」，不另写逻辑。

## Task List

### Task 0：本 Plan 与 todo 已随 `record-on-receipt` 的 Task 0 提交

- 验收：本分支从 `claude/record-on-receipt` 开出后，这两个文件已在。

### Task 1：标记两侧的空行（先红）

`test_review_marker.py` 先加用例并确认失败：Spec 里五种写法 × pending／approved 写出后，标记前后都有空行（文件开头除外），本来合格的写法不多加；
`\r\n` 文件补的也是 `\r\n`；approve 后文件里的指纹等于按最终文件重算的指纹，阶段为已批准；标记在文件末尾时后面不补。再改 `_with_marker`。

- 验收：`test_review_marker.py` 全绿；现有用例不改。
- 文件：`hooks/review_mark.py`、`hooks/test_review_marker.py`。

### Checkpoint 1（report）：三套核心回归全绿

### Task 2：用 `oxfmt --check` 复查

用 review-mark 在临时目录写出五种样本（pending 与 approved 各一份），用使用者前端里的 `oxfmt --check` 逐个检查，退出码记进 todo。

- 验收：十个样本退出码都是 0。
- 文件：无仓库文件改动（只记 todo）。

### Task 3：文档、CHANGELOG 与 0.70.1 版本号

CHANGELOG 把 `[0.70.1]` 写定日期并补本模块一条；两份 `plugin.json` 改为 0.70.1，中英 README 的 `--ref` 改为 v0.70.1。

- 验收：`validate.sh` 通过（清单版本一致）。
- 文件：`CHANGELOG.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、`README.md`、`README.en.md`。

### Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行

列出实际改动、验证结果与未验证项；拟回告：module-crew 插件负责人会话（`local_dbe419ad-a2e3-43c4-9f29-445faa8d7e0e`，Claude 原生会话消息），
发版后告知 0.70.1 版本号、改了什么、已有文件不会被批量改；随后以「已告知」关闭事项 75SV50T。

### 发版后的验证

安装副本上用 review-mark 写一份样本，用 `oxfmt --check` 复查；按拟回告通知报告方并关闭事项。
