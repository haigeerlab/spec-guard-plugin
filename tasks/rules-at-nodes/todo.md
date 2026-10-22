# Todo: rules-at-nodes

- [x] Task 0：同步批准标记、提交 Plan 与 todo — 按开工通知 C127 `module-crew sync` 到集成分支 e4b4ace（HEAD 450f32d）；Spec 带标记 acbb03de976c，与批准版只差 AC9 一句（用户批准 C122 时要求的范围内修正，已记变更记录，最终验收附差异）；三方合并保留了本分支 Plan 的 `pending` 行，改取集成分支带 `approved` 的版本（只差这一行）。validate、phase-guard（438 例）、verify-artifacts（74 例）全过。module-crew 入口按协调通知改用 0.11.0。
- [x] Task 1：停点规则与检查点规则（C2、C4） — `test_workflow_checkpoints.py` 新增 `NodeRulesTests`（7 例：五节顺序与「以后者为准」、各节体积、各节规则要素、与检查点规则共用的短语、检查点规则开头的指向行、D19①、D19②），改前因 `node-rules.md` 不存在 7 例全红。新建 `references/node-rules.md`（Spec、Plan 两节直接用新小项名）；检查点规则开头加指向行、「批 Plan 按范围授权」条末加 D19①、「回告」段按 C4 改写；原用例 `test_change_sources_are_recorded_and_answered` 的「批准最终 gate 即批准回告」随 C4 改为「批准最终 gate 即同意按这段文字发送」。全文件通过。各节体积（字节）：能力图审阅 987、Spec 交审 1410、Plan 交审 1315、中途 gate 739、最终验收 1581。
- [x] Task 1b：交审小项对上游章节（C7） — 新增 `test_each_review_item_names_its_upstream_chapter`，改前 14 个子断言红；检查点规则「交审要让用户看到内容」条加 C7 对照表（23 行，含 SG-b 的边界、未决问题、架构决定与文档建议附加）与「对应不上的只能作为附加项追加」规则，`node-rules.md` 各小项名后括注「上游 …」或「附加」。全文件通过；`check-interface.py` 通过；没有新增读取上游章节名的代码（只改 .md 与回归）。
- [x] Task 1c：复制块、条目编号与小项新名（C8、C9） — 回归先改：`CARD_SECTIONS` 换新名（Spec 五项、Plan 六项）、`test_how_to_approve_uses_one_copy_block` 加 v2.6 写法与编号规则并断言不含「批准；D1 A」、`test_mirrors_follow_the_card_sections` 改断言新名与短写法、`NodeRulesTests` 的 Spec 节加复制块短语；改前 7 处红。随后改检查点规则「交审要让用户看到内容」（Spec、Plan 两行新名，`combined` 为五项接六项，加「旧名照认」一句）与「交审时说明怎么批准」（v2.6 复制块写法、编号规则），`review-mark.md`、`SKILL.md` 同句，`node-rules.md` 两处「怎么批准」。改中又按新意替换两条旧断言：「范围内与范围外」→「总是做、先问、不做三档」，「合成一行」→「待定问题接在后面」（v2.6 不再合成一行）。全文件通过；`check-interface.py` 通过（旧节名仍在「照认」一句与对照表里）；`validate.sh --quick` 通过；仍含「以所装协作插件的规定为准」，无「去决策收件箱答」。
- [ ] Task 1d：`interface.json` 升 1.9 的公共变更请求（C10）
- [ ] Task 2：阶段注入附停点规则（C3 `module_stage.py`）
- [ ] Task 3：IDLE／MAP_ONLY 附停点规则（C3 `phase-guard.sh`）
- [ ] Task 4：约定块瘦身（C1）
- [ ] Task 5：与 `cost-slim-link-follow` 重叠的说明文字（C5）
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 6：合入集成分支并跑完整检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做
