# Todo: cost-slim-link-follow

- [x] Task 0：提交已批准的 Spec 标记、Plan 与 todo — Spec（C84，修订后标记 61b845f）与 Plan（C87／C97）由模块协调带批准标记提交到集成分支 30d5510；按开工通知 `module-crew sync`（HEAD 82d51fe，已含该提交）；validate、phase-guard（438 例）、verify-artifacts（74 例）全过。
- [x] Task 1：成本报告瘦身（C1） — 测试先改：返工信号四个用例与 Codex apply_patch 用例换成「报错调用不计入 `subagents`（正文含收回原因或其他文字都一样）」「成功调用的正文含收回文字也照常计入」「task 与 Codex task 不再有 `dispatches`／`redispatches`／`reclaims`／`edits_after_handback`」，多模块对照用例改为断言 JSON 无 `comparison`，表格断言含「子代理记录」、不含派活／重派／收回／交回后改／对照／返工，无法统计的部分提到 `spec-guard-link.json`；在原代码上 7 失败 27 错误。实现：删 `EDIT_TOOLS`、`HOOK_DENIAL`、`RECLAIM_MARK`、`PATCH_FILE`、`_text` 与 `comparison()`，`_claude_events` 只取错误标记与提问时间，Codex 不再收集补丁路径；表格列与金额列对齐。默认 python3 与 `/usr/bin/python3` 3.9.6 各跑 138 例全过；全仓旧字段只剩 `evals/dispatch-cost/results/` 历史结果与报告。
- [x] Task 2：派活规则退役（C2） — 测试先改：`test-setup-teardown.sh` 派活段换成「模板保留且首行注明退役」「setup 不写规则段」「`--dispatch`／`--no-dispatch` 退出 2、说明已退役、不改文件」「旧块带规则段时 `--replace` 预览单列退役行、不需要 `--accept-removals`，写入后块回到基础模板」「CRLF 与缩进标记仍认作旧规则段」「正文提及或块外标记不算」，teardown 用例改用旧版写法夹具；空行检查只保留关闭态；`test_project_config.py` 改为不列 `dispatch`、`set --key dispatch` 退出 2；原代码上分别红（模板首行、config 2 例）。实现：`setup-convention.sh` 两个参数退役、删开关状态与 `dispatch_status`，`retired_status` 只在旧块带标记时打印；`project_config.py` 删 `dispatch` 项、`BLOCKS`、`DISPATCH_MARKER`、`_dispatch` 与只为它服务的字典格式化；两份模板首行加退役注释。setup/teardown 53 例、config 37 例全过。
- [x] Task 3：跟随解析（C3） — 测试先加 `Follow` 七例：无指向文件静默打印会话目录；目录级指向打印目标、stderr 写「本次操作的是被指向的项目」与来源、指向文件路径；本会话登记优先，别的标识与空标识走目录级；只有别的会话登记时打印会话目录；未启用、不存在、格式无效三种都退出 2、stdout 空、不退回会话目录；本会话登记失效时诊断写明是本会话的登记；会话目录自己已启用时不跟随。共用目录提示改为「命令也会跟随，各会话用 --session 登记」；原代码上 8 例红。实现 `follow()` 与 `follow` 子命令（复用 `resolve_for`、`enabled`、`safe_fragment`，失效措辞与阶段注入一致）。默认 python3 与 `/usr/bin/python3` 3.9.6 各 39 例全过；phase-guard 438 例全过。
- [x] Checkpoint 1（report）：变异核对 — 在 scratchpad 里 `mktemp -d` 建的四份 `git archive HEAD` 副本上各改一处：`follow` 不传会话标识（不优先查会话登记）→ `test_project_link.py` 2 例红；`follow` 失效时退回会话目录、退出 0 → 2 例红；成本报告把报错的 Agent 调用计入 `subagents` → `test_module_cost_report.py` 1 例红；`--replace` 预览不再把规则模板当 `--known` → `test-setup-teardown.sh` 报「旧块带规则段时预览应单列退役行、不需要 --accept-removals」。
- [x] Task 4：Claude 命令入口（C4，不含 `config.md`、`review-mark.md`） — 20 个带脚本调用的命令把取根换成 `follow` 两行（proposal-review／promotion-preflight／promotion-proof 的 `--project .` 改为 `--project "$PROJECT"`；setup、teardown 以 `CLAUDE_PROJECT_DIR="$PROJECT"` 调脚本；local-ticket-ledger 给 status／preflight／initialize 传 `--project-dir "$PROJECT"`），首个调用块后加一句「照原文转述跟随说明、退出 2 不改用会话目录」；ticket、local-ticket-portability 两个说明型命令给出 `follow` 命令取项目根；link-project 第 67 行改为其他命令与阶段注入自动跟随。`check-command-parity.py` 要求 Codex 侧同步带 `--project-dir`，所以 `skills/local-ticket-ledger-ops/SKILL.md`（不与 sibling-rules-out 重叠）提前在本 task 改：代码块传 `CODEX_THREAD_ID`，正文注明 Claude 改传 `CLAUDE_CODE_SESSION_ID`。`test_project_link.py` 加入口扫描两例（其余三个 SKILL.md 与 config.md、review-mark.md 暂列例外）。`test_project_link.py` 41 例、`check-command-parity.py`、`validate.sh --quick` 通过。
- [x] Task 5：等 `sibling-rules-out` 合入后同步 — 开工前它已合入集成分支（92dffd7，C92），按同步基线与开工通知 sync 进本分支（HEAD 82d51fe）；本步再次 `module-crew sync` 报已是最新（含 30d5510），不需要发【等待其他会话】。
- [x] Task 6：重叠文件与 Codex 入口（C4 `config.md`、`review-mark.md`、C5） — `config.md` 取根改 `follow`、描述与只读汇总表去掉 dispatch；`review-mark.md` 取根改 `follow`；`spec-guard-ops` 解析环境段改为 `$FROM`（会话目录）＋`follow` 得 `$PROJECT`（`CODEX_THREAD_ID`），setup 一节的 `--dispatch` 说明换成退役说明、config 一节去掉 dispatch、link-project 一节改用 `$FROM` 并写明其他命令自动跟随、删去「要手动换成被指向路径」那段；`ticket` 与 `local-ticket-portability` 两个 skill 给出 `follow` 命令（代码传 `CODEX_THREAD_ID`，正文注明 Claude 改传 `CLAUDE_CODE_SESSION_ID`）。`test_project_link.py` 去掉例外后 41 例过；`check-command-parity.py`、`validate.sh --quick` 通过；命令与 skill 中已无「不会自动跟随」「作为项目传入」。
- [x] Task 7：阶段注入措辞（C6） — 先 `module-crew sync`（合入 b19fe11，只是 rules-at-nodes 的 Spec 批准，代码未合入，HEAD 6b3f3ac）。测试先改：目录级与会话登记两条 `Linked project` 全文、目录级包含断言、两条 zh-CN 关联项目用例改为新文字并断言不再含「作为项目传入」；原代码上第 14、18 段红。实现：`phase-guard.sh` 四段文字把「运行命令时把这个路径作为项目传入」换成「spec-guard 命令会自动跟随到这个项目」，目录级那句「传入你自己的项目路径」换成「用 `link-project` 给本会话登记自己的项目」；解析逻辑与失效诊断不变。phase-guard 438 例全过，ShellCheck 无告警。
- [ ] Task 8：文档（C7）
- [ ] Task 9：公共文件实查（C8）
- [ ] Task 10：端到端跟随核对
- [ ] Task 11：合入集成分支并跑完整检查
- [ ] Checkpoint 2（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **变更**：`cost-report` 只看 token 与主会话轮次：去掉派活、重派、收回、交回后改与「派过／没派过」对照（决定 D17）；`--json` 删
> `dispatches`、`redispatches`、`reclaims`、`edits_after_handback`，`dispatches_unrecorded` 改名 `subagents_unrecorded`，新增 `subagents`。
> 派活规则退役：`setup-convention --dispatch`／`--no-dispatch` 被拒，`--replace` 会移除旧块里的派活规则段。
> 有项目指向时，除 `link-project` 外的所有命令自动跟随到被指向的项目，并输出「本次操作的是被指向的项目 `<路径>`」；指向失效时命令停下并说明（决定 D18）。
