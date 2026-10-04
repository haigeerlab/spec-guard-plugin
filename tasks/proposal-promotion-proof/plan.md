# Plan: proposal-promotion-proof

> 登记说明：转为单一能力图时，本模块的 initiative 时期计划被原样恢复
> （见 [`docs/decisions/2026-09-28-single-capability-map.md`](../../docs/decisions/2026-09-28-single-capability-map.md) 的「本次改动」第一条）。登记时模块已交付，因此没有
> `tasks/<module-id>/todo.md`；`plan-without-todo` 判据据此按已完成计，这不是漏建。

Spec: `spec/proposal-promotion-proof.md`

## Architecture decisions

- Proof is a fresh remote-default observation, not a label transition or local diff.
- It requires an `accepted` review and verifies first appearance on the default branch's first-parent history against the promotion commit's first parent.
- Existing Proposal, publication, review and capability-map validators remain authoritative; no bridge/state client is imported.

## Implementation slices

### Slice 1: Remote-history fixtures and proof states

Add local bare-remote fixtures for proved, non-accepted, invalid and unknown without external services.

### Slice 2: Fixed snapshot and first-appearance verification

Reuse isolated remote snapshot mechanics; verify parent absence and exact map/Proposal relationship.

### Slice 3: Safe output and quality gate

Add JSON/reference guidance, focused test wiring and full validation.

## Current checkpoint

**Type:** implementation complete; merge-history focused test and repository full validation passed.

**Next step:** All modules in this capability map are implemented. Review the local diff before any separately authorized integration, migration or commit.
