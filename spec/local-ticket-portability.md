# Spec: local-ticket-portability

登记：Proposal #104 已接受；远端默认分支在 `36f1822` 晋级，本次只读证明为
`proved`。本 Spec 由该 Proposal 的职责、依赖和验收意图展开。

## 目标与假设

本模块使已启用 Local Epiq 账本的项目能生成可核验的离线归档，在全新隔离环境恢复
原事项 ID、事件、讨论、状态与附件；用户指定目标时，能把选中的事项逐条交接到
GitHub 或 GitLab Issue，失败后可对账重试。Local 无需 PR/MR；迁移也不恢复已退役的
日常 hosted Tracker bridge。

假设 Epiq 版本固定为 1.11.0，现有 `local-ticket-ledger` 与
`ledger-worktree-owner` 状态契约保持不变。GitHub/GitLab 的普通 Issue 在本模块中
只承担显式交接目标；后续日常托管事项管理是另一项能力。所谓“切换工作面”只表示
一条事项已有经读回验证的远端地址，不让插件自动接管后续托管日常流程。

## 来源与快照

1. 只读检查当前 Git common dir、`.epiq/project.json`、`__epiq_state__`、
   `EPIQ_GLOBAL_DIR` 和状态 worktree 归属。`foreign`、`unknown`、分支缺失、
   不一致或不可读时停止；归档还须状态 worktree 为 `owned`，不能把 `absent`
   推断为完整的本地历史。不移动、prune、重建或清理任何 worktree。
2. Epiq 1.11.0 的权威事件位于状态 worktree 的 `.epiq/events`，媒体位于
   `.epiq/media`。事件文件包括 tracked 与 live／rotated／folded pending 形态。
   清点保留原始文件名、字节、相对路径、大小和 SHA-256；不同载荷共用事件 ID、
   坏 JSONL、缺失附件或媒体哈希不符必须报告并停止。
3. 记录源分支 HEAD 与文件清单，复制后重读来源并核对。变化则丢弃本次临时输出
   并报告“源在快照期间变化”；完成后产生的新事件属于下一个快照。直接 Epiq 工具
   仍可绕过受控入口，因此不宣称全局冻结或原子快照。

## 离线归档与恢复

归档是用户指定路径下的版本化目录：`manifest.json`、`state.bundle`、项目配置，
以及事件与媒体原始文件（包括未提交部分）。状态分支历史若含 `.epiq/` 以外的
路径则拒绝归档，避免 bundle 夹带项目源码。输出目录必须位于来源仓库的所有 linked worktree 和状态 worktree 之外，
不能经符号链接指回两者；创建目录前检查这一条件。manifest 记录格式版本、
Epiq 版本、项目 ID、状态分支 HEAD、快照截止点、原始事件 ID 清单以及每个文件的
相对路径／长度／哈希。`verify --prove` 在隔离环境计算物化事件与事项视图摘要。
目录默认仅当前
用户可读。绝对工作路径不参与恢复；不自动 `epiq_sync`、Git push、Git add 或上传。

恢复先在新临时 Git 仓库与独立 Epiq 全局目录做证明：验证 manifest 和所有字节，
从 bundle 建立状态分支，覆盖未提交文件前检查目标为空，随后用固定 Epiq 运行时
读回全部事项、事件、评论、状态和附件，再添加一条合成事项确认可继续写入。
路径穿越、符号链接、坏哈希、不兼容版本、已有同名分支或 worktree 均拒绝。
真实恢复仍须用户指定目标；已有目标事件不覆盖、不自动合并，输出冲突报告并保留
两边原始数据。同机恢复相同项目 ID 时须使用独立 `EPIQ_GLOBAL_DIR`，不能接管原
状态 worktree。真实恢复要求目标为没有文件或历史的空 Git 仓库，Epiq 全局目录也为空；
目标不能是共享 Git common dir 的 linked worktree（其 `.git` 是文件），须先准备独立空仓库；
成功时将项目身份配置提交到目标仓库当前默认分支，并从 bundle 建立状态分支及独立
worktree，不推送远端。写入中断保留部分目标数据供诊断，不自动重试或清理。
隔离证明中的 Epiq 身份仅供验证；真实恢复后须在目标环境完成本机 Epiq 用户身份设置，
才能继续写入新事项，恢复结果需明确报告这一待办。
归档只覆盖事项账本，不包含项目源码或全部 Git 分支；代码引用的
目标若不可达，须在交接预览中明确报告。仅同盘副本不能证明抵御机器或磁盘故障。

## 显式远端交接

交接使用平台无关的只读来源快照：`projectId + issueId` 作为稳定来源身份，
当前标题／描述／状态、按源顺序的全部历史事件（包括已被替代的正文、评论和状态变化）、
附件内容哈希、原作者／时间、代码引用和源摘要分开保留。GitHub 与 GitLab
适配器各自把它映射到远端 API；
共同的是验收语义，不要求两平台或 Local 具有相同页面、PR/MR 流程或元数据字段。

1. 预览只读：用户给出平台、主机、仓库／项目和可见性，并选定事项。预览包含
   Local 稳定 ID、现行正文、已替代的正文及各次决定、按序评论与状态变化、附件
   处理、来源作者与时间的文本说明、目标地址、代码引用可达性、无法原样映射的
   字段及源摘要。
   每个历史事件要有稳定标记，在目标中可读回对应内容；仅保留当前正文不算完整交接。
   未知可见性、权限或源变化使预览失效；GitLab Issue URL 的协议和主机须与项目元数据的 `web_url` 一致；私有预览文件不得写入来源仓库的任何 linked worktree。
   附件能力和可见性须按当前目标与工具
   实测：不支持上传、无法读回原文件哈希，或无法证明目标附件访问边界时，
   不上传该附件，也不把该事项标记为完整交接。
2. 每条事项使用不同于 Proposal 命名空间的稳定标记；每条评论使用自己的稳定标记。
   创建前对目标做完整分页查找；未知或不完整的查找不能视为缺席。GitHub 搜索结果
   中的 PR、GitLab 系统 notes 和平台自动关闭行为须分别处理。同一来源标记若匹配
   多条远端事项，或同一 `projectId + issueId` 的来源摘要已分叉，进入 `conflict`，
   不自动合并或选择一条。
3. 用户对精确目标和预览内容授权后，逐条创建或沿用远端 Issue。写后读回正文、
   标记、评论、附件处理结果和状态；超时或响应丢失先按标记对账。仅仅查不到
   刚提交的标记不足以证明创建失败，此时停止自动重试，留下待对账记录。受管
   发布进程按来源与目标串行化；平台不提供原子唯一键，不能保证不受外部并发
   写入影响。若目标被人工改动、权限变化或局部发布失败，记录待对账，不覆盖
   改动也不盲建第二条。
4. 本地私有映射日志记录每项 `planned`、`partial`、`verified` 或 `conflict`、
   远端 URL 与源摘要，并随下一份归档导出。映射日志本身不是防重的唯一依据：
   丢失后仍须靠远端标记重新核对。只有完整读回才标记 `verified`；Local 历史始终
   可读，后续托管事项操作不属于本模块。
   归档中的映射日志是可核验的导出副本；恢复到账本目标时不自动写入另一项目的
   用户级映射分区，避免把旧环境的目标身份误当作新环境的已验证状态。

## 命令

以下是模块对外的 CLI 形状，实际参数由实施计划逐项落实；读命令不得写来源或目标：

```text
python3 -B plugins/spec-guard/hooks/local_ticket_portability.py inventory --project <repo> --format json
python3 -B plugins/spec-guard/hooks/local_ticket_portability.py archive --project <repo> --output <directory>
python3 -B plugins/spec-guard/hooks/local_ticket_portability.py verify --archive <directory>
python3 -B plugins/spec-guard/hooks/local_ticket_portability.py verify --archive <directory> --prove --runtime-dir <pinned-runtime>
python3 -B plugins/spec-guard/hooks/local_ticket_portability.py restore --archive <directory> --project <empty-repo> --epiq-global-dir <empty-directory> --confirm
python3 -B plugins/spec-guard/hooks/local_ticket_portability.py handoff-preview --project <repo> --platform <github|gitlab> --host <host> --target <project> --visibility <public|internal|private> --issue-id <id> --output <preview.json>
python3 -B plugins/spec-guard/hooks/local_ticket_portability.py handoff-publish --project <repo> --preview <preview.json> --confirm
python3 -B plugins/spec-guard/hooks/test_local_ticket_portability.py
/bin/bash scripts/validate.sh
```

`archive` 只创建用户指定的新目录，已存在则拒绝。`restore` 只接受空目标且须明确
确认；`handoff-publish` 在调用时重读源摘要和目标权限，并由宿主向用户展示精确
目标、可见性与内容后取得本次写入授权。`--confirm` 本身不代替人的授权。

## 项目结构与代码风格

实现以 Python 3.9 兼容的 `plugins/spec-guard/hooks/`、命令、技能及参考文档为边界；
不安装新服务或复活旧 bridge。CLI 负责调度，归档读写与 GitHub／GitLab 发布适配器
分文件实现；测试使用临时 Git 仓库和伪造的提供方响应，不接触用户账本。
延续现有 hook 风格：用短码诊断、类型明确的结果和原子文件替换；外部内容视为数据，
不作为命令或授权。不要把绝对来源路径写进归档或远端 Issue。

## 验证策略与完成标准

合成验收覆盖已提交与 pending 事件、两版描述、讨论、开关状态、附件、独立 clone、
路径攻击、源变化、部分发布、分页、响应丢失和人工改动；模拟 GitHub 与 GitLab
均不得重复 Issue 或评论。真实远端往返只在目标与内容再次获授权后运行；未运行
就报告“模拟通过，线上未验证”。运行上面的聚焦测试与 `scripts/validate.sh`。
在独立环境读回完整事件与附件、恢复后继续写入，以及两平台的部分失败不重复发布
三项证据齐备前，不把本模块标为已完成。
这三项模块能力验收可使用合成事项和经授权的合成远端目标；不要求用户真实账本已
离机备份或真实敏感历史已迁移。真实项目启用时另行核对独立备份、受保护的传输与
每条事项的附件读回；同盘归档和 `partial` 交接不能冒充这些操作证据。

## 边界

- 始终：保留原始事件和媒体；读回后才报告成功；局部失败可恢复；Local 可读。
- 先问：真实恢复到用户项目、任何托管平台写入、改变 Epiq 版本或宿主配置。
- 不做：自动双向同步、Local PR/MR、原作者与时间的原生伪造、自动修改 Proposal
  Issue、标签、能力图或 `.agent/state.json`。
- 私有映射日志位于用户级受管目录，权限默认仅当前用户可读；精确 schema 在实施
  计划中固定并加版本。目标附件上传能力缺失、超过平台限制或权限无法核实，
  就保持 `partial`；不静默丢弃附件或把 Local 事项标记为完整交接。

## 开放问题

无阻塞问题。归档 schema 的字段和 CLI 错误短码由实施计划固定，并以正反测试验证。
