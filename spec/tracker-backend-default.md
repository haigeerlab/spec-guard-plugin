# Spec: tracker-backend-default

## Objective

`.agent/state.json` 的 `tracker` 字段同时承担三个互不相干的职责，彼此矛盾：

- `phase-guard.sh:28` 把带已知值的该字段当作**现行激活信号**之一；
- `setup-convention.sh:97` 今天仍然写入 `"tracker":"none"`，而 `none` 不触发任何逻辑，
  只是让上面那条正则匹配得上的**魔法占位符**；
- `module_stage.retired_tracker()` 把 `github`/`gitlab` 读作**已退役模式**，用来抑制
  plan-without-todo 的提醒与汇总，而 `verify-artifacts.sh:92` 又对这个文件的存在本身
  发出「检测到历史状态文件」告警——对插件自己刚装的文件告警。

旧的远端 tracker 模式（任务住在远端 Issue、`/plan` 只写 `plan.md`）已于 2026-09-15 前退役
（`docs/retirements/spec-github-bridge-retirement.md`），其 bridge 代码已删净并由
`hooks/test-retire-legacy-tracker-bridge.sh` 守住。残留的只有这个字段本身。

同时，日常使用缺少一个真正需要的东西：**项目级默认事项后端**。今天每个托管事项入口都要
逐次手打 `--platform/--host/--target`。实际使用中这个选择在很长时间里是不变的（代码在
GitHub 上就一直用 GitHub），只有在平台不可用时才需要紧急切换。

本模块把这两件事一次做完：**删掉退役字段，换成一个单一用途、语义准确的项目级默认 backend**。
删旧与立新是同一件事的两面——只删不换，用户就只能永远手打参数；只换不删，三重职责冲突仍在。

登记：2026-10-04 按用户决定经 `/spec-guard:add-module` 快速插入能力图，决策记录见
`docs/decisions/2026-10-04-tracker-backend-default.md`。

## Assumptions

用户已于 2026-10-04 确认：

1. **不考虑向后兼容。** 本插件只有本项目在使用，退役概念直接删除，不留过渡期、不留兼容读取。
2. **`.agent/state.json` 与 `activeModule` 保留。** 只删该文件内的 `tracker` 字段，以及
   无人读取的 `modules` 空对象。文件本身是当前模块书签，继续由 `module_stage.active_module()` 使用。
3. **激活信号不减少。** 第二个信号从「带已知 tracker 值」改判为「含 `activeModule` 键」。
   `activeModule` 恰是该文件存在的唯一理由，用它当激活证据语义准确；直接删掉 `has_state()`
   会让声明块被删过的项目静默，静默在设计上等同于未启用，不可接受。
4. **完成判据不变。** 「有 `tasks/<id>/plan.md` 且没有未勾选项即完成」保持逐字不变。删除的
   只是 `retired_tracker()` 这个**警告抑制**，不是完成判据本身。本仓库没有 `.agent/state.json`，
   `retired_tracker()` 恒为 False，因此删除它对本仓库零行为变化。
5. **默认值只预填，不决定。** 新增 `.agent/tracker.json` 保存项目默认 backend 与精确目标；
   它只在调用方未显式给出时填进**预览**，预览必须标明来源，每次外部写入仍然逐次授权。
6. **默认值对已有事项零影响。** 改默认值不移动、不复制、不关闭任何既有事项，也不改变其绑定。
7. **默认值不是激活信号。** `.agent/tracker.json` 的有无与 phase-guard 是否注入完全无关。

以下为本 Spec 提出、待评审确认的范围：

8. 本模块只提供默认值的**读取与设置入口**；第一个程序化消费者是后续模块 `proposal-closeout`。
   既有的 `hosted-ticket-workflow` 入口在本模块中不改变其必填参数。
9. `spec/hosted-ticket-workflow.md` 的「不新增项目级 Tracker 配置」被本模块**明确推翻**，
   按本仓库先例（`docs/decisions/2026-10-04-a10-single-mac-promotion-gate.md` 修订
   `2026-09-28-xats-sunset.md`）写进决策记录，其余条款继续有效。

## Contract

### C1 删除退役字段（`hooks/setup-convention.sh`）

- 第 97 行写入的内容从 `{"tracker":"none","modules":{},"activeModule":""}` 改为
  `{"activeModule":""}`。`modules` 空对象无任何读取点（全仓库 `modules` 的命中均在
  `capability-history.py` 的能力历史快照结构中，与本文件无关），一并删除。
- 既有 `.agent/state.json` 不被改写：该分支只在文件不存在时执行，行为不变。

### C2 激活信号改判（`hooks/phase-guard.sh`）

- `has_state()` 的判据从
  `'"tracker"[[:space:]]*:[[:space:]]*"(none|github|gitlab)"'`
  改为 `'"activeModule"[[:space:]]*:'`。
- `has_block || has_state || exit 0` 的结构与注释随之更新：激活信号仍是两个，说明改为
  「独占一行的声明块标记，或含 `activeModule` 的 `.agent/state.json`」。
- `teardown-convention.sh` 把 `state.json` 改名为 `.disabled` 的停用方式不变，仍然有效。

### C3 删除警告抑制（`hooks/module_stage.py`、`hooks/verify-artifacts.sh`）

- 删除 `retired_tracker()`（`module_stage.py:55-57`）及其两处调用（`:128`、`:134`）。
- `verify-artifacts.sh` 内嵌 Python 删除 `from module_stage import ... retired_tracker`
  与 `and not retired_tracker(root)`。
- 完成判据、阶段取值、计数行、`Paused` 行、plan-without-todo 的 T1 提醒与 T2 汇总文案
  全部逐字不变。

### C4 重新界定历史状态告警（`hooks/verify-artifacts.sh:92-93`）

- 当前对 `.agent/state.json` 的**存在**发 warn，这会对 `setup-convention` 刚装的文件告警。
- 改为：只有当该文件确实含 `tracker` 键时才 warn，文案改为指出这是已退役字段并给出处理方式
  （`从 .agent/state.json 中删除 tracker 字段；它已退役，不再被读取`）。
- 文件存在但不含 `tracker` → 不输出，不改变退出码。

### C5 项目默认 backend（新 `hooks/tracker_default.py`）

文件 `.agent/tracker.json`，提交进仓库，单一用途：

```json
{ "version": 1, "defaultBackend": "github",
  "defaultTarget": { "host": "github.com", "repo": "owner/name" } }
```

`defaultTarget` 按 backend 取固定形状，多余或缺失字段一律 `invalid`：

| backend | defaultTarget |
| --- | --- |
| `github` | `{"host": <hostname>, "repo": "<owner>/<name>"}` |
| `gitlab` | `{"host": <hostname>, "projectId": <正整数>}` |
| `local` | `{"projectId": "<Epiq projectId>"}` |

GitLab 的目标采用正整数 project id，与既有 Proposal 命令
（`proposal_tracker_read` 的 `glab api projects/<id>/issues`）一致，不引入第二种目标形态。

- `read_default(root) -> DefaultResult`：
  - `absent`：文件不存在。**不是错误**，表示没有默认值。
  - `invalid`：存在但 JSON 不可解析、`version != 1`、backend 不在三值内、或 target 形状不符。
    带稳定诊断码 `tracker-default-invalid`。**绝不静默降级为 absent。**
  - `configured`：带 `backend` 与规范化后的 `target`。
- `resolve(explicit_backend, explicit_target, default) -> Resolution`：
  - 两者都显式 → `resolved(source="explicit")`。与默认不同**不是冲突**，默认只是预填。
  - 都未显式，默认为 `configured` → `resolved(source="project-default")`。
  - 都未显式，默认为 `absent` → `target-unselected`。
  - 都未显式，默认为 `invalid` → `target-unselected`，透传 `tracker-default-invalid`。
  - 只给 backend：与默认的 backend 相同 → 用默认的 target，`source="project-default-target"`；
    不同或无默认 → `target-unselected`。
  - 只给 target 不给 backend → `target-unselected`（目标形状不足以反推 backend）。
- `as_json()` 只输出 `state`、`backend`、`source`、规范化 target 与稳定诊断码；不输出文件
  绝对路径、原始解析错误或任何事项内容。

### C5b 文档本身是攻击面（2026-10-04 审查后补入）

`.agent/tracker.json` 是**仓库内容**：敌对仓库控制它的每一个字节，也控制那个 inode 本身。因此：

- **读取不跟随符号链接、不无界读取。** 用 `O_NOFOLLOW | O_NONBLOCK` 打开，`fstat` 要求普通文件，
  读取上限 64 KiB。悬空链接、指向真实文件的链接、目录、设备、FIFO、超限、非 UTF-8 字节
  **一律 `invalid`**——其中任何一种被报成 `absent`，都会被读成「没配过默认值」。
- **预览不回显文档原文。** 当前字节不是可用文档时，预览只说明「现有文档不可用，将被整体替换」并打印
  **拟写入的内容**，绝不打印读到的内容。否则把 `.agent/tracker.json` 指向 `~/.ssh/id_ed25519` 即可在
  **不需要 `--confirm`** 的预览里把它泄进 agent 上下文。
- **`.agent` 是符号链接时拒绝写入**，报 `agent-directory-unsafe` 并退出 2。否则 `--confirm` 会把文档写进
  别的项目，静默改掉那个项目的默认写入目标。
- **写入走新建的独占临时文件**（`tempfile.mkstemp`，`O_CREAT|O_EXCL`，0600），再 `os.replace`。
  文件名不可预测，所以预先埋在 `.agent/` 里的 `.tmp` 名字无法劫持写入；`rename` 不跟随链接，所以
  目标处的符号链接是被**替换**而不是被写穿。权限用 `lstat` 读取，普通文件才沿用其 mode，否则 0644。
  任何一步失败都删除临时文件并原样抛出。
- **写入失败不泄露路径或异常原文**：报 `tracker-default-unwritable` 并退出 2。
- **`set` 不创建任意祖先目录**：`--project` 必须已是目录，只 `mkdir` 缺失的 `.agent` 一层。
- **标识符有长度上界**：host ≤ 253、`repo` 每段 ≤ 100 且**首字符须为字母数字**（避免未来的消费者把它
  当成选项传递），`version` 必须是严格的整数 1（排除 `true` 与 `1.0`）。

### C6 入口（`hooks/tracker_default.py` CLI 与命令/skill）

```text
tracker_default.py show --project <dir> --format json
tracker_default.py set  --project <dir> --backend <github|gitlab|local> \
                        [--host <h>] [--repo <o/n>] [--project-id <v>] [--confirm]
```

- `show` 只读。
- `set` 默认只打印改前/改后的 JSON 差异；`--confirm` 才原子写回 `.agent/tracker.json`
  这一个文件（保留既有权限，新建时 0644），不触碰 `state.json`、`spec/`、`tasks/` 或 Git。
- `set` 写入前校验目标形状；不校验目标在远端是否真实存在（那是写入时的 `target_facts()` 的职责）。
- Claude 命令 `/spec-guard:tracker-default`，Codex 经 `spec-guard-ops` skill 的同名一节；
  两边语义相同，`scripts/check-command-parity.py` 须通过。

### C7 文档

- 新增 `docs/retirements/state-tracker-field.md`：退役了什么、为什么、移除的内容、迁移
  （手工从 `.agent/state.json` 删掉 `tracker` 键即可；无此键的项目无需动作）。
- 新增 `docs/decisions/2026-10-04-tracker-backend-default.md`：记录「默认值 ≠ 权威」的区分、
  对 `spec/hosted-ticket-workflow.md` 相应条款的修订，以及五条不变量。
- `spec/plan-without-todo.md` 的「修订：已退役的远端 tracker 模式」一节改写为指向退役说明，
  并写明抑制逻辑已删除；**完成判据的表述逐字不变**。
- `docs/workflow.md`：安装约定写入的文件清单更新；命令对照增加 `tracker-default` 一行；
  阶段提示一节说明激活信号。
- `docs/concepts.md`：术语表增加 `backend`、`精确目标`、`source authority`，并写明
  `activeModule` 是书签、阶段是每轮实时推导。
- `docs/optional-features.md`：本模块不新增可选能力，不改动。
- `CHANGELOG.md` Unreleased 的 `### 移除` 与 `### 新增`。

## Commands

```text
python3 -B plugins/spec-guard/hooks/tracker_default.py show --project . --format json
python3 -B plugins/spec-guard/hooks/test_tracker_default.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash plugins/spec-guard/hooks/test-verify-artifacts.sh
/bin/bash plugins/spec-guard/hooks/test-setup-teardown.sh
/bin/bash plugins/spec-guard/hooks/test-hook-entry.sh
python3 scripts/check-command-parity.py
/bin/bash scripts/validate.sh
/bin/bash evals/codex-plugin-smoke.sh --selftest
```

## Project structure

```text
plugins/spec-guard/hooks/tracker_default.py           -> C5, C6 读取、解析、resolve 与 CLI
plugins/spec-guard/hooks/test_tracker_default.py      -> C5, C6 正反测试
plugins/spec-guard/hooks/setup-convention.sh          -> C1
plugins/spec-guard/hooks/phase-guard.sh               -> C2
plugins/spec-guard/hooks/module_stage.py              -> C3
plugins/spec-guard/hooks/verify-artifacts.sh          -> C3, C4
plugins/spec-guard/hooks/test-*.sh                    -> 夹具去掉 tracker 字段
plugins/spec-guard/commands/tracker-default.md        -> C6
plugins/spec-guard/skills/spec-guard-ops/SKILL.md     -> C6
docs/, spec/plan-without-todo.md, CHANGELOG.md        -> C7
```

## Testing strategy

每项先写测试并确认它在当前代码上失败，再改实现。全部使用临时目录，不触碰真实项目。

### T1 激活信号（`test-phase-guard.sh`）

- 只有声明块、没有 `state.json` → 注入（现有用例，保持通过）；
- 只有 `{"activeModule":""}`、没有声明块 → **注入**（新，当前代码会静默）；
- 只有 `{"activeModule":"alpha"}` → 注入且当前模块为 alpha；
- 只有 `{"tracker":"none"}`、没有声明块 → **不注入**（新，锁死退役字段不再是信号）；
- 两个信号都没有 → 静默（现有用例）；
- `state.json.disabled`（teardown 后）→ 静默（现有用例）。

### T2 警告抑制已删除（`test-verify-artifacts.sh`、`module_stage`）

- 有 Plan 无 todo 的模块存在 + `{"tracker":"github"}` → **仍然发汇总 warn**（新，当前被抑制）；
- 同上但 `tracker` 为 `gitlab` → 同；
- 无 `state.json` → 发 warn（现有行为，保持）；
- T1 阶段提醒行：`activeModule` 指向缺 todo 的已完成模块时**总是**追加提醒行，不再看 tracker。

### T3 历史状态告警重新界定（`test-verify-artifacts.sh`）

- `{"activeModule":""}` → **不发**「历史状态文件」warn（新，当前会发）；
- `{"tracker":"none","activeModule":""}` → 发 warn，文案指向退役字段；
- 无文件 → 不发。

### T4 setup/teardown（`test-setup-teardown.sh`）

- 全新项目安装 → `state.json` 内容恰为 `{"activeModule":""}`，**不含** `tracker` 与 `modules`；
- 已存在的 `state.json`（含旧 `tracker`）→ 不被改写；
- teardown → 改名为 `.disabled`，hook 静默；`--keep-state` → 仍激活。

### T5 默认值读取（`test_tracker_default.py`）

每个 backend 一组正反：

- 三种 backend 的合法文件 → `configured`，target 规范化正确；
- 文件不存在 → `absent`；
- JSON 坏、`version: 2`、backend 为 `none`/未知值、github 缺 `repo`、github 的 `repo` 没有
  恰好一个 `/`、gitlab 的 `projectId` 为字符串或 ≤0、local 缺 `projectId`、
  target 带多余键 → 全部 `invalid` + `tracker-default-invalid`，**不得降级为 absent**；
- `as_json` 不含绝对路径、原始异常文本。

### T6 resolve 判定表（`test_tracker_default.py`）

| explicit backend | explicit target | default | 期望 |
| --- | --- | --- | --- |
| 有 | 有 | 任意 | `resolved`，source=explicit |
| 有 | 有（与默认不同） | configured | `resolved`，source=explicit（**不是冲突**） |
| 无 | 无 | configured | `resolved`，source=project-default |
| 无 | 无 | absent | `target-unselected` |
| 无 | 无 | invalid | `target-unselected` + `tracker-default-invalid` |
| 有（同默认 backend） | 无 | configured | `resolved`，source=project-default-target |
| 有（异于默认 backend） | 无 | configured | `target-unselected` |
| 无 | 有 | 任意 | `target-unselected` |

### T7 `set` 入口（`test_tracker_default.py`）

- 不带 `--confirm` → 打印差异，**文件未改动**（断言 mtime 与内容）；
- 带 `--confirm` → 原子写回，内容与预览一致，权限保留；
- 目标形状不合法 → 非零退出，不写文件；
- 不触碰 `.agent/state.json`（断言其内容在 set 前后逐字相同）。

### T7b 敌对文档（C5b，2026-10-04 审查后补入）

每条都先在当前代码上复现问题再修复，证据记在提交说明里：

- `.agent/tracker.json` 是指向项目外文件的符号链接 → `read_default` 为 `invalid`；`set` **预览**
  （无 `--confirm`）的输出**不含**被指向文件的任何内容；`set --confirm` 不修改被指向的文件，
  且事后该路径不再是符号链接；
- 悬空符号链接 → `invalid`（**不是 `absent`**）；
- `.agent/` 中预埋 600 个 pid 形状的 `tracker.json.<n>.tmp` 符号链接 → `set --confirm` 不覆盖被指向文件，
  且默认值写入成功；
- `.agent` 本身是指向项目外目录的符号链接 → `set --confirm` 退出 2，目标目录内不出现 `tracker.json`；
- 非 UTF-8 字节 → `read_default` 为 `invalid`；`show` 退出 0 并只输出 `{"state":"invalid",…}`；
  `show` 与 `set` 的 stderr 都**不含** `Traceback`；
- 文档超过 64 KiB → `invalid`；路径是目录 → `invalid`；
- host 300 字符、`repo` 段 200 字符 → `normalize_target` 返回 `None`。

### T8 退役扫描

- `test-retire-legacy-tracker-bridge.sh` 增加断言：已发布插件表面不再出现
  `"tracker"[[:space:]]*:` 的写入或读取（退役说明与历史报告除外）。

## Boundaries

- **Always**：先红后绿；hook 只读、只输出宿主 JSON；只依赖 bash/git/python3，不引入 `jq`；
  保留 `from __future__ import annotations`；Python 3.9 与默认 python3 两种下均通过；
  macOS 兼容检查显式用 `/bin/bash`；删除附退役说明与迁移要点。
- **Ask first**：改变完成判据；减少激活信号的数量；让 `.agent/tracker.json` 参与激活判断；
  让默认值在没有预览的情况下影响任何写入。
- **Never**：在 Spec、代码、测试、提交信息或 PR 中写入其他项目的名称、模块或编号；
  把 backend 默认值写回 `.agent/state.json`；让默认值改变已有事项的绑定；
  恢复旧 tracker bridge 或 XATS；修改全局 Claude/Codex 配置。

## Success criteria

- 全新安装的项目，`.agent/state.json` 内容恰为 `{"activeModule":""}`，阶段注入正常。
- 只有 `{"tracker":"none"}` 的项目不再被当作已启用；只有 `{"activeModule":...}` 的项目被当作已启用。
- 删除 `retired_tracker()` 后，本仓库 `verify-artifacts` 与阶段注入的输出与删除前逐字相同
  （因为本仓库无 `state.json`），且带旧 `tracker` 值的临时夹具不再被抑制告警。
- 三种 backend 的默认值读取与 resolve 判定表全部正反通过，非法输入一律 `invalid`，
  绝不降级为 `absent`。
- `set` 不带 `--confirm` 不写文件；带 `--confirm` 只写 `.agent/tracker.json` 一个文件。
- `scripts/validate.sh`、`test-phase-guard.sh`、`test-verify-artifacts.sh`、
  `check-command-parity.py`、`codex-plugin-smoke.sh --selftest` 全部通过。
- 仓库中不再有 `tracker` 字段的写入点与读取点；退役说明与决策记录齐备。

## Open questions

无。`.agent/tracker.json` 的字段与 CLI 短码由实施计划固定，并以正反测试验证。
