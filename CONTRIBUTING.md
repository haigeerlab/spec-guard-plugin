# 贡献指南

## 报 bug

在 [GitHub Issues](https://github.com/haigeerlab/spec-guard-plugin/issues) 选“Bug 报告”模板，写清楚：

1. **现象**：你做了什么、期望看到什么、实际看到什么。阶段提示不对时，贴出 agent 收到的原始提示，或在 Claude Code
   里运行 `/spec-guard:phase` 的输出。
2. **环境**：系统、宿主及版本（Claude Code 或 Codex）、spec-guard 版本、`python3 --version`。
3. **能复现的最小步骤**：能力图有问题时，附上 `/spec-guard:verify-artifacts` 的输出。

请不要贴密钥、令牌或私有仓库的内容。想提需求用“需求”模板。

## 改 README

`README.md`（中文，默认入口）和 `README.en.md`（英文）章节一一对应。**改 README 时，同一个 PR 里两份一起改**；
英文版里链到中文文档即可，只有 README 做双语。

## 提 PR 前

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

三个都绿才提。

**显式写 `/bin/bash`**：macOS 上 `bash` 可能是 Homebrew 的 5.x，而 3.2 才是
这个项目踩过坑的版本。**CI 不替你覆盖这一条** —— `.github/workflows/ci.yml` 只跑
`ubuntu-latest`（单元素矩阵，为的是不被 macOS runner 排队阻塞 PR），那上面的
`/bin/bash` 是 5.x。bash 3.2 的语法陷阱在 CI 里只由 `scripts/check-bash32.py`
这个静态判据覆盖，真正在 3.2 上跑过的只有你本机那一次。某一次 push 或 PR 是否真的
跑过 CI，看 Actions 标签页或 `gh pr checks`。本地跑 `scripts/validate.sh` 加上面两条
回归脚本（即预推送 hook 那一套）是唯一必须满足的门禁。

## 改 phase-guard.sh

这是核心文件，改动有三条硬约束（详见 [CLAUDE.md](CLAUDE.md)）：

1. 默认不生效 —— 未声明约定的仓库必须静默 `exit 0`
2. 探测失败就降级 —— **绝不能报假断链**
3. 只读 —— 它是探测器，不做任何写操作

**改了状态机逻辑必须加测试用例。** 测试文件在 `plugins/spec-guard/hooks/test-phase-guard.sh`。

## 加新的断链检测

新增一条前先问：

- [ ] 这个「断链」有没有合理的例外？（有的话不该报，或者要可配置）
- [ ] 探测依赖的东西不存在时会怎样？（必须降级，不能误报）
- [ ] 检测成本多少？（hook 在每次发言前跑，超过 1s 有体感）

**宁可漏报也不要误报。** 假断链会让人关掉整个机制。

## 加新命令

1. `plugins/spec-guard/commands/<name>.md`
2. 必须有 frontmatter（`validate.sh` 会检查）
3. 若是常用命令，在中英两份 README 的“常用命令”表里各补一行
4. 在 Codex 侧接一条路由，通常在 `plugins/spec-guard/skills/spec-guard-ops/SKILL.md`（Codex 只读 skill，不读 command）
5. 在 `docs/commands.md` 补上这条命令的说明，并在“命令对照”表里补一行（`scripts/check-command-table.py` 会检查）
6. `scripts/check-command-parity.py` 会校验 command 与 skill 路由是否对得上

## 发版

见 [docs/release-process.md](docs/release-process.md)。**版本号不升，使用者收不到更新。**

## 不接受的 PR

- fork 或 vendored 上游 agent-skills 的文件
- 给 phase-guard.sh 引入 `jq` 之类的硬依赖
- 让 hook 做写操作
- 在本仓库的 CLAUDE.md 里写激活字符串（会导致插件在自己仓库上激活）—— 本仓库
  是通过 `AGENTS.md` 的 Codex 约定块有意自激活的（见 [CLAUDE.md](CLAUDE.md)），
  这条规则针对的是 `CLAUDE.md` 本身
