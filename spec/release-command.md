# Spec: release-command

<!-- spec-guard: review approved 27da24eead6b -->

## Objective

把 spec-guard 自己的发版步骤固定成一个按阶段调用的命令 `scripts/release.py`，取代现在散在 `docs/release-process.md` 与会话记忆里、每次靠 agent 手拼的
一长串命令。agent 照着调用；autopilot 的「插件」模板也调用它（模板的第 3、4、6、7、9 步）。这几天连发 0.91.0～0.91.3 时手拼出过的错
（zsh 通配符、交互式 `cp`、`release-evidence.py` 少写子命令、Codex ref 要精确替换、ChatGPT 是否重开要比启动时间）在命令里一次固定。

给谁用：发版的 agent；autopilot 的「插件」模板（只读与备包两步）；用户（看结果、给授权）。

对外接口与用法草案一致吗：单模块需求，没有用法草案。

登记：S101 r3 第 ② 条（用户 11-21「按推荐批准」，总账 1d5fd45），ecosystem-lead #21883 转来；模板步骤见总账 `research/2026-11-21-合并之后的接管梳理.md` 第一节。
需求确认：用户 2026-11-22「确认插入；Q16 A」。账本 7AX305A。

## Assumptions

1. **形态**：仓库里的维护者脚本 `scripts/release.py`（只发 spec-guard 自己，不是给使用者项目的插件命令），子命令 `check`、`prepare`、`publish`、
   `install`、`smoke`、`evidence`。只依赖 Python 标准库与 `git`、`gh`、`claude`、`codex`、`tar` 这些已有命令，不用 shell 拼接（`subprocess` 传列表）。
2. **输出**：每个子命令在标准输出最后一行打一行 JSON `{"schema": "spec-guard.release/v1", "step", "version", "status", ...事实}`，之前是给人看的中文
   说明。`status` 取 `ok`、`preview`、`refused`、`waiting-on-user`、`failed`；退出码依次 0、0、2、3、1。
3. **一次发版的记录**：各步的事实（合并提交、包的路径与 sha256、Release 地址、两侧安装时间、smoke 结果）写进一份本机记录，供后面的步骤与 `evidence`
   读：`state_paths.state_dir("release") / "<版本>.json"`（`~/.spec-guard/release/`，可用 `SPEC_GUARD_STATE_DIR` 改）。不进仓库。
4. **各步做什么**：
   - `check --pr <号>`（只读）：PR 已合并（`gh api` 的 `merged` 为真）、`origin/main` 等于合并提交、合并提交上的 CI 结论为成功、两份 `plugin.json`
     与 README 中英 `--ref` 是同一版本、本地与远端都还没有这个 tag。任一条不满足就 `refused` 并写明哪一条。
   - `prepare`（只在本机）：从合并提交 `git archive` 打包（`.claude-plugin` 与 `plugins/spec-guard`），写 `ARTIFACT-MANIFEST.json`，打包前与解压后各跑一次
     `release-package.py validate`，确认没有 `._*`；从 CHANGELOG 截出这一版的 Release 说明。产物放在 `mktemp` 建的固定前缀目录里。
   - `publish`：预览列出将执行的远端写入；`--confirm` 才打附注 tag 并推送、`gh release create --verify-tag`、回下载核对 sha256、确认 `releases/latest` 是它。
   - `install`：预览列出两侧要做的事；`--confirm` 才执行。Claude：`claude plugin marketplace update` 与 `claude plugin update`，读 `installed_plugins.json`
     的版本、提交与更新时间。Codex：先把 `~/.codex/config.toml` 备份到本机记录目录，再只替换 `[marketplaces.spec-guard-marketplace]` 一节里 `ref` 那一行
     （恰好一处，否则 `refused`、不改文件），`codex plugin marketplace upgrade`，读 `codex plugin list --json`。两侧安装目录都与包逐文件比对（忽略 Claude 的
     `.in_use`），报出两侧安装时间。
   - `smoke`：跑 `evals/codex-plugin-smoke.sh --plugin-id … --expected-source …`。退出 0 为 `ok`；退出 2 且输出写着没观察到 hook 事件时为 `waiting-on-user`，
     说明要用户在新开的命令行 `codex` 里用 `/hooks` 重新批准；其余为 `failed`。同时读 ChatGPT 桌面版主进程的启动时间，与 Codex 安装时间比，报「已重开 /
     未重开 / 查不到」。
   - `evidence`：按本机记录写 `docs/releases/v<版本>-{source,package,claude,codex}.json`，格式与现有证据相同；smoke 没成功时 codex 那份写 `not-verified`
     并写明原因；`--note <文字>` 可追加到 source 的结果里（本模块改了什么、分支上的检查）。写完逐份跑 `release-evidence.py validate`。只写文件，不提交。
5. **授权底线**：`publish`、`install` 不带 `--confirm` 只预览、不碰远端或本机宿主。按 S101 Q14，spec-guard 的发布档位最高只到 prepare：autopilot 不经用户只能调用
   `check`、`prepare`；`publish`、`install` 照旧凭用户原话授权，由调用方负责，命令不判断授权来源。
6. **不归本命令**：通知 ecosystem-lead 与回告别的会话；合并任何 PR；证据 PR 的提交、推送与开 PR；⌘Q 重开 ChatGPT 与批准 hook（桌面动作）；别的插件的发版。
7. **文档**：`docs/release-process.md` 的步骤改为调用这些子命令（保留为什么这样做的说明），把记忆里的打包方法写进仓库。插件行为不变，接口版本不变；版本号随下次发版改。

## Contract

- **C1** `scripts/release.py`：六个子命令（假设 1～5），共用本机记录（假设 3）与输出格式（假设 2）。
- **C2** `scripts/test_release.py`：用临时 git 仓库与 `PATH` 里的假 `gh`／`claude`／`codex` 跑各子命令，不碰网络与真实宿主；在 `scripts/validate.sh` 登记。
- **C3** 文档：`docs/release-process.md` 改为调用命令。

## Acceptance criteria

- **AC1** `check`：已合并且 main、CI、版本、tag 都对 → `ok`；未合并、main 不等于合并提交、CI 不是成功、两份 manifest 或 README `--ref` 不一致、tag 已存在 → 各自 `refused` 并写明原因。
- **AC2** `prepare`：包里只有 `.claude-plugin` 与 `plugins/spec-guard` 加 `ARTIFACT-MANIFEST.json`，打包前后都过 `validate`，没有 `._*`，Release 说明等于 CHANGELOG 那一节；不跑任何远端写入。
- **AC3** `publish`、`install`：不带 `--confirm` 不调用任何写远端或改宿主的命令（测试里假命令记录调用，断言为空）；带 `--confirm` 时按假设 4 的顺序调用，回下载 sha256 不同则 `failed`。
- **AC4** Codex 配置：只改那一行 `ref`，其余字节不变，改前有备份；那一节没有或有多处 `ref` → `refused`、文件不变。
- **AC5** `smoke`：退出 0 → `ok`；退出 2 且是 hook 未批准 → `waiting-on-user`（退出码 3）；其余 → `failed`；ChatGPT 启动时间早于安装时间报「未重开」。
- **AC6** `evidence`：写出的四份都过 `release-evidence.py validate`；smoke 未成功时 codex 那份为 `not-verified` 且没有 `observedAt`、`evidence`。
- **AC7** 每个子命令最后一行是合法 JSON，`status` 与退出码对应（假设 2）；`validate.sh`、phase-guard、verify-artifacts 全绿。

## Boundaries

- **会做**：C1～C3 及回归。
- **先问再做**：让 `publish`、`install` 在没有 `--confirm` 时执行；改 Codex 配置里 `ref` 以外的内容；让命令自己判断用户授权。
- **不做**：假设 6 列出的事；改插件本身的行为或接口版本。

## 并行边界

- 独占：`spec/release-command.md`、`tasks/release-command/`、`scripts/release.py`、`scripts/test_release.py`、`scripts/validate.sh`、`docs/release-process.md`
- 公共：无

## 文档建议

`docs/release-process.md` 改为「调用 `scripts/release.py` 的哪一步、各步之间谁做什么（用户授权、⌘Q、批 hook、合并证据 PR）」；README 不变（维护者流程不在 README）。CHANGELOG 在发版时写。项目没有文档基线。
