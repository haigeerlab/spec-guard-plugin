# Todo: review-marker-legacy-projects

- [x] Task 1：Next gate 的中性措辞（先红） — `test-phase-guard.sh` 第 13 段：三条现有用例的期望改为中性措辞，新增 Plan 无标记时不含“keep going”、Plan 已批准时与 0.57.0 逐字相同、已批准时没有无标记说明，共多 3 例；先在第一条变红。`review_hint` 一并返回 Plan 的评审状态，`describe` 只对 `approved` 说 keep going，对 `none` 给中性说明。252 例全绿。
- [x] Task 2：Spec 没有标记时允许单独批准 Plan（先红） — `test_review_marker.py`：原“Spec 未批准即拒绝”一例拆成四例（Spec 无标记允许且 Spec 文件逐字未变、Spec 文件不存在允许、待审核／已修订／无效各拒绝且拒绝信息含单独确认的要求、Spec 已批准照常），先 3 例失败，改 `review_mark.py` 后 23 例全绿；Spec 状态改用 `file_review_state` 判。临时项目实跑：都没有标记时 Next gate 是中性措辞，单独批准 Plan 成功、Spec 未动，之后 Next gate 变回 keep going。与 Task 1 同一个提交（提交脚本不允许留未暂存的改动）。
- [x] Checkpoint 1（report）：三套核心回归与单测全绿，ShellCheck 无警告 — 随 Task 1、2 的提交跑 `verify-and-commit.sh` 全档：`validate.sh`（含 `test_review_marker.py` 23 例）、phase-guard 252 例、verify-artifacts 52 例（未改）、ShellCheck 无告警。未验证：两边宿主的实际呈现（发版后做）。
- [ ] Task 3：规则文本、命令与文档（先红）
- [ ] Task 4：版本号
- [ ] Checkpoint 2（gate）：模块评审；批准 Plan 即授权推送和开 PR，合并由用户进行
