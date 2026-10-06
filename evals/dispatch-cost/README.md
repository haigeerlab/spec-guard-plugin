# 派活成本对照（ledgerlite）

用同一个种子项目、同一组 task 和隐藏测试，比较「主代理自己做」与「`--dispatch` 派给子代理」的花费。
这是 2026-10-05～06 与 tier-guard 联调时用的脚手架；结论与每轮数字记在
[spec/build-task-dispatch.md](../../spec/build-task-dispatch.md) 的修订记录里，这里只负责能重跑。

不进 `validate.sh`：每次运行都要调用真实宿主、花真钱。

## 内容

| 路径 | 作用 |
|---|---|
| `seed/` | 种子项目：约 900 行 Python 记账库，已带 spec、plan 与 5 个 task 的 todo（含 2 个故意埋的缺陷） |
| `reference/` | 5 个 task 全部做完的参考实现，只用来证明隐藏测试可以通过 |
| `hidden/` | 隐藏测试，按 task 分类；判定「便宜是不是因为活没干完」 |
| `defects/` | 隐藏测试用到的数据 |
| `variants/G`、`variants/W` | 联调中途临时改过、没有单独提交的派活规则，覆盖在 v0.44.0 上重现 |
| `prices.json` | tier-guard 口径的价格表（用户 2026-10-05 批准；未经官方核实，见文件内 `note`） |
| `results/` | 18 次运行的 `module_cost_report.py --json` 输出与运行元数据（原始数据） |
| `verify-seed.sh` | 证明种子有效：自带测试全绿，隐藏测试在种子上全红、在参考实现上全绿，缺陷 A 恰好差 0.01 |
| `run.sh` | 跑一次：建项目、装约定块、调用宿主跑 `/build auto` 到全部勾选 |
| `grade.sh` | 判分并计价：隐藏测试 + 成本报告 |

## 组

| 宿主 | 组 | spec-guard | `--dispatch` | 含义 |
|---|---|---|---|---|
| claude | N | `639107e` | 否 | 不派（对照组） |
| claude | R | `639107e` | 是 | 「默认不派、大量探索才派」 |
| claude | F | `v0.44.0` | 是 | 每个 task 都派 |
| claude | G | `v0.44.0` + `variants/G` | 是 | 每个都派，档位定义补上「取舍」 |
| claude | S | `v0.45.0` | 是 | 现行规则：只派改 3 个以上文件、验收明确的 task |
| codex | N | `d2d1b70` | 否 | 不派（对照组） |
| codex | R | `d2d1b70` | 是 | 默认不派 + 「取舍」 |
| codex | F | `v0.44.0` + `variants/G` | 是 | 每个都派 + 「取舍」 |
| codex | W | `v0.44.0` + `variants/W` | 是 | F + 派出后一次长等待、不短间隔轮询 |
| 任意 | custom | `SG_REF` | `SG_FLAG` | 自定义版本，例如以后测新规则 |

主代理：Claude 为 opus，Codex 为 `gpt-6.1-sol` / medium（`CLAUDE_MODEL`、`CODEX_MODEL`、`CODEX_EFFORT` 可改）。
子代理模型由 tier-guard 决定。

## 跑法

```bash
/bin/bash evals/dispatch-cost/verify-seed.sh
```

```bash
export RUNS=/tmp/dispatch-cost-runs AGENT_SKILLS_DIR=<agent-skills 插件目录> TIER_GUARD_DIR=<tier-guard 插件目录>
/bin/bash evals/dispatch-cost/run.sh claude N 1
/bin/bash evals/dispatch-cost/grade.sh "$RUNS/C-N1"
```

- `RUNS` 必须在本仓库之外：Claude 会读取上级目录的 `CLAUDE.md`，放在仓库里会污染对照，脚本会拒绝。
- Claude 组通过 `--plugin-dir` 加载三个插件，不受本机已安装版本影响。联调时 agent-skills 0.6.11、tier-guard 0.2.5。
- Codex 组的 agent-skills 与 tier-guard 用本机 Codex 已安装的版本；`codex` 不在 `PATH` 时设 `CODEX=<路径>`。
  `codex exec` 会把运行目录记为 trusted，脚本结束后撤回这一条。
- `DRY_RUN=1` 只建项目和约定块，不调用宿主，用来检查组配置。
- 一次运行中途停下来问人时，脚本最多用固定的一句话续两次；`meta.json` 的 `stops` 与 `open_items` 记录了这件事。

## 判读

- 每组至少跑 2 次，比较均值与波动：联调里同组两次相差可达 20%～25%（S 组 $2.47 / $1.96，W 组 $0.793 / $0.657）。
- 只比较隐藏测试全部通过的运行。`Task3Rounding.test_tricky_set_2_signs_and_forms` 已作废：种子 spec 的 Task 3「补充约定」只接受
  `-?\d+(\.\d{1,2})?`，与它要求的 `+0.58` 冲突，判读时忽略这一条。
- 金额按 API 价格折算，用来比较组间相对差异，不是订阅账号的实际扣费。
- 看 `合计（含收尾）` 一行，它和整次运行的会话总账能对上。
- 不要把真实项目的「开启前 / 开启后」直接对比：task 不同，结论不可信。

## 已知局限

- 种子是小项目（主会话上下文约几万 token）。「主会话上下文很大时派活能否省钱」没有在这里测过。
- `results/` 中的会话 id 指向当时机器上的记录，换机器后只能当数字看，不能重算。
