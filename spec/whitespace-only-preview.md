# Spec: whitespace-only-preview

<!-- spec-guard: review approved 76bd20d0a07f -->

## 目标

0.86.2 起 `--replace` 按段比较、去掉空白再比（reflow-tolerant-replace）。块里某段与模板只差空白或折行时，这段不列进
`will remove:`／`will add:`；可块又不是逐字节相同，`block content unchanged` 也不报。结果是预览一行内容都没有，
真正写入却会把这些段改成模板的写法。2026-11-02 发版核对时，用一份 oxfmt 格式化过的真实块（只差中文标点后的空格）实测：
`--replace --dry-run` 的块内说明为空，读预览的 agent 回报「块里到底有没有实际要改的内容，这份输出看不出来」。

本模块让预览如实说出这类改动。给谁用：用 Markdown 格式化工具的项目，以及替用户读预览、转述给用户的 agent。

## 假设

用户已于 2026-11-02 确认（「立项做」，针对本会话提出的改法）：

1. **另起一行报告**：块里有段与模板只差空白或折行时，`--replace --dry-run` 多打印一行
   `will adjust whitespace or line wrapping: N paragraph(s)`，N 是这类段的个数。和 `will adjust blank lines` 一样，这不需要
   `--accept-removals`。
2. **怎样算「只差空白或折行」**：一个列表项或段落，去掉空白后与模板里某段相同（即 0.86.2 判为「没有删减」的段），但它在块里的原文
   （各行去掉行尾换行后按原样拼接，含行首缩进与行内空白）与模板那段的原文不同。
3. **与其他行并存**：有增删、空行变化时照样打印这一行；只有块逐字节与将写入的内容相同时才报 `block content unchanged`（不变）。
4. **不改判定与写入**：`will remove:`／`will add:`、`[needs --accept-removals]`、拒绝条件、写入内容、teardown 都不变。
5. 文档：`commands/setup-convention.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md` 里讲预览内容的地方补上这一行。
6. 发 0.86.3，只是修复，`interface.json` 不变；仓库里不出现消费项目的名字、模块或编号。

## 命令

```text
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh evals/*/*.sh
```

## 测试策略

- 先写测试并确认在 0.86.2 上失败，再实现。
- `test-setup-teardown.sh`：
  - 块被折开再拼回（中文标点后带空格）：两侧 `--replace --dry-run` 报 `will adjust whitespace or line wrapping:`，个数与改动的段数一致，
    不报 `block content unchanged`，没有 `will remove:`；
  - 有续行的旧块升级：同样报这一行；
  - 块与模板逐字节相同：不报这一行，照旧报 `block content unchanged`；
  - 既有增删、空行、本地段用例全部通过。
- 变异：去掉这一行的打印、把「原文不同」的条件去掉（每段都算），两处都必须让测试变红。

## 边界

- Always：先红后绿；只加预览里的一行说明，判定与写入不变。
- Ask first：把只差空白的段逐段列出原文；在真正写入（非 `--dry-run`）时也打印；改 teardown 预览。
- Never：因为这一行要求 `--accept-removals`；在 Spec、代码、测试、提交信息或 PR 中写入消费项目的名称、模块或编号。

## 成功标准

- 块里有段只差空白或折行时，`--replace --dry-run` 报 `will adjust whitespace or line wrapping: N paragraph(s)`，N 正确。
- 块与模板逐字节相同时不报这一行，照旧报 `block content unchanged`。
- 增删、`[needs --accept-removals]`、写入结果与 0.86.2 相同；既有回归全部通过。
- 三处讲预览的文档补上这一行。

## 待定问题

- 无。
