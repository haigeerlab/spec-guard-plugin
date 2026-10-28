# Spec: codex-hook-reapproval-docs

<!-- spec-guard: review approved 8996749a1748 -->

## 目标

补上 Codex 0.164 带来的文档缺口：从这一版起，Codex 把 hook 的批准绑定到插件内容（openai/codex#54619，
`~/.codex/config.toml` 的 `[hooks.state]` 记 `trusted_content_hash`）。插件内容一变，原来的批准就失效，
**每次升级 spec-guard 都要重新批准它的 hook**，否则 hook 被跳过、不报错，阶段提示不再出现。

现在的文档还按旧行为写（2026-10-28 核对）：

1. `README.md` / `README.en.md` 安装表 Codex 一栏写「开新会话即可」；「更新」一节只说「新增的 `SessionStart` hook 要信任一次」。
2. `docs/troubleshooting.md` 第 41 行说「原有的 `UserPromptSubmit` 一项不受影响」，在 0.164 上已经不对；「阶段提示没有出现」的原因列表
   没有 Codex 批准失效这一条（第 19 行只写了 Claude Code）。
3. `docs/release-process.md`「发布」第 5 步只写「在 `/hooks` 查看 `UserPromptSubmit`」；`docs/maintainer-workflow.md` 第 120～130 行
   没说 smoke 返回 2 时先查批准。
4. `evals/codex-plugin-smoke.sh` 返回 2 时只打印「未观察到宿主 hook 事件或匹配的会话注入」，不提示可能是批准失效。
   v0.85.1 发版时 smoke 连续两次返回 2，查了一轮才定位到这个原因。

给谁用：在 Codex 里使用 spec-guard 的用户（升级后阶段提示消失）、发版的维护者（smoke 返回 2）。

登记：需求来自用户本人（2026-10-28，确认需求总结「说完了」），不需要回告。

## 边界

**总是做**

- 批准步骤按本机实测写：命令行版 `codex` 启动时提示「Hooks need review」（N 个 hook 新增或改变），进入 `/hooks` 逐个批准；
  spec-guard 的 hook 是 `hooks/hooks.json` 里的 3 个（`UserPromptSubmit` 1 个、`SessionStart` 2 个）。
- 说明批准失效的表现：hook 被跳过、不报错；`codex exec` 同样静默跳过。
- 只改文档时按快档提交；改了 `codex-plugin-smoke.sh` 就跑 `--selftest`、`validate.sh` 与 ShellCheck。

**先问**

- 发现需要改插件包（hook、技能、命令）才能说清时。

**不做**

- 不改插件包，不改版本号，不发版（插件行为没变；文档随 `main` 生效，下次发版时 CHANGELOG 再提）。
- 不在插件里加检测（例如 hook 自己发现没被批准），不改 smoke 的退出码与判决逻辑，不加绕过批准的开关或说明。
- 不替用户批准 hook。

## 要你确认的假设

1. **桌面版的说法写成「可能不弹提示」**：维护者文档第 120 行已写「Codex 桌面版不弹出钩子信任提示」，但这次没有在桌面版上重新实测。
   面向用户的 README 与故障排查写成「桌面版可能不提示，没有阶段提示时到命令行版 `codex` 的 `/hooks` 里批准」；维护者文档那句保留原样。
2. **只写 0.164 起的行为，标明版本**：写「Codex 0.164 起」，旧版 Codex 的说法（只有新增的 hook 要信任）保留一句，不删。
3. **顺带提一句其他插件**：`codex plugin marketplace upgrade` 会一起更新所有 marketplace，其他插件的 hook 同样会出现在待批准列表里；
   只提这一句，不展开其他插件的做法。
4. 分支 `claude/codex-hook-reapproval-docs`，从 `main`（`00e497e0`，v0.85.1 证据合并后）开出；一个 PR。

## 验收标准

- AC1：README 中英安装表的 Codex 一栏与「更新」一节写明：Codex 0.164 起每次安装或升级 spec-guard 后，在命令行版 `codex` 的 `/hooks`
  批准 spec-guard 的 3 个 hook，再开新会话；桌面版可能不提示；已开着的会话要重开。`check-readme-sync.py` 通过。
- AC2：`docs/troubleshooting.md` 第 41 行改正（0.164 起原有的 `UserPromptSubmit` 也要重新批准）；「阶段提示没有出现」原因列表加 Codex 一条
  （0.164 起升级后批准失效），排查表对应一行补上。
- AC3：`docs/release-process.md`「发布」第 5 步写成「在命令行版 `codex` 的 `/hooks` 批准 spec-guard 的 3 个 hook，再跑 smoke」；
  `docs/maintainer-workflow.md` 写明 smoke 返回 2 时先查批准（`[hooks.state]` 或启动 `codex` 看是否提示「Hooks need review」）。
- AC4：`codex-plugin-smoke.sh` 返回 2（未观察到注入）时多打印一行提示：Codex 0.164 起升级后要在命令行版 `codex` 的 `/hooks` 重新批准；
  退出码与判决不变，`--selftest` 通过；`validate.sh` 通过；读仓库文档的回归（`DOC_REGRESSIONS`）通过。

## 未决问题

- **Q1：smoke 的提示行什么时候打印？**
  - A（推荐）：返回 2（未观察到注入）时总是多打印这一行。简单，不依赖 `codex --version` 的输出格式；旧版 Codex 上多一行无害。
  - B：先跑 `codex --version`，只在 0.164 或更新时打印。多一次调用和一段版本解析，解析失败还要再定怎么办。
- **Q2：分支从哪开？**
  - A（推荐）：从 `main`（`00e497e0`）开，已开好 `claude/codex-hook-reapproval-docs`。
  - B：等下次有插件改动时一起做。

**已定（2026-10-28，用户）：Q1 A；Q2 A。**

## 文档建议

本模块就是文档改动：README 中英、`docs/troubleshooting.md`、`docs/release-process.md`、`docs/maintainer-workflow.md`。
CHANGELOG 不在本模块写（不发版），下次发版时在「文档」一节带上。项目没有文档基线。

## 变更记录
