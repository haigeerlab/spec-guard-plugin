# Todo: pre-push-ref-only-skip

- [x] Task 1：回归先行（先红）— `test_pre_push_environment.py` 新增：只删远端分支时检查调用 0 次且分支已删；只推 tag 时调用 0 次且 tag 到达远端；分支与 tag 一起推时调用 3 次；推送清单为空时（直接运行钩子）调用 3 次。现有钩子上前两例为红
- [x] Task 2：钩子实现 — 生成的钩子读完 stdin，全部为删除或 tag 时打印跳过原因并退出 0；pre-push 回归 7 例通过。变异均被抓到：tag 判定放宽到任意 ref、去掉删除判定、清单为空也跳过（为此补了空清单用例，原计划的“不读完 stdin”变异改为这一条）
- [x] Task 3：文档 — `docs/maintainer-workflow.md` “提交前”一节写明跳过规则与重新安装
- [x] Checkpoint 1（report）：validate 与 pre-push 回归通过，ShellCheck 无告警
- [x] Checkpoint 2（gate）：模块评审；Plan 获批即授权推送与开 PR，合并由用户进行 — PR #267 由用户合并于 0b0f470
- [x] Task 4：重新安装本机钩子 — 合并后在主线上重装，安装内容与生成文本一致；真实删除 claude/pre-push-ref-only-skip 时打印“跳过检查（只有删除 …）”，推送 2 秒完成
- [ ] Task 5：0.55.0 统一发版时补证据
