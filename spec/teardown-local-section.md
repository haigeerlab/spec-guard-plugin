# Spec: teardown-local-section

## Objective

0.54.1 让 `setup-convention --replace` 保留约定块里的本地段，并在删除手写行前要求 `--accept-removals`。但
`teardown-convention` 仍用 `managed-block.py remove` 删掉 BEGIN/END 之间的全部内容：本地段和其他手写行一起消失，
预览只说“声明块已移除（N 行）”。这和“用户的行不会被悄悄删掉”的承诺相悖。来源：第二轮联调对 PR #262 的审查意见，
用户 2026-10-08 选定按推荐先做。

读者：在项目里装了 Spec Guard 约定块并要移除它的用户（Claude Code 的 `CLAUDE.md`、Codex 的 `AGENTS.md`）；本插件维护者。

## Assumptions

用户于 2026-10-08 确认：

1. teardown 删除约定块时，本地段内的行（不含两行本地段标记）留在块原来的位置，不需要任何参数。
2. 块内本地段以外、又不属于现行模板或派活规则段的非空行：`--dry-run` 逐行列出 `will remove:`；真正 teardown 不带
   `--accept-removals` 时退出 1，指令文件与 `.agent/state.json` 都不改。与 `--replace` 规则一致；旧模板的行同样需要接受。
3. 本地段标记不成对、颠倒或重复时拒绝，不改任何文件。
4. 没有手写行时行为不变：setup→teardown 往返逐字节还原；只有派活规则段时不需要接受。
5. `--accept-removals` 只对实际会删除块的 teardown 有意义；目标宿主没有约定块时给出它，按用法错误退出 2。
6. 版本 0.54.2，单独发版。

## Requirements

1. `managed-block.py remove` 接受 `[--known FILE]... [--accept-removals] [--dry-run]`：本地段内的行原样留在块的位置，
   其余需接受的删除没有 `--accept-removals` 时退出 3 不写文件；`--dry-run` 打印 `will remove:` 清单（需接受的行带
   `[needs --accept-removals]`）与 `keeps the local section in place (N lines)`，不写文件。所有校验在写之前完成。
2. `teardown-convention.sh`：以现行模板和派活规则段作为已知行；预览缩进打印上面的清单；拒绝时报未改动并退出 1，
   且不碰 `state.json`；解析 `--accept-removals`（目标块不存在时退出 2）；完成提示里说明本地段留在原位置的行数。
3. 命令 `teardown-convention.md`（含 argument-hint）、Codex skill `spec-guard-ops` 的 teardown 一节、`docs/workflow.md`
   写明本地段留在原位置与 `--accept-removals`。
4. 回归（`test-setup-teardown.sh`）：本地段内容留在原位、标记消失、state 停用；预览列出手写行且不改文件；有手写行时不带
   参数退出 1、指令文件与 state 都不变，带参数后移除；本地段标记损坏时拒绝；`--accept-removals` 在无块时退出 2；
   Codex 宿主至少一例；原有往返、派活规则段、重复标记用例保持通过。每条新断言先在现有代码上变红，并手动改坏确认会变红。
5. CHANGELOG `## [0.54.2]`，两份清单与 README `--ref`，按 `docs/release-process.md` 发版。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Boundaries

- Always：只用 `bash` / `git` / `python3`；测试在临时目录里；拒绝时不改任何文件（含 `state.json`）。
- Ask first：推送、PR、tag、发版。
- Never：不经接受删除用户的行；改动激活判据或块标记本身；改变 setup 的行为。

## Success criteria

1. 用户写在本地段里的行在 teardown 后留在原位置。
2. 任何会删掉用户行的 teardown 都先被列出，并且要用户明确接受。
3. 没有手写行的 teardown 与原来逐字节相同。

## Open questions

无。
