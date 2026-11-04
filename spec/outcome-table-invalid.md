# Spec: outcome-table-invalid

<!-- spec-guard: review approved 13d47ca32e31 -->

## 目标

`/spec-guard:documentation-verification` 读 Plan 里的 `Documentation outcome` 表时，借用 `documentation_impact.py` 的 `_table` 解析。
表写坏时 `_table` 抛 `ImpactError`，而核验器没把它转成自己的 `VerificationError`；命令行入口 `main` 只接 `VerificationError`、`OSError`、
`UnicodeError`，于是打出 Python 堆栈、不按约定输出 `{"state": "invalid", "error": …}` 并退出 1。影响表与基线在 `parse_impact` 里已经转换过，没有这个问题。

2026-11-04 doc-outcome-hint 构建时顺带发现（只有表头的 outcome 表），0.86.4 起就存在。本模块让这几种写坏的表按其他结构错误一样报 `invalid`。

给谁用：启用文档基线的项目，以及替用户跑核验、读 JSON 的 agent。

## 假设

用户已于 2026-11-04 确认（「说完了，开模块」，针对本会话的需求总结）：

1. **覆盖的情况**：outcome 表只有表头没有数据行、缺分隔行、分隔行写错、某一行格数不对——即 `_table` 对 outcome 表抛 `ImpactError` 的四种情况。
2. **改法**：在 `documentation_verification.py` 的 `_outcomes` 里调用 `_table` 处接住 `ImpactError`，以原报错文字抛 `VerificationError`；
   `main` 不改（它已接 `VerificationError`，输出 `invalid` 并退出 1）。
3. **不变**：表格解析与格式要求（空表仍然无效）、`attention`／`ready`／`absent` 判定、JSON 字段、`interface.json`；不改 `documentation_impact.py`。
4. 发 0.86.6，只是修复；需求来自用户本人，无回告；仓库里不出现消费项目的名字、模块或编号。

## 命令

```text
python3 -B -m unittest plugins/spec-guard/hooks/test_documentation_verification.py
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## 测试策略

- 先写测试并确认在 0.86.5 上失败，再实现。
- `test_documentation_verification.py`：
  - 四种写坏的 outcome 表各一例，`verify_documentation` 抛 `VerificationError`，报错文字含 `Documentation outcome table`；
  - 命令行入口：只有表头的 outcome 表，`main` 输出可解析的 JSON、`state` 为 `invalid`、返回 1；
  - 其余既有用例全部通过。
- 变异（草稿副本）：去掉这次的转换，测试必须变红。

## 边界

- Always：先红后绿；只做异常转换，报错文字不改。
- Ask first：放宽 outcome 表格式（例如允许空表）；改 `documentation_impact.py` 的 `_table`；改 JSON 字段或退出码约定。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费项目的名称、模块或编号。

## 成功标准

- 四种写坏的 outcome 表，命令行都输出 `{"state": "invalid", "error": …}` 并退出 1，不再出现堆栈。
- 合法表与缺表的输出与 0.86.5 相同；既有回归全部通过。

## 待定问题

- 无。
