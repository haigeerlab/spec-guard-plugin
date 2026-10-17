# Todo: hint-language-follow

- [x] Task 0：提交 Spec、能力图、已批准的 Plan 与 todo — 2026-10-18 用户批准 Plan、决定不做外部审查（已写拒绝标记）；review_mark 记录后与能力图、Spec 一起提交。
- [x] Task 1：语言判据、项目配置行与位置行（先红后绿） — `test-phase-guard.sh` 新开第 18 段：zh-CN 的 IDLE 为中文，`zh-TW`、`zh-Hans`、`en`、`ja` 与无效配置（`zh_CN`）为英文，先红；`test_session_context.py` 新增 4 例（中文分支、中文分离 HEAD、其他语言不变、命令行 `--lang`），先红。实现 `hint_language`、`--hint-language`、`config_lines` 中文、`location_line(root, lang)`、phase-guard 取语言并传 `--lang` 后转绿。与计划不一致：原有 5 处用 `zh-CN` 测英文配置行的用例（第 9、16 段的 `LANG_LINE` 与两项都设）按本模块有意改变的行为失效，改为 `pt-BR`，测的仍是「非中文语言出英文配置行」；无效配置那两例不变。IDLE 用例同时覆盖 shell 自己的句子，所以 Task 3 的实现在这一步一起完成。
- [x] Task 2：`module_stage.describe` 的全部说明文字（先红后绿） — 第 18 段补 14 例（NEEDS_SPEC、NEEDS_PLAN 待审与无标记、BUILDING 两种 gate、Codex、会话上下文超阈值、DONE 含挂起、DONE、未合并提交、MODULE_DONE、activeModule 不在图中、MAP_INVALID、外部审查行），先红后改 `module_stage.py`：英文字面量原地不动，并排加中文；`COMMANDS_ZH` 只覆盖 free-next、free-current、delegate-review 的说明文字。与计划不一致：命令里的 `(Codex: …)` 保留英文半角写法，不改全角，后接中文时用一个空格分隔。
- [x] Task 3：phase-guard.sh 自己输出的几句（先红后绿） — 实现已在 Task 1 完成（IDLE 用例先红），这里补 MAP_ONLY、压缩后提醒、阶段算不出来、读不到能力图、目录级与本会话登记两种关联项目共 6 例，补上时已是绿的。回归 371→391 例。
- [ ] Checkpoint 1（report）：英文逐字节不变的差分证明，加改坏验证
- [ ] Task 4：verify-artifacts 一侧的正反回归
- [ ] Task 5：根因对照实测（佐证，不是硬门槛）
- [ ] Task 6：文档、CHANGELOG 与版本号
- [ ] Checkpoint 2（gate）：模块验收；推送与开 PR 先问用户，合并由用户进行

<!-- spec-guard: external-review declined -->
