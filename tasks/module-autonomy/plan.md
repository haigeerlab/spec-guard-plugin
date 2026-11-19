# Plan: module-autonomy

<!-- spec-guard: review approved -->

Spec：[spec/module-autonomy.md](../../spec/module-autonomy.md)（2026-11-19 批准）。

## 架构决定

- **判据只有一处**：`project_config.module_tier(root, module_id) -> (tier, source)`。`map_view` 和外部调用方都调它，不各自合并
  `moduleAutonomy` 与 `autonomyTier`。档位顺序 `TIERS` 已是从严到宽，「宽于项目」直接比下标。
- **校验沿用 config-per-key**：`VALIDATORS["moduleAutonomy"]` 校验整个对象（形状、`capability_map.MODULE_ID`、档位），不合法时整个键
  失效；`load` 不改。`summary` 对它给对象值，未设为 `{}`、来源 `default`。
- **写入**：`_change` 增加可选 `module` 参数，只在 `key == "moduleAutonomy"` 时允许；在现有对象上改一个条目后整体复用原有的预览、
  原子写入、读回流程。命令行 `set`／`unset` 加 `--module`，`set --key moduleAutonomy` 不带 `--module` 退出 2（值必须按条目写）。
- **阶段提示不动**：`config_lines` 只为列出的几个键出行，`moduleAutonomy` 合法时不出行；不合法时照现有规矩出「已忽略」一行。
  只加回归守住，不改 `module_stage.py`。
- **`/map --json`**：`map_view` 给每个模块加 `autonomy`（常量 `AUTONOMY_FIELDS = ("tier", "source", "widerThanProject")`），文字版不变。
- **verify-artifacts**：在现有配置检查后，用一小段 python 读 `moduleAutonomy` 的 id 与能力图比较，能力图上没有的 id 各报一条 ⚠️；
  读不了时不报（配置本身的失效已由 `check` 判）。

## 任务

- **Task 0**：提交已批准的 Spec 与本 Plan、todo。验证：`validate.sh --quick`、本仓库 verify-artifacts 0 失败。
- **Task 1**：`project_config.py` 的校验、`module_tier` 与 `--module` 写入。先在 `test_project_config.py` 写测试并确认失败（AC1、AC2）。
  验证：单测全绿。
- **Task 2**：`/map --json` 的 `autonomy`。`test_map_view.py` 先写 AC3 的例子并确认失败；文字版输出不变的例子守住。验证：单测全绿。
- **Task 3**：阶段提示回归（AC4）与 verify-artifacts 警告（AC5）。`test-phase-guard.sh` 加一段：设与不设 `moduleAutonomy` 输出逐字相同；
  `test-verify-artifacts.sh` 加两例：未知 id 警告不失败、不合法值失败。验证：两套回归全绿。
- **Task 4**：接口 1.14。`interface.json` 新增 `moduleAutonomy` 条目、`mapView` 写明 `autonomy`；`check-interface.py` 核对字段与
  `map_view.AUTONOMY_FIELDS`、`moduleAutonomy.values` 与 `TIERS` 一致；`test-checkers.sh` 加反例。验证：检查器回归绿，改字段名变红（AC6）。
- **Task 5**：说明文字。`commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`（config 与 `/map` 两段）、
  `docs/concepts.md` 自治档位一行。验证：`validate.sh --quick`。
- **Task 6**：版本 0.89.0 与 CHANGELOG（新增、接口 1.14、升级须知）。验证：`check-manifests.py`、`check-readme-sync.py`（AC7）。

## 会改哪些文件

- 新增：`tasks/module-autonomy/{plan,todo}.md`。
- 修改：`hooks/project_config.py`、`hooks/test_project_config.py`、`hooks/map_view.py`、`hooks/test_map_view.py`、`hooks/test-phase-guard.sh`、
  `hooks/verify-artifacts.sh`、`hooks/test-verify-artifacts.sh`、`interface.json`、`scripts/check-interface.py`、`scripts/test-checkers.sh`、
  `commands/config.md`、`skills/spec-guard-ops/SKILL.md`、`docs/commands.md`、`docs/concepts.md`、两份 `plugin.json`、`README.md`、`README.en.md`、`CHANGELOG.md`。
- 新增依赖、锁文件：无。

## 风险

- **`project_config` 的读取方多**（阶段提示、verify-artifacts、config 命令、map）：新键只加进 `VALIDATORS`，`load` 行为不变；
  用「设与不设阶段提示逐字相同」与现有 config 回归守住。
- **旧版本读到新键**：0.68.0–0.88.0 只忽略并警告；0.67.1 及更早整份判无效。说明与 CHANGELOG 写明团队升级后再设。
- **interface 1.14 的读取方**（module-crew、autopr）：只新增字段，旧读取方忽略即可；发版回告写明。

## 检查点

- Checkpoint 1（report）：发布前完整检查（validate、phase-guard、verify-artifacts、smoke 自检、ShellCheck）；变异验证两处
  （`module_tier` 不看 `moduleAutonomy`、`widerThanProject` 恒为假）各让回归变红；临时项目命令行实跑：设一个模块档位 → `/map --json`
  报来源与宽于项目 → `unset` 回到项目档位。记进 todo 后继续。
- Checkpoint 2（gate）：最终验收；通过后推送并开本模块 PR，合并由用户进行。
- 发版（合并后按 Checkpoint 2 授权）：打 tag、发 Release、刷新两个宿主、证据收尾 PR，并回告 autopr-design 与 ecosystem-lead。

## 未决问题

- 无。
