# Plan: local-convention

> 登记说明（2026-09-28）：本模块已交付，登记时无待办。本计划只记录交付范围、验证方式与已知缺口，供后续修改时参考。决策见 `docs/decisions/2026-09-28-single-capability-map.md`。

## 范围

本地多模块目录约定的安装与移除。

## 实现文件（plugins/spec-guard/ 下）

- hooks/setup-convention.sh、hooks/teardown-convention.sh、hooks/managed-block.py
- templates/claude-block-local.md、templates/codex-block-local.md、templates/CAPABILITY-MAP.md
- commands/setup-convention.md、commands/teardown-convention.md、skills/spec-guard-ops/SKILL.md（setup）

## 验证

- test_workflow_checkpoints.py（模板中的检查点指令可达）
- scripts/check-readme-sync.py（README 内嵌声明块与模板一致）
- `/bin/bash scripts/validate.sh`

## 已知缺口

- setup 与 teardown 没有回归测试；`--replace` 前不做标记校验，缺 END 标记时会在建好目录后才报错（审计 P2-14）
- teardown 往返会多出一个换行
