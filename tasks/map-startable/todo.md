# Todo: map-startable

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan（含 off 不变分两层的做法），review_mark 记录后与 todo 一起提交。
- [x] Task 1：off 等同于没有开关的长期断言（预期直接绿） — `test_map_view.py` 新增 `ConcurrencyOff` 2 例与夹具 `CON_*`（Spec 带并行边界、Build order 带逗号组）：off、只有 version、带未知键的 on、取值无效四种配置下，JSON（去掉 generatedAt）与表格（去掉分钟戳）都和没有配置文件时逐字节相同；字段集合等于 TOP_KEYS／MODULE_KEYS。预期直接绿；临时让 map_view 在有配置文件时多输出一个字段，4 种情况全部变红，已复原。
- [x] Task 2：开关 on 时的 JSON 新字段（先红后绿） — `test_map_view.py` 新增 `ConcurrencyOnJson` 7 例，先全红；`test_capability_map.py` 新增 `DeclaredGroupsTests` 4 例，先红 3 例（CLI 输出不变那例本来就绿，作防线）。实现：`capability_map.py` 的 `_parse_declared_order` 同时返回原样逗号分组，`ParsedMap` 新增 `declared_groups`（`order_groups` 与 CLI 输出不变）；`map_view.py` 新增 `_scope`、`_overlap`、`_concurrency`，`build()` 末尾仅在开关为 on 时加字段。解析器 11 例、map 45 例全绿，`test_python_compat` 通过。期间一例是测试写错：Build order 第一个模块是当前模块（算进行中），不是就绪，期望值改正并加注释。
- [x] Task 3：表格里就绪模块的说明与冲突一行（先红后绿） — `test_map_view.py` 新增 `ConcurrencyOnTable` 4 例，先红 2 例（无冲突不出行、off 都没有两例本来就绿，作防线）；`_status_cell` 加 `concurrent` 参数，`render` 在开关为 on 且有冲突时于「未合入主线」前插一行，路径经 `clean()` 处理（与表格其他取自文件的文字一致）。map 49 例全绿。
- [x] Checkpoint 1（report）：一次性整份比对、三套核心回归与改坏验证 — 一次性整份比对（临时脚本，不入库）：`e7e2859` 导出的整套 hooks 与当前版本，在 CON 与原有 STATUS 两个夹具 × 无配置／off／只有 version／取值无效四种配置 × 表格与 JSON，共 16 组逐字节相同（JSON 去掉 generatedAt，表格去掉分钟戳）；另在本仓库真实能力图（113 个模块）上表格与 JSON 也相同。改坏验证：`_overlap` 改为前缀匹配时 `test_overlap_paths_and_order`、`test_same_name_prefix_is_not_an_overlap` 变红；开关 off 时也加字段时 `test_off_keeps_the_fixed_key_sets` 变红（「与无配置逐字节相同」那例不红，因为两边多出同样的字段，两例搭配才完整）；均已复原。三套核心回归：Task 1～3 各次提交全档通过（最后 `c8ca903`：phase-guard 368、verify-artifacts 67）。
- [x] Task 4：设计文档与 CHANGELOG — `docs/design.md` 的 `map_view.py` 一行补开关为 on 时只增字段；CHANGELOG「未发布」小节「新增」加一条。
- [ ] Checkpoint 2（gate）：模块验收
