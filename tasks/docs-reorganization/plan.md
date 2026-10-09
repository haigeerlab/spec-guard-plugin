# Plan: docs-reorganization

依据 [`spec/docs-reorganization.md`](../../spec/docs-reorganization.md)（用户 2026-10-09 批准 Spec）。分开审：本 Plan
单独批准。PR 分三批，每批一个分支、一个 PR，上一批合并后再开始下一批；提交一律走 `scripts/verify-and-commit.sh`。

## 第一批：删除与整理（分支 `claude/docs-reorganization`）

### Task 1：合并协作拆分总结

把 `docs/collaboration-split-summary.md` 里仍有用的内容（拆分后的职责边界、用户需要做的迁移步骤）并入
`docs/migrations/2026-10-07-collaboration-split.md`，并入前后对照，避免重复。

### Task 2：删除文档并清理现行引用

删除 Spec 假设 7 列出的文件。删前再跑一遍 `git grep`：`spec/`、`tasks/` 里的引用按假设 3 不改；现行文档（README、
`docs/`、`CLAUDE.md`、`AGENTS.md`、`CONTRIBUTING.md`）与 `scripts/`、`evals/` 里的引用全部改掉或删去，
`docs/reports/README.md` 删去对应条目。

### Task 3：约定块移到 `docs/convention-block.md`

回归先行：`scripts/test-checkers.sh` 的 readme-sync 用例改为对 `docs/convention-block.md` 构造正反例，并新增“英文
README 的 `--ref` 落后于清单版本 → 报错”（第二批才有 `README.en.md`，检查器对不存在的英文 README 跳过）；在现有
检查器上为红。再改 `scripts/check-readme-sync.py`，把 README 的约定块与 Agent Skills 集成约定移到新文件，README 只留
链接。变异：检查器改回读 README。

### Checkpoint 1（gate）：第一批评审

一次性脚本核对全部站内链接（不入库）；`validate.sh` 通过；推送并开第一批 PR，交第二轮联调审，由用户合并。

## 第二批：README 双语（分支 `claude/docs-readme`）

### Task 4：中文 README

按 Spec 需求 4 的大纲重写 `README.md`；撤掉旧迁移说明的链接；命令与参数逐条对照 `plugins/spec-guard/commands/*.md`，
对照结果（命令、参数、出处）写进 todo。

### Task 5：英文 README

新建 `README.en.md`，章节与中文版一一对应；两份顶部放语言切换行；命令同样逐条对照。

### Task 6：维护规则与反馈入口

`CONTRIBUTING.md` 补“怎么报 bug”和“改 README 时两份一起改”；`docs/maintainer-workflow.md` 同步这条规则；核对并按需
更新 `.github/ISSUE_TEMPLATE/bug.yml`。

### Checkpoint 2（gate）：第二批评审

链接核对、`validate.sh` 通过；推送并开第二批 PR，交第二轮联调审，由用户合并。

## 第三批：新建与重写文档（分支 `claude/docs-guides`）

### Task 7：`docs/commands.md`

从 `docs/workflow.md` 的“命令对照”一节拆出全部命令、参数和输出，workflow 里留链接；逐条对照命令文件。

### Task 8：`docs/troubleshooting.md`

覆盖阶段提示不出现、MAP_INVALID（含模块表数量的新报错）、python3 故障、Codex 不加载插件；每条写现象、原因、
检查命令与解决办法，命令以仓库现有脚本为准。

### Task 9：`docs/design.md` 中文架构说明

部件、数据流、两个宿主的差异、不变量；文件名不变，`CLAUDE.md`、`AGENTS.md` 里对它的描述同步。文档导航里标明
维护者文档（`maintainer-workflow`、`release-process`、`lenses`、`upstream-analysis`）。

### Checkpoint 3（gate）：第三批评审

链接核对、`validate.sh` 通过；推送并开第三批 PR，交第二轮联调审，由用户合并。

### Task 10：下次发版时补证据
