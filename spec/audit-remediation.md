# Spec: audit-remediation

## Objective

2026-09-28 的项目级只读审计（v0.24.0，`b2882c8`）核实了一批缺陷：命令报告成功但没做成、诊断把不同原因
混成一个、Codex 缺少 Claude 已有的入口、校验器漏检，以及文档与代码不一致。它们都不需要改变任何模块的设计。
本模块把这些缺陷逐项修掉，每项先写能在旧代码上失败的测试。

同一审计的 P1（Python 3.9 导入失败）已在 `2e9c4da` 单独修复，不在本模块内。

登记：2026-09-28 按用户决定经 `/spec-guard:add-module` 快速插入能力图，未经 Proposal 流程。

## Assumptions

1. 只修"不改设计"的缺陷。凡是会改变默认行为、删除或合并模块、放宽安全边界的事项，都不在本模块内（见 Boundaries）。
2. 所有修复都在工作区源码里验证：用仓库测试和临时消费者项目，不以本仓库 phase-guard 的输出为证据（它来自已安装版）。
3. 每项修复是一个任务、一个提交；任务之间没有顺序依赖，按 Plan 的顺序串行完成。

## Contract

每项给出：审计证据 → 修复后必须成立的行为。

### R1 快速插入不再假成功，也不再改权限（module-insert）

- 证据：`module-insert.py` 的 `_module_table_rows` 与 `_build_order_line_index` 扫描原始行，不跳过代码围栏；
  能力图在真实模块表之前有围栏示例表时，预览改的是示例，`--confirm` 输出"已写入"并退出 0，新模块却不在能力图里。
  写入用 `mkstemp` 加 `os.replace`，能力图权限从 0644 变为 0600。
- 修复后：
  - 模块表与 Build order 行的定位跳过代码围栏，与 `capability_map` 的可见行规则一致；
  - 预览和写入都断言新 id 出现在新能力图的解析结果（模块行与 Build order）中，否则拒绝并非零退出，不写文件；
  - 写入后能力图保留原有权限位。

### R2 晋级预检与证明的诊断可区分（proposal-promotion-proof）

- 证据：`prove` 在没有任何 first-parent 提交包含新模块时返回 `invalid`，与"晋级内容违反声明"无法区分；
  `preflight_as_json` 和 `as_json` 把分层诊断覆盖成 `promotion-preflight-<state>` / `promotion-<state>`，
  缺 Issue 与缺 Proposal 都显示为 `absent`；晋级白名单不允许 `tasks/<id>/todo.md`，与本插件约定冲突；
  依赖不匹配、`end` 锚点错位、Spec 头部错误三条判据没有测试守护（变异体存活）。
- 修复后：
  - 没有提交包含新模块时，返回新状态 `not-promoted`（诊断 `promotion-not-found`），命令文档说明它的含义与下一步；
  - 预检和证明透传下层的具体诊断（发布层、tracker 层、验收记录层各不相同），与 `proposal_mainline_review.as_json` 的做法一致；
  - 晋级提交**可以**额外包含 `tasks/<id>/todo.md`，不强制；其他路径仍被拒绝；
  - 上述三条判据各有一个反例测试。

### R3 验收记录可以按文档写出（proposal-mainline-review）

- 证据：验收记录要 7 个精确字段，其中 `policyDigest` 是策略规范化 JSON 的 sha256；docs、commands、references、
  skills、README 中没有任何一处说明格式或算法。
- 修复后：
  - 主链裁决结果为 `accepted-candidate` 时，输出里附带一份可直接复制的验收记录 JSON（含 `policyDigest`），
    并注明应写入的路径；命令本身仍不写任何文件；
  - `references/proposal-mainline-review.md` 与 `docs/workflow.md` 第 6 步写明字段、路径和"不可改写"的规则。

### R4 Codex 与 Claude 的入口一致，并有检查守住（local-convention、capability-history）

- 证据：`spec-guard-ops` 没有 teardown 一节，`docs/workflow.md:136` 却说有；`/history-integrity` 的 `correct`
  在 Codex 侧没有路由；没有任何检查比对命令与 skill 的入口。
- 修复后：
  - `spec-guard-ops` 增加 teardown 一节（先 `--dry-run` 预览，再经用户确认执行）和 history `correct` 路由；
  - 新检查器：`commands/*.md` 中引用的每个 `hooks/<脚本>`，都必须出现在至少一个 skill 中；刻意不对称的入口
    写进检查器的显式允许清单并说明原因；
  - 检查器在 `scripts/test-checkers.sh` 中有一正一反用例，并接入 `validate.sh`。

### R5 历史孤立目录在三棵树上都会被发现（capability-history）

- 证据：`verify-history.sh:27` 只在 `spec/history` 下报孤立目录；`tasks/history`、`.agent/history` 下的未登记
  目录会让校验"通过"。
- 修复后：三棵树中每个含文件的目录，都必须是账本中某条记录（能力图、Spec、Plan 或 state）所在的目录，否则
  报 `orphan history evidence` 并非零退出。本仓库现有的历史证据仍然通过。

### R6 退役扫描能发现回归（local-convention）

- 证据：`test-retire-legacy-tracker-bridge.sh` 只检查 10 个精确路径和少量文件的正则；新增使用 `gh issue create`
  的命令、或 `/sync-map` 出现在 hook 脚本中都不会被发现；扫描器从未被喂过反例。
- 修复后：
  - 扫描范围扩大到 `plugins/spec-guard/` 下所有非测试文件；匹配已退役的标识（`sync-map`、`spec-github-bridge`、
    `spec-gitlab-bridge`、`workspace_binding`、`bind-workspace`）和写 Issue 的命令（`gh issue create|edit`、
    `glab issue create|update`）；
  - 现行文件里"不调用旧 bridge"这类否定说明（目前在 `references/proposal-promotion-proof.md` 与
    `references/proposal-boundary-guidance.md`）用显式、带理由的允许清单放行，不用宽泛的排除；
  - 扫描器能接收一个根目录参数，并在 `scripts/test-checkers.sh` 中有一正一反用例。

### R7 归档只留下备份文件本身（collaboration-messaging）

- 证据：在较新的 SQLite（3.43.2，macOS 系统 Python 3.9 自带）下，`native_collaboration_archive.py` 的备份步骤
  在归档目录里留下 `.messages-*.sqlite-shm`，`test_native_collaboration_cutover.py` 的
  `test_archive_keeps_uncheckpointed_wal_mail_and_unread_state` 因此失败。
- 修复后：归档目录只包含 `messages.sqlite`；该测试在默认 `python3` 与 `/usr/bin/python3` 下都通过。

### R8 文档与代码一致

逐处改为与代码一致的事实，不改变任何行为：

- `spec/documentation-verification.md`：删去"`/verify-artifacts` 显示文档事实"及对应测试承诺（该集成已在
  `55278e9` 删除；重新接入属于新需求）；
- `docs/workflow.md` 命令对照：Codex 的 teardown 与 history 路由与 R4 后的实际一致；
- `commands/phase.md`：`DONE` 的含义与建议与 `module_stage.py` 一致（当前模块完成即报 DONE；新需求默认用 add-module）；
- `docs/decisions/2026-09-28-quick-insert.md`：状态改为已实现（0.24.0）；
- `CLAUDE.md`、`docs/lenses.md`：不再把已删除的 `scripts/mutation-check.py` / `evals/next-redo.sh` 当作现有工具，
  lenses 中的历史条目标明已删除；
- `CONTRIBUTING.md`、`scripts/install-git-hooks.sh`：CI 的描述改为不作具体运行次数断言的准确说法；修正
  `CLAUDE.md#发版` 失效锚点；"加新命令"补上 Codex skill 路由与 `docs/workflow.md` 命令对照；
- `docs/migration-strict-serial.md`：去掉"待发布候选"的过时说法；
- `spec/collaboration-messaging.md`：Commands 与测试清单补齐已存在的脚本和测试。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_module_insert.py                 # R1
python3 -B plugins/spec-guard/hooks/test_proposal_promotion_proof.py      # R2
python3 -B plugins/spec-guard/hooks/test_proposal_mainline_review.py      # R3
/bin/bash scripts/test-checkers.sh                                        # R4, R6
/bin/bash plugins/spec-guard/hooks/test-history-verification.sh           # R5
/bin/bash plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh   # R6
python3 -B plugins/spec-guard/hooks/test_native_collaboration_cutover.py  # R7
/usr/bin/python3 -B plugins/spec-guard/hooks/test_native_collaboration_cutover.py   # R7（macOS）
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Project structure

```text
plugins/spec-guard/hooks/module-insert.py, test_module_insert.py                    -> R1
plugins/spec-guard/hooks/proposal_promotion_proof.py, test_proposal_promotion_proof.py,
  commands/proposal-promotion-{preflight,proof}.md                                   -> R2
plugins/spec-guard/hooks/proposal_mainline_review.py, test_proposal_mainline_review.py,
  references/proposal-mainline-review.md, docs/workflow.md                          -> R3
plugins/spec-guard/skills/spec-guard-ops/SKILL.md, scripts/check-*.py（新检查器）,
  scripts/test-checkers.sh, scripts/validate.sh                                     -> R4
plugins/spec-guard/hooks/verify-history.sh, test-history-verification.sh             -> R5
plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh, scripts/test-checkers.sh -> R6
plugins/spec-guard/hooks/native_collaboration_archive.py                            -> R7
R8 所列文档                                                                          -> R8
CHANGELOG.md（Unreleased）                                                           -> 每项修复
```

## Testing strategy

- 每项修复先写测试，并确认它在修复前的代码上失败（记录失败输出），再修复到通过。
- R1、R2、R5、R6 必须有反例：断言拒绝时非零退出、不写任何文件或不放行。
- 新检查器（R4、R6）遵守 `docs/lenses.md` A2：一正一反，且"零个输入不算通过"。
- R2 的三条新反例要能杀死审计中存活的变异体：依赖比较、`end` 锚点位置、Spec 头部检查。
- 每个任务完成后运行 Commands 中的三条最小验证；R7 额外用 `/usr/bin/python3` 运行。
- R8 只改文档，用 grep 断言旧说法已消失，并通过 `check-readme-sync.py` 与 `validate.sh`。

## Boundaries

- Always：先红后绿；每项一个提交；复用 `capability_map`、`spec-digest.py`、`module_stage.py`，不复制它们的算法；
  hook 只报告、不写文件；输出仍是宿主接受的 JSON。
- Ask first：任何会改变默认行为的修复；放宽或收紧 Proposal 判据的范围超出 R2 所列；新增依赖；改 CI 配置。
- Never（本模块不做，各自另立 Spec）：
  - 协作信箱唤醒默认值改为 `wake:null`；XATS token 路径改为只走 stdio；epiq 与 XATS 依赖锁定；
  - 审计第 6 节的过度设计项（主链授权层、Proposal 模块合并、协作切换脚本合并、文档治理合并、能力历史冻结）；
  - GitHub Actions 与分支保护设置；
  - 删除或合并任何已有模块，改能力图 `## 目标`。

## Success criteria

- R1–R7 各有至少一个在旧代码上失败、在新代码上通过的测试，失败输出记录在对应提交或 Plan 的验收记录中。
- 在全新的临时消费者项目里，只按文档操作即可写出有效的验收记录（R3），不需要读源码。
- Codex 侧能通过 `spec-guard-ops` 完成 teardown（预览与执行），检查器会拦下之后新增的不对称入口（R4）。
- R8 所列文档中不再有与代码冲突的说法。
- 三条最小验证在默认 `python3` 与 `/usr/bin/python3` 下都通过；工作区 `git status` 只包含本模块的改动。

## Decisions

用户于 2026-09-28 批准本 Spec，并采用默认：

1. R2 允许晋级提交额外包含 `tasks/<id>/todo.md`（不强制）。这是本模块唯一一处放宽证明判据。
2. R2 的新状态名为 `not-promoted`。
