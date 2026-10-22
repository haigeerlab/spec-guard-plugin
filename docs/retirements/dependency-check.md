# 退役：dependency-check

状态：已退役。代码在 0.78.1（模块 `install-by-scope`，决定 62，提交 `a42a7f1b`）删除；能力图里的那一行在 2026-10-22
由模块 `fact-fixes` 移出（用户批准事项 C30、C37）。

## 退役的是什么

`verify-artifacts` 对进行中模块的依赖改动核对：从模块 Spec 第一次提交起，对比 `package.json`、`pyproject.toml`、
`requirements*.txt` 里直接新增的包与 Plan「需要的外部条件」，没列出的逐个报出（0.78.0 引入，`hooks/dependency_check.py`）。

## 为什么退役

决定 62 把装包改为批 Plan 即按范围授权、构建时默认放行，「Plan 必须写需要的外部条件」随之去掉，逐项对比失去依据。
最终验收仍列出新增直接依赖与锁文件改动（规则见共享检查点规则「最终验收」）。

当时 `spec/install-by-scope.md` 第 5 条写「能力图里 `dependency-check` 那一行作为历史保留，不改」；2026-10-22 的审查指出
图里一直把它显示为现行模块（功能清单 A-138），按 `retired-module-separation` 的先例改为归档。

## 归档

- Spec：[`dependency-check/spec.md`](dependency-check/spec.md)
- Plan：[`dependency-check/plan.md`](dependency-check/plan.md)
- todo：[`dependency-check/todo.md`](dependency-check/todo.md)

三份文件由 `git mv` 原样移来，只作历史证据，不回写其中的设计；文中的旧路径与「现行」说法按当时理解。
CHANGELOG 与 `docs/releases/` 里的提及保持原样。
