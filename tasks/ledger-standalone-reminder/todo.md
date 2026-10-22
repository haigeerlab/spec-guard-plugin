# Todo: ledger-standalone-reminder

- [x] Task 0：同步批准标记 — 按开工通知（C194）单独 `module-crew sync` 到集成分支 42d30ca（HEAD f952cee3），Spec、Plan 取集成分支带批准标记的版本；validate、phase-guard（488 例）、verify-artifacts（74 例）全过。
- [x] Task 1：只有账本时的三处提醒（改动 1） — 回归先写：第 19 段「未激活的目录有账本文件时 fresh 也静默」翻成反向；新增第 23 段 15 例（fresh／compact／转来消息中英、普通轮与正文中段提及静默、缺 python3 时 fresh 仍出英文而另两处静默、宿主 ROOT 在别处而 cwd 在只有账本的仓库子目录、无账本无信号三事件静默；只有账本的输出都断言不含状态码），改前第 19、23 段红。实现：`phase-guard.sh` 加 `has_ledger`；`inactive_before_python` 认账本并设 `PRE_LEDGER`，只有账本的 UserPromptSubmit 在 bash 里看 `"prompt"` 是否以 `<cross-session-message ` 开头，不是就在启动 python3 前退出；`LINKED` 处分出 `LEDGER_ONLY`；`receipt_hint` 定义前移到 `fresh_out` 之后（调用处与 `ZH` 不动）。phase-guard 502 例全过；用记录调用的假 python3 实测：普通轮 0 次调用，转来消息那轮出记账提醒。新段断言改用 here-string 而不经管道（经管道时用例数不计入，`fail` 也只退出管道子 shell）。本机没有 ShellCheck（不全局安装），留给 CI 的 ShellCheck。
- [ ] Checkpoint 1（report）：变异核对
- [ ] Task 2：宿主移除命令实测（AC6 的证据）
- [ ] Task 3：说明文字（改动 2）
- [ ] Task 4：真实宿主核对（AC9）
- [ ] Task 5：合入集成分支并跑完整检查
- [ ] 最终验收（gate）：模块最终验收；不含推送与开 PR，合并由模块协调按用户原话做

## 拟写的更新说明（由模块协调整批写入 CHANGELOG）

> **修复**：本地事项账本的读回提醒不再依赖多模块约定（决定 D11）。项目根有 `.epiq/project.json`、没有启用约定时，会话开始与清空后出读回提醒，
> 压缩后出账本核对提醒，别的会话转来消息那一轮出记账提醒；其余轮次静默。启用了约定的项目不变。
> **文档**：README 与本地事项账本说明补上卸载步骤：接入过宿主的，卸插件前移除账本的 Claude MCP 条目与 ask 规则、Codex MCP 表；账本数据保留（审查 F8）。

## 对使用者的影响

- 只用本地事项账本、没启用多模块约定（或 teardown 掉了约定）的项目，会话开始、清空、压缩后会看到账本提醒，别的会话来消息时会看到记账提醒；平时每轮没有注入。
- 接入过宿主的账本用户，卸载 spec-guard 前多一步：按 README 移除账本的宿主配置；账本数据不用删。
