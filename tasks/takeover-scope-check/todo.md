# Todo: takeover-scope-check

- [x] Task 0：提交 Plan 与 todo — 2026-11-22 用户批准 Spec（「批准；Q10 A；Q11 A」）与 Plan（「Plan 批准」）。
- [x] Task 1：scope_applies、default_base、预先声明放行与 JSON 字段 — `module_scope.py` 新增 `scope_applies`（开关 on 或接管档位有非 human 项）、`default_base`（Spec 第一次加入的提交的父提交，Q10 A）、`_declared_paths`（Plan 已批准且未改时的预先声明公共路径）、`classify`（越界文件里命中预先声明的记为 `declared`）；`check` 的 `--base` 可省（取不到报 base-unknown 退出 2），JSON 加 `declared` 计数，`SCOPES` 加 `declared`。`interface.json` 的 `scopeCheck` 同步。`test_module_scope.py` 新增 `TakeoverCheck` 3 例（改前 3 失败；其中一例原断言没算上写档位本身改了 config，改正），55 例通过。构建中发现 Spec 假设 2 把「公共类别」写成「与现在一样不算越界」，与现有检查不符（现在算越界），按「与现在一样」的本意改正措辞并记入 Spec 变更记录，最终验收附差异。
- [x] Task 2：阶段提示 — `module_stage.scope_overreach()`：只在 BUILDING 且模块接管档位有非 human 项时，用 `module_scope.default_base` 与 `classify` 算越界；有越界时加「越界：N 个文件（前 5 个）」一行，建议下一步换成停下逐个说明交用户（同意就补进边界或预先声明并复审，不同意就撤回），节点按中途 gate；没有可用并行边界时同样停下（Q11 A）；基线取不到时只报「未判定」。越界写进状态码事实。`test-phase-guard.sh` 新增第 30 段 2 例（先写、改前失败），PARTS=30，533 例通过；第 25 段原先断言 `takeover: merge` 等配置不改阶段提示（takeover-config 时成立），本模块起接管模块构建中会做越界检查，改为只比不影响当前模块的配置。
- [ ] Task 3：接口与规则
- [ ] Checkpoint 1（report）：完整检查、变异验证与实跑
- [ ] Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行
