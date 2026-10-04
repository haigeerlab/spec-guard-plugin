# Todo: phase-context-sanitization

- [x] Task 1：`safe_fragment(value, limit=80)`——折叠空白、删反引号与反斜杠、超长截断、非字符串返回空串；单元测试并在 validate.sh 登记
- [ ] Task 2：`activeModule` 校验与文案——`active_module_state` 三态、无效时不回显值但仍报告、值无效不影响激活；两条先红
- [ ] Task 3：`MapError` 与 ref 名经净化——保留可辨认的原文；加反例证明 verify-artifacts／module-insert 的终端输出仍带原文
- [ ] Task 4：文档与决策记录——phase.md、workflow、workflow-checkpoints、决策记录、CHANGELOG（安全修复 + 行为变化）；反向自查 Spec 每条契约都已落地
- [ ] Checkpoint：两种 Python 全量 + 重跑两个复现 + 本仓库零差异 + 牙齿检查（变异须作用在值被使用之前）+ 代码与安全审查 + 开 PR 等 CI，不自行合并
