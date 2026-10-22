# Plan: tracker-provider-unify

<!-- spec-guard: review approved -->

依据 [`spec/tracker-provider-unify.md`](../../spec/tracker-provider-unify.md)（2026-10-22 批准，事项 C5）。
Spec 的两个待定问题按用户答复定为：**Open question 1 选 A**（Proposal 只读命令缺省主机 `github.com`／`gitlab.com`，与收尾一致，更新说明写明）；
**Open question 2 选 A**（收尾一侧 GitLab 放宽为与目标 `web_url` 同一 scheme）。

分支 `tracker-provider-unify`，worktree `.claude/worktrees/current-plugin-owner-aa5b98-crew/tracker-provider-unify`，从集成分支 `crew/fix-batch` 开出。
module-crew 模块会话：只本地提交，不推送、不开 PR；合并由模块协调按用户原话做。CHANGELOG 与版本号由模块协调整批合完后统一改，
本模块把拟写的更新说明记在 todo 里（用户 2026-10-22 答复）。

所需工具：无 UI 改动，不需要浏览器或电脑操作；不访问真实 GitHub/GitLab。

## 并行边界

- 独占：`plugins/spec-guard/hooks/hosted_ticket_provider.py`、`plugins/spec-guard/hooks/local_ticket_provider.py`、`plugins/spec-guard/hooks/local_ticket_github.py`、`plugins/spec-guard/hooks/local_ticket_gitlab.py`、`plugins/spec-guard/hooks/local_ticket_preview.py`、`plugins/spec-guard/hooks/proposal_tracker_read.py`、`plugins/spec-guard/hooks/proposal_closeout_github.py`、`plugins/spec-guard/hooks/proposal_closeout_gitlab.py`、`plugins/spec-guard/hooks/proposal_review.py`、`plugins/spec-guard/hooks/proposal_promotion_proof.py`、`plugins/spec-guard/hooks/test_tracker_provider_contract.py`、`plugins/spec-guard/hooks/test_hosted_ticket_read.py`、`plugins/spec-guard/hooks/test_hosted_ticket_write.py`、`plugins/spec-guard/hooks/test_hosted_ticket_actions.py`、`plugins/spec-guard/hooks/test_local_ticket_providers.py`、`plugins/spec-guard/hooks/test_local_ticket_publish.py`、`plugins/spec-guard/hooks/test_proposal_tracker_read.py`、`plugins/spec-guard/hooks/test_proposal_closeout_providers.py`、`plugins/spec-guard/hooks/test_proposal_review.py`、`plugins/spec-guard/hooks/test_proposal_promotion_proof.py`、`plugins/spec-guard/commands/proposal-review.md`、`plugins/spec-guard/commands/proposal-promotion-preflight.md`、`plugins/spec-guard/commands/proposal-promotion-proof.md`、`plugins/spec-guard/references/proposal-tracker-read.md`、`spec/proposal-tracker-read.md`、`spec/local-ticket-portability.md`

说明：
- 越界检查（`module_scope.py`）只从 Spec 读这一节。本节按用户答复写在 Plan；**是否同时把同样一节补进 Spec**（Spec 指纹会变，最终验收附差异一并复审）在本次交审里请用户定。
- 另有两个文件本模块要各改一小段，但可能与同批其他模块重叠，不列为独占：`scripts/validate.sh`（登记新测试一行）、
  `plugins/spec-guard/skills/spec-guard-ops/SKILL.md`（Proposal 命令段补 `--host`）。改前先 `module-crew sync`，冲突按 sync 规则处理。
- 下游 `proposal-fixes` 依赖本模块（会改 `proposal_closeout.py` 与候选池），本模块不碰 `proposal_closeout.py`。

## 实现要点

- **共享层只有一处**：`hosted_ticket_provider.py` 的 `GitHubIssues`／`GitLabIssues` 扩展为能被三类调用方共用：
  GitLab 目标接受项目路径或正整数 project id（`target_facts` 按形态比对 `path_with_namespace` 或 `id`，记下读回的路径与 scheme）；
  列表与单项多带 `labels`（原样列表）与 `container`（GitHub `full_name`、GitLab `project_id`），已有字段不变。
- **普通 Issue 判定**沿用现有 `GitLabIssues._issue` 的写法（`issue_type`、`type` 缺省按普通 Issue；地址认 `/-/issues/` 与 `/-/work_items/`），交接与收尾改用它。
- **适配层只做差异**：交接把 `HostedTicketError` 转成 `InventoryError`（消息不变）、`ProviderRejected` 转成本地 `ProviderRejected`（状态码不变），
  分页上限的消息仍为 `publication-uncertain: provider pagination limit reached`；GitLab 正文补末尾换行、`set_closed(closed)` 可重新打开、写权限判断留在 `local_ticket_preview`。
  收尾把共享层的规范化结果映射回 `recover_tracker_issue` 认的平台形状（GitHub `number/body/labels/state/repository`、GitLab `iid/project_id/description/labels/state`）。
  Proposal 读取同样映射后交给原 `recover_tracker_issue`；`HostedTicketError` → `unknown`。
- **Proposal CLI**：`proposal_review.py`、`proposal_promotion_proof.py` 加 `--host`，传进 `read_tracker(..., host=...)`；结果 JSON 加 `host`。
- **结构检查**写成测试：扫描 `hooks/*.py`（排除 `test_*`），除 `hosted_ticket_provider.py` 外不得出现 `"gh"`／`"glab"` 字面量。

## Task List

### Task 0：提交已批准的 Spec 标记、Plan 与 todo

Spec 已按用户答复写入批准标记；Plan 获批后用 `review_mark` 记批准，与 todo 一起提交。

- 验收：`verify-and-commit.sh` 快档通过。

### Task 1：共享回归（先红）

新增 `hooks/test_tracker_provider_contract.py`：Spec「Testing strategy」第一组全部断言，四个入口（托管事项客户端、交接适配、Proposal 读取、收尾适配）
用同一批 fixture 跑；加上结构检查。现在应当红：交接与收尾的 `issue_type`、Proposal 读取的 `--hostname` 与 50 页、交接的 `work_items` 地址与写入状态、结构检查。
在 `scripts/validate.sh` 登记一行。记下红的用例清单。

- 验收：新测试运行、失败的恰是 Spec 列出的分叉；其他测试不变。
- 验证：`python3 -B plugins/spec-guard/hooks/test_tracker_provider_contract.py`（预期失败）、`/bin/bash scripts/validate.sh --quick`。

### Task 2：共享层扩展（托管事项保持绿）

按「实现要点」扩展 `GitHubIssues`／`GitLabIssues`（project id、`labels`、`container`）。托管事项入口的共享回归用例转绿；原有托管事项回归不变。

- 验收：`test_hosted_ticket_read.py`、`test_hosted_ticket_write.py`、`test_hosted_ticket_actions.py` 全过；共享回归中托管事项入口全绿。
- 文件：`hosted_ticket_provider.py` 与上述测试（只在需要新字段断言时改）。

### Task 3：交接改用共享层

`local_ticket_github.py`／`local_ticket_gitlab.py` 改为包共享客户端；`local_ticket_preview.target_facts` 改用共享客户端读目标再判写权限；
`local_ticket_provider.py` 删去传输与分页，只留错误类型（或从共享层转出）。更新 `test_local_ticket_providers.py` 中直接测本地传输的用例改测共享传输；
`test_local_ticket_publish.py` 的状态断言不改。

- 验收：交接入口的共享回归全绿（`issue_type`、`work_items`、写入状态未知）；`test_local_ticket_providers.py`、`test_local_ticket_publish.py`、`test_local_ticket_portability.py` 全过，错误短码不变（AC2、AC6）。

### Task 4：收尾改用共享层

`proposal_closeout_github.py`／`proposal_closeout_gitlab.py` 读取改调共享客户端并映射回原形状；`set_stage` 与写入不变；GitLab scheme 跟随目标（Open question 2 选 A）。

- 验收：收尾入口共享回归全绿；`test_proposal_closeout_providers.py`、`test_proposal_closeout.py` 全过（AC2、AC6）。

### Task 5：Proposal 读取改用共享层并绑定主机

`read_tracker` 加 `host` 关键字，用共享客户端读完整候选集；GitHub 由 `gh issue list` 改为 `gh api`；分页 50 页。
`proposal_review.py`、`proposal_promotion_proof.py` 加 `--host`（缺省按平台），JSON 加 `host`。更新 `test_proposal_tracker_read.py` 的 GitHub fixture 为 REST 形状、
`test_proposal_review.py`／`test_proposal_promotion_proof.py` 补 `--host` 用例。

- 验收：共享回归全绿，包括结构检查（AC1～AC4）；三份测试全过（AC3、AC6）。

### Checkpoint 1（report）：变异核对

在一份工作区副本上分别：去掉 GitLab 列表的 `issue_type=issue`；去掉 Proposal 读取的 `--hostname`；把 `MAX_PAGES` 改回 10。每种都应让共享回归变红；结果记进 todo（AC5）。

### Task 6：文档与更新说明

`commands/proposal-review.md`、`proposal-promotion-preflight.md`、`proposal-promotion-proof.md`、`skills/spec-guard-ops/SKILL.md` 的 Proposal 段、
`references/proposal-tracker-read.md` 写明 `--host` 与缺省；`spec/proposal-tracker-read.md`、`spec/local-ticket-portability.md` 只改事实句（`gh issue list`、10 页、普通 Issue 判定）。
在 todo 里写拟进 CHANGELOG 的更新说明（含 Open question 1 的行为变化：自建实例要给 `--host`），由模块协调整批写入。

- 验收：`/bin/bash scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全过（AC7）。

### Task 7：合入集成分支

单独执行 `module-crew sync`，把集成分支合进本分支，再跑完整检查（三条最小验证）。

- 验收：sync 退出码 0（冲突按 sync 规则处理）；三条检查全过。

### Checkpoint 2（gate）：模块最终验收

发最终验收【交审】：按 AC1～AC7 逐条给证据、变异核对结果、改动统计与越界检查（`module_scope.py check --base crew/fix-batch` 的结果，Spec 没有并行边界一节时如实说明）、
新增依赖与锁文件（预计无）、提交表、拟写的更新说明。不推送、不开 PR，合并由模块协调按用户原话做。

## 风险

- `test_local_ticket_publish.py` 依赖本地传输的错误类型与消息：适配层的错误转换写错会让发布器状态变；以该测试原样全过为准。
- GitHub Proposal 读取从 `gh issue list` 换成 `gh api` 后，fixture 要整体换形状；Proposal 身份规则仍只在 `recover_tracker_issue`，不在适配层另写判定。
- Open question 1 的行为变化对已有自建实例用法可见，更新说明必须写明。
- `scripts/validate.sh` 与 `spec-guard-ops/SKILL.md` 可能与同批模块冲突，sync 时处理。

## 中途会停下的地方

- Checkpoint 1：`report`，记录后继续。
- Checkpoint 2：`gate`，最终验收；不含推送与开 PR。
- 无其他中途 `gate`。
