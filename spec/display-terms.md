# Spec: display-terms

<!-- spec-guard: review approved 432c265ca12a -->

## Objective

给用户看的中文里，"评审""审核""审批"三个词混着用，同一件事有时叫"评审标记"、有时说"等待用户审核"，又和"审查"
"批准""验收"并存。同生态的几个插件已经统一为三个词：**审查**（agent 或审查者做的技术检查）、**批准**（用户的决定）、
**验收**（只指最终验收）。本模块把 spec-guard 给用户看的文字按这个分工改过来；命令名、配置键、标记写法、JSON 取值与英文
文字都不变，所以不影响任何读取方。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `review-approval-marker`、`project-config`、`hint-language-follow`。
需求来自接入协调人转述的用户决定 53（S6）；"评审节奏"改叫"批准节奏"由用户在本会话定。

## Assumptions

1. **按意思换，不按字面换**。对照表：

   | 原文 | 改为 | 依据 |
   |---|---|---|
   | 评审标记、评审状态标记 | 批准标记 | 标记记录的是用户的批准状态 |
   | 评审节奏 | 批准节奏 | 决定一个模块批准一次还是两次 |
   | 待审核、等待用户审核、等用户审阅（指状态） | 待批准、等用户批准 | 等的是用户的决定 |
   | 评审状态、评审状态未知 | 批准状态、批准状态未知 | 同上 |
   | 能力图评审 | 能力图审阅 | 用户看过能力图并确认；"审阅"不在停用词里 |
   | 先评审再 `--confirm`、尚未评审、视为已评审（指 Spec） | 先批准再……、尚未批准、视为已批准 | 指用户批准 Spec |
   | 代码评审、API 评审、人工评审、评审人、新鲜评审（Proposal） | 代码审查、API 审查、人工审查、审查人、新鲜审查 | 技术检查 |
   | 经过评审的决定记录（Proposal） | 经过审查的决定记录 | Proposal 是被审查的提案 |
   | 审批 | 批准 | 用户的决定 |

   拿不准的个案在构建时按"谁做的、做的是什么"判断：用户的决定 → 批准；技术检查 → 审查；看一遍 → 审阅。
2. **改动范围是现行的产品文字**：hook 输出（`module_stage.py`、`map_view.py`、`verify-artifacts.sh`、`module-insert.py`、
   `proposal_promotion_proof.py`）、命令与 skill 说明（含 frontmatter 的 description）、约定块模板与 `docs/convention-block.md`、
   本仓库 `AGENTS.md` 的约定块、共享检查点规则与其他 references、README 与 `docs/` 下的现行文档，以及断言这些文字的测试。
   共享检查点规则里「评审节奏」「评审状态标记」两节的标题也改，引用这两节的地方一起改。
3. **历史记录不改**：`spec/`、`tasks/`、`docs/releases/`、`docs/reports/`、`docs/decisions/`、`docs/retirements/`、`docs/research/`
   与 CHANGELOG 已有条目是当时的记录，保持原样。
4. **不改的东西**：命令名 `review-mark`、配置键 `reviewCadence`、标记行 `<!-- spec-guard: review pending|approved -->`、
   JSON 取值（`pending`、`approved` 等）、`map-view` 的 JSON 字段、所有英文文字（`artifactLanguage` 不是 `zh-CN` 时的提示）。
5. **加一条防回退的断言**：在现行产品文字（上面第 2 条的文件）里不再出现"评审""审核""审批"；历史目录不在检查范围。
6. **只增文字层面的变化**：阶段判定、退出码、标记格式都不变；用户项目里已装的约定块会在下次 `setup-convention --replace`
   时看到这几行文字变化，和以往每次改模板一样。
7. 发版 0.75.0。

## Contract

- 按 Assumptions 第 1 条改写第 2 条范围内的全部中文文字；节标题 `## 评审节奏` → `## 批准节奏`、`## 评审状态标记` →
  `## 批准标记`，所有「见共享检查点规则「…」」的引用同步。
- `map_view.py` 表头"待审核："→"待批准："，审查列里的"待审核"→"待批准"（`REVIEW_WORDS`）；JSON 不变。
- `module_stage.py` 阶段提示里 `- 评审:` 一行的标签改为 `- 批准:`，句中"正在等用户审阅"→"正在等用户批准"等；英文不变。
- 新增测试：一条断言扫描第 2 条的文件，三个停用词都不出现（以文件清单写在测试里，新加的产品文件要加进清单）。
- CHANGELOG `[0.75.0]` 写明改了哪些叫法、哪些不变；版本号 0.75.0（两份清单）与中英 README 的 `--ref`。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
python3 -B plugins/spec-guard/hooks/test_workflow_checkpoints.py
python3 -B plugins/spec-guard/hooks/test_map_view.py
```

## Testing strategy

- 先加防回退断言（现在会红，列出全部命中），改完转绿。
- 断言旧文字的现有测试（`test-phase-guard.sh`、`test-verify-artifacts.sh`、`test_map_view.py`、`test_workflow_checkpoints.py`、
  `test-setup-teardown.sh` 等）改为断言新文字；英文分支的断言不改。
- 每改完一类文件跑一次对应测试；最后全套。

## Boundaries

- **会做**：现行产品文字与对应测试的改名、一条防回退断言。
- **先问**：改命令名、配置键、标记写法、JSON 取值；改历史记录；引入同生态插件的其他术语（决策收件箱等）。
- **不做**：英文文字；阶段判定与行为。

## Success criteria

- AC1：第 2 条范围内的文件不再出现"评审""审核""审批"，防回退断言通过；历史目录未被改动。
- AC2：阶段提示、`/map` 表格、verify-artifacts 输出里，批准标记、批准节奏、待批准等新叫法出现在原来的位置，测试断言新文字。
- AC3：命令名、配置键、标记行、JSON 取值与英文输出逐字不变（`test_map_view.py` 的 JSON 期望不改；英文阶段提示的回归不改）。
- AC4：`validate.sh`、phase-guard、verify-artifacts 全套通过。

## Open questions

- 无。
