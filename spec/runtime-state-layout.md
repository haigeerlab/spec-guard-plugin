# Spec: runtime-state-layout

## Objective

插件写文件的位置没有成文规则，本机状态因此长出了两个根目录：账本运行时与交接日志在 `~/.spec-guard/`，托管事项的
写入意图与 Proposal 收尾日志在 `~/.local/state/spec-guard/`。没有一张表说明"什么放哪、入不入库、谁能删"，
以后很容易再长出第三个根。

本模块把三类位置写成文件布局，把仍在 `~/.local/state/spec-guard/` 的两处并到统一根目录，并加一个检查器守住它。

登记：2026-10-08 经 `/spec-guard:add-module` 插入能力图。同批：`project-config`（#255）、`module-suspend`（#256），均已合并。

## Measured state (2026-10-08, this machine, read-only)

| 位置 | 内容 | 结论 |
|---|---|---|
| `~/.spec-guard/local-ticket-ledger/runtime` | 已安装的账本程序，119 MB；路径写在 `~/.claude.json` 的 MCP 配置里 | 不动 |
| `~/.spec-guard/local-ticket-portability` | 3 份交接日志（防重复交接） | 不动 |
| `~/.spec-guard/{native-collaboration,session-delegation,collaboration}` | agent-relay 的状态；已安装的 agent-relay 代码仍引用前两者用于迁移 | 归 agent-relay，spec-guard 不报告、不碰 |
| `~/.local/state/spec-guard/{hosted-ticket-intents,proposal-closeout}` | 空 | 迁到统一根目录 |
| `~/.local/state/spec-guard/closeout-previews` | 空；本仓库任何提交都没有写过它（`git log -S` 无结果） | 来历不明，不当作 spec-guard 遗留报告 |

## Assumptions

用户已于 2026-10-08 确认（第 1 条按实测修正后确认）：

1. **本机统一根目录是 `~/.spec-guard/`**，可用环境变量 `SPEC_GUARD_STATE_DIR` 覆盖（覆盖对所有本机状态生效）。
2. 只迁移 `hosted-ticket-intents` 与 `proposal-closeout` 两处。旧位置**整目录回退**：新目录不存在而旧目录存在时继续用旧目录，
   同一类记录永远只在一个目录里；从不删除旧目录。
3. **每个 checkout 自己的运行时状态**放在 `$(git rev-parse --git-path spec-guard)`（即 `.git/spec-guard/`）。本次只写进规则，
   现有的 `.git/spec-guard-local-restore.lock` 不移动。
4. `.agent/state.json` 不迁移；布局里标明它是每个 checkout 各自的、不该入库。
5. `spec/history/`、`tasks/history/`、`.agent/history/` 归为"历史归档：入库、只读、不再新增"（只有一次性迁移工具写它们）。
6. agent-relay 的目录不报告、不碰。
7. **范围收窄：** 原先说"报告 spec-guard 自己不再使用的旧目录 `closeout-previews`"；实测它不是本仓库代码写的，不报告。
   改为报告迁移后的两个旧位置（仍作回退读取时）。

## Contract

### `hooks/state_paths.py`（本机状态位置的唯一来源）

- `state_root()`：`SPEC_GUARD_STATE_DIR`（非空时）或 `~/.spec-guard`。
- `state_dir(name, legacy=None)`：`state_root()/name`；仅当它不存在、且给了 `legacy` 而 `legacy` 存在时返回 `legacy`。
- `LEGACY_STATE` 列出两个旧位置；`legacy_in_use()` 返回其中正被回退使用的那些。
- 只计算路径，不创建目录；目录仍由使用方按现有权限规则（0700）创建。

### 使用方

- `hosted_ticket.INTENT_ROOT`、`proposal_closeout.JOURNAL_ROOT` 改为经 `state_dir` 取得（带旧位置）。
- `local_ledger_runtime.default_runtime_dir`、`proposal_closeout_local.DEFAULT_RUNTIME`、
  `local_ticket_journal.default_journal_root` 改为经 `state_dir` 取得；默认值逐字节等于现在的路径。

### 检查器 `scripts/check-state-paths.py`

- 扫描 `plugins/spec-guard/hooks/*.py`（不含测试）：除 `state_paths.py` 外，出现 `Path.home()`、`expanduser` 或 `~/` 字面量的位置
  必须在允许清单里（读宿主配置：`~/.claude`、`~/.codex`、`CLAUDE_CONFIG_DIR`、`CODEX_HOME`；epiq 自己的 `~/.epiq-global`）。
  其余一律失败并列出文件与行号。扫描到 0 个文件算"没找到"，不算通过。接入 `validate.sh`，并在 `test-checkers.sh` 加正反样例。

### 报告

- `/spec-guard:config` 的 `show` 末尾加两行事实：本机状态根目录（及是否来自 `SPEC_GUARD_STATE_DIR`）；正被回退使用的旧位置
  （没有则不输出）。只读，不建议删除有内容的目录。

### 文件布局文档

- `docs/design.md` 新增 `## File layout`：四类（项目内入库产物、历史归档、每个 checkout 的状态、本机状态）各列路径、
  是否入库、谁写、能否删除；注明 agent-relay 的目录不属于 spec-guard。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_state_paths.py
python3 -B plugins/spec-guard/hooks/test_project_config.py
python3 -B scripts/check-state-paths.py .
/bin/bash scripts/test-checkers.sh
/bin/bash scripts/validate.sh
npx --yes shellcheck@4.1.0 -S warning plugins/spec-guard/hooks/*.sh scripts/*.sh evals/*.sh evals/*/*.sh
```

## Testing strategy

- 先写测试并确认失败，再实现。
- `test_state_paths.py`：默认根、环境变量覆盖、空环境变量按未设置；新目录存在用新、只有旧目录用旧、都不存在用新；
  `legacy_in_use`；五个使用方的默认值与现在逐字节相同（在临时 HOME 下比较）。
- 检查器：正样例（只在允许清单内使用家目录）通过；反样例（新增一个家目录写入）失败并给出行号；空目录报"没找到"。
- `test_project_config.py`：`show` 输出根目录行；有旧位置回退时输出那一行，没有时不输出。
- 既有单测（hosted ticket、proposal closeout、local ledger、portability）全部通过。
- 变异：回退条件写反、忽略环境变量、检查器漏扫 `expanduser`，都必须让测试变红。

## Boundaries

- Always：先红后绿；不移动、不删除任何已有数据；默认路径对现有用户不变。
- Ask first：移动账本运行时或交接日志；删除任何旧目录；改动 agent-relay 的目录。
- Never：合并两个目录里的记录；hook 写文件；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 本机状态只有一个根目录（可覆盖），写在文件布局里；检查器拦得住新的家目录写入。
- 已有数据（账本运行时、交接日志、旧位置里的意图与日志）全部仍然可用，没有任何文件被移动或删除。
- `/spec-guard:config` 能看到根目录和正被回退使用的旧位置。

## Open questions

- 无。
