# Plan: capability-history

> 登记说明（2026-09-28）：本模块已交付，登记时无待办。本计划只记录交付范围、验证方式与已知缺口，供后续修改时参考。决策见 `docs/decisions/2026-09-28-single-capability-map.md`。

## 范围

历史账本的格式、只读核验与审计、只追加的更正，以及迁移预览。

## 实现文件（plugins/spec-guard/ 下）

- hooks/capability-history.py、hooks/verify-history.sh、hooks/history-migration.py
- commands/history-integrity.md、skills/spec-guard-ops/SKILL.md（history）；Claude Desktop MCPB 的 verify_history、audit_history 已随 MCPB 退役

## 验证

- test-capability-history.sh
- test-history-verification.sh
- test-history-migration.sh
- `/bin/bash scripts/validate.sh`

## 已知缺口

- `history-migration.py import --confirm` 与写入动词没有命令或 skill 入口；是否开放需另行决定
- `artifact_history.py` 已不被 verify-artifacts 调用，是否删除或重新接入需另行决定
