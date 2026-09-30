# Spec: insert-existing-spec

## Objective

`add-module`（`hooks/module-insert.py`）在 `spec/<id>.md` 已存在时拒绝插入（"已存在，拒绝覆盖"）。但命令从不写 Spec
文件，所谓"覆盖"不会发生；而 Spec 在、能力图行不在时，`verify-artifacts` 又报"能力图上没有的模块 spec"。先写 Spec
再插入能力图的顺序因此必然卡住，只能把 Spec 挪走、插入、再挪回。

原拒绝的真实顾虑是：阶段判定只看 Spec 是否存在，插入后阶段直接成为 `NEEDS_PLAN`，一份未评审的 Spec 会绕过
"写并评审 Spec"。本模块去掉拒绝，改为在预览中把这一点明确告诉用户，由用户确认。

登记：2026-09-30 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-09-30 确认（按推荐方案）：

1. `spec/<id>.md` 已存在不再是拒绝条件；其余校验（检查点、做到一半需 `--interrupt`、能力图严格校验、摘要与顺序不变、
   `--proposal` 的预检／本地图一致／`_matches` 自检）全部不变。
2. 预览在此情况下多输出一段提示：Spec 已存在，插入后该模块阶段为 `NEEDS_PLAN`（视为已评审）；若尚未评审，先评审
   再 `--confirm`。`--confirm` 的写入结果同样打印这一提示。
3. 不新增参数；写入范围仍只有 `spec/CAPABILITY-MAP.md`，从不创建、修改或删除 Spec 文件。
4. 不带该情况时，预览与写入输出逐字不变。
5. 一个 task：代码、测试、文档与 CHANGELOG；与已合并的证明诊断码一起发 v0.35.0。

## Contract

- `module-insert.py`：删除"已存在，拒绝覆盖"的拒绝；`preview()` 结果新增布尔字段（如 `existing_spec`）；
  `format_report` 与写入后的阶段提示在该字段为真时追加提示行；`--proposal` 路径同样适用。
- `commands/add-module.md`：删除"`spec/<id>.md` 已存在：拒绝"的说明，改为"会提示，未评审先评审"；
  Codex `spec-guard-ops` 同步（如有相同表述）。
- `CHANGELOG.md` Unreleased `### 变更`。

## Commands

```text
python3 -B plugins/spec-guard/hooks/test_module_insert.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 scripts/check-command-parity.py
```

## Testing strategy

- 先写测试并确认它在当前代码上失败，再修改。
- Spec 已存在时：预览成功、输出含提示、不写文件；`--confirm` 只改能力图、Spec 文件逐字不变、写入后阶段为
  `NEEDS_PLAN`、输出含提示；插入后 `verify-artifacts` 不再报"能力图上没有的模块 spec"。
- `--proposal` 模式下 Spec 已存在：同样允许并提示。
- 原有的"Spec 已存在即拒绝"断言按新行为改写并在提交说明中列出；其余已有测试保持通过，无该情况时输出逐字不变。
- 两种 Python 下三条最小验证与上述测试都通过。

## Boundaries

- Always：先红后绿；只在 `--confirm` 时写能力图；从不写 Spec 文件。
- Ask first：新增参数；放宽其他校验；自动评审或改写 Spec。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 先写 Spec 再运行 add-module 能直接插入，预览与写入都明确提示阶段变化；`verify-artifacts` 随之通过。
- 其余行为逐字不变；两种 Python 下全部检查通过。

## Open questions

- 无。
