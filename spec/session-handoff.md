# Spec: session-handoff

## Objective

fresh-session-hint 在模块边界建议开新会话，但开新会话时用户要自己写交接：仓库在哪、哪个分支或 worktree、HEAD、
阶段到哪、哪些发布证据没核对、有没有没合并的提交。这些全是仓库文件和 git 里的事实，却要让模型读完整个主会话上下文
再去查；而交接恰好发生在模块收尾、上下文最大的时候。

本模块提供一条只读命令，从文件与 git 拼出可以直接粘贴到新会话的交接文本，末尾留一行"下一步：____"由用户填写
（为什么做下一件事是用户的判断，不由命令推测）。在已启用约定的项目里，整条提示词恰好等于这条命令时，由
UserPromptSubmit hook 本地作答，不调用模型。阶段提示里的 Module boundary 行改为指向这条命令。

登记：2026-10-06 经 `/spec-guard:add-module` 插入能力图。

## Assumptions

用户已于 2026-10-06 确认：

1. 新增只读命令：Claude 斜杠命令 `/spec-guard:handoff`，Codex 走 `spec-guard-ops` 的 `handoff` 操作。输出交接文本，含：
   仓库路径、分支与 worktree、HEAD、阶段与模块计数、最新发布证据中 `not-verified` 的项、当前分支未合并提交，
   末尾 `下一步：____`。
2. 只拼事实，不推测意图，不读会话记录内容。
3. Module boundary 行改为指向这条命令；阶段判定不变。
4. 不写文件，只输出到终端供复制。
5. 状态栏显示阶段不在本模块范围。
6. **不做自然语言话术拦截。** 依据（2026-10-06 调研）：本机 3096 条历史提示词中可机械回答的状态问句约 20 条（0.6%），
   而"继续"一类约 25%；状态问句常与"继续"写在一起，按语义拦截必然误吞；可靠拦截只能匹配固定说法，那就是一条命令。
7. **只本地作答这一条命令。** hook 仅在整条提示词（去掉首尾空白后）恰好等于触发词时拦截；带参数或任何其他文字都放行。
   实测（`claude -p`，Claude Code 2.1.289）：hook 能看到原样的斜杠命令并在展开前拦下，`total_cost_usd` 为 0、`num_turns` 为 0；
   Codex 0.160.0 `codex exec` 实测 `decision:"block"` 后状态为 `Blocked`、没有模型调用。
8. **Claude 与 Codex 分别输出。** Claude：`{"decision":"block","reason":<文本>,"hookSpecificOutput":{"hookEventName":
   "UserPromptSubmit","suppressOriginalPrompt":true}}`；Codex：只有 `decision` 与 `reason`。实测 Codex 输出里多一个
   `suppressOriginalPrompt` 时 hook 被判为 `Failed`，提示词照常送给模型。
9. **拦截失败即放行。** 拼装出错、超时或任何异常时，不拦截，照常输出阶段注入（原有行为），让命令按普通斜杠命令 / skill
   由模型执行同一脚本。未启用约定的项目里 hook 仍静默退出，命令同样走普通路径。
10. **未合并提交只看当前分支**，判据与 done-unmerged-hint 相同（`unmerged_commits`：本地已知的远端默认分支，不联网）；
    不列其他本地分支。
11. **not-verified 只读最新一版。** 取 `docs/releases/` 下版本号最大的一组 `v<版本>-*.json`，列出 `status` 为
    `not-verified` 的 `subject`；目录不存在或没有这类文件时写"无发布证据"，不报错。
12. **位置以会话所在目录为准。** 本会话（桌面版、worktree `hello-226c46`）里阶段提示报告的是 `main` 与主仓路径，与实际
    worktree 不符。phase-guard 优先用 `CLAUDE_PROJECT_DIR`；推测桌面版 worktree 会话中它指向原项目目录。处理：hook 输入带
    `cwd` 时用 `git -C <cwd> rev-parse --show-toplevel` 作为项目根，取不到再退回现有逻辑。

    实测记录（2026-10-06，Task 1）：本会话记录的 `cwd` 字段全部是该 worktree（或其子目录），而同一会话每轮注入的阶段提示
    报告主仓路径与 `main`，即 phase-guard 的根目录解析落在主仓。worktree 内临时 `.claude/settings.local.json` 注册的探针
    hook 一轮未执行；在主仓放同样探针的操作被宿主权限检查拒绝，未执行。因此 hook 输入 `cwd` 的实际值与
    `CLAUDE_PROJECT_DIR` 的取值**未直接实测**。用户确认按此推进：改动只在输入 `cwd` 解析出的 git 根与现有根不同时生效，
    `cwd` 若同样指向主仓则行为不变（无害）；是否真正修正由 Checkpoint 2 的安装版桌面会话核对。

## Contract

- 新增 `hooks/session_handoff.py`（只依赖标准库，复用 `module_stage` 的阶段计数、`unmerged_commits`、`session_context.location_line`）：
  - `handoff_text(root) -> str`：按第 1、10、11 条拼文本；某一项取不到时该项写"未知"，不中断。
  - `is_trigger(prompt) -> bool`：去首尾空白后恰好等于 `/spec-guard:handoff` 或 `spec-guard handoff`（Codex 触发词，见 Open questions）。
  - 命令行入口 `python3 session_handoff.py <root>`：打印交接文本，退出 0。
- `phase-guard.sh`：已有的标准输入读取处顺带取 `prompt`；激活后、`is_trigger` 为真且 `handoff_text` 成功时，按第 8 条输出拦截 JSON
  （有 `CLAUDE_PROJECT_DIR` 视为 Claude，否则视为 Codex），不再输出阶段注入；其他情况行为逐字不变。
- `module_stage.MODULE_BOUNDARY` 改为：`- Module boundary: start the next piece of work in a new session; run /spec-guard:handoff
  (Codex: spec-guard handoff) for paste-ready handoff text. This stage summary carries over, the conversation does not need to.`
- 新增 `commands/handoff.md` 与 `spec-guard-ops` 的 `handoff` 操作：运行 `session_handoff.py` 并原样输出（hook 未拦截时的退路）。
- 输出仍是宿主接受的 JSON；不使用 `cmd | grep -q`；只依赖 bash、git、python3。

交接文本格式（中文标签，与用户手写的交接一致）：

```text
<仓库名> 仓库（<worktree 根目录>，分支 <分支>|分离 HEAD，HEAD <短 sha>）。
## 现状
阶段 <STAGE>；模块 <总数>，Spec <n>，Plan <n>，进行中 <n>，完成 <n>；当前模块 <id|无>。
未合并提交：<n> 个（相对 <ref>）| 无（相对 <ref>）| 未知（没有本地已知的远端默认分支）
发布证据 v<版本> 中 not-verified：<subject、…> | 无      ← 没有发布证据文件时整行为“发布证据：无”
## 下一步
下一步：____
```

IDLE、MAP_ONLY、MAP_INVALID 的阶段行分别为"阶段 IDLE；没有能力图。""阶段 MAP_ONLY；有能力图，没有模块 Spec。"
"阶段 MAP_INVALID；能力图无法解析，运行 verify-artifacts 查看。"；不在 git 仓库里时分支、HEAD 与未合并提交写"未知"。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_session_handoff.py
/bin/bash scripts/validate.sh
```

## Testing strategy

- 先实测第 12 条：在桌面版 worktree 会话里记录 hook 收到的 `CLAUDE_PROJECT_DIR` 与输入 `cwd`（临时 hook 写到 scratchpad，不改用户配置）；
  结论写进本 Spec 再动 phase-guard。
- 先写测试并确认在当前代码上失败，再改实现。
- `test_session_handoff.py`（临时 git 夹具）：各阶段文本；分离 HEAD；linked worktree 报告自己的根目录；有 / 无 / 取不到未合并提交；
  发布证据：取最大版本、多文件合并、无 not-verified、目录缺失、坏 JSON；`is_trigger` 的正例（含首尾空白）与反例
  （带参数、"继续 /spec-guard:handoff"、大小写不同、空串）。
- `test-phase-guard.sh`：触发词 → Claude 环境输出带 `suppressOriginalPrompt` 的拦截 JSON，Codex 环境输出不含该字段；
  非触发词、无标准输入、非 JSON 输入、拼装脚本失败 → 输出与现在逐字相同（Module boundary 行除外）；未启用项目 → 静默；只读。
- Checkpoint：安装版在真实宿主各跑一次——Claude CLI、桌面版 Code 标签页、Codex TUI——记录拦截后用户实际看到什么；
  看不到 `reason` 的宿主如实记为 `not-verified` 或 `host-verified` 并说明现象。

## Boundaries

- Always：先红后绿；只读；拦截失败即放行；交接文本只含事实。
- Ask first：增加第二个触发词或任何自然语言匹配；改变阶段判定；写任何文件。
- Never：读取或输出会话记录内容；在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号。

## Success criteria

- 在已启用项目里输入 `/spec-guard:handoff`，Claude Code 不调用模型即显示交接文本（`claude -p` 下费用为 0）；Codex 的实际表现有记录。
- 未拦截时，同一命令经模型执行得到相同文本。
- Module boundary 行指向该命令；其余阶段输出与判定不变。
- 第 12 条有实测结论；成立时阶段提示在 worktree 会话里报告正确的分支与目录。

## Open questions

- Codex 触发词：Codex TUI 对未知的 `/` 命令可能在客户端就报错、到不了 hook，所以暂定纯文本 `spec-guard handoff`；
  需在 Checkpoint 实测 Codex 的 skill 调用方式后定稿。
- 桌面版 Code 标签页里拦截消息带 "UserPromptSubmit operation blocked by hook:" 前缀，若显示为错误样式、体验不可接受，
  是否退回为只提供普通命令（第 7 条取消）——Checkpoint 后由用户决定。
