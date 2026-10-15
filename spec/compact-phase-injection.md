# Spec: compact-phase-injection

<!-- spec-guard: review approved 146897658dd0 -->

## Objective

阶段注入是插件的核心功能，但它只挂在 `UserPromptSubmit` 上：只有用户发消息的那一轮才有注入。实地观察到的一个消费者项目的
Codex 会话，42 轮里有 34 轮完全没有注入——它们由其他会话的消息或唤醒触发，不经过这个钩子。两次一轮中途的上下文压缩都发生在
这类轮次里：压缩后 agent 把 8.5 小时前的请求当成当前任务重做，一次给别的会话发了不该发的消息、改了已验收模块的 todo；另一次
做完一件已完成的事就结束了这一轮，模块停在一半，没有人知道。

两边宿主都有“会话开始”钩子（`SessionStart`），并能指定只在压缩后触发（matcher `compact`）。观测会话实测：Codex 一轮中途压缩后，
钩子在同一轮内约 0.5 秒后触发，注入内容以 developer 消息进入对话并被模型读到；Claude Code 手动 `/compact` 后也会触发，注入内容
下一轮被模型引用。

本模块让两边宿主在压缩后也注入阶段提示：当前在哪个模块、下一项未勾的任务、下一个 gate。只读只报告，不写文件。

登记：2026-10-15 经 `/spec-guard:add-module` 插入能力图。问题由观测会话报告并实测，插件所有者核对了钩子注册，用户已确认做法。

## Assumptions

用户已于 2026-10-15 确认：

1. **两边都注册 `SessionStart`，matcher 为 `compact`。** 只在压缩后触发；会话启动、恢复、`/clear` 都不触发，避免多出注入。
2. **复用现有阶段提示。** 内容与 `UserPromptSubmit` 时相同，再多一句：
   > Context was just compacted: earlier requests in the summary may already be done; check the todo and the state record
   > before redoing anything.

   不写“压缩前的旧指令不是新任务”：压缩前用户刚下的指令也可能还没记进 todo，那样写会让 agent 丢掉它。
3. **事件名按实际事件给出。** 现在阶段钩子的输出与 `hooks.json` 里出错时的兜底都把事件名写死为 `UserPromptSubmit`。压缩后注册的
   那一项用参数告诉脚本这是哪个事件（例如 `phase-guard.sh SessionStart`），脚本据此输出事件名；不带参数时输出与改前逐字相同。
   不靠解析钩子输入来猜事件。
4. **不变量不变。** 无激活信号的项目照旧静默；钩子只读、不写文件；只依赖 bash、git、python3；输出是宿主接受的 JSON。
5. **不加 Stop 钩子**拦“收工”：agent 可能确实在等别的会话，拦下会打转，也超出“只报告”的边界。
6. **说明写清前提**：共用会话目录时要按会话登记自己的项目（`link-project --session`），否则注入的是别的项目；todo 做完就勾，否则
   “下一项”是旧的。
7. 版本 0.61.0（新增钩子是功能变化），一个 PR。

以下要在动手前实测，结果可能改变做法：

8. **信任会不会受影响。** README 写 Claude Code 首次使用要在 `/hooks` 信任插件的钩子、Codex 不用；观测会话的 Codex 实测用的是配置里
   定义的钩子，需要信任，不是插件自带的钩子。要实测：插件新增一项钩子后，两边宿主是否要重新信任；**已有的 `UserPromptSubmit` 是否
   因此失效**。若已有钩子会失效，先停下交用户决定，不往下做。
9. **Claude Code 一轮中途的自动压缩是否触发 `SessionStart(compact)`**，以及 **Codex 由其他会话消息触发的轮次里中途压缩是否触发**。
   测得出就记录；测不出如实记为未验证。不触发时结果与现在相同，不会更差。

## Contract

### 钩子注册（`hooks/hooks.json`，两边宿主共用这一份）

- 保留现有 `UserPromptSubmit` 一项，逐字不变。
- 新增 `SessionStart` 一项，matcher `compact`，命令与现有一项相同，只是调用 `phase-guard.sh SessionStart`，两处出错兜底里的事件名为
  `SessionStart`。

### `phase-guard.sh`

- 接受一个可选参数：`SessionStart` 或 `UserPromptSubmit`；不带参数等同 `UserPromptSubmit`。其他值按 `UserPromptSubmit` 处理（不报错，
  避免宿主差异让钩子失败）。
- 所有输出（正常注入、python3 不可用、python3 跑不起来三种）的 `hookEventName` 用这个值。
- 为 `SessionStart` 时，在注入末尾加 Assumptions 2 那一句；其余内容与 `UserPromptSubmit` 相同。
- 不带参数时，所有输出与改前逐字相同。

### 文档

- `docs/design.md`：阶段注入一节写明两个触发点。
- `docs/troubleshooting.md`：压缩后没有注入时查什么（信任、宿主版本、按会话登记）。
- `README.md`、`README.en.md`：若实测发现需要信任新钩子，改安装表里的那一行；`--ref` 改为 v0.61.0。
- `CHANGELOG.md` 新增 `[0.61.0]`，写清前提与（若需要）升级后要信任新钩子。
- 两份 `plugin.json` 改为 0.61.0。

### 不变

阶段判定、`module_stage.py`、`verify-artifacts`、约定块模板与所有命令的行为都不变。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
shellcheck plugins/spec-guard/hooks/phase-guard.sh
```

## Testing strategy

- 先改测试并确认失败：`test-phase-guard.sh` 新增一段——带 `SessionStart` 参数时三种输出的事件名都是 `SessionStart`、注入末尾有那一句、
  其余内容与不带参数时相同；无激活信号的项目带参数时同样静默；不带参数时输出与改前逐字相同（现有用例不改期望值）。
- `hooks.json` 的结构检查：两项都在，`SessionStart` 的 matcher 是 `compact`，兜底里的事件名与所在项一致。
- macOS `/bin/bash` 跑全套与 ShellCheck。
- 变异：把参数忽略、或把那一句加到 `UserPromptSubmit` 上，断言应变红。
- 宿主实测（Assumptions 8、9）：先在动手前测信任；发版后两边各在临时项目里触发一次压缩，看压缩后的注入是否出现。

## Boundaries

- Always：钩子只读；不带参数时输出逐字不变；两边共用一份 `hooks.json`。
- Ask first：已有钩子会因新增一项而要重新信任；注册 `startup`、`resume` 等其他触发点；加 Stop 钩子；让钩子写文件。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 两边宿主压缩后都注入阶段提示，事件名正确，末尾有核对提醒。
- 不带参数的现有注入逐字不变；无关项目照旧静默。
- 全套检查与 ShellCheck 通过。
- 信任与中途压缩两项实测有结果，或如实记为未验证。

## Open questions

- 无。Assumptions 8、9 是动手前要测的事实，不是待用户决定的问题；第 8 项的结果若是“已有钩子会失效”，再交用户决定。
