# Spec: boundary-hint-unknown-size

<!-- spec-guard: review approved cf19463e9157 -->

## Objective

阶段提示在模块之间（`MODULE_DONE`／`DONE`）读不到会话上下文大小时，照样输出一行不带大小的"模块边界: 这是释放上下文的
好时机"，还附上 `/compact` 的写法（`context-hint-thresholds` 当初有意保留的"保守"行为）。可 Claude 的大小来自会话记录里最后
一条带用量的记录，**新会话的第一轮还没有任何用量，必然读不到**：于是一个刚开、上下文几乎为空的会话，第一句话就被建议释放上下文。
2026-10-19 本仓库实际发生过：会话开头收到这一行，界面显示上下文才 30% 左右。

本模块让 `MODULE_DONE`／`DONE` 与 `NEEDS_SPEC` 一样：**读不到大小就不出边界行**。读得到时的两档阈值（模块之间 70%、模块中途
80%）、文字与其他阶段都不变。

登记：2026-10-19 经 `/spec-guard:add-module` 插入能力图，依赖 `context-hint-thresholds`、`boundary-hint-70`、`phase-hint-gaps`。
用户在本会话确认了问题与修法。

## Assumptions

1. **只改一个分支**：`module_stage.py` 里 `context_tokens is None` 时给 `boundary_note_line` 赋不带大小那一行的分支，改为空串。
   读得到且达到边界档时的带大小那一行、模块中途 80% 的上下文行、`unattended` 时清空的逻辑都不动。
2. **两边宿主一样处理**：Claude 与 Codex 共用这一分支；Codex 读不到时同样不出。
3. **读不到的其他情形也一并静默**：会话记录尾部窗口里没有用量记录（例如最近都是很大的工具输出）、路径给不出、读失败。
   代价是这些情形下少提示一次；它们本来就说不出大小，按 `context-hint-thresholds` 最初写的"读不到就不提"处理。
4. **不改读数逻辑**：`session_context.py` 怎么取用量、窗口与压缩后的大小都不变。
5. **英文与中文两种语言的不带大小那一行都不再出现**；带大小的那一行（`本会话上下文约 N k token`）照旧。
6. 发版 0.76.0；CHANGELOG 写明行为变化与原因。现行文档里没有描述这条行为，不需要改文档。

## Contract

- `module_stage.py`：`context_tokens is None` → `boundary_note_line = ""`；这一分支里内联的中英两句不带大小的文字随之删除
  （`module_stage.py:763` 一带，别处不用）。
- 回归（`test-phase-guard.sh`）：
  - 读不到大小的 `MODULE_DONE`、`DONE` 不出边界行，也不出上下文行（中英、Claude、Codex、判断不了宿主各一例）；
  - 原来借"读不到大小"这一情形检查边界行**文字**的用例（Claude 与 Codex 的 `/compact` 写法、斜杠命令说明、中文 DONE 那一例），
    改为喂一份达到边界档的会话记录，断言带大小的那一行，文字检查的覆盖不减少；
  - 读得到且低于阈值、读得到且达到阈值、`NEEDS_SPEC`、模块中途、无人值守的现有用例期望不变。
- CHANGELOG `[0.76.0]`；版本号 0.76.0（两份清单）与中英 README 的 `--ref`。

## Commands

```bash
/bin/bash scripts/validate.sh
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
```

## Testing strategy

先把"读不到大小时出边界行"的断言改成"不出"（会红），再改分支转绿；借这一情形检查文字的用例先改为带大小的版本（改前改后都应绿，
证明文字覆盖没丢）。变异：恢复原分支 → 新断言变红。

## Boundaries

- **会做**：一个分支、对应回归、CHANGELOG 与版本号。
- **先问**：改阈值；改读数方式；为"新会话第一轮"另做识别（比如看会话记录有没有用户消息）。
- **不做**：其他阶段的上下文提示；`unattended` 逻辑；文档以外的说明。

## Success criteria

- AC1：读不到上下文大小时，`MODULE_DONE` 与 `DONE` 的阶段提示里没有"模块边界"／`Module boundary` 那一行（中英、两边宿主、判断不了宿主）。
- AC2：读得到且达到边界档时，带大小的边界行与原来逐字相同；`/compact` 写法、斜杠命令说明等文字检查仍有用例覆盖。
- AC3：低于阈值、`NEEDS_SPEC`、模块中途、无人值守的现有用例期望不变；phase-guard 全套通过。
- AC4：恢复原分支时，AC1 的断言变红。

## Open questions

- 无。
