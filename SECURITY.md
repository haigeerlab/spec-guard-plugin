# 安全策略

## 支持的版本

只修复最新发布版（见 [Releases](https://github.com/haigeerlab/spec-guard-plugin/releases)）。修复随下一个版本发布，
不回补旧版本；请先升级到最新版确认问题仍在。

## 怎么报告

**不要公开提 issue。** 请用 GitHub 的私密漏洞报告：打开仓库的
[Security](https://github.com/haigeerlab/spec-guard-plugin/security) 页，点 “Report a vulnerability”。
报告只有你和维护者看得到。

请写明：

- 版本号（`plugin.json` 里的 `version`）与宿主（Claude Code 或 Codex，以及版本）；
- 复现步骤，最好是一个最小项目；
- 影响：能读到什么、写到哪里、在什么条件下发生。

## 范围

属于本仓库的：

- 每轮自动运行的钩子（`plugins/spec-guard/hooks/`）；
- 斜杠命令、skill 与它们调用的脚本；
- 写入消费者项目的约定块模板。

例如：钩子把凭据或不可信的远端文本原样放进 agent 上下文、命令在未确认时写了文件或远端、路径处理越出项目目录。

不属于本仓库的，请到对应仓库报告：上游 [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)、
会话协作插件 agent-relay、Claude Code 与 Codex 宿主本身。

## 回应

本项目由一人维护，不承诺固定的回应时限。确认是漏洞后会在私密报告里沟通修复方式，修复发布后在 CHANGELOG 中说明。
