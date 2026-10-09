# Todo: self-report-tmpdir-independence

- [x] Task 1：回归先行（先红）— `validate.sh` 用 `mktemp -d` 在 git 目录下建 `sg-self-report-tmpdir.XXXXXX`，以它为 TMPDIR 再跑一遍 `test_self_report.py`，只删带该前缀的目录（最初写法 `cd "$X" && pwd -P` 后 `rm -rf` 被安全检查拦下：git 失败时会删当前目录，已改掉）。现有用例在外部 TMPDIR 下 FAILED (failures=1)
- [x] Task 2：修正用例 — 改用固定路径 `/tmp/sg-self-report-fixture/badmap`；外部与默认 TMPDIR 下 36 例均通过；改回 `self.root` 推导时外部 TMPDIR 下重新变红
- [x] Checkpoint 1（report）：validate 全部通过；用 `scripts/verify-and-commit.sh` 提交
- [x] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR，合并由用户进行 — PR #272 由用户合并于 e9c8e03
- [x] Task 3：下次发版时补证据 — v0.55.1 已发版（#280），验证记录见 `docs/releases/v0.55.1-*.json`
