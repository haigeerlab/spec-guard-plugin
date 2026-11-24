# 发布流程

发布的完成标准不是 Git 已推送，而是 marketplace 中安装的插件副本与已发布内容一致。

## PR 节奏

`main` 受分支保护，每个改动都要经 PR 与 CI，所以 PR 的切分决定了合并次数：

1. **一个模块一个 PR。** Spec、Plan、代码、文档与 CHANGELOG 在同一个 PR 里；需要发版时，版本号改动（下节第 1、2 条）
   放在这个 PR 的最后一个提交，不再另开发版 PR。合并后在合并提交上打 tag。
2. **一个需求跨多个模块时，一个需求发一次版**：只在最后一个模块的 PR 里改版本号。在此之前合并的模块让 `main` 的代码
   领先于已发布版本：Codex 钉在 tag 上不受影响，Claude 的 marketplace 源是 `main` 上的 `./plugins/spec-guard`，但按版本号
   判断是否更新，版本号不变时不会拉到中间状态。
3. **发版后只开一个收尾 PR**：发布证据、该模块最后一个检查点的勾与零星更正，在全部宿主核对完成后一次提交，不拆成几个。
   不要把它们留到下一个模块的 PR：那期间模块在 `main` 上仍显示进行中，`add-module` 也会因“做到一半”拒绝插入；
   也不要只留在本地，避免随 worktree 丢失。
4. **合并由用户在对话里决定**：agent 问“可以合并吗”，用户回“合并”后，agent 先看 PR 状态：
   必需检查 `CI required` 已通过（`mergeStateStatus` 为 `CLEAN`）时执行 `gh pr merge --squash`；还没跑完时执行
   `gh pr merge --auto --squash`，由 GitHub 等它通过后合并；agent 核实已合并（第 5 条）再告诉用户合并提交。下面一种情况除外。
   用户已于 2026-10-13 给出长期授权：发版后的收尾 PR 同时满足“只改
   `docs/releases/` 下的文件与该模块 `todo.md` 末尾的一行”和“CI 通过”时，维护它的 agent 可以自行合并；多改了任何别的
   文件就照常按上面问用户。
5. **PR 是否已合并由 agent 自己核对**：用户不必回来说“已合并”；agent 在继续之前单独一步确认 PR 的 `merged` 为真、
   `main` 指向它的合并提交，再做打 tag 等后续动作。核对不通过就停下来说明，不往下做。

## 发布前

1. 确认 Claude 与 Codex manifest 的版本一致，并把中英两份 README（`README.md`、`README.en.md`）里 Codex 安装命令
   的 `--ref` 改成新版本；`check-readme-sync.py` 会拦下不一致。
2. 按用户影响更新 `CHANGELOG.md`。
3. 若存在破坏性行为变更，先在 `docs/migrations/` 提供迁移指南。
4. 运行 `/bin/bash scripts/validate.sh` 与受改动面影响的聚焦测试。
5. 若修改 Codex manifest、hook 或技能，运行 `/bin/bash evals/codex-plugin-smoke.sh --selftest`。
6. 最终待发布提交还须在 macOS 用系统 `/bin/bash` 跑上述完整校验，以及
   `plugins/spec-guard/hooks/test-phase-guard.sh` 和
   `plugins/spec-guard/hooks/test-verify-artifacts.sh`。记录运行主机与结果；
   Ubuntu CI 不能替代 macOS Bash 3.2 验证，无法运行时标为未验证。

## 发布（合并之后）

合并之后的步骤由 `scripts/release.py` 按阶段执行（release-command）。每个子命令先打中文说明，最后一行是一行 JSON
（`schema: spec-guard.release/v1`，`status` 为 `ok`／`preview`／`refused`／`waiting-on-user`／`failed`，退出码依次 0、0、2、3、1）。
各步的事实存在本机记录 `~/.spec-guard/release/<版本>.json`（可用 `SPEC_GUARD_STATE_DIR` 改），后一步从这里读，不进仓库。

| 步 | 命令 | 做什么 | 谁授权 |
|---|---|---|---|
| 1 | `python3 -B scripts/release.py check --pr <号>` | 只读：PR 已合并、`origin/main` 等于合并提交、合并提交上的 CI 成功、两份 manifest 与 README `--ref` 是同一版本、tag 还不存在 | 无需（autopilot 可调用） |
| 2 | `python3 -B scripts/release.py prepare --version <版本>` | 只在本机：从合并提交 `git archive` 打包，写 `ARTIFACT-MANIFEST.json`，打包前与解压后各跑一次 `release-package.py validate`，确认没有 `._*`；从 CHANGELOG 截出 Release 说明 | 无需（autopilot 可调用） |
| 3 | `python3 -B scripts/release.py publish --version <版本> --confirm` | 打附注 tag 并推送、发 Release、回下载核对 sha256、确认是 latest。不带 `--confirm` 只打印将执行的命令 | 用户原话 |
| 4 | 通知 ecosystem-lead | Release 一发出就发通知（不等后面的步骤）；走信箱，不在命令里 | — |
| 5 | `python3 -B scripts/release.py install --version <版本> --confirm` | Claude：marketplace update 与 plugin update；Codex：先备份 `~/.codex/config.toml`，只替换 `[marketplaces.spec-guard-marketplace]` 一节里的 `ref` 那一行，再 upgrade。两侧都与发布包逐文件比对，报出安装时间。不带 `--confirm` 只预览 | 用户原话（升级会影响本机所有会话） |
| 6 | 用户在桌面上做 | 新开终端启动命令行 `codex`，在 `/hooks` 里批准 spec-guard 的 hook（Codex 0.164 起每次升级后都会失效）；⌘Q 退出 ChatGPT 再打开（已开的 Codex 会话不会换到新版） | 用户本人 |
| 7 | `python3 -B scripts/release.py smoke --version <版本>` | 跑真实 Codex smoke。hook 没重新批准时返回 `waiting-on-user`（退出码 3），做完第 6 步再跑；同时比较 ChatGPT 主进程启动时间与安装时间，报已重开／未重开／查不到 | 无需 |
| 8 | `python3 -B scripts/release.py evidence --version <版本> [--note <文字>]...` | 写 `docs/releases/v<版本>-{source,package,claude,codex}.json` 并逐份 `release-evidence.py validate`；smoke 没成功时 codex 那份如实写 `not-verified`。只写文件，不提交 | 无需 |
| 9 | 证据 PR | agent 提交、推送、开 PR；只改 `docs/releases/` 与该模块 todo 末尾一行且 CI 通过时，按上面「PR 节奏」第 4 条由 agent 合并 | — |

打包方法（命令里固定，写在这里备查）：`git archive --prefix=spec-guard-v<版本>/ <合并提交> .claude-plugin plugins/spec-guard`，加
`ARTIFACT-MANIFEST.json`（`schemaVersion` 1、`artifactKind` `spec-guard-plugin`、版本、三份清单路径），用 Python `tarfile` 打成
`spec-guard-v<版本>.tar.gz`（不调用 tar 命令：CI 的 GNU tar 不认 macOS 的 `--no-mac-metadata`，也不会带出 `._*`）。gzip 带时间戳，
同一提交重打出的包与已发布资产字节不同，比对时按解压后的文件树。

命令不做的事：通知别的会话、合并任何 PR、证据 PR 的提交与开 PR、⌘Q 与批准 hook、别的插件的发版。按 S101 Q14，spec-guard 的发布
档位最高只到 prepare：autopilot 不经用户只能调用 `check`、`prepare`。

## 发布后核对

项目有 `spec/proposals/` 时，再跑一次只读收尾扫描（本仓库每次发版都跑），把 `pending` 列给用户；每一条仍按
`/spec-guard:proposal-closeout` 单独预览、单独授权，扫描结果不构成授权：

```bash
python3 -B plugins/spec-guard/hooks/proposal_closeout.py scan --project . \
  --backend github --target haigeerlab/spec-guard-plugin
```

真实 smoke 的 `--expected-source` 必须与 `codex plugin list --json` 里的 `source.path` 精确一致（`smoke` 默认取 `install` 记下的值）：
本地 marketplace 通常是候选工作区，Git marketplace 则是 Codex 的缓存副本。不要猜测这两个路径相同。

如果开发分支与安装副本版本不同，先判定是“待发布候选”还是“本地分支落后于发布线”。不要仅为
消除版本差异改 manifest；应在独立的合并或发布任务中决定版本与变更来源。
