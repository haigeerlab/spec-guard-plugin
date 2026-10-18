# Todo: open-commitments

- [x] Task 0：提交已批准的 Plan 与 todo — Plan 经用户批准（2026-10-18），与本 todo 一次提交。
- [x] Task 1：规则「未了的承诺」与模板行（先红） — `test_workflow_checkpoints.py` 新增 1 例（新一节的关键词；两份模板与 `docs/convention-block.md` 含新增两行），先失败；共享检查点规则在「需求来源与回告」后新增「未了的承诺」，三处约定块各新增两行，`git diff` 无删除行；43 例全绿，`verify-and-commit.sh` 全档通过（6092464）。
- [x] Task 2：钩子的读回提醒（先红） — `test-phase-guard.sh` 新增第 19 段 11 例（fresh：无账本静默、未激活目录静默、有账本只出英文/中文提醒、缺 python3 仍给英文、跟随指向按目标判断、指向失效静默；压缩后：无账本原句、有账本换成带账本的一句（中英）；UserPromptSubmit 有无账本逐字相同），并把第 15 段的 hooks.json 结构断言改为三项、新增「压缩那一项与 origin/main 逐字相同」；先在旧代码上确认第 15、19 段失败。`phase-guard.sh` 新增 `fresh_out`（只判断 `.epiq/project.json`，JSON 手写，不靠 python3）与带账本的压缩后核对句；`hooks.json` 新增 `startup|clear` 一项，命令与压缩那一项只差 `fresh` 参数。403 例全绿。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告 — 随 Task 2 的提交跑 `verify-and-commit.sh` 全档（暂存了 `.sh`，含 ShellCheck 4.1.0）。
- [x] Task 3：宿主实测新一项钩子会触发 — Claude：临时项目（约定块 + `.epiq/project.json`）里 `claude -p --plugin-dir <工作区插件> --model haiku` 跑一轮，会话记录里 `SessionStart:startup` 钩子输出了英文读回提醒，并进入 `hook_additional_context`（与另一插件的注入并列），模型上下文里有。Codex：未测——smoke 只测已安装到 Codex 的那份插件，测工作区版本要改本机 Codex 安装，新的一项钩子还要用户在 `/hooks` 信任；放到发版后同步宿主时测。`/clear`（两边）也放到发版后在交互会话里测。
- [x] Task 4：文档、CHANGELOG 与版本号 — `docs/workflow.md` 一段（有人在等的事不靠会话记忆）；`docs/design.md` 钩子表与数据流补新的 `SessionStart` 一项；CHANGELOG `[0.69.0]`（含 Codex 要信任新一项钩子）；两份 `plugin.json` 改为 0.69.0，中英 README 的 `--ref` 改为 v0.69.0，安装表补信任说明，数据与隐私一节补「只看 `.epiq/project.json` 在不在」；`validate.sh` 通过。另核对成功标准：临时项目先用 0.68.0（`git archive e77af2e`）装约定块，再用工作区版本 `setup-convention local --replace`（Claude 与 `--host=codex` 各一次），退出码都是 0，新增行已写入，不需要 `--accept-removals`。
- [x] Checkpoint 2（gate）：模块评审；推送与开 PR 在此由用户确认，合并由用户进行 — 2026-10-18 在对话里列出实际改动的 19 个文件（均在 Plan 范围内；删除行来自第 15 段 hooks.json 断言改为三项）、验证结果与未验证项（Codex 新钩子、两边 `/clear`、真实会话行为、未做独立代码评审），以及拟回告（session-protocol 契约负责人，Claude 原生会话消息，发版后发 0.69.0 的改动与升级方法，随后以「已告知」关闭 HP2G7RV）；用户验收通过，拟回告一并批准，确认推送与开 PR；不做外部审查。
- [ ] 发版后的验证

## 外部审查意见

<!-- spec-guard: external-review declined -->

用户在最终验收时选择直接验收、不做外部审查（2026-10-18）。
