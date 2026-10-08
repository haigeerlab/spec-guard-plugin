# Plan: map-table-count-diagnostic

依据 [`spec/map-table-count-diagnostic.md`](../../spec/map-table-count-diagnostic.md)。分支 `claude/map-table-count-diagnostic`。

## Overview

两处小改动，各一个 task、一条提交，先写能在当前代码上失败的测试。本模块随 0.55.0 发布：不改版本号、不改
CHANGELOG，变更说明发给发版会话，由它统一写进 0.55.0。

## Architecture Decisions

- 计数报错由 `capability_map.py` 里一个函数生成，严格与历史两处共用；阶段提示和 verify-artifacts 不各自拼文本。
- 行号来自 `_visible_lines` 之后的下标：围栏内容被替换为空行而不是删除，所以下标 + 1 就是原文件行号。

## Task List

### Task 1：模块表计数报错（C1）

新建 `test_capability_map.py`（登记 validate.sh），phase-guard 与 verify-artifacts 回归各加两张表的夹具；实现共用的报错函数。

- 验收：Spec「Testing strategy」单元、phase-guard、verify-artifacts 三组通过；两边回归全量通过。
- 文件：`capability_map.py`、`test_capability_map.py`、`test-phase-guard.sh`、`test-verify-artifacts.sh`、`scripts/validate.sh`

### Task 2：自观测报告排除临时目录（C2）

- 验收：Spec「Testing strategy」self_report 一组通过；本机重跑 F-1203 不含临时目录项目。
- 文件：`scripts/self_report.py`、`scripts/test_self_report.py`

### Checkpoint（gate）：模块评审

全部套件、3.9、CI 同级别 ShellCheck（改了两个 .sh）通过；牙齿检查（去掉行号或去掉排除，相应测试变红）。
本 Plan 获批即授权推送本分支并开本模块 PR；合并由用户进行，合并后通知发版会话并在事项 E0F51J9 记录结果。
