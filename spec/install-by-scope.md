# Spec: install-by-scope

<!-- spec-guard: review approved 11e1be04762b -->

## Objective

0.78.0 让 Plan 必须写「需要的外部条件」，并让 verify-artifacts 拿依赖清单的新增内容逐项去比。在一个真实的前端项目上实跑的结果是：
进行中的模块一升级就报「Plan 没有需要的外部条件一节」；同一仓库的工作区包被算成新增依赖；满屏是 typescript、vue 这类基础包。
AI 事先列不全要装的包，强制列清单再逐项对比，只是换了一种方式打扰用户。

本模块按用户决定 62 放宽装包，和上游 agent-skills 对齐：批 Plan 按已批准的范围授权，构建时装包默认放行，不再问用户；去掉清单
要求、逐项对比和与之配套的几句规则；最终验收照旧列出新增的直接依赖，作为用户看新增包的唯一位置。高风险操作的保底不变。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `scope-authorization`、`dependency-check`。需求来自接入协调人转达的
用户决定 62；用户在本会话同意放宽方案。

## Assumptions

1. **SG-1 改写**：「批 Plan 按范围授权」改为：用户批准 Plan，就授权了已批准范围内的工作——改本仓库文件、跑测试与构建、本地提交，
   以及构建需要的装包（含从官方源联网），按范围、不按次数，不再为这些问用户。`gate` 检查点与远端写入照旧。
2. **SG-2 去掉**：删掉「Plan 开头写需要的外部条件」这一条与 verify-artifacts 对它的提示。规则留一句：项目愿意在 Plan 里写要用的
   依赖或工具可以写，不强制、不检查。UI 自验那条恢复为「Plan 开头列出验证所需的工具并确认可用」。
3. **SG-4 改写**：「只在这几类情况停下问用户」的清单去掉「Plan 没列的新依赖」一项，删掉「Plan 没列的新依赖只问一次」整条。
   高风险一项补上「全局安装、下载脚本直接执行（例如把远端脚本经管道交给 shell）」；推送、发布、删除工作区外的文件、改全局配置、
   外发凭据保留；`reset --hard`、`rm -rf` 这类不可逆操作仍属「不可逆或高风险」。
4. **SG-5 保留并收窄**：最终验收清单末尾那一行改为：本模块新增的直接依赖（取自依赖清单的差异，不凭记忆）与锁文件有没有改动，
   **排除工作区自己的包**（`workspace:` 协议引用或本仓库内的包）；都没有写「无」。去掉「verify-artifacts 会对照 Plan 报出没列出的
   新增依赖」那半句。
5. **SG-5b 去掉**：删除 `hooks/dependency_check.py`、`hooks/test_dependency_check.py`，以及 verify-artifacts 里「依赖改动」与
   「需要的外部条件」两段和它们的回归用例；`scripts/validate.sh` 的单测登记一并去掉。能力图里 `dependency-check` 那一行作为历史
   保留，不改。
6. **宿主确认（SG-8）**：保留通用的一条——停在宿主确认前告诉用户去哪个会话、点什么，这不算问用户做决定；去掉决定 61 那句「宿主
   分不出包在不在 Plan 里……开工时一条命令把 Plan 列出的包一次加完」。
7. **SG-6（一次列全所需权限）与 SG-3 不变。**
8. **四处约定块同步**：两份模板、`docs/convention-block.md`、本仓库 `AGENTS.md`。约定块里「批 Plan 即按范围授权……」一行改为第 1 条
   的说法，去掉「需要的外部条件」；最终验收一行的「新增依赖与锁文件改动」保留并加「不含工作区自己的包」。
9. **版本**：0.78.1（补丁版：放宽规则、去掉一项检查）；CHANGELOG `[0.78.1]` 写明去掉了什么和原因；两份清单、中英 README 的 `--ref`。
   已经按 0.78.0 写了这一节的 Plan 不受影响，也不需要删。

## Contract

### 共享检查点规则 `references/workflow-checkpoints.md`

- 「批 Plan 按范围授权」改为第 1 条；删「Plan 开头写需要的外部条件」，换成第 2 条那一句「愿意写可以写，不强制、不检查」。
- 「只在这几类情况停下问用户」按第 3 条改；删「Plan 没列的新依赖只问一次」。
- 「最终验收列出实际改动的文件」末尾按第 4 条改。
- 「UI 自验」按第 2 条恢复。
- 「宿主确认」按第 6 条删掉后半段。

### 约定块（四处）

按第 8 条改两行。

### `hooks/verify-artifacts.sh` 与文档

- 删「需要的外部条件」「依赖改动」两段；`commands/verify-artifacts.md` 与 `docs/commands.md` 删对应说明。
- 删 `dependency_check.py`、`test_dependency_check.py` 及 `validate.sh` 里的登记。

### 不变

- `phase-guard.sh` 与每轮注入；verify-artifacts 其他检查与退出码；SG-3、SG-6；`/map` 与 `gates` 字段。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
```

## Testing strategy

- `test_workflow_checkpoints.py`：`test_plan_approval_authorizes_by_scope` 改为断言新说法（按已批准范围、装包默认放行、不按次数、
  全局安装与下载脚本直接执行属高风险、排除工作区自己的包、宿主确认不算做决定），并断言规则与两份模板里**不再**出现「只问一次」
  「一条命令」「verify-artifacts 会对照 Plan」；「需要的外部条件」只允许出现在「愿意写可以写」那一句里。
- `test-verify-artifacts.sh`：删掉两段的用例，加一例反向：未完成模块的 Plan 没有这一节、清单里新增了包，verify-artifacts 不出提示。
- 原有 `test_workflow_checkpoints.py` 其他断言（含原有停点「测试改不红」「记一份 ADR」「权限被拒」「结果未知」）保持绿。

## Boundaries

- **会做**：规则改写、删掉一项检查与一个模块、约定块与文档同步、0.78.1。
- **先问**：保留依赖核对的任何部分（例如只报锁文件改动）；改 SG-3、SG-6 或高风险清单的其余部分。
- **不做**：改宿主权限配置；改 `/map`；删能力图里的历史行。

## Success criteria

- AC1：规则写明批 Plan 按已批准范围授权、构建时装包默认放行、不按次数，`gate` 与远端写入照旧。
- AC2：规则、约定块与 verify-artifacts 都不再要求或检查「需要的外部条件」；规则只留「愿意写可以写」一句，UI 自验恢复原说法。
- AC3：「只问用户」清单不含新依赖，没有「只问一次」；高风险一项含全局安装与下载脚本直接执行。
- AC4：最终验收那一行列新增直接依赖与锁文件改动，排除工作区自己的包；不再提 verify-artifacts 对照 Plan。
- AC5：`dependency_check.py` 与它的单测、verify-artifacts 两段与用例、`validate.sh` 登记都已删除；未完成模块新增依赖时 verify-artifacts 不出提示。
- AC6：宿主确认只保留通用一条，没有「开工时一条命令」。
- AC7：四处约定块一致；0.78.1 版本号、README `--ref`、CHANGELOG 齐全；`validate.sh`、两边回归与 `test_workflow_checkpoints.py` 通过；`phase-guard.sh` 不变。

## Open questions

- 无。
