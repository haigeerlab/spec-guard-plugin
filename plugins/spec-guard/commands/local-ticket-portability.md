---
description: 只读核验或离线归档 Local 事项，明确指定目标后恢复或逐项交接到 GitHub/GitLab
---

加载本插件的 `local-ticket-portability` skill，按用户请求执行 `inventory`、`journal-candidates`、
`journal-bind-preview`、`journal-bind`、`archive`、
`verify`、`restore`、`handoff-preview` 或 `handoff-publish`。普通事项创建、讨论和关闭
仍用 `/spec-guard:ticket`；不要因查看账本而自动归档、同步或迁移。

真实恢复须展示归档与空目标路径；托管写入须先展示预览文件中的精确主机、项目、可见性、
事项正文、历史评论和附件处理，再取得针对这次目标与内容的明确授权。`--confirm`
只是命令防误触参数，不代替人的授权。未经授权只做只读检查或预览。
日志重绑定须先展示候选、来源证据、预览中的键核对结果和仓库身份限制，再取得
针对该候选的明确确认；不可把 `journal-candidates` 的单个候选当作自动归属证明。
绑定只在本机用户级目录写指针，不修改旧日志或远端；Git worktree 修复另行处理。
