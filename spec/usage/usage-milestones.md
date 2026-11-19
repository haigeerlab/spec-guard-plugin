# Usage draft: usage-milestones

开工前看清用法与分段验证（总账 S89）。

## Entry points

| Entry | Does | Module |
|---|---|---|
| 能力图审阅（规则） | 多模块需求同一轮默认给出用法草案：入口清单、典型用法、里程碑，并写出拆分核对结论 | usage-draft |
| `spec/usage/<需求>.md` | 草案文件，格式见 `templates/USAGE.md` | usage-draft |
| `/spec-guard:verify-artifacts` | 多一项「用法草案」：查草案结构、与能力图和 Build order 的对应 | usage-draft |
| `/spec-guard:add-module` 预览 | 有草案时写明锚点所在里程碑，提醒把新模块归进里程碑 | usage-draft |
| 阶段提示的里程碑停点 | 一个里程碑的模块全部完成、还没确认时停下，要求按典型用法实际跑一遍、摆证据，等用户判定 | milestone-stop |
| `/spec-guard:milestone-mark` | 用户判定通过后，先预览后确认，在草案里记下该里程碑已确认 | milestone-stop |

## Typical usage

### U1: 提一个要拆成几个模块的需求

你描述需求，agent 总结、你确认说完。下一轮交审里同时看到能力图新行和 `spec/usage/<需求>.md`：有哪些入口、各归哪个模块、
两三个典型用法、分几个里程碑。拆漏或拆多会在交审里写明。批准后跑 `/spec-guard:verify-artifacts`，「用法草案」一项通过。

### U2: 中途补一个模块

用 `/spec-guard:add-module` 插入。预览写明锚点在哪份草案的哪个里程碑，提醒你把新模块加进里程碑表。忘了加不会被拦；
加了但排到后一个里程碑之后、或归了两个里程碑，`verify-artifacts` 会报出来。

### U3: 一个里程碑做完

这个里程碑最后一个模块的最终验收通过后，阶段提示报告停点，agent 不直接开下一个模块，而是按本里程碑的典型用法实际跑一遍，
把命令与输出摆给你。你说通过，agent 用 `/spec-guard:milestone-mark` 预览、你确认后记下，阶段提示转到下一个模块；
你说不通过，就在本里程碑补任务，或回头改草案和后面还没开工的模块。

## Milestones

| Milestone | Usage | Modules |
|---|---|---|
| M1 | U1, U2 | usage-draft |
| M2 | U1, U2, U3 | milestone-stop |
