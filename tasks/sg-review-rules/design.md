# 技术方案: sg-review-rules

<!-- spec-guard: review pending -->

需求文档：`spec/sg-review-rules.md`（用户 2026-11-27「确认需求」）。照已批总体技术方案第 7 节模块 5 那一行，不重新选型。

## 现状调研

查了下面这些（spec-guard 主干 `f63bf6b4` 加本分支）：
- **重要需求判定**：`module_stage.important()`（`module_stage.py:1703`）按顺序给出 `multi-module`（`usage_draft.batches`）、`cross-unknown`、`cross-module`（并行边界的公共文件或与未完成模块重叠）、`risk-unknown`、`risk-path`。新流程模块的影响面路径已经算进 `risk-path`（plan-auto-approve），也已经去掉了本模块自己的文档。
- **技术方案送审判定**：`design_requirement()`（`:824`）。`important` 档直接返回 `need: user`；否则看 `impact_has_old_files()`，返回 `old-files`、`impact-unknown`；再看 `designReview: on`（`configured`）。`impact_has_old_files()` 回归文档检查（regression-doc-check）也在用，所以不能删。
- **谁批技术方案**：`design_approver()`（`:852`）重要需求一律 `user`，否则看档位的 `design` 项。`design_approval()` 按批准人、送审需要、轮次记录算出 `/map --json` 的 `designApproval`，两轮有阻断后交用户（`exhausted`）。`map_view._effective_takeover()`（`map_view.py:434`）在重要需求时把 `design` 显示成 `human`，`designForcedBy: important`。
- **需求文档**：`requirement_wait()`、`requirement_hint()` 管确认停点；需求文档的批准标记只认用户（`codex-route-requirement`）。`review-mark --target spec --state codex-reviewed --review <报告>` 已经能给需求文档记一轮 Codex 审查：在「外部审查意见」一节加一行 `codex-review round=N blocking=B sha256=<审查时文件 sha256 的前 12 位>`，不改批准标记。
- **技术方案的轮次**：`review-mark --target design --state reviewer-reviewed|reviewer-approved --review <报告>` 写 `design-review round=… vendor=… report=…` 行；delegate 报告的 `selection: none` 记成「没有审查者」（`vendor=none`）。`review_mark.py:424` 只认原始档位 `normal`、`important`。
- **风险清单**：`_risk_patterns()`（`:1687`）读 `.github/autopr/risk-paths.json`，读不到返回 `None`；`risk_hit()` 判路径命中。本仓库没有这份清单。
- **规则文字**：`workflow-checkpoints.md` 的「需求确认」一节没有「先审一轮」，「技术方案审查」一节写着重要需求的技术方案交用户、跨模块必为重要需求；`node-rules.md` 的「Spec 交审」「技术方案交审」两节同样。

没查的：hub 和 module-crew 实际怎样用 `designApproval.reason`（只在接口说明里改取值，不改它们的代码）。

## 影响面

路径都从仓库根目录写起；越界检查按这里引用的路径判定范围。

| 文件 | 改什么 |
|---|---|
| `plugins/spec-guard/hooks/module_stage.py` | `important()` 新流程不算 `multi-module`、`cross-module`；`design_requirement()` 换成三种高风险；`design_approver()` 去掉重要需求一律交用户；新增需求文档审查记录的解析、`requirement_review()`、确认停点的「先审一轮」提示与审查后改动差异 |
| `plugins/spec-guard/hooks/review_mark.py` | `--target spec` 新增 `--state host-reviewed`、`no-reviewer`；`approved` 在新流程 normal／important 没有审查记录时拒绝（`requirement-unreviewed`）；预览打印审查以来的改动；`--target design` 按生效档位放行，也接受 `host-reviewed`、`no-reviewer` |
| `plugins/spec-guard/hooks/map_view.py` | 每个模块加 `requirementReview`；`designForcedBy` 对新流程恒为 `null` |
| `plugins/spec-guard/hooks/verify-artifacts.sh` | 不新增调用：新检查放在 `module_stage.flow_doc_problems` 里，脚本已经在调 |
| `plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md` | 「需求确认」「技术方案审查」两节与对应停点按新规则改 |
| `plugins/spec-guard/references/doc-skeletons.md` | 需求文档审查记录的两种写法 |
| `plugins/spec-guard/commands/review-mark.md`、`plugins/spec-guard/skills/spec-guard-ops/` | 两个新状态的用法 |
| `plugins/spec-guard/interface.json` | 升 `1.27`，只加取值与字段 |
| `plugins/spec-guard/hooks/test_sg_review_rules.py`（新）、`plugins/spec-guard/hooks/test_important_requirement.py`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test_review_marker.py`、`plugins/spec-guard/hooks/test_map_view.py`、`plugins/spec-guard/hooks/test_workflow_checkpoints.py`、`plugins/spec-guard/hooks/test_stop_rules.py`、`plugins/spec-guard/hooks/test-phase-guard.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh` | 正反例；钉旧规则的断言改成钉新规则，不删断言 |
| `scripts/validate.sh` | 登记新测试文件 |
| `docs/workflow.md`、`docs/commands.md` | 使用者说明 |

版本号不在本模块改：模块 5～7 一次发版还是分开发由用户定，定了再决定在哪个模块改版本号与 CHANGELOG。

## 实现方案

### 1. 需求文档先审一轮（需求规则 1～5、Q3 A）

- **哪些模块要审**：`requirement_review_required(root, module)`：新流程模块，且 `effective_tier` 是 `normal` 或 `important`。被规则抬升的 `bug`、`small` 也要审。
- **三种记录**，都写在需求文档的「外部审查意见」一节，都带审查当时整份文件 sha256 的前 12 位：
  - delegate：沿用现有的 `codex-review round=N blocking=B sha256=…` 行（`review-mark --target spec --state codex-reviewed --review <报告>`）。
  - 宿主子会话：新行 `<!-- spec-guard: requirement-review reviewer=host blocking=B sha256=… -->`，用 `review-mark --target spec --state host-reviewed --blocking <B>` 写。审查结论由 agent 照子会话的原话写进同一节。
  - 没有审查者：新行 `<!-- spec-guard: requirement-review reviewer=none sha256=… -->`，用 `review-mark --target spec --state no-reviewer` 写，同一节写明原因。
- **`requirement_review(root, module)`** 返回 `None`（老流程）或 `{"required", "status", "records"}`：`status` 是 `not-required`、`missing`、`reviewed` 之一；`records` 是 `[{reviewer: codex|host|none, blocking, sha256}]`。只审一轮：有一条就是 `reviewed`，之后改了文件也算数。
- **硬拦**：`review-mark --target spec --state approved`（以及 `both`）对 `required` 且 `missing` 的模块拒绝，退出 2，拒绝码 `requirement-unreviewed`，不写文件。
- **确认停点的提示**：`requirement_hint` 在 `missing` 时，下一步写「先审一轮」，列出三条路（delegate 的 review 命令、宿主全新子会话、写明没有审查者），并说明审完改好、附上审查结论再复述确认；`reviewed` 时照现在的复述确认，另加一句「交用户时附上审查提了什么、改了哪些、哪些没采纳」。
- **审查以来的改动差异**：`review-mark --target spec --state approved` 的预览，从 git 里倒着找需求文档整份 sha256 前 12 位等于最后一条记录的那个版本（最多看 50 个提交，同 `REQUIREMENT_AT_LIMIT`），打印那个版本到现在的差异；找不到（没提交过、超出范围）就写明原因。阶段提示不打印差异，只提示「预览会打印」。

### 2. 技术方案只在三种高风险时送审（需求规则 6～9、Q2 A）

`design_requirement()` 改成：

1. 新流程 `bug`、`small`（生效档位）：没有技术方案，返回 `None`（不变）。
2. 算三种理由（一种命中就送审，返回第一个命中的作 `reason`，全部写进新字段 `reasons`）：
   - `risk-path`：`impact_paths(design)` 去掉本模块自己的文档后，有路径命中 `_risk_patterns()`。清单读不到时不算命中（需求规则 9），阶段提示里已有的「T4 路径：没有可读的风险路径清单，未检查」照旧。
   - `irreversible`：「接口和数据改动」（或 `Interface and data changes`）一节去掉空白、句末标点、列表符号、注释后，不是空的，也不是（不分大小写）「不涉及」「无」「没有」`None`、`N/A`、`Not applicable`、`No changes` 之一。
   - `new-dependency`：影响面里有路径的文件名是依赖清单或锁文件：`package.json`、`package-lock.json`、`npm-shrinkwrap.json`、`yarn.lock`、`pnpm-lock.yaml`、`requirements*.txt`、`pyproject.toml`、`poetry.lock`、`Pipfile`、`Pipfile.lock`、`go.mod`、`go.sum`、`Cargo.toml`、`Cargo.lock`、`Gemfile`、`Gemfile.lock`。
3. 都不命中时，`designReview: on` 返回 `configured`；否则 `need: none`。
4. 删掉 `important → need: user` 和 `old-files`、`impact-unknown` 两个分支；`impact_has_old_files()` 留给回归文档检查用。

### 3. 谁批技术方案（需求规则 10～12、Q4 A）

- `design_approver()`：只看档位的 `design` 项，`reviewer` → `reviewer`，否则 `user`；不再因重要需求返回 `user`。
- `design_approval()` 不用改分支逻辑：`need: review` + `reviewer` 时，无阻断的 `reviewer-approved` 就是 `approved`（`approvedBy: reviewer`）；`need: none` + `reviewer` 是 `not-required`；`design=human` 时照旧 `pending-user`；两轮有阻断照旧交用户。
- `map_view._effective_takeover()`：新流程模块不再把 `design` 强制成 `human`，`designForcedBy` 恒为 `null`（字段保留，接口说明改为「从 1.27 起新流程恒为 null」）。
- 技术方案的宿主子会话退路：`review-mark --target design --state host-reviewed --blocking <B>` 写一行 `design-review round=N blocking=B sha256=… vendor=host same-vendor=true criteria=host report=none`（照现有行的格式，`vendor` 取 `host`）；`B` 为 0 时同时写 `reviewer-approved` 标记，等同于一轮无阻断的审查。`--state no-reviewer` 写 `vendor=none` 那种行（现有的 `unreviewed`）。
- `review_mark.py:424` 的档位检查改成 `effective_tier`，让被抬升的 `bug`、`small` 能记技术方案。

### 4. 重要需求判定（需求规则 14～16、Q1 A）

`important()` 里，`multi-module` 与 `cross-module` 两段只在 `not _v2(root, module)` 时执行；新流程模块只剩 `risk-path`（`cross-unknown`、`risk-unknown` 原本就只对老流程的 Codex 档生效）。`effective_tier` 的抬升逻辑不变。

### 5. 审查报告给 hub 模块 8 的位置与格式（需求规则 13、S8）

- **结构化事实**：`/map --json` 每个模块的 `requirementReview`（`{required, status, records}`）与已有的 `designApproval`（`status`、`approvedBy`、`reason`、新增 `reasons`、`rounds`，每轮有 `blocking`、`sha256`、`vendor`、报告指纹 `reportSha256`）。hub 只读 `/map --json`，不读文档。
- **审查原文**：需求文档与技术方案各自的「外部审查意见」一节，agent 写入审查提了什么、怎么处理；delegate 报告本体在 delegate 的产物目录，`/map` 里只给报告的 sha256。
- 技术方案批准后把这一节抄给 ecosystem-lead，转 hub 模块 8。

### 6. 规则文字与使用者文档

- `workflow-checkpoints.md`「需求确认」：新流程 normal／important 需求先审一轮（三条路、只审一轮、硬拦、交用户时附审查提了什么、改了哪些、哪些没采纳，以及审查以来的改动）；「新流程需求由用户确认」一条把「重要需求时先 interview-me」保留。
- 「技术方案审查」：送审只看三种高风险与 `designReview`；`design=reviewer` 时重要需求也由第二审查者放行；删掉「重要需求一律交用户」「跨模块必为重要需求」的说法；「重要需求判定」写明新流程只看风险路径。
- `node-rules.md` 的「Spec 交审」「技术方案交审」对应改一两句，守住每节 3200 字节上限。

### 7. 接口

`interface.json` 升 `1.27`：`designApproval.reason` 取值加 `risk-path`、`irreversible`、`new-dependency`，`old-files`、`impact-unknown` 标「1.27 起新流程不再出现」；`designApproval.reasons` 新字段；`mapView` 每个模块加 `requirementReview`；`reviewMark` 的 state 加 `host-reviewed`、`no-reviewer` 与 `--blocking`；`important.reasons` 说明新流程只会是 `risk-path`；`designForcedBy` 说明改写。

## 接口和数据改动

| 位置 | 改动 | 旧调用方 |
|---|---|---|
| `/map --json` 每个模块 `requirementReview` | 新字段 | 不读 |
| `designApproval.reason` | 新增三个取值，新流程不再给 `old-files`、`impact-unknown` | module-crew、hub 主干都不读这个取值（已核） |
| `designApproval.reasons` | 新字段 | 不读 |
| `takeover.designForcedBy` | 新流程恒为 `null` | 读到 `null` 即「没有强制」，与原义一致 |
| `important.reasons` | 新流程不再出现 `multi-module`、`cross-module` | hub 只对老流程模块用它；module-crew 不读（已核） |
| 需求文档 | 新记录行 `requirement-review reviewer=host|none …` | 旧版 spec-guard 不认，忽略 |
| `review-mark` | 新 state `host-reviewed`、`no-reviewer`，新参数 `--blocking`，新拒绝码 `requirement-unreviewed` | 旧版不认这些参数 |

## 风险与回滚

- **宿主子会话的记录靠 agent 自觉**：`host-reviewed` 没有可验的报告，agent 可以不审就记。缓解：只能记一次（只审一轮），审查原话必须写进「外部审查意见」，交用户时一并给出；需求最后仍要用户确认。
- **module-crew、hub 对这些取值的依赖**（2026-11-27 在两个仓库主干上 `git grep` 核过）：hub `audit/plan_check.py:79-85` 读 `important.reasons`，但新流程模块被排除在这项检查之外（同文件下方「新流程模块不按老流程审批规则检查」）；hub `orchestrator/flow.py:212` 只看 `designForcedBy` 这个键在不在，所以保留字段、值为 `null` 不影响；module-crew 主干没有读 `important.reasons`、`designApproval.reason`、`designForcedBy` 的代码。都不受影响。
- **硬拦会挡住正在走流程的模块**：已经交给用户、还没确认的新流程需求文档，升级后要先补一轮审查记录才能确认。可以用 `no-reviewer` 写明原因放行，不会卡死。
- **没有风险清单的项目**：`risk-path` 永远不命中，技术方案只因 `irreversible`、`new-dependency` 送审。提示照旧写明没有清单。
- **回滚**：一个 PR，revert 合并提交即可。已写进文档的 `requirement-review` 行留着不起作用；回滚后旧版重新按 `old-files` 等规则判，已经放行的技术方案可能变回待审，需要时重新记录。

## 方案取舍

- **需求文档审查记录放在哪**：选「外部审查意见」一节里的记录行，和现有 `codex-review` 行同一处、同一种写法；没选在批准标记里加字段，因为批准标记只认用户，混进审查信息会让「谁批的」难判。
- **宿主子会话用什么证明**：选只记一行加审查原话；没选要求宿主子会话也产出 delegate 格式的报告，因为没装 delegate 正是退路成立的前提，要求它的报告格式不现实。
- **审后改动用什么给用户看**：选在 `review-mark` 预览里按 sha256 从 git 找审查时的版本；没选在审查时另存一份文本副本，因为 git 里已经有，副本还会进仓库占地方。
- **`irreversible` 的空值判定**：选固定清单；没选「少于 N 个字算空」，字数门槛对中英文都不稳。
- **`designForcedBy` 字段**：选保留、新流程恒为 `null`；没选删掉，删字段要升主版本，module-crew 读接口要求主版本一致。

## 待定问题

无。审查报告给 hub 的位置与格式在第 5 节定下，技术方案批准后回告 ecosystem-lead。
