# Plan: release-command

<!-- spec-guard: review approved -->

Spec：[spec/release-command.md](../../spec/release-command.md)（2026-11-22 批准；Q16 A）。

## 架构决定

- **一个脚本、一个记录**：`scripts/release.py` 用 `argparse` 子命令；每次发版一份本机记录 `state_paths.state_dir("release")/<版本>.json`，每步读进来、补上本步的事实、原子写回。
  版本号从合并提交上的 `plugins/spec-guard/.claude-plugin/plugin.json` 读，`check` 记下合并提交，后面各步都以它为准（不读工作区）。
- **外部命令一处出口**：所有外部命令走一个 `run(args)`（列表、不经 shell、带超时），测试用 `PATH` 前置的假命令记录调用与返回预设输出。
  写远端或改宿主的命令集中在 `publish`、`install`，且都在 `--confirm` 分支里，预览只打印将执行的命令。
- **复用已有检查器**：包校验调 `scripts/release-package.py validate`，证据校验调 `scripts/release-evidence.py validate`，smoke 调 `evals/codex-plugin-smoke.sh`；不复制它们的判据。
- **Codex 配置只动一行**：按节解析 `[marketplaces.spec-guard-marketplace]`，节内恰好一行 `ref = "..."` 才替换；先把原文件复制到本机记录目录的 `backups/` 再原子写回。
- **路径安全**：临时产物只放在 `mktemp` 建的 `spec-guard-release-` 前缀目录；删除前核对前缀。家目录用法：Claude、Codex 的配置读写在 `scripts/` 下（家目录检查只管 `hooks/`），机器状态经 `state_paths`。

## 任务

编码任务（Task 1～3）交给 Codex（`/delegate:run --write`），我写派活说明、验收（读差异、自己重跑、变异）、提交。

- **Task 0**：提交本 Plan 与 todo。验证：`validate.sh --quick`。
- **Task 1**（Codex）：骨架（子命令、输出格式与退出码、本机记录）＋ `check` ＋ `prepare`，以及 `scripts/test_release.py` 对应用例（AC1、AC2、AC7 的这两步），在 `validate.sh` 登记；先写测试确认失败。
- **Task 2**（Codex）：`publish`、`install`（含 Codex 配置一行替换与备份）及用例（AC3、AC4）；先写测试确认失败。
- **Task 3**（Codex）：`smoke`、`evidence` 及用例（AC5、AC6）；先写测试确认失败。
- **Task 4**（我）：`docs/release-process.md` 改为调用命令，写进打包方法与各步之间谁做什么。

## 会改哪些文件

- 新增：`tasks/release-command/{plan,todo}.md`、`scripts/release.py`、`scripts/test_release.py`。
- 修改：`scripts/validate.sh`（登记测试）、`docs/release-process.md`。
- 不改：插件本身（`plugins/`）、接口、版本号、CHANGELOG、README。新增依赖、锁文件：无。

## 风险

- **假命令与真命令的输出形状不一致**：`gh api`、`claude plugin`、`codex plugin list --json` 的真实输出我在这几天都实际看过，派活时把真实样例给 Codex；CP1 再在本仓库用真命令跑只读的 `check` 与本机的 `prepare` 对照。
- **gzip 时间戳**：`prepare` 产物的 tar.gz 与已发布资产的字节不会相同，比对按解压后的文件树，不比整包 sha256。
- **真实写入在本模块里不跑**：`publish`、`install --confirm` 只在测试里对假命令跑；第一次真用在下一次发版，发版时如有出入按返工处理。

## 检查点

- Checkpoint 1（report）：完整检查与变异（去掉 `--confirm` 判断、Codex 配置多处 `ref` 时仍替换，各让回归变红）；本仓库实跑：`check --pr 472` 应为 `ok`（tag 已存在时为 `refused`，按实际写明），
  `prepare` 对 v0.91.3 打出的包与已发布资产解压后逐文件一致；`publish`、`install` 不带 `--confirm` 的预览输出贴进 todo。
- Checkpoint 2（gate）：最终验收；通过后推送并开 PR，合并由用户进行。本模块不改插件，不发版。

## 预先声明

- 公共路径：无
- 外部依赖：无
- 质量与工作区配置：无
- 补丁：无

## 未决问题

- 无。
