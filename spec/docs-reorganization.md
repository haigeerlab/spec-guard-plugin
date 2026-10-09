# Spec: docs-reorganization

## Objective

仓库文档是随模块一路加出来的：README 139 行里混着安装、上手、约定块全文、Agent Skills 集成约定与维护入口；`docs/`
下有 30 多份文件，研究笔记、验收记录、早期报告和现行说明放在一起，第一次接触的人分不清哪份是给自己看的。本模块把文档
按读者重新分组，README 只回答“这是什么、怎么装、怎么用、出问题看哪”，其余内容链接过去。来源：第二轮联调按用户意见
整理的需求，用户 2026-10-09 确认写入能力图并就两处冲突选 A，另有一处变更“README 提供中文和英文两种，默认中文”。

读者：第一次接触本插件的开发者（README、使用者文档）；想参与开发的人（架构、贡献）；本仓库维护者（维护与发版文档）。

## Assumptions

用户于 2026-10-09 确认：

1. README 写给第一次接触的开发者；维护和发版内容放 `docs/`，README 只链接过去。
2. README 做两版：`README.md` 中文、默认入口；`README.en.md` 英文，章节与中文版一一对应。两份顶部放语言切换行
   （`简体中文 | [English](README.en.md)`，英文版对应写法）。英文版里链到中文文档即可，只有 README 做双语。
   维护规则写进 `CONTRIBUTING.md` 与 `docs/maintainer-workflow.md`：改 README 时同一个 PR 里两份一起改。不加中英
   同步检查器。
3. 删除就是从仓库删掉，git 历史里还在，不另建归档目录。`spec/`、`tasks/`（含 `spec/history/`）里指向被删文档的链接
   不改：它们是过去模块的记录，链接内容可在 git 历史中找到（冲突 1 选 A）。同理不改的还有已发布的证据
   `docs/releases/0.9.0-local-candidate.json`：它有 2 处指向 `docs/research/0.9.0-local-candidate/` 下的证据文件
   （`regressions.json`、`package-results.json`），删除后只能在 git 历史中查看（第二轮联调审查 #275 时指出）。
4. 不在范围内：`spec/`、`tasks/`；`plugins/` 下的 commands、skills、references（只核对 README 与它们说法一致，不改它们）。
5. 被检查器或插件引用的文档保留：`docs/lenses.md`、`docs/decisions/`、`docs/retirements/`、`docs/releases/`、
   `docs/collaboration-interface.md`、`docs/baselines/collaboration-pre-split.md`（`scripts/collaboration-owned.txt`
   引用）、`docs/design.md`。
6. `docs/design.md` 文件名不变，内容用中文重写为架构说明（部件、数据流、两个宿主的差异、不变量）；插件包里引用它的
   `state_paths.py` 与 `test-retire-legacy-tracker-bridge.sh` 不动（冲突 2 选 A）。
7. 删除（删前再核一遍引用）：`docs/research/` 整个目录、`docs/acceptance/`、`docs/collaboration-split-brief.md`、
   `docs/collaboration-split-summary.md`（有用部分先并入 `docs/migrations/2026-10-07-collaboration-split.md`）、
   `docs/migration-strict-serial.md`（随 v0.12.0 的迁移，现行用户已不会遇到）、`docs/reports/` 里 2026-09-12 与
   09-13 的 4 份早期报告。`docs/reports/README.md` 里指向被删文件的条目同步删去。
8. 旧迁移说明（v0.15、v0.16.2、proposal v2、仓库迁移）从 README 撤掉链接，文件保留在 `docs/migrations/`。
9. 不改插件发布包与版本号；不加长期的链接检查器，所有链接用一次性脚本核对一遍。
10. PR 分三批，按顺序：① 删除与整理；② README 双语；③ 新建文档。

## Requirements

1. **使用者文档**：`README.md` / `README.en.md`；`docs/workflow.md`；新建 `docs/commands.md`（全部命令、参数和输出，
   从 workflow 的“命令对照”一节拆出）；`docs/concepts.md`；`docs/optional-features.md`；新建 `docs/troubleshooting.md`
   （至少覆盖阶段提示不出现、MAP_INVALID、python3 故障、Codex 不加载插件）；`docs/migrations/`；`CHANGELOG.md`。
2. **开发者文档**：`docs/design.md` 中文架构说明；`CONTRIBUTING.md` 补上怎么报 bug；核对并按需更新已有的
   `.github/ISSUE_TEMPLATE/bug.yml`（仓库已有 bug 模板，不另建 `bug_report.md`）；`docs/decisions/`。
3. **维护者文档**：`docs/maintainer-workflow.md`、`docs/release-process.md`、`docs/lenses.md`、`docs/upstream-analysis.md`
   （导航里标明给维护者看）、`CLAUDE.md`、`AGENTS.md`。
4. **README 大纲**（两版一致）：项目定位 → 使用场景与边界 → 核心概念（一屏，链到 concepts）→ 前置条件
   （agent-skills 插件、bash、git、python3 3.9+，两个宿主）→ 快速开始（两个宿主分栏，再给一条最短路径）→ 常用命令
   （约 6 个，其余链到 commands.md）→ 运行效果与自检 → 更新与卸载 → 故障排查（3～5 条，其余链到 troubleshooting.md）
   → 架构与文档导航（使用者与开发者分两组，说明 `spec/`、`tasks/` 是本仓库自用的）→ 开发、贡献与反馈 → 许可。
5. **约定块**：从 README 移到新建的 `docs/convention-block.md`；`scripts/check-readme-sync.py` 改为核对这份文件里的
   SYNC 区与模板逐字节一致，`--ref` 版本检查同时覆盖 `README.md` 与 `README.en.md`；`scripts/test-checkers.sh` 里它的
   正反用例同步改，含“英文 README 的 `--ref` 落后于清单版本 → 报错”。
6. **核实**：两份 README 与 `docs/commands.md` 里的命令和参数逐条对照 `plugins/spec-guard/commands/*.md` 的
   frontmatter 与正文核实；所有站内链接用一次性脚本核对一遍（不入库）；`validate.sh` 全部通过。
7. 第一个提交顺带勾掉 `local-check-dedup` 的 Task 5 与 Checkpoint 2（用户 2026-10-09 确认接受 252 秒）。

## Commands

```bash
/bin/bash scripts/validate.sh
python3 scripts/check-readme-sync.py
/bin/bash scripts/verify-and-commit.sh -- -m "<信息>"
```

## Boundaries

- Always：删除前核对引用；命令与参数以 `plugins/spec-guard/commands` 为准；提交走 `verify-and-commit.sh`。
- Ask first：推送、PR；删除第 7 条以外的文档；改 `plugins/` 下任何文件。
- Never：改插件行为或版本号；加长期链接检查器；改 `spec/`、`tasks/` 里的历史链接。

## Success criteria

1. 第一次接触的人只看 README（中文或英文）就能装好、跑通、知道出问题看哪里。
2. 每份留下的文档都能从 README 或文档导航找到，并标明给谁看。
3. 删掉的文档不再被现行文档或检查器引用；`validate.sh` 通过。

## Open questions

无。
