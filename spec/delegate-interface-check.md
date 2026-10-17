# Spec: delegate-interface-check

<!-- spec-guard: review approved a9ecaaedfc47 -->

## Objective

0.65.0 的外部审查提示只看 delegate 装没装、启没启用，命令名 `/delegate:review`、`/delegate:doctor` 写死在 spec-guard 里
（delegate-review-hint 的 D3-A）。当时 delegate 还没发布接口说明。现在 delegate v0.5.3 已在安装目录里带上 `interface.json`：
interface 1.0，`review.command` 为 `/delegate:review`，`doctor.command` 为 `/delegate:doctor`。delegate 负责人约定：只增加可选
字段时升次版本，删字段、改名或改含义时升主版本，建议按 `>=1.0,<2.0` 检查。

本模块让提示按这份接口说明校验版本，并从中取命令名。这样 delegate 以后改名或升主版本时，提示不会写错命令，也不会在接口不兼容时
继续提议。

登记：2026-10-17 经 `/spec-guard:add-module` 插入能力图。来源是 delegate 负责人发布 interface.json 后的对接建议，用户 2026-10-17
在本会话决定排成模块（「把『按 >=1.0,<2.0 读 delegate 的 interface.json』插进能力图，写 Spec 交我审」）。

## Assumptions

1. **只在提示本来要出现时才读。** 也就是处在三个检查点之一、这个模块还没有外部审查记录、delegate 已装并启用。其他时候不多读
   任何文件，每轮注入的开销不变。
2. **读取结果分四种，按 delegate 负责人的建议，「缺文件」和「读取失败」都不当成没装：**

   | 读到的情况 | 提示怎么出 |
   |---|---|
   | interface 在 `>=1.0,<2.0` 内 | 照常出，Claude 侧的命令名取自文件 |
   | 文件不存在（delegate 0.5.2 及更早） | 和现在一样，用默认命令名 |
   | 读不出、不是合法 JSON、`interface` 格式不对 | 和现在一样，用默认命令名 |
   | 主版本不在范围内（`<1` 或 `>=2`） | 不出提示 |

   主版本不兼容时不出提示，是因为这时命令名和报告格式都可能已经变了，提议一个可能不存在的命令比不提更糟。用户想用时，
   仍可以直接调用 delegate。
3. **命令名只接受固定形式。** `review.command`、`doctor.command` 必须完全匹配 `/delegate:` 加小写字母和连字符；不匹配或缺字段时，
   该项用默认值。文件里的其他文字一律不进注入，延续 0.65.0「只代入固定措辞和已校验的值」的规则。
4. **Codex 侧只做版本门槛，不换命令名。** interface.json 写的是 Claude 的斜杠命令；Codex 侧入口仍是 `delegate:delegate-routing`
   和「以 delegate 自己的体检为准」。
5. **Codex 侧怎么找安装目录。** 不调子进程，就没法问 Codex 当前启用的是哪个版本。所以在
   `${CODEX_HOME}/plugins/cache/<市场>/delegate/` 下恰好只有一个版本目录时，才读其中的 interface.json；有多个或一个都没有时，
   保持现有提示，不猜最新的那个。本机实测现在只有 `0.5.0` 一个目录。Claude 侧用插件记录里的 `installPath`，路径是确定的。
6. **提示行的其余措辞不变。** 拒绝标记、「外部审查意见」小节、每模块一次等规则都不变。
7. 版本 0.67.0（提示行为在边界上有变化：接口不兼容时不再出提示），一个 PR。这个分支从 v0.66.0 的证据分支开出（#342 还没合并），
   #342 合并后会自动对上。

## Contract

### `hooks/sibling_plugins.py`

新增 `delegate_review_entry(project, host) -> dict | None`：

- delegate 没装或没启用时返回 None（和现在的 `delegate_enabled` 为 False 时相同）；
- 主版本不兼容时返回 None；
- 其余情况返回 `{"review": <命令>, "doctor": <命令>, "source": "interface" | "default"}`：
  - 版本兼容时，命令取自文件，不合规的那一项用默认值；
  - 文件不存在或读不出时，两项都用默认值。

`delegate_enabled` 保留，供已有调用和测试使用。Codex 侧的市场名从 `config.toml` 的表头取得，与现在的判断同一处。

### `hooks/module_stage.py`

`external_review_hint` 改为调用 `delegate_review_entry`：返回 None 就不出提示；Claude 侧用返回的命令名拼出原措辞；Codex 侧措辞
不变。`COMMANDS` 里写死的 delegate 命令保留作默认值。

### 文档

- `references/workflow-checkpoints.md`「外部审查意见」一节补一句：装了 delegate 但它的接口主版本不兼容时，不出提示。
- `docs/design.md` 的 `sibling_plugins.py` 一行补上：会读 delegate 的 interface.json，按 `>=1.0,<2.0` 校验。
- CHANGELOG 记一条「变更」。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_sibling_plugins.py
/bin/bash plugins/spec-guard/hooks/test-phase-guard.sh
/bin/bash scripts/validate.sh
```

## Testing strategy

- **`test_sibling_plugins.py` 先写失败的测试：**
  - Claude 侧：interface 1.0 → 命令取自文件；1.7 → 仍兼容；2.0 和 0.9 → None；文件不存在 → 默认值；不是合法 JSON → 默认值；
    `review.command` 为 `rm -rf /` 或 `/other:review` → 该项用默认值；没装 → None。
  - Codex 侧：一个版本目录且 interface 1.0 → 返回值；一个版本目录且 interface 2.0 → None；两个版本目录 → 默认值；
    没有版本目录 → None（等同现在「缓存目录不存在」判为没装）。
- **`test-phase-guard.sh` 第 17 段补正反例：**
  - 夹具里的 delegate 带 interface 1.0、命令名改为 `/delegate:review2` → 提示里出现 `/delegate:review2`；
  - interface 2.0 → 不出提示；
  - 没有 interface.json → 和现在逐字相同。
- 改坏验证：把版本范围改成 `<3.0`，确认「2.0 不出提示」那例变红，再复原。
- 发版后：本机把 delegate 升到 0.5.3，在两个宿主的已安装副本上看检查点提示；Claude 侧来源应为 interface。

## Boundaries

- Always：读不到或读不懂时保持现有提示；不调子进程；文件里只有通过校验的命令名进注入。
- Ask first：读 interface.json 里的其他字段（backends、report 等）；在提示里报告 delegate 的版本或状态；Codex 侧在多个版本目录里
  推断当前版本。
- Never：把「缺文件」或「读取失败」报成没装；把 delegate 写成依赖；运行 delegate 的任何脚本。

## Success criteria

1. delegate 的接口为 1.x 时，Claude 侧的提示命令取自它的 interface.json；接口主版本不兼容时，不出提示。
2. delegate 0.5.2 及更早（没有这个文件）和文件损坏时，提示与 0.66.0 逐字相同。
3. 不合规的命令名不会进入注入；阶段提示每轮不调子进程。

<!-- spec-guard: external-review declined -->
