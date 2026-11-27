# 技术方案: sg-review-rules

<!-- spec-guard: review pending -->

需求文档：`spec/sg-review-rules.md`（用户 2026-11-27「确认需求」）。照已批总体技术方案第 7 节模块 5 那一行，不重新选型。

## 现状调研

查了下面这些（spec-guard 主干 `f63bf6b4` 加本分支）：
- **重要需求判定**：`module_stage.important()`（`module_stage.py:1703`）按顺序给出 `multi-module`（`usage_draft.batches`）、`cross-unknown`、`cross-module`（并行边界的公共文件或与未完成模块重叠）、`risk-unknown`、`risk-path`。新流程模块的影响面路径已经算进 `risk-path`（plan-auto-approve），也已经去掉了本模块自己的文档。
- **技术方案送审判定**：`design_requirement()`（`:824`）。`important` 档直接返回 `need: user`；否则看 `impact_has_old_files()`，返回 `old-files`、`impact-unknown`；再看 `designReview: on`（`configured`）。`impact_has_old_files()` 回归文档检查（regression-doc-check）也在用，所以不能删。
- **谁批技术方案**：`design_approver()`（`:852`）重要需求一律 `user`，否则看档位的 `design` 项。`design_approval()` 按批准人、送审需要、轮次记录算出 `/map --json` 的 `designApproval`，两轮有阻断后交用户（`exhausted`）。`map_view._effective_takeover()`（`map_view.py:434`）在重要需求时把 `design` 显示成 `human`，`designForcedBy: important`。
- **需求文档**：`requirement_wait()`、`requirement_hint()` 管确认停点；需求文档的批准标记只认用户（`codex-route-requirement`）。`review-mark --target spec --state codex-reviewed --review <报告>` 已经能给需求文档记一轮 Codex 审查：在「外部审查意见」一节加一行 `codex-review round=N blocking=B sha256=<审查时文件 sha256 的前 12 位>`，不改批准标记。
- **技术方案的轮次**：`review-mark --target design --state reviewer-reviewed|reviewer-approved --review <报告>` 写 `design-review round=… vendor=… report=…` 行；`DESIGN_ROUND`（`module_stage.py:57`）要求 `report=` 后是 64 位十六进制；不符合的行由 `:927` 判为损坏。delegate 报告的 `selection: none` 记成「没有审查者」（`vendor=none`）。`review_mark.py:424` 只认原始档位 `normal`、`important`。
- **`/map` 里的 `designApproval`**：`map_view.py:145` 只发布 `DESIGN_APPROVAL_FIELDS`（`status`、`approvedBy`、`reviewerVendor`、`sameVendor`、`reportSha256`、`rounds`）里的键，`design_requirement()` 的 `reason` 现在**不在** `/map` 里；`rounds` 每轮只有 `round`、`blocking`、`sha256`、`vendor`、`sameVendor`（`DESIGN_ROUND_FIELDS`，`:62`），报告指纹只在顶层、对应最后一轮。
- **需求文档的 Codex 轮次**：`review_mark` 给需求文档记 `codex-reviewed` 时按已有轮数加一，不限轮数。
- **风险清单**：`_risk_patterns()`（`:1687`）读 `.github/autopr/risk-paths.json`，读不到返回 `None`；`risk_hit()` 判路径命中。本仓库没有这份清单。「T4 路径：没有可读的风险路径清单，未检查」只由 `scope_overreach()` 给出，而它在 `BUILDING` 以外的阶段直接返回（`:2586`），所以写完技术方案、等审查时没有这句提示。
- **规则文字**：`workflow-checkpoints.md` 的「需求确认」一节没有「先审一轮」，「技术方案审查」一节写着重要需求的技术方案交用户、跨模块必为重要需求；`node-rules.md` 的「Spec 交审」「技术方案交审」两节同样；`doc-skeletons.md:14` 的档位表写着 `important`「重要需求（新模块、跨模块、碰高风险路径）」「技术方案由用户批」。
- **下游读这些值的代码**（2026-11-27 在本机两个仓库的 `origin/main` 上 `git grep` 并打开命中行核过；autopilot-hub `1abf140`，module-crew `b91b2ae`）：
  - hub `audit/flow_check.py:36-42`：新流程 `tier == important` 的模块，`designApproval` 不是 `approved` 且 `approvedBy == user` 就报严重问题 `important-design-not-user`。**本模块让重要需求在 `design=reviewer` 时由审查者放行，这里会误报。**
  - hub `orchestrator/flow.py:86-95`：合并前核验接受 `not-required`，或 `approved` 且 `approvedBy` 是 `user`、`reviewer`，不受影响；`:212` 只看 `designForcedBy` 键在不在，不受影响。
  - hub `audit/plan_check.py:79-85`：读 `important.reasons`，只在老流程分支里用（新流程模块在 `:59` 就被挑出去，`:88` 写明「不按老流程审批规则检查」），不受影响。
  - module-crew `module_crew/takeover.py:139-141`：读 `important.reasons`，只在 `spec == codex` 时用，新流程模块随后被 `FLOW_SPEC` 覆盖（`:149`），不受影响。
  - module-crew `module_crew/takeover.py:169-170`（`_design`）：`tier == important` 一律返回 `human`（「重要需求：技术方案由用户批」）。**本模块之后它仍把重要需求的技术方案交人**，不会出错，但和 spec-guard 给的批准人不一致：用户要多批一次。

## 影响面

路径都从仓库根目录写起；越界检查按这里引用的路径判定范围。

| 文件 | 改什么 |
|---|---|
| `plugins/spec-guard/hooks/module_stage.py` | `important()` 新流程不算 `multi-module`、`cross-module`；`design_requirement()` 换成三种高风险；`design_approver()` 去掉重要需求一律交用户；新增需求文档审查记录的解析、`requirement_review()`、确认停点的「先审一轮」提示与审查后改动差异 |
| `plugins/spec-guard/hooks/review_mark.py` | `--target spec` 新增 `--state host-reviewed`、`no-reviewer`；`approved` 在新流程 normal／important 没有审查记录时拒绝（`requirement-unreviewed`）；预览打印审查以来的改动；`--target design` 按生效档位放行，也接受 `host-reviewed`、`no-reviewer` |
| `plugins/spec-guard/hooks/map_view.py` | 每个模块加 `requirementReview`；`DESIGN_APPROVAL_FIELDS` 加 `reason`、`reasons`、`riskList`；`DESIGN_ROUND_FIELDS` 加 `reportSha256`；`designForcedBy` 对新流程恒为 `null` |
| `plugins/spec-guard/hooks/verify-artifacts.sh` | 不新增调用：新检查放在 `module_stage.flow_doc_problems` 里，脚本已经在调 |
| `plugins/spec-guard/references/workflow-checkpoints.md`、`plugins/spec-guard/references/node-rules.md` | 「需求确认」「技术方案审查」两节与对应停点按新规则改 |
| `plugins/spec-guard/references/doc-skeletons.md` | 需求文档审查记录的两种写法；档位表 `important` 一行改成「碰高风险路径」「技术方案按档位的 design 项：reviewer 时由第二审查者放行，否则用户批」 |
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
  - 没有审查者：新行 `<!-- spec-guard: requirement-review reviewer=none sha256=… reason=<原因> -->`，用 `review-mark --target spec --state no-reviewer --reason "<一行原因>"` 写。`--reason` 必填：去掉首尾空白后不能为空、不超过 200 字、不能含换行、`--`、`>`，否则拒绝（`requirement-review-reason`），不写文件。解析时 `reason=` 为空或缺失的行算损坏，不算记录。
- **`requirement_review(root, module)`** 返回 `None`（老流程）或 `{"required", "status", "records"}`：`status` 是 `not-required`、`missing`、`reviewed` 之一；`records` 是 `[{reviewer: codex|host|none, blocking, sha256, reason}]`（`reason` 只有 `none` 有，其余为 `null`）。只审一轮：有一条就是 `reviewed`，之后改了文件也算数。
- **只记一轮**：`required` 的需求文档已有任一种记录（`codex-review`、`requirement-review reviewer=host|none`）时，`codex-reviewed`、`host-reviewed`、`no-reviewer` 三种写法都拒绝（`requirement-review-recorded`），退出 2，不写文件。老流程模块和不 `required` 的模块，`codex-reviewed` 照旧按轮次累加。
- **硬拦**：`review-mark --target spec --state approved`（以及 `both`）对 `required` 且 `missing` 的模块拒绝，退出 2，拒绝码 `requirement-unreviewed`，不写文件。
- **确认停点的提示**：`requirement_hint` 在 `missing` 时，下一步写「先审一轮」，列出三条路（delegate 的 review 命令、宿主全新子会话、写明没有审查者），并说明审完改好、附上审查结论再复述确认；`reviewed` 时照现在的复述确认，另加一句「交用户时附上审查提了什么、改了哪些、哪些没采纳」。
- **审查以来的改动差异**（S9）：新函数 `requirement_review_diff(root, module)`，从 git 里倒着找需求文档整份 sha256 前 12 位等于那条记录的版本（最多看 50 个提交，同 `REQUIREMENT_AT_LIMIT`），返回统一差异；当前文本与记录指纹相同时返回「审查后没有改动」；找不到（没提交过、超出范围、git 读不了）返回原因。两处用它：
  - **阶段提示**：`requirement_hint` 在 `reviewed` 的确认停点直接写出差异，最多 60 行，超出时写「还有 N 行，`review-mark --target spec --state approved` 的预览里有全文」；取不到时写原因。只在确认停点算，其他阶段不跑 git。
  - **`review-mark --target spec --state approved` 的预览**：打印全文差异或原因。

### 2. 技术方案只在三种高风险时送审（需求规则 6～9、Q2 A）

`design_requirement()` 改成：

1. 新流程 `bug`、`small`（生效档位）：没有技术方案，返回 `None`（不变）。
2. 算三种理由（一种命中就送审，返回第一个命中的作 `reason`，全部写进新字段 `reasons`）：
   - `risk-path`：`impact_paths(design)` 去掉本模块自己的文档后，有路径命中 `_risk_patterns()`。清单读不到时不算命中（需求规则 9），返回值另带 `riskList: "ok"|"no-list"`。
   - `irreversible`：「接口和数据改动」（或 `Interface and data changes`）一节去掉空白、句末标点、列表符号、注释后，不是空的，也不是（不分大小写）「不涉及」「无」「没有」`None`、`N/A`、`Not applicable`、`No changes` 之一。
   - `new-dependency`：影响面里有路径的文件名是依赖清单或锁文件：`package.json`、`package-lock.json`、`npm-shrinkwrap.json`、`yarn.lock`、`pnpm-lock.yaml`、`requirements*.txt`、`pyproject.toml`、`poetry.lock`、`Pipfile`、`Pipfile.lock`、`go.mod`、`go.sum`、`Cargo.toml`、`Cargo.lock`、`Gemfile`、`Gemfile.lock`。
3. 都不命中时，`designReview: on` 返回 `configured`；否则 `need: none`。
4. 删掉 `important → need: user` 和 `old-files`、`impact-unknown` 两个分支；`impact_has_old_files()` 留给回归文档检查用。
5. **没有风险清单的提示**（S6）：`riskList` 是 `no-list` 时，技术方案阶段（`NEEDS_REGRESSION` 的技术方案提示，`_review_hint` 的 design 一关）也写「T4 路径：没有可读的风险路径清单，`risk-path` 未检查」，并建议补清单；`/map --json` 的 `designApproval.riskList` 给同一个值。`BUILDING` 的越界检查那句照旧。

### 3. 谁批技术方案（需求规则 10～12、Q4 A）

- `design_approver()`：只看档位的 `design` 项，`reviewer` → `reviewer`，否则 `user`；不再因重要需求返回 `user`。
- `design_approval()` 不用改分支逻辑：`need: review` + `reviewer` 时，无阻断的 `reviewer-approved` 就是 `approved`（`approvedBy: reviewer`）；`need: none` + `reviewer` 是 `not-required`；`design=human` 时照旧 `pending-user`；两轮有阻断照旧交用户。
- `map_view._effective_takeover()`：新流程模块不再把 `design` 强制成 `human`，`designForcedBy` 恒为 `null`（字段保留，接口说明改为「从 1.27 起新流程恒为 null」）。
- 技术方案的宿主子会话退路：`review-mark --target design --state host-reviewed --blocking <B>` 写一行 `design-review round=N blocking=B sha256=… vendor=host same-vendor=true criteria=host report=none`；`B` 为 0 时同时写 `reviewer-approved` 标记，等同于一轮无阻断的审查。`--state no-reviewer` 写 `vendor=none … report=none`，状态照现有的 `unreviewed`（交用户批）。
  - **行格式扩展**：`DESIGN_ROUND` 的 `report=` 改成接受 64 位十六进制或字面量 `none`；`design_round_records()` 把 `none` 解析成 `reportSha256: null`。`report=none` 只允许和 `vendor=host`、`vendor=none` 同时出现，其余组合仍按损坏报（`:927`）。
  - **旧版兼容**：0.98.0 及以前的 spec-guard 读到 `report=none` 的行会按损坏报。只在同一项目混用新旧版本时出现，写进 CHANGELOG。
- `review_mark.py:424` 的档位检查改成 `effective_tier`，让被抬升的 `bug`、`small` 能记技术方案。

### 4. 重要需求判定（需求规则 14～16、Q1 A）

`important()` 里，`multi-module` 与 `cross-module` 两段只在 `not _v2(root, module)` 时执行；新流程模块只剩 `risk-path`（`cross-unknown`、`risk-unknown` 原本就只对老流程的 Codex 档生效）。`effective_tier` 的抬升逻辑不变。

### 5. 审查报告给 hub 模块 8 的位置与格式（需求规则 13、S8）

- **结构化事实**：`/map --json` 每个模块的 `requirementReview`（`{required, status, records}`）与 `designApproval`。`designApproval` 现有 `status`、`approvedBy`、`reviewerVendor`、`sameVendor`、`reportSha256`（最后一轮）、`rounds`；本模块新加 `reason`、`reasons`、`riskList`，并给 `rounds` 每轮加 `reportSha256`（宿主子会话与没有审查者的轮次为 `null`），hub 可以逐轮对上报告。hub 只读 `/map --json`，不读文档。
- **审查原文**：需求文档与技术方案各自的「外部审查意见」一节，agent 写入审查提了什么、怎么处理；delegate 报告本体在 delegate 的产物目录，`/map` 里只给报告的 sha256。
- 技术方案批准后把这一节抄给 ecosystem-lead，转 hub 模块 8。

### 6. 规则文字与使用者文档

- `workflow-checkpoints.md`「需求确认」：新流程 normal／important 需求先审一轮（三条路、只审一轮、硬拦、交用户时附审查提了什么、改了哪些、哪些没采纳，以及审查以来的改动）；「新流程需求由用户确认」一条把「重要需求时先 interview-me」保留。
- 「技术方案审查」：送审只看三种高风险与 `designReview`；`design=reviewer` 时重要需求也由第二审查者放行；删掉「重要需求一律交用户」「跨模块必为重要需求」的说法；「重要需求判定」写明新流程只看风险路径。
- `node-rules.md` 的「Spec 交审」「技术方案交审」对应改一两句，守住每节 3200 字节上限。
- `doc-skeletons.md` 档位表 `important` 一行：说明改成「重要需求（碰高风险路径）」，技术方案一栏改成「按档位的 design 项：reviewer 时由第二审查者放行，否则用户批」；老流程不用这张表。规则测试钉住新文字，并断言旧说法「技术方案由用户批」不再出现。

### 7. 接口

`interface.json` 升 `1.27`：`designApproval` 新字段 `reason`（取值 `risk-path`、`irreversible`、`new-dependency`、`configured`，不送审时为 `null`；`old-files`、`impact-unknown` 写明「1.27 起新流程不再出现」）、`reasons`、`riskList`；`designApproval.rounds` 每轮加 `reportSha256`；顶层 `reportSha256` 与 `rounds` 的报告指纹允许 `null`（宿主子会话、没有审查者）；`statusValues` 里写着「not important、只列新文件」的说明按新判定改写；`mapView` 每个模块加 `requirementReview`；`reviewMark` 的 state 加 `host-reviewed`、`no-reviewer`，参数加 `--blocking`、`--reason`，拒绝码加 `requirement-unreviewed`、`requirement-review-recorded`、`requirement-review-reason`；`important.reasons` 说明新流程只会是 `risk-path`；`designForcedBy` 说明改写。

## 接口和数据改动

| 位置 | 改动 | 旧调用方 |
|---|---|---|
| `/map --json` 每个模块 `requirementReview` | 新字段 | 不读 |
| `designApproval.reason`、`reasons`、`riskList` | 新字段（`reason` 以前只在内部，不在 `/map`） | 不读 |
| `designApproval.rounds[*].reportSha256` | 新字段；宿主子会话、没有审查者的轮次为 `null` | 不读 |
| `designApproval.approvedBy` | 新流程重要需求在 `design=reviewer` 时可为 `reviewer` | **hub `audit/flow_check.py:36-42` 会报 `important-design-not-user`；module-crew `takeover.py:169-170` 仍交人**（见风险与待定问题） |
| `takeover.designForcedBy` | 新流程恒为 `null` | 读到 `null` 即「没有强制」，与原义一致 |
| `important.reasons` | 新流程不再出现 `multi-module`、`cross-module` | hub、module-crew 都只在老流程分支用它（已核） |
| 需求文档 | 新记录行 `requirement-review reviewer=host|none …` | 旧版 spec-guard 不认，忽略 |
| 技术方案 | `design-review` 行的 `report=none` | 0.98.0 及以前按损坏报 |
| `review-mark` | 新 state `host-reviewed`、`no-reviewer`，新参数 `--blocking`、`--reason`，新拒绝码 `requirement-unreviewed`、`requirement-review-recorded`、`requirement-review-reason` | 旧版不认这些参数 |

## 风险与回滚

- **宿主子会话的记录靠 agent 自觉**：`host-reviewed` 没有可验的报告，agent 可以不审就记。缓解：只能记一次（`requirement-review-recorded` 拒绝第二条），审查原话必须写进「外部审查意见」，交用户时一并给出；需求最后仍要用户确认。
- **阶段提示要跑 git**：差异只在需求确认停点算，最多看 50 个提交、最多输出 60 行；其他阶段不跑。
- **下游两处和新规则冲突**（核对位置见现状调研）：
  - hub `audit/flow_check.py:36-42` 要求新流程重要需求的技术方案 `approvedBy == user`。spec-guard 让它在 `design=reviewer` 时由审查者放行后，hub 巡检会对这类模块报严重问题，是误报。要 hub 改成：`takeover.design` 是 `reviewer` 时也接受 `approvedBy == reviewer`。
  - module-crew `takeover.py:169-170` 把重要需求的技术方案一律交人。不会出错，只是用户要多批一次；要 module-crew 去掉这条，改按 `takeover.design`。
  - 这两处是对方仓库的代码，本模块不改；技术方案批准后经 ecosystem-lead 把两条改动需求发给两边。发版顺序见待定问题。
  - 其余读法不受影响：hub `orchestrator/flow.py:86-95` 合并前核验已接受 `reviewer`，`:212` 只看 `designForcedBy` 键在不在；两边读 `important.reasons` 都只在老流程分支。
- **硬拦会挡住正在走流程的模块**：已经交给用户、还没确认的新流程需求文档，升级后要先补一轮审查记录才能确认。可以用 `no-reviewer` 写明原因放行，不会卡死。
- **没有风险清单的项目**：`risk-path` 永远不命中，技术方案只因 `irreversible`、`new-dependency` 送审。提示照旧写明没有清单。
- **回滚**：一个 PR，revert 合并提交即可。已写进文档的 `requirement-review` 行留着不起作用；回滚后旧版重新按 `old-files` 等规则判，已经放行的技术方案可能变回待审，需要时重新记录。

## 方案取舍

- **需求文档审查记录放在哪**：选「外部审查意见」一节里的记录行，和现有 `codex-review` 行同一处、同一种写法；没选在批准标记里加字段，因为批准标记只认用户，混进审查信息会让「谁批的」难判。
- **宿主子会话用什么证明**：选只记一行加审查原话；没选要求宿主子会话也产出 delegate 格式的报告，因为没装 delegate 正是退路成立的前提，要求它的报告格式不现实。
- **审后改动用什么给用户看**：选按 sha256 从 git 找审查时的版本，阶段提示与 `review-mark` 预览都给；没选在审查时另存一份文本副本，因为 git 里已经有，副本还会进仓库占地方。
- **宿主子会话的技术方案轮次怎么记**：选扩展现有 `design-review` 行，`report=none`；没选另起一种行，因为另起的行旧版也不认，还要在 `designApproval` 里合并两种来源。
- **`irreversible` 的空值判定**：选固定清单；没选「少于 N 个字算空」，字数门槛对中英文都不稳。
- **`designForcedBy` 字段**：选保留、新流程恒为 `null`；没选删掉，删字段要升主版本，module-crew 读接口要求主版本一致。

## 待定问题

- **发版顺序**（用户 2026-11-27「批准，发版等 hub」）：技术方案批准后经 ecosystem-lead 把两条需求发给 hub、module-crew；spec-guard 照常实现、开 PR、合并，**发版等 hub 的 `flow_check` 改动合并后再发**；module-crew 那条只是多批一次，不卡发版。
- 审查报告给 hub 的位置与格式在第 5 节定下，技术方案批准后回告 ecosystem-lead。

## 外部审查意见

<!-- spec-guard: design-review round=1 blocking=8 sha256=a5c893b4ede0 vendor=openai same-vendor=false criteria=design-v1 report=38446db77f4a452621658b2ea5a493a7a7d492f061de1274f94df7619cdb98f5 -->

第 1 轮（Codex，gpt-5.6-sol high，8 条阻断、1 条建议），逐条对照代码核实，全部采纳：
1. 阶段提示不打印差异，不满足 S9 → 采纳：`requirement_hint` 在确认停点直接给差异（最多 60 行）或原因。
2. 没有落实「需求文档只审一轮」→ 采纳：已有任一种记录时三种写法都拒绝（`requirement-review-recorded`）。
3. 宿主子会话的 `report=none` 不符合 `DESIGN_ROUND` → 采纳：正则接受 `none`，只限 `vendor=host|none`，旧版兼容写进风险。
4. `designApproval` 新字段会被 `DESIGN_APPROVAL_FIELDS` 丢掉 → 采纳，并更正现状：`reason` 原本就不在 `/map`，作为新字段加入。
5. 逐轮报告指纹不存在 → 采纳：`rounds` 每轮加 `reportSha256`。
6. 没有风险清单的提示只在 `BUILDING` 出现 → 采纳：技术方案阶段也提示，`/map` 给 `riskList`。
7. `doc-skeletons.md` 档位表仍写「技术方案由用户批」→ 采纳：改表并加文字回归。
8. `no-reviewer` 不写原因也能过闸 → 采纳：`--reason` 必填并写进记录行。
9. （建议）下游兼容结论没有证据 → 采纳。重新核对后**原结论是错的**：hub `audit/flow_check.py:36-42` 会误报、module-crew `takeover.py:169-170` 仍交人；已写进现状调研、接口表、风险与待定问题，并写明核对的提交。
