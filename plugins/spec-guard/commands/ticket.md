---
description: 用自然语言查看、创建、讨论或关闭当前项目的本地事项
---

把用户在命令后的内容当作日常本地事项请求，加载本插件的 `ticket` skill 并执行。用户只说
`/spec-guard:ticket` 时，列出当前仓库的未关闭事项，简要显示短编号、标题和当前状态；若账本尚未
启用，仅做只读诊断并给出一条启用步骤。

例如：

- `/spec-guard:ticket 记个 bug：测试环境的接口响应异常`
- `/spec-guard:ticket 查看 <事项短编号> 并补充我的排查结果`
- `/spec-guard:ticket 创建事项并告诉另一位 Agent 帮忙复查`

项目初始化、安装或宿主配置仍交给 `local-ticket-ledger-ops`，不因执行本命令而自动触发。
