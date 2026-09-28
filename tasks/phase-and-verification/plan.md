# Plan: phase-and-verification

> 登记说明（2026-09-28）：本模块已交付，登记时无待办。本计划只记录交付范围、验证方式与已知缺口，供后续修改时参考。决策见 `docs/decisions/2026-09-28-single-capability-map.md`。

## 范围

阶段注入 hook、只读产物校验与共享检查点规则。

## 实现文件（plugins/spec-guard/ 下）

- hooks/hooks.json、hooks/phase-guard.sh、hooks/verify-artifacts.sh
- references/workflow-checkpoints.md
- commands/phase.md、commands/verify-artifacts.md、skills/spec-guard-ops/SKILL.md（phase and verify）、mcp/claude_desktop_server.mjs（phase、verify）

## 验证

- test-phase-guard.sh（9 例）
- test-verify-artifacts.sh（8 例）
- test-claude-desktop-mcp.sh
- `/bin/bash scripts/validate.sh`

## 已知缺口

- hooks.json 在插件根变量都缺失时回退执行项目内脚本（审计 P1-2），需真实 Codex 宿主确认可利用性
- Codex 下以当前目录而非 Git 根定位项目
- 阶段只到 SPECED，不识别 plan 与 todo（审计 P1-3，需产品决定）
