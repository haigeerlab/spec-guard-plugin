# Todo: map-startable

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan（含 off 不变分两层的做法），review_mark 记录后与 todo 一起提交。
- [x] Task 1：off 等同于没有开关的长期断言（预期直接绿） — `test_map_view.py` 新增 `ConcurrencyOff` 2 例与夹具 `CON_*`（Spec 带并行边界、Build order 带逗号组）：off、只有 version、带未知键的 on、取值无效四种配置下，JSON（去掉 generatedAt）与表格（去掉分钟戳）都和没有配置文件时逐字节相同；字段集合等于 TOP_KEYS／MODULE_KEYS。预期直接绿；临时让 map_view 在有配置文件时多输出一个字段，4 种情况全部变红，已复原。
- [ ] Task 2：开关 on 时的 JSON 新字段（先红后绿）
- [ ] Task 3：表格里就绪模块的说明与冲突一行（先红后绿）
- [ ] Checkpoint 1（report）：一次性整份比对、三套核心回归与改坏验证
- [ ] Task 4：设计文档与 CHANGELOG
- [ ] Checkpoint 2（gate）：模块验收
