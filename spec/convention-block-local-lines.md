# Spec: convention-block-local-lines

## Objective

`setup-convention --replace` 现在把 BEGIN/END 标记之间的全部内容换成模板，不看块里原有什么；`--dry-run` 只打印
“replace the convention block”。项目自己写进约定块的行会被悄悄删掉。本仓库 `AGENTS.md` 的 Codex 约定块就有 5 行
手写的 Proposal 与退役规则（同时比现行模板少 10 行），一次 `--replace` 就会把它们抹掉。来源：project-config 会话
2026-10-08 交接的候选 2，用户确认按推荐顺序做。

读者：在项目里装了 Spec Guard 约定块的用户（Claude Code 的 `CLAUDE.md`、Codex 的 `AGENTS.md`）；本插件维护者。

## Assumptions

用户于 2026-10-08 确认：

1. 约定块内可以有一个本地段，用独占一行的 `<!-- BEGIN:spec-guard-local -->` 与 `<!-- END:spec-guard-local -->`
   圈出；`--replace` 把它（含两行标记）原样放到新块末尾。本地段最多一个；标记不成对、顺序颠倒或出现多个时拒绝，
   不改任何文件。
2. `--replace --dry-run` 逐行列出将删除与将新增的行（忽略空行；本地段不计入，因为它原样保留）。
3. 真正替换时，若会删除本地段以外、且不属于现行模板或派活规则段的非空行，拒绝并不改文件，列出这些行；用户看过后加
   `--accept-removals` 才执行。现行模板与规则段里的行（例如 `--no-dispatch` 关掉规则段）不需要接受。
4. 因为仓库不保存历代模板，从旧模板升级时旧模板的行也算“模板以外的行”，需要用户看一眼再加 `--accept-removals`。
5. 本仓库 `AGENTS.md` 的 5 行手写规则移进本地段，再用新的 `--replace` 补齐模板；替换前把预览给用户看。本仓库
   `CLAUDE.md` 没有 Claude 约定块，不涉及。
6. 版本 0.54.1，单独发版。

## Requirements

1. `managed-block.py` 增加读出块内本地段与计算差异的能力；`replace` 写入时保留本地段。所有校验在写之前完成，失败时
   文件逐字节不变。
2. `setup-convention.sh`：
   - `--replace --dry-run` 打印 `will remove:` / `will add:` 逐行清单（没有差异时说明“块内容不变”）；
   - 真正 `--replace` 时，存在需接受的删除且没有 `--accept-removals`：退出 1，列出这些行，不改文件；
   - `--accept-removals` 只在 `--replace` 时有意义，单独给出时报用法错误；
   - 首次安装（没有块）与 `teardown-convention` 的行为逐字节不变。
3. 命令 `setup-convention.md`、Codex skill `spec-guard-ops` 的 setup 一节、`docs/workflow.md` 写明本地段与
   `--accept-removals`；模板本身不加本地段。
4. 回归（`test-setup-teardown.sh` 及 managed-block 的测试）：本地段保留；预览列出删除与新增；有手写行时不带参数拒绝且
   文件不变；带参数后替换且本地段在末尾；只删规则段（`--no-dispatch`）不需要接受；本地段标记损坏时拒绝；首次安装与
   teardown 往返逐字节不变。每条新断言先在现有代码上变红，并手动改坏一次确认会变红。
5. 本仓库 `AGENTS.md`：5 行手写规则在本地段内，块内模板部分与现行 Codex 模板一致。
6. CHANGELOG `## [0.54.1]`，两份清单与 README `--ref`，按 `docs/release-process.md` 发版。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Boundaries

- Always：只用 `bash` / `git` / `python3`；测试在临时目录里；拒绝时不改任何文件。
- Ask first：推送、PR、tag、发版；改本仓库 `AGENTS.md` 前先给预览。
- Never：不经接受删除用户的行；改动激活判据或块标记本身。

## Success criteria

1. 用户写在本地段里的行在 `--replace` 后原样保留。
2. 任何会删掉用户行的替换都先被列出，并且要用户明确接受。
3. 首次安装、teardown 与没有手写行的替换行为不变。

## Open questions

无。
