# Spec: pre-declared-scope

<!-- spec-guard: review approved ef61e447e019 -->

## Objective

多模块并行时，模块常常要改不归它独占的公共文件：共享目录、质量与工作区配置、补丁，或者新加外部依赖。今天 module-crew 把这些改动
一律作为公共变更请求逐次问用户；LIVE-SAAS 的 N1 七批回放里，4 批卡在质量与工作区配置这一类。S29 的方向（用户 2026-10-24 批准）是：
**Plan 里预先声明这些高风险项，批准 Plan 就一并授权，超出声明才停。**

本模块是 spec-guard 这一侧：

1. Plan 可以写一节 `## 预先声明`（`## Pre-declared`），按固定格式列出公共路径、外部依赖、质量与工作区配置、补丁；
2. 新的只读接口 `declaredScope`，把这一节和 Plan 的批准状态交给 module-crew；
3. verify-artifacts 校验这一节的格式；
4. 交审 Plan 的规则写明：声明要逐条列给用户看，批准即授权，哪些东西不能预先声明。

module-crew 拿到名单后怎么归类、自动落地、事后汇总，是它自己的模块（S32 第二节），不在这里。

登记：依据 `plugin-ecosystem/proposals/2026-10-24-S29-预先声明高风险项.md` 与同目录 S32 方案（两份都由用户批准，总账 `612634c`）。
2026-10-26 用户在本会话确认需求：「需求齐了，按两个模块、一次发版，三个问题按推荐」；同日对两处冲突的答复：「A：去掉 verify-artifacts 对
『需要的外部条件』的对比，只校验预先声明一节格式；Plan 改过用 git 比对判断」。账本 TKYJ8DH。本模块与 `autonomy-tier` 一起发 1.11，
版本号在 `autonomy-tier` 里改。

## Assumptions

1. **只增不改。** 已有的 Spec／Plan／todo 格式、批准标记（含 Plan 标记不带指纹）、`scopeCheck`、`scopeOverlap` 都不变。没有这一节的 Plan，
   一切行为和今天相同。
2. **这一节不受 `moduleConcurrency` 限制。** 有就解析、校验、在交审时列出；没有就没有任何输出。module-crew 自己有开关决定用不用它。
3. **写法规矩照搬「并行边界」：** 每行 `- 名称：值`，值用 `、` 或 `,` 分隔，每项一对反引号；路径相对项目根、不许通配符、不许 `..`，
   目录以 `/` 结尾。四行各最多出现一次，**缺的行等于 `无`**；整节为空（四行都缺或都是 `无`）也合法，等于什么都没声明。
4. **「质量与工作区配置」「补丁」只能逐个文件写，不能写目录**（以 `/` 结尾即 `bad-path`）。「公共路径」文件、目录都可以。
5. **外部依赖写成 `` `名称@范围` ``**，`@scope/pkg@^1` 这种带作用域的名称也支持；名称和范围都不能为空、不能含空白。不限定是哪个包管理器，
   也不去源上核实包存在。范围以 `workspace:` 开头的项判 `bad-dependency`：内部链接不算外部依赖，写了说明理解有偏差，早报比悄悄忽略好。
6. **Plan 批准判断用 git 比对（用户 2026-10-26 定）。** `approvedCommit` 是最近一次让 `tasks/<id>/plan.md` 的批准标记变成 `approved` 的提交；
   `planApproved` 为 true 当且仅当工作区里这份 Plan 的标记是 `approved`，并且它的内容与 `approvedCommit` 那一版逐字节相同。批准后又改过
   （无论是否提交）、批准还没提交、不在 git 仓库里、或在浅克隆里找不到那次提交，都是 `planApproved: false`，此时 `approvedCommit` 为 `null`。
7. **删除文件、改对外契约、安全例外不能预先声明**——这是规则文字，接口识别不了：写在「公共路径」里的文件被删，仍归 module-crew 按
   「一律要问」处理。
8. **不和「需要的外部条件」比对（用户 2026-10-26 定）。** 0.78.1 起（用户决定 62）Plan 不再要求那一节，「外部依赖」一行本身就是给 module-crew
   的正式名单。
9. **命令放在 `module_scope.py`**，作为子命令 `declared`：并行边界的反引号路径、分隔符和代码围栏处理只有一份实现，直接复用。

## Contract

### C1 Plan 的「预先声明」一节

```markdown
## 预先声明

- 公共路径：`packages/bootstrap/`、`apps/web/vite.config.ts`
- 外部依赖：`axe-core@^4`、`@vitejs/plugin-vue@^5`
- 质量与工作区配置：`eslint.config.mjs`、`pnpm-workspace.yaml`
- 补丁：无
```

- 标题 `## 预先声明` 或 `## Pre-declared`；行名 `公共路径`／`Public paths`、`外部依赖`／`Dependencies`、`质量与工作区配置`／`Configs`、
  `补丁`／`Patches`；`无`／`none` 表示没有。HTML 注释行与空行跳过；代码围栏里的示例不算。
- 这一节到下一个 `#` 或 `##` 标题为止。

### C2 只读接口 `declaredScope`

命令：`python3 -B hooks/module_scope.py declared --project <project-root> --module <module-id>`，只读，不受 `moduleConcurrency` 限制。

- **退出 0**，stdout：
  ```json
  {"module": "<id>", "planApproved": false, "approvedCommit": null, "declared": true,
   "publicPaths": ["packages/bootstrap/"], "dependencies": [{"name": "axe-core", "range": "^4"}],
   "configs": ["eslint.config.mjs"], "patches": []}
  ```
  `declared` 为 false 表示 Plan 没有这一节（或没有 `plan.md`），四个列表都为空。列表按 Plan 里写的顺序，去重。
- **退出 4**：这一节格式错，stdout `{"module": "<id>", "error": "<code>"}`，`code` 为 `bad-path`、`bad-dependency`、`unknown-line`、
  `duplicate-section`、`unreadable`（Plan 不是 UTF-8 或读不出）之一；不回显文件内容，也不给出批准状态。
- **退出 2**：用法错误——模块 id 不合法、不在能力图里、`--project` 不是目录或没有能力图。
- `interface.json` 的 `interface` 升到 `1.11`，新增 `declaredScope` 条目（command、readOnly、exitCodes、values.error、contract 指向本 Spec）；
  `scripts/check-interface.py` 核对错误码与代码常量一致。

### C3 verify-artifacts

- 对能力图里阶段不是 `DONE`、有 `tasks/<id>/plan.md` 的模块：有这一节且格式对，计入一条 `✅`（「预先声明格式正确：n 个模块」）；格式错，
  一条 `❌`（模块 id 与错误码），verify-artifacts 判失败——和「并行边界」格式错同等对待；没有这一节不提示。
- 读不出能力图时给「未验证」。已完成模块不追溯。

### C4 规则文字

- `references/node-rules.md`「Plan 交审」加一条：Plan 有「预先声明」一节时，把四行逐条列在交审正文里（写 `无` 的行也列），并写明一句
  「批准本 Plan 即授权以下公共改动」。
- `references/workflow-checkpoints.md` 在「批 Plan 按范围授权」之后加一段「预先声明」：什么时候写（模块要改不归它独占的公共文件、要新加
  外部依赖时）、四行的写法（指向 C1）、批准即授权；删除文件、改对外契约、安全例外不能预先声明，写了也不算，照旧逐次问；Plan 不得自加比
  插件默认更严的逐项授权条款，确要加，交审时醒目标为「比默认更严的选择」，由用户定。
- 这一段只在 Plan 有这一节时才相关，规则里写明「没有这一节时不用写」，不要求每个 Plan 都写。

## Acceptance criteria

- **AC1** 解析：中英两种标题与行名；四行齐全、缺行、整节全 `无`；目录与文件路径；带作用域的依赖名；代码围栏里的示例节不算——都按 C1 解析，
  有单元测试。
- **AC2** 错误码：通配符、`..`、绝对路径、「质量与工作区配置」或「补丁」写目录 → `bad-path`；依赖缺 `@范围`、名称或范围为空、含空白、
  `workspace:` 范围 → `bad-dependency`；未知行名、同一行出现两次 → `unknown-line`；两个「预先声明」标题 → `duplicate-section`。每种都有用例，
  输出不含文件里的任何文字。
- **AC3** 批准判断（真 git 仓库夹具）：标记写成 approved 并提交 → `planApproved: true`、`approvedCommit` 为那次提交；之后改一个字未提交 → false、
  null；提交这次修改（标记仍是 approved）→ false、null；改回 pending 再批准并提交 → true，`approvedCommit` 为新的那次；approved 但从未提交 →
  false、null；不在 git 仓库 → false、null。
- **AC4** 命令：退出码 0／2／4 与 stdout 形状如 C2；没有 `plan.md`、没有这一节都是退出 0、`declared: false`。
- **AC5** `interface.json` 为 1.11、含 `declaredScope`；`check-interface.py` 通过；把代码里的错误码改掉一个，它变红。
- **AC6** verify-artifacts：未完成模块的这一节格式错 → 失败并给出模块 id 与错误码；格式对 → 计数；没有这一节、已完成模块 → 不提示；
  `test-verify-artifacts.sh` 有正反用例。
- **AC7** 规则：`node-rules.md`「Plan 交审」与 `workflow-checkpoints.md` 含 C4 的要点，`test_workflow_checkpoints.py`／`test_stop_rules.py` 有断言；
  阶段注入在 Plan 交审节点照常带出新的一条。
- **AC8** `scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh` 全绿；改到 `.sh` 时 CI 同版 ShellCheck 无告警。

## Boundaries

- **会做**：上述 C1～C4 及回归；`interface.json` 1.11 与 `declaredScope` 条目；CHANGELOG 未发布段一条；todo 末尾记更新说明。
- **先问再做**：要改 Plan 批准标记的格式；要让这一节受某个开关控制；发现 module-crew 需要的字段超出 C2。
- **不做**：`autonomyTier` 与底线规则（归 `autonomy-tier`）；版本号与发版（归 `autonomy-tier`）；module-crew 的归类、自动落地、汇总；
  恢复「需要的外部条件」一节或任何依赖逐项对比；改 `scopeCheck`／`scopeOverlap` 的行为。

## 并行边界

- 独占：`spec/pre-declared-scope.md`、`tasks/pre-declared-scope/`、`plugins/spec-guard/hooks/module_scope.py`、`plugins/spec-guard/hooks/test_module_scope.py`、`plugins/spec-guard/hooks/verify-artifacts.sh`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/references/node-rules.md`
- 公共：无

## 文档建议

改 `references/node-rules.md`、`references/workflow-checkpoints.md`（规则）与 `interface.json`；README 的命令与功能清单不涉及（这是给
module-crew 的接口，不是用户命令），CHANGELOG 记一条。项目没有文档基线，不需要文档影响登记。

## 变更记录
