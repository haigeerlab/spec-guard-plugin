# Plan: local-ticket-portability

依据 [`spec/local-ticket-portability.md`](../../spec/local-ticket-portability.md) 与已晋级的
Proposal #104。已有 Local 事项是本次工作的受理入口；模块任务以本目录的
[`todo.md`](todo.md) 为准，不把任务写入 Proposal Issue。先完成离线恢复证明，再允许
显式托管交接；每个任务完成时记录聚焦测试结果和仍未验证的边界。

## 实现顺序

```text
来源清点 ─→ 归档／校验 ─→ 隔离恢复证明 ─→ 显式恢复
    │
    └────→ 交接预览 ─→ 对账日志与假提供方 ─→ GitHub 适配 ─→ GitLab 适配
                                                   └──────────────┬──────────────┘
                                                                  ↓
                                                        命令、文档与总验收
```

任务 1–4 为本地可移植性；任务 5–8 为逐项显式交接；任务 9 收束命令和文档。
每一阶段结束先检查其验收证据，再开始下一阶段。普通 GitHub/GitLab 日常 Issue
管理、PR/MR 交付和 Proposal 生命周期均不在本计划中。

## 决策与数据契约

1. **来源事实。** 复用 `local_ledger_runtime.py` 的项目身份、固定的 Epiq 1.11.0
   版本和 `stateWorktree` 诊断。只有同一 Git common dir 的 `owned` 状态可归档。
   按 Epiq 原始文件清点 tracked 与 live／rotated／folded pending 事件和媒体；同 ID
   不同载荷、坏 JSONL、缺附件或来源变化一律失败。Epiq 物化视图用于交叉验证，
   不能替代原始事件。直接 Epiq 工具可绕过受控入口，所以成功报告只对应快照截止点。
2. **归档 v1。** 新建权限为仅当前用户可读的输出目录；拒绝位于来源仓库或状态
   worktree 内的路径及符号链接回指。目录含 `manifest.json`、只含
   `refs/heads/__epiq_state__` 可达对象的 `state.bundle`、`.epiq/project.json`、
   pending 原始文件、媒体文件和当时的映射日志快照。manifest 固定
   `formatVersion=1`、`epiqVersion=1.11.0`、`projectId`、`stateBranch`、
   `stateHead`、`capturedAt`、`eventIds` 与 `files[{path,size,sha256}]`；
   所有路径为受限相对路径，不能存来源绝对路径或凭据。先写临时目录并复核来源，
   最后以排他方式发布；失败留下明确诊断，不把半成品当归档。检查状态分支
   每个历史提交的改动路径，只允许 `.epiq/`；否则 bundle 可能夹带源码。
   事件／媒体原始文件全部覆盖到归档，以包含已提交后又修改的文件。
3. **恢复。** `verify` 只检查结构、所有字节和 Git bundle 完整性；恢复证明在
   临时 Git 仓库与独立 `EPIQ_GLOBAL_DIR` 完成，并调用锁定的 Epiq 运行时读回
   事项、全部事件与附件，输出物化事件和事项视图摘要，再写一条合成事项。
   真实 `restore` 只接受用户指定的
   空 Git 仓库及空 Epiq 目录，先完成同样预检；如写入中断，报告剩余状态并停止，
   不删除或强制覆盖。成功时在目标默认分支提交项目身份配置，建立状态分支与独立
   worktree，不推送远端。恢复的是账本，不是项目源码与其他 Git 分支。
4. **交接快照。** 每个源事项以 `projectId + issueId` 标识，源摘要覆盖有序原始
   事件、附件哈希和当前视图。预览 JSON 版本为 1，含目标平台、主机、项目、
   可见性、精确拟发布文本、事件／评论标记、附件能力与代码引用可达性，不含
   绝对源路径或凭据。预览输出只能写到来源仓库与状态 worktree 之外的用户指定
   新文件。发布时用 `--project` 重读来源，并重新核实目标权限与可见性；
   摘要或权限变化使预览失效。
5. **持久对账。** 日志放在受管用户目录下，按 Git common dir 的 SHA-256 与
   `projectId` 分区，避免独立 clone 同 ID 相互覆盖；目录权限 0700、文件 0600，
   JSON schema 版本为 1，原子替换。每项记录目标身份、来源摘要、意图标记、
   远端 URL、已验证的事件标记和 `planned/partial/verified/conflict`。远端标记
   才是丢失日志后的对账依据。一次来源与目标组合只允许一个受管发布进程；
   平台没有原子唯一键，外部并发写入不在“绝不重复”保证内。
6. **提供方适配。** 分别用显式目标的 `gh api`、`glab api` 分页列举和写入
   Issue／评论，不调用退役 bridge 或 Proposal 读取器。每次外部写入前落下
   意图；响应丢失时先读回，查不到也不自动再创建。目标有多重标记、人工修改
   或同 ID 不同源摘要时转 `conflict`。每个历史事件以可读文本和稳定标记发布；
   仅有当前正文不能标为 `verified`。当前 GitHub CLI 没有 `--attach`，因此
   附件能力运行时探测；GitLab 上传后需能按权限读回并核对哈希。能力或可见性
   不足时保持 `partial` 和原始 Local 数据。任何真实目标写入必须另行展示目标
   与内容，获得该次授权。

## 错误与输出约定

- CLI 输出 JSON，成功与失败都含短码 `state`／`diagnostic`；至少区分
  `source-unknown`、`source-changed`、`archive-invalid`、`target-not-empty`、
  `preview-stale`、`provider-unsupported`、`publication-uncertain` 和 `conflict`。
- `inventory`、`verify` 与 `handoff-preview` 不写来源或目标。`archive` 只写
  用户指定的新目录；`restore` 只写指定空目标；`handoff-publish` 只写精确目标
  与本地对账日志。`--confirm` 是命令防误触参数，不能替代宿主获得人的授权。
- 受控发布失败后保留 Local 可读状态。映射为 `verified` 只表示源快照在目标
  已完整读回，不自动关闭 Local 事项或接管未来的日常托管流程。

## 检查点与验收

| 检查点 | 证据 |
| --- | --- |
| 任务 1–2 | 同一夹具的 tracked、pending、folded 和附件被逐字节列入归档；删改任一文件后 `verify` 失败。 |
| 任务 3–4 | 与来源隔离的环境读回相同 ID、事件顺序和附件哈希，且恢复后可继续写入；已有目标绝不覆盖。 |
| 任务 5–6 | 预览不改来源或目标；模拟分页、超时、人工修改、双标记与源分叉时不重复创建。 |
| 任务 7–8 | GitHub 和 GitLab 假提供方分别走完发布、读回与中断对账；附件不支持时诚实保持 `partial`。 |
| 任务 9 | 聚焦合成验收、`scripts/validate.sh`、阶段与产物检查通过；文档不宣称未运行的真实远端往返。 |

## 风险与限制

- Epiq pending 文件可能并发变化；复制前后逐项重读并比较摘要，变化即失败。
  该方法不承诺冻结直接 MCP 写入。跨机器耐久性还需用户把归档复制到独立介质。
- GitHub 当前本机 `gh 2.98.0` 无 `--attach`，即使官方文档描述较新版本的
  附件选项，也不能假定当前环境可用。GitLab 媒体的访问权限可能与 Issue 不同。
  任一附件无法上传并读回原字节时，远端交接只可能是 `partial`。
- 提供方分页和最终一致性会造成“不确定是否已创建”。在不确定状态暂停，
  由远端标记或人工证据解决，不凭一次空查询重发。
- 本计划用伪造提供方做可重复验收；经逐次授权的合成事项也已在 GitHub 与 GitLab
  完成远端往返。它们证明交接适配器的行为，不证明真实账本已有离机备份、HTTP
  目标适合敏感历史，或附件已在远端按原字节和可见性读回。真实数据启用前逐项核对。

## 文件与检查命令

实现限定在 `plugins/spec-guard/hooks/` 的新 CLI、归档／交接辅助模块与聚焦测试，
以及对应 command、skill、reference、`CHANGELOG.md`；不改旧 Proposal 或
`.agent/state.json`。主要命令见 Spec 的“命令”一节。每个任务运行聚焦测试，
最后运行 `/bin/bash scripts/validate.sh`、`/bin/bash
plugins/spec-guard/hooks/verify-artifacts.sh`、`git diff --check`。不提交私有研究
文档或真实 Local 事项内容到公开仓库。
