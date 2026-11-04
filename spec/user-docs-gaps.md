# Spec: user-docs-gaps

<!-- spec-guard: review approved b9d3efc7abfd -->

## 目标

2026-11-04 有人为写一本从想法到代码落地的协作开发手册，通读了 spec-guard 面向使用者的文档，交回 10 条「照文档做会卡住或误解」的缺口（S71）。
逐条对照 v0.86.3 核对后：7 条属实，2 条部分属实，1 条不成立。本模块只修属实的部分，不改插件行为。

给谁用：照文档上手、照文档排障的使用者，以及替用户读命令说明的 agent。

## 假设

用户已于 2026-11-04 确认（「说完了，开模块」，针对本会话的核对结论）：

1. **能力图「审阅记录」**：在 `templates/CAPABILITY-MAP.md` 那一节加一行注释，写明这是第一次审能力图时的自查清单，勾不勾都行，工具不读也不校验，
   能力图的批准以对话里的答复为准；`docs/concepts.md` 术语表补同样一条。复选框和模板结构不动（已装项目的能力图不受影响）。
2. **`activeModule` 谁改**：统一成「agent 按阶段提示直接编辑 `.agent/state.json`，用户也可以自己改；没有专门写它的命令」。
   改 `commands/add-module.md:14`、`skills/spec-guard-ops/SKILL.md:306`（「提醒用户改」）、`commands/phase.md:59`（「建议改」）、
   `docs/troubleshooting.md:158`、`docs/workflow.md:151`，与 `docs/workflow.md:26`、`docs/getting-started.md:402` 的说法一致；
   `workflow.md` 在 `state.json` 那一处补「没有专门的命令」。
3. **参数行补 `--host`**：`commands/setup-convention.md` 的 `argument-hint` 与 `docs/commands.md` 的参数行补 `[--host=codex]`；
   `commands/teardown-convention.md` 与 `docs/commands.md` 补 `[--host=claude|--host=codex]`，各补一句什么时候用（与脚本 usage 一致）。
4. **安装包内对 `docs/` 的引用**：`commands/add-module.md:120`、`commands/phase.md:102`、`commands/teardown-convention.md:65`、
   `commands/verify-artifacts.md:65`、`skills/spec-guard-ops/SKILL.md:110` 这 5 处改成仓库里对应文件的 GitHub 链接
   （`https://github.com/haigeerlab/spec-guard-plugin/blob/main/docs/...`）。hook 脚本里的注释不改（给维护者看的）。
5. **契约路径**：`docs/design.md` 讲 `interface.json` 的地方补一句：契约里的 `spec/...` 路径相对源码仓库根目录，安装包里没有，
   去仓库看；`interface.json` 本身不改（改它就是改接口）。
6. **只管一个项目目录**：`docs/concepts.md`（或 `workflow.md` 开头的目录说明）补一句：一个项目目录一张能力图、一份状态；前后端分仓时各仓各装一份，
   跨仓的接口约定按上游 spec-driven-development 的说法写在提供方模块的 Spec 里，另一边的 Spec 引用它。
7. **关键卡点**：不改名（会动表格与 JSON 输出）。`README.md`、`README.en.md` 功能表、`docs/commands.md:226`、`commands/map.md` 的
   description 与表头说明，各补「只算挂起造成的阻塞」（英文 README 用对应说法）。
8. **想法成形**：`references/workflow-checkpoints.md` 的「需求确认」一节与 `docs/workflow.md` 对应处补一句：想法还不成形、说不出要什么时，
   先用上游 agent-skills 的 `idea-refine` 或 `interview-me`，再进需求确认。需求确认仍不落文件，不改。
9. **Spec、Plan、todo 格式**：不新增模板。`docs/getting-started.md` 加一小段：三者的格式沿用上游 `spec-driven-development` 与
   `planning-and-task-breakdown`；spec-guard 只多这几样标记——批准标记 `<!-- spec-guard: review ... -->`、检查点档位 `（gate）`／`（report）`、
   延期写法「延期：…；恢复条件：…」、`<!-- spec-guard: no-todo -->`——并链接各自的说明处。
10. **不处理**：#1 中「本机 clone 的 main 落后」（环境问题）；#10（`module_stage.py:966` 只在延期数大于 0 时才加「· 延期 n」，示例没有延期项，输出无误）。
11. 发 0.86.4，只改文档与命令说明，`interface.json` 不变；仓库里不出现消费项目的名字、模块或编号。

## 命令

```text
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## 测试策略

- 只改文档，不写新的行为测试。每改一处先跑 `validate.sh --quick`（含读仓库文档的回归、README 同步、约定块同步）。
- 改模板 `templates/CAPABILITY-MAP.md` 后跑 `test-verify-artifacts.sh` 与 `test-phase-guard.sh`：模板里的注释不能让「能力图仍是模板」等判定变化。
- 收尾 grep：包内 `commands/`、`skills/`、`references/` 不再有指向 `docs/` 的相对写法；`activeModule` 不再出现「提醒用户改」「建议改」的不一致说法；
  两个命令的 `argument-hint` 与脚本 usage 列出的参数一致。

## 边界

- Always：只改文档、命令说明与模板注释；说法以现行代码为准，引用行号前先核对。
- Ask first：改 `interface.json` 或输出文字（包括「关键卡点」改名）；新增 Spec／Plan／todo 模板；新增写 `activeModule` 的命令；改模板的复选框结构。
- Never：在 Spec、文档、提交信息或 PR 中写入消费项目的名称、模块或编号；改插件行为。

## 成功标准

- 上面 1–9 每一条都落到了列出的位置，说法与代码一致。
- 包内命令和技能里没有使用者点不开的 `docs/` 相对引用。
- 三条最小验证全部通过；模板注释不改变任何阶段判定。

## 待定问题

- 无。
