# Todo: review-approval-marker

- [x] Task 1：文本指纹入口（先红） — `spec-digest.py` 新增 `text_digest` 与 `text <file>` 子命令，复用 `_h`；自测先加 3 组断言（稳定／定长／随内容变、子命令输出、读不了退出 1），在旧代码上因 `text_digest` 未定义失败，实现后通过；`test-checkers.sh` 的 digest-single-source 5 例仍通过。
- [x] Task 2：标记解析与评审状态（先红） — 新增 `test_review_marker.py` 11 例（五种状态、七种无效写法、正文提及与围栏代码块里的示例不算、指纹不受标记行影响而受其余字符影响），先因导入失败变红；`module_stage.py` 新增 `review_state`／`review_digest`／`review_body`，指纹经 `importlib` 调 `spec-digest.py`。变异三处（包含即可、指纹不排除标记行、`revised` 判成 `approved`）各有断言变红。实现中补定一条：围栏代码块里的行不算标记（否则本模块自己的 Spec 会因示例被判无效），已写回 Spec「标记」一节，Checkpoint 3 请用户过目。单测已登记进 `validate.sh`。
- [x] Task 3：阶段提示的 Review 行与建议语（先红） — `test-phase-guard.sh` 新增第 13 段 30 例：Spec「阶段提示」表逐行、无标记 BUILDING 全文逐字相同、非当前模块的标记不生效、MODULE_DONE／NEEDS_SPEC 不变、注入仍是合法 JSON；先在首例变红。`module_stage.py` 新增 `review_hint`／`file_review_state`，`describe` 只在有话可说时加 Review 行并替换建议语。既有 208 例期望值一处未改，全套 238 例通过。补定两点：待审核与已修订的建议语末尾带一句“用户批准后用 review-mark 记录”；文件读不了时只报一行读取失败、建议语不变（读取失败不是评审状态）。
- [x] Task 4：下一个 gate（先红） — 第 13 段再加 11 例：跳过已勾选项与 `report`、只剩 `report` 不输出、未标注按 `gate`、标题不以 Checkpoint 开头或不是清单项不输出、标题清洗并截到 80 字、Plan 待审核与 NEEDS_PLAN 时不输出；先变红，`module_stage.py` 新增 `next_gate` 后 249 例全绿。Spec「Success criteria」原文说无标记项目只多半句，与 Next gate 对所有 BUILDING 项目生效相矛盾，已改为如实写出这一行，Checkpoint 3 请用户过目。
- [x] Checkpoint 1（report）：判定与阶段提示回归全绿，ShellCheck 无警告 — 随 Task 4 的提交跑 `verify-and-commit.sh` 全档：`validate.sh`、phase-guard 249 例、verify-artifacts 40 例、ShellCheck 无告警。未验证：两边宿主对新增行的实际呈现（发版后做）。
- [ ] Task 5：`review_mark.py`（先红）
- [ ] Task 6：`verify-artifacts`（先红）
- [ ] Checkpoint 2（report）：三套核心回归与新单测全绿，ShellCheck 无警告
- [ ] Task 7：命令文件与 Codex 路由
- [ ] Task 8：规则文本、模板与文档（先红）
- [ ] Task 9：版本号与自用
- [ ] Checkpoint 3（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
