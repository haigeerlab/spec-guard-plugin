# Plan: reflow-tolerant-replace

<!-- spec-guard: review approved -->

依据 [`spec/reflow-tolerant-replace.md`](../../spec/reflow-tolerant-replace.md)（2026-11-02 用户在本会话批准：「批准」，能力图新行同时确认写入）。
分支 `claude/reflow-tolerant-replace`（从 `origin/main` `27abd5dc` 开出），worktree `distracted-morse-46ef70`。串行，在本会话做。
本模块改版本号到 0.86.2。

## Overview

先在 `test-setup-teardown.sh` 写「只改折行」与「真删了字」的正反用例，确认在 0.86.1 上失败；再在 `managed-block.py` 里把
删减判定从逐行改为按段比较。随后把两份模板改成每条规则一行并同步文档，最后改版本号与 CHANGELOG，用真实格式化结果比对一次，交最终验收。

## Architecture Decisions

1. **新增 `_units(lines)`**，放在 `_text` 旁边：按 Spec 的切段规则把块内行切成段，返回 `(显示文字, 键)` 的列表。显示文字是该段各行
   去首尾空白后用一个空格拼起来的结果；键是去掉全部空白、去掉续行 `>` 前缀后的文字。代码围栏内每行自成一段。只用标准库 `re`。
2. **`replace` 与 `remove` 只换比较这一层**：`removed`、`added`、`needs_accept` 与 `_known` 改用段的键；`_refuse` 与预览打印显示文字。
   写入路径（`compose`、`atomic_write`、本地段、空行处理、teardown 的逐字节往返）一行不动。`_text` 仍留给本地段行数统计用。
3. **`_known` 也按段**：`--known` 模板（现行模板与派活规则段模板）切段后取键的集合。
4. **模板改法**：两份 `*-block-local.md` 的续行拼到上一行、开头两行 `>` 拼成一行，中文接中文不加空格，挨着英文或代码留一个空格；
   拼完逐字核对文字未变（去掉全部空白后与 0.86.1 模板相同）。`docs/convention-block.md` 内嵌的块照新模板改，并补一句：
   格式化工具只改折行与空白时 `--replace` 与 teardown 不报删减。
5. **夹具自己生成**：测试里用一小段 Python 把块的软换行换成一个空格（模拟 `proseWrap: 'never'`），或在长行的固定位置插入
   「换行加两格缩进」（模拟旧模板与会折行的格式化），不依赖外部格式化工具，也不依赖 git tag。
6. **真实结果比对**放在 Checkpoint 1：从信箱重读 ecosystem-lead 转来的块（#15713，只含模板文字），放进临时项目，对新代码与新模板
   跑 `--replace --dry-run` 与 teardown 预览；这份材料不进仓库。
7. **发版**照 0.86.1：合并后核对、打 tag、打包、Release、两个宿主核对（Codex 先请你重新批准 hook）、证据收尾 PR，最后告诉总负责人。

## Task List

### Task 0：提交能力图新行、已批准的 Spec 与 Plan 草稿

- 验证：verify-artifacts 0 失败；快档提交。

### Task 1：删减判定按段比较（成功标准 1、2、5）

- 文件：`hooks/managed-block.py`、`hooks/test-setup-teardown.sh`。
- 用例：
  - 正例（块被拼成单行，每处软换行一个空格）：Claude 侧与 Codex 侧 `--replace --dry-run` 不出现 `[needs --accept-removals]`；`--replace`
    不带 `--accept-removals` 成功、写入后块与模板一致；teardown 预览不出现 `[needs --accept-removals]`、真正移除成功且往返照旧；
  - 反例：拼成单行后删掉一条规则里的几个字、删掉整条规则：`--replace` 与 teardown 不带 `--accept-removals` 都拒绝、文件不变；
    改一个词：预览列出一删一增；
  - 既有用例（手改行、本地段、空行、往返）全部通过。
- 验证：新正例在 0.86.1 上失败、改后通过；`test-setup-teardown.sh` 全部通过。

### Task 2：模板每条规则一行与文档（成功标准 3、4）

- 文件：`templates/claude-block-local.md`、`templates/codex-block-local.md`、`docs/convention-block.md`、`hooks/test-setup-teardown.sh`。
- 用例：按决定 5 生成「有续行」的旧块，升级到新模板不报需要接受的删减。
- 验证：两份模板去掉全部空白后与改前相同；模板里不再有缩进续行；`check-readme-sync.py` 与 `test-setup-teardown.sh` 通过。

### Task 3：版本号与 CHANGELOG（PR 最后一个内容提交）

- 文件：两份 `plugin.json`、README 中英 `--ref`、`CHANGELOG.md`（0.86.2：修复、文档）。
- 验证：`check-readme-sync.py`、`check-manifests.py` 通过。

### Checkpoint 1（report）：发布前完整检查与真实结果比对

- macOS 系统 `/bin/bash` 跑 `validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 并记录主机；ShellCheck；`evals/codex-plugin-smoke.sh --selftest`。
- 变异（草稿副本）：比较改回逐行、去掉续行拼接，两处都要让 `test-setup-teardown.sh` 变红。
- 真实结果比对（决定 6），结果记入 todo。

### Checkpoint 2（gate）：最终验收

- 呈现做了什么、成功标准证据、文档与改动表、提交表、Spec 中途改动（如有）、拟回告。通过即同时授权：推送、开 PR；你合并后由我核对合并并按发版步骤一次做完。

### 发版（合并后，按 Checkpoint 2 的授权）

- 核对合并、打 `v0.86.2`、打包、Release、比对 SHA-256；刷新并核对 Claude 与 Codex 安装副本（Codex 先请你在命令行版 `codex` 的 `/hooks` 重新批准再跑 smoke）；
  收尾扫描、证据收尾 PR；按批准的原文回告总负责人。任一步失败就停下说明。

## Files likely touched

- 插件包：`hooks/managed-block.py`、`hooks/test-setup-teardown.sh`、`templates/claude-block-local.md`、`templates/codex-block-local.md`、两份 `plugin.json`
- 仓库：`docs/convention-block.md`、`README.md`、`README.en.md`（只改 `--ref`）、`CHANGELOG.md`；收尾 PR：`docs/releases/v0.86.2-*.json`
- 记录：`spec/CAPABILITY-MAP.md`（已写入）、`spec/reflow-tolerant-replace.md`、本 Plan、`tasks/reflow-tolerant-replace/todo.md`
- 新增依赖、锁文件改动：无。不碰 `setup-convention.sh`、`teardown-convention.sh`（它们只转述 managed-block.py 的输出）、派活规则段模板、阶段判定。

## 风险

- **切段规则误把两条规则并成一段**：模板每条规则都以 `- ` 开头，按列表标记切段；Task 1 的「删掉整条规则」反例兜住。
- **既有用例依赖逐行输出**：预览对单行规则的输出不变（显示文字就是那一行）；有用例变红就在 todo 里列出原因再改。
- **模板拼行改了文字**：Task 2 用「去掉空白后相同」逐字核对。
- **`.sh` 改动**：只有测试脚本；按 CI 参数跑 ShellCheck。
