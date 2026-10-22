# Spec: tracker-provider-unify

<!-- spec-guard: review approved 9e36d79c0af5 -->

## Objective

spec-guard 里有三套各自实现的 GitHub/GitLab 读写，已经出现分叉：

| 用途 | 现在的实现 | 已发现的分叉 |
| --- | --- | --- |
| 托管事项（`hosted-ticket-workflow`） | `hooks/hosted_ticket_provider.py` | 基准：GitLab 列表带 `issue_type=issue`，逐项校验类型；所有请求带 `--hostname`；50 页 × 100 |
| 本地事项交接（`local-ticket-portability`） | `hooks/local_ticket_provider.py`、`local_ticket_github.py`、`local_ticket_gitlab.py`、`local_ticket_preview.py` 的 `target_facts` | 自带一份传输与分页；GitLab 列表**不带** `issue_type=issue`、不校验类型，会把事件（incident）、测试用例等其他类型纳入（审查 F11）；GitLab 事项地址只认 `/-/issues/`，不认 `/-/work_items/`；GitHub 地址比 `hostname` 而非 `netloc`；写入在退出码为 0 时不看 HTTP 状态 |
| Proposal 读取与收尾（`proposal-tracker-read`、`proposal-closeout`） | `hooks/proposal_tracker_read.py` 的 `read_tracker`；`proposal_closeout_github.py`、`proposal_closeout_gitlab.py` | 读取：GitLab 请求**不带** `--hostname`，自建实例与 glab 默认主机不同时读错实例（审查 F7）；GitHub 走 `gh issue list` 而非 `gh api`，也不绑定主机；上限 10 页 × 100。收尾：GitLab 列表不带 `issue_type=issue`；GitLab 只认 `https` |

本模块把它们合并成**一套**读写：一份传输、一份分页、一份 Issue 判定，三个用途在它上面各留一层薄适配，只保留各自真正不同的部分。
合并后的共同行为由同一组回归锁住，以后任何一处再分叉都会变红。

登记：2026-10-22 修复批次插入能力图（用户批准事项 C1），依赖 `hosted-ticket-workflow`、`proposal-tracker-read`。
依据决定记录 D11（「F11 的三套 GitHub/GitLab 读写合并为一套」）、D12（托管事项与交接到远端保留，F11 要修）、D13（Proposal 保留，修 F7），
审查 `docs/reports/2026-10-22-multidimension-audit.md` 的 F7、F11。下游 `proposal-fixes` 依赖本模块。

## Assumptions

1. **合并到 `hooks/hosted_ticket_provider.py`**：收尾适配已经在用它的传输，改动最小。它成为唯一直接调用 `gh`／`glab` 的模块
   （`proposal_tracker_read.py`、`local_ticket_*.py`、`proposal_closeout_*.py` 不再自己拼 `gh`／`glab` 命令）。
   文件名不改；`local_ticket_provider.py` 里的传输与分页删掉，只留本地发布器要的错误类型（或改为从共享模块转出）。
2. **普通 Issue 的判定只有一处**：
   - GitHub：列表与单项里带 `pull_request` 的一律不是 Issue（现行三处一致，保持）。
   - GitLab：列表请求一律带 `issue_type=issue`；返回的任何一项 `issue_type` 不是 `issue`（字段缺省按 `issue`）或 `type` 不是 `ISSUE`（缺省按 `ISSUE`），
     判为平台没按过滤返回 → 整次读取不可信（托管事项 `unknown`、交接 `provider-unavailable`、Proposal 读取 `unknown`），不悄悄跳过。
   - GitLab 事项地址认 `/<项目路径>/-/issues/<iid>` 与 `/<项目路径>/-/work_items/<iid>` 两种；按 project id 绑定的用途（Proposal）用目标读回的 `path_with_namespace` 比对。
3. **GitLab 一律绑定主机，GitHub 同样**：每个 `gh api`／`glab api` 请求都带 `--hostname <主机>`。Proposal 三个只读命令
   （`proposal_review.py`、`proposal_promotion_proof.py` 的预检与证明）新增可选 `--host`，缺省 `github.com`／`gitlab.com`，与 `proposal_closeout.py` 现行缺省一致；
   JSON 结果多一个 `host` 字段，让读的是哪个实例一眼可见。`read_tracker(proposal, platform, target, runner=None, host=None)` 新增关键字参数，不传按同样缺省。
   **行为变化**：以前靠 glab／gh 默认主机读自建实例的用法，升级后要显式给 `--host`；CHANGELOG 写明。
4. **GitHub 的 Proposal 读取改走 `gh api`**：与其他两处同一传输，不再用 `gh issue list --json`。`_closed` 对大写的兼容保留（无害），注释改为如实说明。
5. **分页上限一致**：每页 100、最多 50 页（现托管事项与交接的值），Proposal 读取从 10 页提到 50 页；到上限仍满页 → 不完整，按各用途的「不完整」处理，绝不当作 `absent`。
6. **主机地址比对一致**：响应里的 `html_url`／`web_url` 的 `netloc` 必须与绑定主机逐字相等；GitLab 的 scheme 取目标读回的 `web_url` 的 scheme（允许 `http`／`https`），
   之后每项事项、MR 的地址都必须同一 scheme。收尾一侧由「只认 https」放宽为与此一致（自建 http 实例此前只在收尾一侧被拒）。
7. **写入结果判定一致**：一律用共享的 `run_write_json`（`--include` 读 HTTP 状态；4xx 中的明确拒绝 → `ProviderRejected`，其他失败或读不到状态 → 结果未知）。
   交接一侧以前「退出码 0 就信 payload」的路径收紧到同一规则。
8. **各用途保留的差异**（留在薄适配层，不进共享层）：
   - 交接：目标须有写权限（GitHub `push/maintain/admin`、GitLab 访问级别 ≥ 30）；GitLab 正文补末尾换行（快照摘要比对依赖它）；`set_closed` 可以重新打开；
     对外仍抛 `InventoryError`／本地的 `ProviderRejected`，错误短码（`provider-unavailable`、`publication-uncertain`、`provider-rejected` 等）与现行一致，
     本地发布器（`local_ticket_publish.py`）的状态判定不变。
   - 托管事项：`get_delivery`（PR／MR 交付核对）与私有 note 中出现托管标记即冲突的规则不变；对外结果的截断与脱敏（`public_result`）不变。
   - Proposal：身份规则仍只在 `recover_tracker_issue`／`validate_tracker`；收尾的 `set_stage`（GitHub 先加后删、GitLab 一次请求）不变；读取命令仍只读。
9. **不改**：结果模型（`verified/absent/invalid/unknown`、托管事项的 `found/absent/unknown/conflict`）、标记格式、命令名、`interface.json`、Local（Epiq）后端、tracker-default 的解析。
10. **版本与 CHANGELOG**：本批次统一发版，版本号由模块协调按批次定；本模块不改版本号。CHANGELOG 若是公共文件，由模块协调统一写，本模块在最终验收交审里给出拟写条目。

## Contract

### 共享层 `hooks/hosted_ticket_provider.py`

- 传输：`run_json`、`run_write_json`、`pages`（`PAGE_SIZE = 100`、`MAX_PAGES = 50`）、`HostedTicketError`、`ProviderRejected`，是全插件唯一一份。
- 平台客户端 `GitHubIssues`／`GitLabIssues`：`target_facts`、`list_issues`、`get_issue`、`list_comments`、`create_issue`、`create_comment`、`set_closed`、`get_delivery`，
  按 Assumptions 2、3、5、6、7 实现；GitLab 目标既可给项目路径也可给正整数 project id（后者用于 Proposal）。
  列表与单项把标签一并带出，供 Proposal 使用；其余调用方忽略。

### 薄适配层

- `local_ticket_github.py`／`local_ticket_gitlab.py`：`GitHubHandoff`／`GitLabHandoff` 类名与方法签名不变，内部改调共享客户端，只做 Assumption 8 的交接差异与错误转换。
  `local_ticket_preview.target_facts` 改用共享客户端读目标，再加写权限判断。
- `proposal_closeout_github.py`／`proposal_closeout_gitlab.py`：`GitHubCloseout`／`GitLabCloseout` 类名与方法不变，读取改调共享客户端，`set_stage` 留在这里。
- `proposal_tracker_read.py`：`read_tracker` 用共享客户端读完整候选集，交给原 `recover_tracker_issue`；传输失败、不完整 → `unknown`（与现行一致）。

### 命令与文档

- `proposal_review.py`、`proposal_promotion_proof.py` 新增 `--host`；`commands/proposal-review.md`、`proposal-promotion-preflight.md`、`proposal-promotion-proof.md`、
  `skills/spec-guard-ops/SKILL.md` 对应段与 `references/proposal-tracker-read.md` 写明 `--host` 与缺省。
- `spec/proposal-tracker-read.md`、`spec/local-ticket-portability.md` 里关于「GitHub 用 `gh issue list`」「10 页」及普通 Issue 判定的说法改为如实描述（接口 Spec 只改这些事实句）。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_tracker_provider_contract.py
python3 -B plugins/spec-guard/hooks/test_hosted_ticket_read.py
python3 -B plugins/spec-guard/hooks/test_local_ticket_providers.py
python3 -B plugins/spec-guard/hooks/test_proposal_tracker_read.py
python3 -B plugins/spec-guard/hooks/test_proposal_closeout_providers.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

- **同一组回归**（新增 `hooks/test_tracker_provider_contract.py`）：同一批 GitHub／GitLab JSON fixture 依次喂给四个入口
  （托管事项客户端、交接适配、Proposal 读取、Proposal 收尾适配），断言它们一致：
  - 每条 argv 都以 `gh api --hostname <主机>`／`glab api --hostname <主机>` 开头；GitLab 列表 argv 含 `issue_type=issue`；
  - GitLab 列表里混进一个 `issue_type: incident`（或 `type: TASK`）的项 → 四个入口都判为读取不可信，没有一个把它当成普通 Issue 或悄悄跳过；
  - GitHub 列表里的 PR 四个入口都排除；
  - 第 50 页仍满 100 条 → 四个入口都判不完整；第 11～50 页才结束的候选集 Proposal 读取也能完整读到（以前 10 页即放弃）；
  - `web_url` 用 `/-/work_items/<iid>` 的事项四个入口都接受；主机或 scheme 与目标不同 → 都拒；
  - 写入：`--include` 返回 403／422 → 交接与托管事项都报明确拒绝；退出码 0 但读不到 HTTP 状态 → 都报结果未知。
  - 结构检查：除 `hosted_ticket_provider.py` 外，`hooks/` 下的非测试 Python 文件里不再出现 `"gh"`／`"glab"` 命令字面量。
- **各入口原有回归**照跑并按新 argv 更新 fixture（GitHub Proposal 读取的 fixture 由 `gh issue list` 形状改为 REST 形状）；交接的错误短码、发布器状态断言不变。
- **Proposal CLI**：`--host gitlab.example.com` 时 argv 带该主机；不传时为 `gitlab.com`；结果 JSON 带 `host`。
- **变异**（手工改坏验证，记入 todo）：去掉 GitLab 列表的 `issue_type=issue`、或在 Proposal 读取里去掉 `--hostname`、或把一处 `MAX_PAGES` 改回 10，共享回归都变红。
- 不访问真实网络；本模块不改远端行为语义以外的东西，真实宿主往返不在本模块验收内（托管事项的真实往返证据仍以原模块为准）。不涉及浏览器 UI。

## Boundaries

- **会做**：Assumptions 与 Contract 列出的代码、测试、命令与参考文档、两份接口 Spec 的事实句。
- **先问**：改结果模型或错误短码；让 Proposal 读取命令从 tracker-default 取主机；删除或改名交接／收尾适配类；支持 GitHub/GitLab 以外的平台；改版本号。
- **不做**：任何真实远端写入；改 Local（Epiq）后端、`ticket` 受理、tracker-default 解析；Proposal 锁与候选池诊断（`proposal-fixes` 的范围）；能力图目标段改写（`fact-fixes` 的范围）。
- **并行边界**：下面一节按 Plan 批准时的用户答复（D3 A）补入，与 Plan 同名一节一致；`scripts/validate.sh`（登记新测试一行）与 `plugins/spec-guard/skills/spec-guard-ops/SKILL.md`（补 `--host`）各改一小段、可能与同批模块重叠，不列独占。
- **公共文件**：新测试登记到 `scripts/validate.sh`、写 CHANGELOG，如属公共文件，按【公共变更请求】提给模块协调。

## 并行边界

- 独占：`plugins/spec-guard/hooks/hosted_ticket_provider.py`、`plugins/spec-guard/hooks/local_ticket_provider.py`、`plugins/spec-guard/hooks/local_ticket_github.py`、`plugins/spec-guard/hooks/local_ticket_gitlab.py`、`plugins/spec-guard/hooks/local_ticket_preview.py`、`plugins/spec-guard/hooks/proposal_tracker_read.py`、`plugins/spec-guard/hooks/proposal_closeout_github.py`、`plugins/spec-guard/hooks/proposal_closeout_gitlab.py`、`plugins/spec-guard/hooks/proposal_review.py`、`plugins/spec-guard/hooks/proposal_promotion_proof.py`、`plugins/spec-guard/hooks/test_tracker_provider_contract.py`、`plugins/spec-guard/hooks/test_hosted_ticket_read.py`、`plugins/spec-guard/hooks/test_hosted_ticket_write.py`、`plugins/spec-guard/hooks/test_hosted_ticket_actions.py`、`plugins/spec-guard/hooks/test_local_ticket_providers.py`、`plugins/spec-guard/hooks/test_local_ticket_publish.py`、`plugins/spec-guard/hooks/test_proposal_tracker_read.py`、`plugins/spec-guard/hooks/test_proposal_closeout_providers.py`、`plugins/spec-guard/hooks/test_proposal_review.py`、`plugins/spec-guard/hooks/test_proposal_promotion_proof.py`、`plugins/spec-guard/commands/proposal-review.md`、`plugins/spec-guard/commands/proposal-promotion-preflight.md`、`plugins/spec-guard/commands/proposal-promotion-proof.md`、`plugins/spec-guard/references/proposal-tracker-read.md`、`spec/proposal-tracker-read.md`、`spec/local-ticket-portability.md`

## Success criteria

- AC1：除 `hosted_ticket_provider.py` 外，`hooks/` 的非测试代码不再直接调用 `gh`／`glab`；四个入口共用同一份传输、分页与普通 Issue 判定。
- AC2：四个入口的 GitLab 列表都只认普通 Issue（`issue_type=issue` + 逐项校验）；混入其他类型时都不会把它当普通 Issue。（F11）
- AC3：四个入口的所有请求都带 `--hostname`；Proposal 读取的 GitLab 自建实例可用 `--host` 指定，缺省 `gitlab.com`，结果写明 `host`。（F7）
- AC4：四个入口分页上限都是 50 页 × 100，到上限判不完整。
- AC5：`test_tracker_provider_contract.py` 锁住 AC1～AC4，变异检查（三种改坏）都变红。
- AC6：交接、托管事项、Proposal 读取与收尾的原有回归全部通过；交接的错误短码与发布器状态、Proposal 结果模型不变。
- AC7：`validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 通过。

## Open questions

1. Assumption 3 的行为变化：自建 GitLab／GHE 用户以前不传主机、靠 CLI 默认主机读 Proposal，升级后缺省变成 `gitlab.com`／`github.com`。
   推荐：照收尾现行缺省（一致、可预测），CHANGELOG 写明；另一做法是 Proposal 只读命令对 GitLab 要求必须给 `--host`（更安全但多一步）。
2. Assumption 6 把收尾一侧的 GitLab 由「只认 https」放宽为「与目标 `web_url` 同一 scheme」。推荐放宽（与托管事项、交接一致）；不同意则三处统一收紧为只认 https。
