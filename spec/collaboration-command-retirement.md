# Spec: collaboration-command-retirement

## Objective

会话协作在 0.40 前后拆成独立插件 agent-relay 后，`/spec-guard:collaboration` 作为过渡命令保留，负责把用户转交过去
（`collaboration-dependency`）。0.53.0 的 CHANGELOG 已预告"`/spec-guard:collaboration` 将在 0.54.0 移除"（审查 F20，
用户 2026-10-08 决定），当时核查本机没有在用它的使用方项目。本模块兑现这个预告，并作为本批最后一个模块承载 0.54.0
的版本号改动。

登记：2026-10-08 经 `/spec-guard:add-module` 插入能力图。同批：`project-config`（#255）、`module-suspend`（#256）、
`runtime-state-layout`（#257），均已合并。

## Assumptions

用户已于 2026-10-08 确认（"按推荐继续"：发 0.54.0，发版前先做退役模块）：

1. **只退役命令本身。** `hooks/agent_relay_probe.py` 保留：`skills/ticket` 用它判断 agent-relay 是否可用，再决定是否经协作信箱
   通知；它的回归 `test_agent_relay_probe.py` 也保留。
2. **当时的记录不改：** `docs/releases/`、`docs/retirements/`、历史快照、`spec/proposals/`、迁移文档
   `docs/migrations/2026-10-07-collaboration-split.md`，以及已完成模块的 Spec／Plan（`collaboration-dependency` 等）。
3. **现行文字要改：** 命令表、README、`docs/optional-features.md`、`docs/collaboration-interface.md` 的 Spec Guard 一侧说明、
   协作边界检查器与命令名检查器的说明和允许清单、能力图里 `collaboration-dependency` 那一行（已在写入能力图时改为不点名）。
4. **防回流：** 照 0.52.0 退役 handoff 的做法，把 `spec-guard:collaboration` 加入退役扫描对能力图与插件现行文件的名单。
5. **版本：** 两份插件清单改为 `0.54.0`，README 的 Codex 安装命令 `--ref v0.54.0`，CHANGELOG 的 `## [未发布]` 改为
   `## [0.54.0] - <合并日>`，并在其下补"移除"一节。合并后一次走完 tag → Release → 两边宿主 → 证据 PR（`docs/release-process.md`）。

## Contract

- 删除 `plugins/spec-guard/commands/collaboration.md` 与 `plugins/spec-guard/hooks/test_collaboration_handoff.py`
  （及 `validate.sh` 里对它的调用，如有）。
- `docs/workflow.md` 命令对照表删去该行；"会话协作已移到 agent-relay"的说明保留，改为直接指向 agent-relay 的命令与 skill。
- `README.md` 与 `docs/optional-features.md` 去掉"过渡期 `/spec-guard:collaboration` 会转交"的说法，只说装 agent-relay。
- `docs/collaboration-interface.md` 第 11–12 节一侧：Spec Guard 只经 `agent_relay_probe.py` 与 agent-relay 的 skill 名接触协作；
  记录过渡命令已于 0.54.0 移除。
- `scripts/check-collaboration-boundary.py`：说明与失败提示不再列出过渡命令。
- `scripts/check-command-names.py`：若退役后再无用户可见文件提到 `/agent-relay:collaboration`，删去 `EXTERNAL_COMMANDS` 那一项；
  仍有则保留并更新注释。以实测为准。
- `plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh`：能力图名单与插件现行文件的扫描都加入 `spec-guard:collaboration`。
- 版本与 CHANGELOG 按 Assumption 5。

## Commands

```text
/bin/bash plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh
/bin/bash scripts/test-checkers.sh
python3 -B scripts/check-command-names.py .
python3 -B scripts/check-command-table.py .
python3 -B scripts/check-readme-sync.py .
python3 -B scripts/check-manifests.py .
/bin/bash scripts/validate.sh
/bin/bash evals/codex-plugin-smoke.sh --selftest
```

## Testing strategy

- 先红：退役扫描先加入名字，确认在命令文件与现行文字仍在时失败；删除与改写后转绿。
- 检查器回归（`test-checkers.sh`）与命令名、命令表、README 同步、清单一致性检查全部通过。
- 变异：把命令文件放回、在能力图某行写回该名字，退役扫描都必须变红。
- 发版前按 `docs/release-process.md`：macOS `/bin/bash` 完整校验、两套 hook 断言，以及 Codex smoke 判决器自检。

## Boundaries

- Always：先红后绿；只删过渡命令，不动 `agent_relay_probe.py` 的行为；版本号三处一致。
- Ask first：删除或改写任何当时的记录；动 agent-relay 的仓库或目录。
- Never：在 Spec、代码、测试、提交信息或 PR 中写入消费者项目的名称、模块或编号；合并 PR。

## Success criteria

- 插件里不再有 `/spec-guard:collaboration`，现行文字与能力图里也没有；退役扫描能拦住它回流。
- `ticket` skill 经 `agent_relay_probe.py` 通知的路径不变。
- 版本号 `0.54.0` 在两份清单与 README 一致，CHANGELOG 有 `[0.54.0]` 一节，所有校验通过。

## Open questions

- 无。
