# Spec: convention-block-blank-lines

<!-- spec-guard: review approved cd5eeec5a2cc -->

## Objective

`setup-convention` 写进 `CLAUDE.md`／`AGENTS.md` 的约定块，标记行旁边没有空行。用 oxfmt、Prettier 这类 Markdown 格式化器做提交前检查的项目，
每次改到这两个文件，`oxfmt --check` 都判不合格（账本事项 8AB0R0B，接入协调人在联合演练里实测发现）。

2026-10-18 用使用方项目已装的 oxfmt 在临时文件上实测：

- 没开派活规则段时，oxfmt 在块 `BEGIN` 后、块 `END` 前各补一行；有本地段时，还在 `<!-- BEGIN:spec-guard-local -->` 前后和
  `<!-- END:spec-guard-local -->` 前各补一行。两条标记紧挨着（本地段 `END` 后接块 `END`）时不补。
- 开了派活规则段时，规则段第一行的 `<!-- spec-guard: build-task-dispatch -->` 前后也各补一行。
- 每条标记前后都有空行的写法，`oxfmt --check` 直接通过，格式化不改动。

此外，`hooks/managed-block.py` 的 `_text` 比对前过滤空行，所以 oxfmt 补过空行的块仍被判为最新；但 `--replace` 写入时会把这些空行删掉，
`--dry-run` 预览却从不列出，预览和实际写入对不上。

本模块让 spec-guard 写出的约定块本身符合格式化器的空行规则，并让 `--replace` 的预览如实反映空行变化。

登记：2026-10-18 经 `/spec-guard:add-module` 插入能力图。来源：接入协调人（会话 local_4f410de8-418e-440c-90d8-436a73edcc6b）的联合演练实测，记在本地账本
8AB0R0B；用户本人决定排期，并确认插入与下列假设。

## Assumptions

用户已于 2026-10-18 确认以下 6 条：

1. **标准写法：每条标记前后各一个空行。** 块的 `BEGIN`／`END`、本地段的两条标记、派活规则段的注释，前后各留一个空行，挨着的是另一条标记也一样
   （文件开头与末尾除外）。oxfmt 实测接受，且不会删掉两条标记之间的空行。
2. **本地段内部原样保留。** 那是项目自己写的内容；spec-guard 只保证本地段前后有空行。项目用格式化器整理过本地段后，再 `--replace` 结果不变。
3. **升级已装的块不需要 `--accept-removals`。** 空行的增删不算删掉模板以外的行。`--dry-run` 在空行有变化时多一行
   `will adjust blank lines: add N, remove M`；块完全不用改时照旧报 `block content unchanged`。
4. **判断块是否最新照旧忽略空行。** phase-guard、verify-artifacts 与 `--replace` 的增删行判断都不改；有空行、没空行两种写法都算最新。
5. **teardown 行为不变。** 用新写法安装再卸载，文件与安装前逐字节相同；已有的往返回归继续通过，并为新写法补回归。
6. **版本 0.71.1。** 发版后在账本里关闭 8AB0R0B，把版本号告诉接入协调人（原生会话消息，先给用户看草稿）。

## Contract

写出的块（`[ ]` 表示可选部分）：

```text
<!-- BEGIN:… -->
<空行>
<基础模板正文，去掉首尾空行>
[<空行>
<!-- spec-guard: build-task-dispatch -->
<空行>
<规则段正文>]
[<空行>
<!-- BEGIN:spec-guard-local -->
<本地段内部，原样>
<!-- END:spec-guard-local -->]
<空行>
<!-- END:… -->
```

- `hooks/setup-convention.sh`：新建块按上面的写法拼接；`block_content` 在基础模板与规则段之间放一个空行。
- `templates/claude-dispatch-rule.md`、`templates/codex-dispatch-rule.md`：注释行后加一个空行，其余文字不变。
- `hooks/managed-block.py replace`：按上面的写法组装新块（模板正文去掉首尾空行，本地段原样保留，本地段与正文之间、块标记内侧各一个空行）；
  `--dry-run` 在原有的 will remove／will add 之外，比较新旧块的空行数，有变化时输出 `will adjust blank lines: add N, remove M`；新旧块逐字节相同时输出
  `block content unchanged`，只有空行不同时不输出这一句。`validate`、`remove` 与 `_text` 不变。
- 文件开头或末尾的块：块外两侧的空行处理不变（setup 在已有文件末尾追加块前补一个空行，teardown 照旧回收）。

不改 phase-guard、verify-artifacts、模板正文文字、teardown-convention.sh。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

`test-setup-teardown.sh`（先红后绿，Claude 与 Codex 两边各一遍）：

- 新建块（派活关／开，有无已有文件）：每条标记前后各一个空行，块正文就是按 Contract 拼出的内容；
- 旧写法（无空行）的块 `--replace --dry-run`：列出 `will adjust blank lines: add N, remove 0`，不要求 `--accept-removals`；实际写入后与新建块逐字节相同；
- 新写法的块再 `--replace --dry-run`：`block content unchanged`，写入后逐字节不变；
- 带本地段的块：本地段内部原样保留，前后有空行；本地段内部已被格式化器补过空行的，再 `--replace` 逐字节不变；
- setup→teardown 往返逐字节还原（派活关／开、有本地段）；
- 模板以外的行仍需要 `--accept-removals`（原有回归不变）。

人工核对（不进 CI）：用使用方项目已装的 oxfmt，对新建的块（派活关／开、带本地段）跑 `oxfmt --check`，退出码 0。

## Boundaries

- Always：每条标记前后一个空行；本地段内部原样；预览与写入一致；有无空行都算最新。
- Ask first：改动本地段内部；改模板正文文字；改 teardown 的空行处理；为其他 Markdown 产物统一空行规则。
- Never：把空行的增删当作需要 `--accept-removals` 的删除；让预览漏报实际写入的变化。

## Success criteria

- spec-guard 新建或替换后的约定块，`oxfmt --check` 不再报错。
- 已经被格式化器补过空行的块，`--replace` 不再把空行删掉。
- `--replace --dry-run` 列出的变化与实际写入一致。
- 全套检查通过，setup→teardown 往返仍逐字节还原。

## Open questions

- 无。
