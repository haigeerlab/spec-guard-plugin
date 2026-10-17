# Todo: hint-language-follow

- [x] Task 0：提交 Spec、能力图、已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan、决定不做外部审查（已写拒绝标记）；review_mark 记录后与能力图、Spec 一起提交。
- [x] Task 1：语言判据、项目配置行与位置行（先红后绿） — `test-phase-guard.sh` 新开第 18 段：zh-CN 的 IDLE 为中文，`zh-TW`、`zh-Hans`、`en`、`ja` 与无效配置（`zh_CN`）为英文，先红；`test_session_context.py` 新增 4 例（中文分支、中文分离 HEAD、其他语言不变、命令行 `--lang`），先红。实现 `hint_language`、`--hint-language`、`config_lines` 中文、`location_line(root, lang)`、phase-guard 取语言并传 `--lang` 后转绿。与计划不一致：原有 5 处用 `zh-CN` 测英文配置行的用例（第 9、16 段的 `LANG_LINE` 与两项都设）按本模块有意改变的行为失效，改为 `pt-BR`，测的仍是「非中文语言出英文配置行」；无效配置那两例不变。IDLE 用例同时覆盖 shell 自己的句子，所以 Task 3 的实现在这一步一起完成。
- [x] Task 2：`module_stage.describe` 的全部说明文字（先红后绿） — 第 18 段补 14 例（NEEDS_SPEC、NEEDS_PLAN 待审与无标记、BUILDING 两种 gate、Codex、会话上下文超阈值、DONE 含挂起、DONE、未合并提交、MODULE_DONE、activeModule 不在图中、MAP_INVALID、外部审查行），先红后改 `module_stage.py`：英文字面量原地不动，并排加中文；`COMMANDS_ZH` 只覆盖 free-next、free-current、delegate-review 的说明文字。与计划不一致：命令里的 `(Codex: …)` 保留英文半角写法，不改全角，后接中文时用一个空格分隔。
- [x] Task 3：phase-guard.sh 自己输出的几句（先红后绿） — 实现已在 Task 1 完成（IDLE 用例先红），这里补 MAP_ONLY、压缩后提醒、阶段算不出来、读不到能力图、目录级与本会话登记两种关联项目共 6 例，补上时已是绿的。回归 371→391 例。
- [x] Checkpoint 1（report）：英文逐字节不变的差分证明，加改坏验证 — `evals/hint-english-diff.sh v0.67.0`：37 种夹具（各阶段、评审标记、挂起、暂停、未合并提交、activeModule 三种异常、MAP_INVALID、读不到能力图、阶段算不出来、外部审查、两种关联项目）× 未设／`en`／`ja`／`zh-TW`／无效配置 × 宿主与事件（Claude、Codex、未知宿主、SessionStart、Claude 850k、Codex 230k），英文 905/905 逐字节一致；同样夹具在 `zh-CN` 下 181/181 没有残留英文标签，都带标题行与 `当前阶段: **X**`。第一版串行跑了 12 分钟，改为 8 线程后约 2 分钟。改坏验证：判据放宽为「zh 开头都算中文」时第 18 段 `zh-TW：仍是英文` 变红；英文模板 `re-reads` 改成 `rereads` 时差分报 805/905 不一致；均已复原。耗时：本仓库每轮 hook 中位数 221 ms（0.67.0）→ 247 ms。
- [x] Task 4：verify-artifacts 一侧的正反回归 — 正例复用已有的「合法的项目配置通过」（`zh-CN` + combined）；新增反例「不合规的语言标签判无效」（`zh_CN` → `artifactLanguage-invalid`），与第 18 段「配置无效：英文并报告 invalid」同一份配置。verify-artifacts 代码不改；回归 61→62 例。
- [x] Task 5：根因对照实测（佐证，不是硬门槛） — **未验证。** 我在会话里嵌套跑 `claude -p` 被自动权限分类器拦下（Create Unsafe Agents），改由用户在终端跑脚本（共享笔记目录下的 `hint-language-ab.sh`）：`claude 2.1.301 --safe-mode` 关掉了 CLAUDE.md 与已装插件，但 `--settings` 传入的 UserPromptSubmit hook 同样没有执行（两组都是 hook ran 0/5，没有生成注入日志），所以两组 10 条回复都没收到阶段提示，全是中文，只说明「没有注入时中文提问得到中文回答」，不能佐证或否定「英文提示带偏回复语言」。根因判断仍是推测。
- [x] Task 6：文档、CHANGELOG 与版本号 — `commands/phase.md` 补中文提示说明；`commands/config.md`、`spec-guard-ops` 的 config 一节、`docs/design.md` 项目配置一段写明 `zh-CN` 时阶段提示用中文；`workflow-checkpoints.md` 注明 `下一个 gate`；CHANGELOG `[0.67.1]`「修复」与「维护者工具」；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.67.1。
- [ ] Checkpoint 2（gate）：模块验收；推送与开 PR 先问用户，合并由用户进行

<!-- spec-guard: external-review declined -->
