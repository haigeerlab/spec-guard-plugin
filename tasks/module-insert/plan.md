# Plan: module-insert

依据 [`spec/module-insert.md`](../../spec/module-insert.md)。四个 task 严格串行，每个 task 一条提交，测试先红后绿。

## Task 1：预览与校验（只读）

- 新增 `plugins/spec-guard/hooks/module-insert.py`：解析参数；读取能力图并用 `module_stage.py` 取当前模块；
  按 Spec 做检查点判定和全部校验；在内存里生成插入后的能力图文本，交给 `capability_map.parse_map` 严格校验；
  用 `spec-digest.py` 的 `compute` 比对目标摘要和已有行摘要，并比对已有模块在 Build order 中的相对顺序；
  输出新行、新 Build order、统一 diff、当前模块是否改变、同 id Proposal 提醒。
- 新增 `test_module_insert.py`：正例（`after:`、`end`、有 Plan 未开始时放行、预览不写文件）与全部反例
  （做到一半、能力图无效或缺失、id 重复或不合法、未知依赖、依赖排在锚点之后、锚点不存在、职责为空或多行、
  Spec 已存在），每个反例断言没有写任何文件。接入 `scripts/validate.sh`。
- 验证：`python3 -B plugins/spec-guard/hooks/test_module_insert.py`；`/bin/bash scripts/validate.sh`。

## Task 2：确认后写入

- `--confirm`：重新执行全部检查后，用临时文件加原子替换写能力图。不创建 Spec 骨架（见 Spec「写入」一条的理由）。
- 测试：只改能力图（前后对比项目文件清单）；写入后能力图严格解析通过；目标摘要、已有行摘要和已有模块相对
  顺序不变；新模块排在当前模块之前时，`module_stage` 报告新模块的 `NEEDS_SPEC`。
- 验证：同上。

## Task 3：入口与阶段提示

- 新增 `plugins/spec-guard/commands/add-module.md`：让 agent 先根据上下文提出字段和插入位置并说明理由，运行预览并
  原样展示，得到明确确认后才加 `--confirm`；字段改动后重新预览。
- `skills/spec-guard-ops/SKILL.md` 增加 add-module 一节（Codex 入口）。
- `module_stage.py` 的 DONE 建议指向 `/spec-guard:add-module`，需要留痕时用 Proposal；`test-phase-guard.sh`
  改为断言新措辞。
- 验证：`test-phase-guard.sh`、`scripts/check-command-names.py`、`validate.sh`。

## Task 4：用户文档

- `README.md` 功能表增加快速插入；`docs/workflow.md` 增加「快速插入」一节，作为新增模块的默认做法，Proposal 一节
  注明选用场景；命令对照表增加一行。
- `CHANGELOG.md` Unreleased 记录新命令。
- 验证：`check-readme-sync.py`、`validate.sh`、新文档链接可解析。

## 风险

- 能力图文本插入要保留原有格式（表格对齐不要求，但不能改动其他行）；以「已有行摘要不变」测试兜底。
- Build order 可能含逗号分组：新模块作为单独一步插在锚点所在那一步之后，测试覆盖锚点在分组中的情况。
