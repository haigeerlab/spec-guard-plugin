# Todo: fact-fixes

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-22 用户批准 Plan（事项 C37）；模块协调在集成分支 `0867aab` 记批准标记，`module-crew sync` 合入（`46b340a8`）。
- [x] Task 1：【公共变更请求】能力图与 interface.json — 补丁在草稿副本生成（`--dry-run` 通过，改后能力图解析为 151 个模块），放共享笔记目录 `fact-fixes-public.patch`；首发 #10269 的「文件」漏列三个移动目标，按模块协调要求重发 #10271（事项 C42 取代 C41）；模块协调在集成分支提交 `d5e9423`（三条 git mv）与 `35f85bd`（补丁）。
- [x] Task 2：未启用项目不启动 python3（先红后绿） — `test-phase-guard.sh` 第 11 段新增 3 例：python3 替身计数，未启用项目在 UserPromptSubmit、SessionStart、SessionStart fresh 与四种输入（带 cwd、cwd 非 git、`{}`、非 JSON）下零调用（改前红：每次 1 次）；宿主目录未启用、cwd 在已启用 worktree 时与改前输出相同；cwd 含转义、出现两次、输入约 70KB／900KB 时退回 python3 且结果与改前相同，超过 1MB 时照旧不改根目录。实现中发现 bash 3.2 的 `read` 逐字节读管道（1MB 约 2 秒、超时丢数据），改为只读前 64KB，其余字节由拷贝进程转交（Spec 变更记录第 2 条）。变异（草稿副本里预检恒拿不准）→ 零调用断言红。提交 `b3a19e8`，全档 phase-guard 438 例、verify-artifacts 74 例、ShellCheck 无告警。
- [x] Task 3：README 中英与取代说明、退役说明 — README 中英第 5～8 行改写上游描述，cost-report 说明列出实际读取项；`spec/install-by-scope.md` 第 5 条末尾加取代句；新增 `docs/retirements/dependency-check.md`；`check-readme-sync.py` 通过。
- [x] Checkpoint 1（report）：三套核心回归 — 合入集成分支 `1016639` 之后在 HEAD 上并行跑：`validate.sh` 校验通过、phase-guard 438 例、verify-artifacts 74 例全绿；ShellCheck 随 `b3a19e8` 的全档提交跑过（无告警），之后没有再改 `.sh`。本 checkout 的 verify-artifacts 0 失败，警告里新增 `spec/fact-fixes.md`、`spec/install-by-scope.md` 批准后已修订两条（见最终验收）。
- [x] Task 4：公共变更落地后合入并核对 — `module-crew sync` 合入 `1016639`（HEAD `246bd16b`）。parse_map 通过、151 个模块、无 `dependency-check`；能力图里 `dependency-check` 只剩本模块职责行与变更记录；三份归档与 `188febb4` 原文件 blob 相同，原路径已不存在；`module-insert` 行无 `spec skeleton`（只在变更记录里出现）；`install-by-scope` 依赖为 `scope-authorization`；interface.json `interface` 仍为 1.8，只改一行；阶段注入「模块 151 · … 已完成 141」；verify-artifacts 0 失败。Spec 修订并行边界与 C7 读法，末尾写变更记录。
- [x] Checkpoint 2（gate）：最终验收
- [x] Task 5：返工——预读超时算拿不准（先红后绿） — 本机 `brew install bash`（5.3.20，只在 `/opt/homebrew`）。实测 bash 5 超时返回 142 并保留已读部分，bash 3.2 返回 1 并丢掉。第 11 段加慢输入正反两例（7 万字节分两段、隔 1.5 秒，`slow_bash` 默认 `/bin/bash`）：未修代码上 bash 5 草稿副本红（正向无注入），`/bin/bash` 3.2 走「不挂住、输出合法」分支为绿；`phase-guard.sh` 记下 read 返回值，0 或 >128 设 RAW_MORE；修后两种 bash 都 503 例全过。变异核对（草稿副本删掉 >128 分支）：正向、反向各自变红——第一次核对发现反向的 python3 计数被正向那次污染，挪了清零位置后才真正生效。Spec 变更记录第 3 条。
- [x] Task 6：返工——文档治理一节（EF4KWN4） — `docs/optional-features.md` 第 3 条「核验」补最终验收那一轮提示文档核验、核验按基线状态区分（用 CHANGELOG 0.84.0 doc-chain 的说法）；「不看 Git 历史推断文档状态」改为「不推断文档内容是否过期」。没有英文对照版。
- [x] Task 7：返工——CHANGELOG 与版本号 0.84.1 — CHANGELOG 新开 0.84.1 段（修复写明 0.84.0 引入、来源 `b3a19e8`；文档一条）；两份 `plugin.json` 与中英 README 的 `--ref` 改为 0.84.1；interface 不变。bash 3.2 限制另记账。
- [x] Checkpoint 3（gate）：返工验收；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-23 呈现以前／现在对照、先红后绿（bash 5 与 3.2）、变异核对、全档校验、改动文件与提交表（062e8f8、3cdb9b3）、Spec 变更记录第 3 条的原样差异；用户回复「fact-fixes 返工验收也通过。两个都做完后一起推送开 PR」。Spec 批准标记已用 review-mark 更新。

## 更新说明

供模块协调整批合完后写 CHANGELOG（本模块不改 CHANGELOG 与版本号）。

- 修复：没有启用 spec-guard 的项目里，阶段注入在判定激活之前不再启动 python3——先在 bash 里读 hook 输入的前 64KB，宿主目录与输入 `cwd`
  所在仓库都没有激活信号时直接静默退出；拿不准时照旧交给 python3，已启用项目的输出不变。
- 文档：能力图目标段如实写明远端写入（Proposal 收尾、托管事项、本地事项交接，均需用户授权）并去掉已拆走的协作邮箱；`dependency-check`
  移出能力图并归档到 `docs/retirements/`；`module-insert` 不再说建 Spec 骨架；README 改写对上游 agent-skills 的描述与 cost-report 的读取范围；
  interface.json 写明 `reviewKinds` 的取值自契约 v2.3 起到 v2.5 未变。

## 交接

- `cost-slim-link-follow` 去掉返工信号识别后，README 中英的 cost-report 读取说明（本模块 C6 按当前实现写）要跟着收窄。
