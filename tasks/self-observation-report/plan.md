# Plan: self-observation-report

依据 [`spec/self-observation-report.md`](../../spec/self-observation-report.md)。分支 `claude/plugin-observability-self-optimization-1e4302`。

## Overview

一个只读维护者脚本 `scripts/self_report.py`（python3 标准库），读两个宿主的会话记录，抽出 spec-guard 注入事件，
按两个信号汇总成带指纹的发现项。三个 task 串行，每个 task 一条提交，先写能在当前代码上失败的测试并记录失败输出。

## Architecture Decisions

- **读取层 → 信号层 → 输出层**：两个 reader 只产出统一的注入事件（时间、宿主、项目、会话、行号、阶段、建议行），
  信号与输出与宿主无关。
- **复用而不复制**：JSONL 逐行读取与时间戳解析从 `plugins/spec-guard/hooks/module_cost_report.py` 导入。
- **夹具全部合成**：`--claude-home` / `--codex-home` 指向临时目录，测试不读本机真实会话。
- **不进发布包、不改版本号**：脚本在 `scripts/` 下，插件包内容不变，所以本模块不发版、不改清单版本、不写 CHANGELOG；
  合并即完成。
- 共同验证命令（每个 task 都跑，并在 `PATH=/usr/bin:/bin` 的 python3 3.9 下再跑一次测试）：

  ```bash
  python3 -B scripts/test_self_report.py
  /bin/bash scripts/validate.sh
  ```

## Task List

### Task 1：注入事件读取（C1）

新建脚本与测试，登记 `scripts/validate.sh`。Claude 读顶层 transcript 的 `hook_additional_context` 附件，Codex 读
非子线程 rollout 的 developer 消息；只取 spec-guard 段；解析阶段与建议行；`--since`。

- 验收：Spec「Testing strategy」读取一组全部通过；在本机真实数据上 `--since 3650d` 的阶段分布与 Spec「数据来源」的实测数量级一致。
- 文件：`scripts/self_report.py`、`scripts/test_self_report.py`、`scripts/validate.sh`

### Task 2：信号、指纹与输出（C2–C4）

S1 重复未变、S2 诊断态；归一化与指纹；跨项目合并；人读与 `--json`；项目哈希与 `--reveal`；「无法观测」一节。

- 验收：Spec「Testing strategy」的 S1、S2、指纹、隐私各组全部通过；同一数据运行两次输出完全相同。
- 文件：`scripts/self_report.py`、`scripts/test_self_report.py`

### Checkpoint 1（gate）：真实数据验收

在本机真实数据上运行 `--since 3650d`，把报告给用户看；用独立的一次性脚本手工统计 S2 次数并对照；确认默认输出中找不到
真实项目路径；做一次牙齿检查（改坏 S1 阈值判断或去掉脱敏，相应测试必须变红）。用户看过报告、确认判断合理后才继续。

### Task 3：维护者流程文档（C5）

`docs/maintainer-workflow.md` 增加「自观测报告」一节：运行、挑选、按指纹查账本、预览后建事项并去掉真实项目名、以「不修」关闭的用法。

- 文件：`docs/maintainer-workflow.md`

### Checkpoint 2（gate）：模块评审

全部套件通过（validate.sh、phase-guard、verify-artifacts）。本 Plan 获批即授权推送本分支并开本模块 PR；合并由用户进行。
