# Spec: project-sections

<!-- spec-guard: review approved 10fe4a237c42 -->

## Objective

S110 要求 spec-guard 是通用插件、不与前端耦合，各类项目特有的内容通过「项目追加章节」的扩展口由项目在配置里声明（需求第四节：前端的浏览器兼容、视觉回归，
后端的数据迁移、接口契约，游戏的试玩清单）。本模块给出这个扩展口：项目在 `.agent/config.json` 声明要给哪份文档追加哪些章节，
新流程模块的文档就必须带上这些章节（内容可以写「不涉及」），阶段提示在要写那份文档时把它们列出来。

本模块是 M1 的最后一个，M1（flow-doc-skeletons、project-sections）在这里一起发版。

给谁用：给自己项目定规矩的用户；写新流程文档的 agent；读 verify-artifacts 结果的人和 CI。

对外接口与用法草案一致吗：一致，对应用法草案入口表的 `projectSections` 一行与 U4。

登记：ecosystem-lead #22328 分派（S110）。需求确认：用户 2026-11-24「说完了，照这样做」「确认插入，Q1–Q6 按推荐」。按规则是重要需求（同一需求批量插入 8 个模块），Spec 由用户批。

## Assumptions

1. **配置键与写法**：`.agent/config.json` 加 `projectSections`，值是对象，键是文档种类 `requirement`、`design`、`regression` 之一，值是章节名列表，例如：
   `{"design": ["浏览器兼容"], "regression": ["视觉回归"]}`。
   章节名：非空、去掉首尾空白后最多 40 个字符、不含换行和 `|`、`#`，同一种文档里不重复、不与该文档的骨架章节同名；每种文档最多 10 个。
   任何一条不合法，整个键失效（按未设置处理），`show`、阶段提示、verify-artifacts 按现有「个别键有问题」的规则报 `projectSections` 无效；其余配置照常生效。
2. **设置方式**：`/spec-guard:config` 的 `set --key projectSections --value '<JSON 对象>'` 先预览后 `--confirm`，`unset` 去掉整个键。这是项目规矩，不是接管档位，不需要用户原话；照常先预览、用户确认后写入。
   老版本 spec-guard（0.84.0 起）遇到不认识的键只忽略这一个键，所以团队里有人没升级也不会让整份配置失效。
3. **只作用于新流程模块**：带 `flow v2` 标记的模块，`flow_doc_problems` 在骨架章节之外再要求这些追加章节（标题存在即可，内容可以是「不涉及」）；
   `bug`、`small` 档只写一份需求文档，`requirement` 的追加章节照样要求，`design`、`regression` 的追加章节不要求（没有这两份文件）。老模块不查。
4. **阶段提示**：新流程模块在 `NEEDS_DESIGN`、`NEEDS_REGRESSION`、`NEEDS_SPEC`（写需求文档）时，下一步提示在骨架说明之后加一句「另加本项目要求的章节：A、B」（中英）；没有声明时不加。
   `projectSections` 本身不在每轮阶段提示里单独占一行（同 `moduleConcurrency`）。
5. **`/map --json`**：不加字段。追加章节是写文档的要求，不是模块状态。
6. **骨架文档**：`references/doc-skeletons.md` 加一节说明追加章节怎么声明、对哪些档位生效。
7. **版本与发布**：插件版本 0.94.0（M1 新增接口与配置，次版本）；CHANGELOG 写 M1 两个模块；README 中英 `--ref`。接口不另升（`interface.json` 1.18 不描述配置键；`commands/config.md` 是配置的权威说明）。
   合并后用 `scripts/release.py` 发 0.94.0，通知 ecosystem-lead 与 S110 各方（autopr-design、delegate-owner、mc-coord）。
8. **不做**：追加章节的内容检查（只查标题在不在）；按模块的追加章节；给老模块补章节；回归用例的格式（regression-doc-check）。

## Contract

- **C1** `hooks/project_config.py`：`projectSections` 的校验、`set` 接受 JSON 对象、`show` 显示（假设 1、2）。
- **C2** `hooks/module_stage.py`：`flow_doc_problems` 读追加章节（假设 3）；下一步提示加追加章节一句（假设 4）。
- **C3** `references/doc-skeletons.md`、`commands/config.md`、`docs/commands.md`（如有配置说明）（假设 2、6）。
- **C4** 版本 0.94.0、CHANGELOG、README（假设 7）。

## Acceptance criteria

- **AC1** `set --key projectSections` 对合法值预览后 `--confirm` 写入、读回一致；对每类不合法值（不是对象、键不是三种文档、章节名为空或超长或含 `|`／`#`／换行、重复、与骨架同名、超过 10 个）退出 2 且不写文件。
- **AC2** 文件里 `projectSections` 不合法时，只有这个键失效：`show` 与 verify-artifacts 报它无效，其余配置（如 `artifactLanguage`）照常生效。
- **AC3** 声明了 `design: ["浏览器兼容"]` 的项目，normal 档模块的技术方案缺「浏览器兼容」时 verify-artifacts 失败，写了标题（内容「不涉及」）时通过；bug、small 档不要求 `design`／`regression` 的追加章节，但要求 `requirement` 的。
- **AC4** 老模块（没有流程标记）不受 `projectSections` 影响：verify-artifacts 与阶段提示输出与不设这个键时一致。
- **AC5** 阶段提示在 `NEEDS_DESIGN` 时列出追加章节（中英）；没有声明时提示与 flow-doc-skeletons 的输出逐字相同。
- **AC6** 变异：不读追加章节、校验不拦重复章节名，各让对应回归变红。
- **AC7** `validate.sh`、phase-guard、verify-artifacts 全绿；两份 `plugin.json` 为 0.94.0，`scripts/validate.sh` 的版本一致性检查通过。

## Boundaries

- **会做**：C1～C4 及回归；合并后的发版与通知（发版与安装要用户授权）。
- **先问再做**：按模块的追加章节；检查章节内容；改骨架章节本身。
- **不做**：假设 8 列出的事。

## 并行边界

- 独占：`spec/project-sections.md`、`tasks/project-sections/`、`plugins/spec-guard/hooks/project_config.py`、`plugins/spec-guard/hooks/test_project_config.py`、`plugins/spec-guard/hooks/module_stage.py`、`plugins/spec-guard/hooks/test_flow_v2.py`、`plugins/spec-guard/hooks/test-verify-artifacts.sh`、`plugins/spec-guard/references/doc-skeletons.md`、`plugins/spec-guard/commands/config.md`、`docs/commands.md`、`plugins/spec-guard/.claude-plugin/plugin.json`、`plugins/spec-guard/.codex-plugin/plugin.json`、`CHANGELOG.md`、`README.md`、`README.en.md`
- 公共：无

## 文档建议

`commands/config.md` 的配置表加 `projectSections` 一行（写法、作用范围、不需要原话）；`references/doc-skeletons.md` 加「项目追加章节」一节；CHANGELOG 写 M1。项目没有文档基线。
