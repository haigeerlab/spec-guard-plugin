# Todo: delegate-review-hint

- [x] Task 0：提交已批准的 Plan 与 todo — 2026-10-17 用户批准 Plan，review_mark 记录后与 todo 一起提交。
- [x] Task 1：测试隔离（先做，行为不变） — `test-phase-guard.sh` 的 `run()` 默认把 `CLAUDE_CONFIG_DIR`、`CODEX_HOME` 指向空目录（用例可用 `SG_CLAUDE_HOME`／`SG_CODEX_HOME` 伪造安装），339 例不变。其余会走到阶段提示的测试在 Task 3 实现后按本机（装了 delegate）实跑结果补隔离。
- [x] Task 2：`sibling_plugins.py` 安装判断（先红后绿） — 先写 `test_sibling_plugins.py`（Claude 6 例、Codex 5 例），导入失败为红；实现后 11 例全绿。Claude 侧的记录读取与 settings 合并抽成 `claude_plugin_root(project, plugin)`，`agent_relay_probe` 改为调用它（断言不改、全绿）；阶段提示用的那条路径从 worktree 的 `.git` 文件定位主检出设置，不调 git。`test_python_compat` 通过；新测试登记进 `validate.sh`。
- [x] Task 3：外部审查状态判定与阶段提示行（先红后绿） — `module_stage.py` 新增 `external_review_state`、`external_review_hint`，提示行接在 Review 行后，入口按宿主写（Claude `/delegate:review` + `/delegate:doctor`；Codex `delegate:delegate-routing` + delegate 自己的体检，Codex 侧 delegate 只有这一个技能）。`test-phase-guard.sh` 新增第 17 段 23 例，回归 339→362 例。实现先于用例写成，因此补了一次红灯验证：临时换回旧 `module_stage.py`，第 17 段变红，恢复后转绿。钩子不传宿主时按 Claude 处理，所以「未知宿主」的写法走不到，那条用例改为断言默认 Claude 写法。本机装着 delegate 跑全档也全部通过，其余测试不需要再补隔离。
- [x] Checkpoint 1（report）：三套核心回归全绿，ShellCheck 无警告，并在草稿副本上做一次改坏验证 — Task 3 提交时 `verify-and-commit.sh` 全档（含 ShellCheck）通过；改坏两处，各自变红：拒绝标记判断失效 →「Spec 里有拒绝标记：不再提示」红；Codex 入口改错 →「Codex 宿主：写技能入口」红；均已复原。
- [x] Task 4：规则、文档、CHANGELOG 与版本号 — `references/workflow-checkpoints.md` 新增「外部审查意见」一节（只提议、落点、按 delegate 报告字段引用不写严重程度、跑不起来记一行、拒绝标记、每模块一次）；`docs/design.md` 部件表加 `sibling_plugins.py`，数据流第 3 步注明检查点时只读本机插件记录；CHANGELOG `[0.65.0] - 2026-10-17`「新增」两条；两份 `plugin.json` 与 README 中英 `--ref` 改为 0.65.0。
- [x] Task 4 补充：按 delegate 负责人 2026-10-17 发来的报告解读规则，`workflow-checkpoints.md`「外部审查意见」加「怎么读结论」一条（只有 completed 且 findings／no_findings_in_scope 才算有结论；no_findings_in_scope 不等于没有缺陷；其他情况记「未得出结论」及原因；注明 limitations）。只改文档；阶段提示不读 delegate 的 interface.json（D3-A），按版本校验另作后续模块。
- [x] Checkpoint 2（gate）：模块评审；PR 转为可评审由用户确认，合并由用户进行 — 2026-10-17 在对话正文列出：实际改动的 18 个文件（新增 6、修改 12、删除 0，没有超出 Plan 的文件）；Claude、Codex 两份提示行原文；验证结果（362 例与 11 例全绿、两处改坏都变红、Task 3 补了一次红灯验证）；未验证项（真实宿主里的表现、Codex 配置不常见的写法、拿不到宿主时的措辞、没做独立审查）；文档建议（无）；拟回告。之后又按 delegate 负责人的规则补了「怎么读结论」一条并告知用户。用户验收通过，PR #339 转为可评审，合并由用户进行。
- [ ] 发版后的验证
