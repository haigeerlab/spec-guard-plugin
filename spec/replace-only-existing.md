# Spec: replace-only-existing

<!-- spec-guard: review approved c7a2e6187a83 -->

## 目标

`setup-convention --replace` 的命令说明写着「仅替换已有受管声明块」，脚本却没这么做：`hooks/setup-convention.sh` 的
`install_block` 只在目标文件已有块时走替换，没有块时照新建处理，往目标文件追加一个块（2026-11-02 在 0.86.0
`setup-convention.sh:101-147` 核对）。目标文件按宿主选：Claude 侧是 `CLAUDE.md`，Codex 侧（`--host=codex`）是 `AGENTS.md`。

实际使用中踩到的情况（来源匿名化）：块只在 `AGENTS.md` 的项目，按 0.86.0 升级说明「用 `setup-convention --replace`
更新约定块」以默认（Claude 侧）预览，得到的是「在 `CLAUDE.md` 追加一个约定块」；没有 `CLAUDE.md` 的项目则会新建一个。
这些项目的规则写明共同约束只在 `AGENTS.md` 维护，追加一份等于复制出第二套规则。0.86.0 的升级说明本身也把话说得太笼统。

本模块让 `--replace` 只替换、从不新建，没有块时说清楚该在哪一侧运行；并改正升级说明。

给谁用：只在一侧放约定块的项目（只有 `AGENTS.md`，或只有 `CLAUDE.md`），以及给这类项目写升级说明的维护者。

## 假设

用户已于 2026-11-02 确认（「立项修 0.86.1」，针对本会话提出的修法）：

1. **`--replace` 只替换已有块，从不新建。** 目标文件没有块（含文件不存在）时拒绝：不改任何文件、不建任何目录，退出码 1
   （与「声明块标记无效」的拒绝相同）。
2. **拒绝在任何写入之前发生**，与 0.84.2 的「会被拒的 `--replace` 不先建目录」（review-residual-fixes C3）同一位置。
3. **`--dry-run` 给同样的结论**：打印同一条拒绝说明并退出 1，不打印「append a convention block」。
4. **提示该用哪一侧**：另一侧文件里有块时，说出块在哪个文件、改用哪种写法（Claude 侧命令与 Codex 侧技能两种说法都给）；
   两侧都没有块时，提示去掉 `--replace` 来新建。
5. **不带 `--replace` 的行为不变**：没有块时照旧新建，有块时照旧跳过并提示用 `--replace`。
6. **改正说法**：CHANGELOG 0.86.0 的升级须知、README 中英、`docs/workflow.md` 里「用 `--replace` 更新约定块」改为
   「在已有块所在的一侧运行 `--replace`」，两侧都有块就各跑一次。
7. **发 0.86.1**，只是修复，`interface.json` 不变。
8. 仓库里不出现消费项目的名字、模块或编号。

## 约定

### 判定

- 「有块」沿用现有判据：目标文件里有独占一行的开始或结束标记（`marker_lines` 大于 0），且通过 `managed-block.py validate`。
  标记无效时照旧拒绝并报「标记无效」，不走本模块的提示。
- 另一侧：Claude 侧的另一侧是 `AGENTS.md` 的 `spec-guard-codex-convention` 标记，Codex 侧的另一侧是 `CLAUDE.md` 的
  `agent-skills-convention` 标记；只看是否有独占一行的标记，不校验另一侧块的结构。

### 输出（stderr，退出 1，文件与目录都不变）

- 另一侧有块，Claude 侧运行：
  `❌ CLAUDE.md 里没有约定块，--replace 只替换已有块；约定块在 AGENTS.md：改用 --host=codex（Claude 侧 /spec-guard:setup-convention --replace --host=codex，Codex 侧 spec-guard-ops 的 setup-convention 一节）。未改动任何文件`
- 另一侧有块，Codex 侧运行：
  `❌ AGENTS.md 里没有约定块，--replace 只替换已有块；约定块在 CLAUDE.md：去掉 --host=codex（Claude 侧 /spec-guard:setup-convention --replace）。未改动任何文件`
- 两侧都没有：
  `❌ <目标文件> 里没有约定块，--replace 只替换已有块；要新建约定块，去掉 --replace 再运行。未改动任何文件`
- `--dry-run` 下输出与退出码相同（拒绝说明先于「═══ Spec Guard local convention ═══」之后的任何预览行）。
- 提示文字给人看，不是接口：调用方只应依赖退出码 1 与「文件、目录都不变」。2026-11-02 核对，其他插件没有调用 `--replace`（module-crew 与 decision-inbox 只提示首次启用 `/spec-guard:setup-convention`），没有地方引用这些文字，发版前不必再报影响面。

### 文档

- `commands/setup-convention.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`：写明没有块时 `--replace` 拒绝及提示。
- CHANGELOG 0.86.1 的「修复」写本模块；CHANGELOG 里 0.86.0 的升级须知那一行改为按已有块所在的一侧运行，并在 0.86.1 里说明更正过；GitHub 上 v0.86.0 的
  Release 说明不改（远端写入，需另行询问）。
- README 中英「已经装过旧版约定块的项目」那段、`docs/workflow.md:74` 同一说法，补「在块所在的一侧运行，两侧都有就各跑一次」。

## 命令

```text
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh evals/*/*.sh
```

## 测试策略

- 先写测试并确认在当前代码上失败，再实现。
- `test-setup-teardown.sh` 正反用例：
  - 只有 `AGENTS.md` 有块，Claude 侧 `--replace`（带与不带 `--dry-run`）：退出 1、提示改用 `--host=codex`、`CLAUDE.md` 不存在或不变、
    不建 `spec/`、`tasks/`、`.agent/`；
  - 只有 `CLAUDE.md` 有块，`--host=codex --replace`：退出 1、提示去掉 `--host=codex`、`AGENTS.md` 不变；
  - 两侧都没有块，`--replace`：退出 1、提示去掉 `--replace`、什么都不建；
  - 回归：有块时 `--replace` 照常替换；两侧都有块时各自替换互不影响；不带 `--replace` 时没有块照旧新建。
- 变异：去掉新加的拒绝分支、把检查挪到建目录之后，两处都必须让测试变红。

## 边界

- Always：先红后绿；拒绝前不写任何文件；不带 `--replace` 的行为逐字节不变。
- Ask first：让 `--replace` 自动切换到另一侧去替换；同时更新两侧；改 teardown 的行为。
- Never：在没有块的文件里新建块（带 `--replace` 时）；在 Spec、代码、测试、提交信息或 PR 中写入消费项目的名称、模块或编号。

## 成功标准

- 块只在 `AGENTS.md` 的项目，Claude 侧跑 `--replace`（含 `--dry-run`）被拒，提示改用 `--host=codex`，什么都没改。
- 块只在 `CLAUDE.md` 的项目，Codex 侧跑 `--replace` 被拒，提示去掉 `--host=codex`。
- 两侧都没有块时 `--replace` 被拒，提示去掉 `--replace`。
- 有块时的替换、不带 `--replace` 的新建，既有回归全部通过。
- 0.86.0 升级说明与 README、workflow 的说法已改正。

## 待定问题

- 无。
