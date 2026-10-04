# Todo: tracker-backend-default

- [x] Task 1：`tracker_default.py` 的 `read_default` / `resolve` / `as_json`——三 backend 形状、非法一律 invalid 不降级、T5 三正八反与 T6 判定表八行
- [x] Task 2：入口 `show` / `set`——预览不写文件、`--confirm` 原子写回单文件、不触碰 state.json、命令与 Codex skill parity
- [x] Task 3：删 `tracker` 字段、激活信号改判 `activeModule`——setup-convention 写入、phase-guard 判据与注释、六个用例（两个先红）
- [x] Task 4：删 `retired_tracker()`、历史告警重新界定、退役扫描断言——三条先红、完成判据逐字不变、本仓库输出零差异
- [ ] Task 5：文档——退役说明、决策记录（修订 hosted-ticket-workflow 条款）、plan-without-todo 修订段、workflow、concepts、CHANGELOG
- [ ] Checkpoint：两种 Python 下全部回归 + smoke + `git diff --check`，临时项目实跑三情形，本仓库零差异核对，代码与安全审查，开 PR 等 CI，不自行合并
