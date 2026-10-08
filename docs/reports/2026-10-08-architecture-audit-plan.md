# 多维度架构审查计划（2026-10-08，已批准）

本文件是审查**计划**，不是报告。计划获批后执行，结论写入 `docs/reports/2026-10-08-architecture-audit.md`，
按 [docs/reports/README.md](README.md) 的最低内容要求组织。

## 基线与范围

- 基线：`origin/main` `7ea9130`（v0.52.0 发布并完成证据之后），worktree
  `.claude/worktrees/great-bouman-4da4d6` 分离在该提交、工作区干净。
- 范围：`plugins/spec-guard/`（hooks 96 个文件、命令与 skill 28 个、templates、references、清单）、
  `scripts/`、`evals/`、`.github/workflows/`、`docs/`（只看与代码的一致性）。
- 不在范围：agent-relay 仓库本身（只看 Spec Guard 一侧的 `agent_relay_probe.py` 与边界检查）；
  任何远端写入、真实账本写入、宿主配置修改；10-05 审计已收口的 12 项不重审，除非发现回归。

## 假设（用户 2026-10-08 确认）

1. 只读审查，只产出报告；修复另按 add-module 逐个开模块，由用户从报告中挑选。
2. 六个维度（下文 D1–D6）。
3. 维度扫描派给 Codex 只读执行，经 delegate 插件（`/delegate:delegate`，`delegate@delegate-marketplace`）；主会话负责
   汇总、逐条核验和写报告。计划于 2026-10-08 获用户批准。
4. 在干净上下文中执行（新会话或 `/clear` 之后），本计划是新会话的入口。

## 维度与要回答的问题

每个维度都以 [docs/lenses.md](../lenses.md) 为判据来源，发现要注明对应条目（如 A2、C5）。

| 维度 | 要回答的问题 | 重点位置 |
|---|---|---|
| **D1 架构边界与耦合** | hooks 的分层是否清楚（入口 hook、共享库、命令脚本、测试）；有无循环导入、跨层直接调用；协作拆分与 handoff 退役后有无死代码、孤儿函数、只剩测试在用的模块；共享判据是否只有一个实现 | `hooks/*.py` 的导入图、`phase-guard.sh`、`module_stage.py`、`capability_map.py`、`spec-digest.py`、`scripts/check-collaboration-boundary.py` |
| **D2 不变量** | CLAUDE.md「不变量」逐条是否被代码守住、是否有检查器或测试守住：默认不生效、探测失败降级、hook 只读、唯一指纹算法、不依赖 jq、共享判据两边同改、输出合法 JSON、不用 `cmd \| grep -q`、`/bin/bash` 3.2 兼容与 `${VAR}` 多字节规则 | `hooks/*.sh`、`phase-guard.sh`、`verify-artifacts.sh`、`scripts/validate.sh` |
| **D3 双宿主一致性** | Claude 命令与 Codex `spec-guard-ops` 各节是否一一对应、参数与行为一致；两份清单、`hooks.json`、模板约定块是否同步；17 个命令的规范引导段是否一致；文档里的命令对照表是否与实际一致 | `commands/`、`skills/*/SKILL.md`、`.claude-plugin/`、`.codex-plugin/`、`hooks/hooks.json`、`templates/`、`docs/workflow.md` |
| **D4 测试与判据有效性** | 有无"全绿但没断言"（A2c）、零的两种成因分不开（A5）、断言粒度太粗（B1b）、只在一个配置下验证（B1）；`validate.sh` 是否跑到了全部测试文件；有无依赖源码仓库或真实环境的测试；挑 3–5 个关键判据做手工变异抽查是否会红 | `hooks/test*`、`scripts/validate.sh`、`scripts/test-checkers.sh`、`evals/` |
| **D5 安全与本机数据** | 子进程调用（`shell=True`、参数拼接）、路径穿越与符号链接、写入文件的权限、仓库内容进入 hook 注入前的净化、需要确认的写操作是否真有门禁、gh/glab 调用的凭据处理 | 所有调用 `subprocess`/`os.system` 的文件、`local_ticket_*`、`proposal_*` 写路径、`phase_context` 净化 |
| **D6 冗余与过度设计** | 没有消费者的功能、重复实现、文档与代码分叉（D1 两份真相源）、已退役内容的残留；对任何"建议删除"，先列出本机其他项目是否在用（只读 grep，结果只进报告给用户看，不写进仓库） | 全仓；跨项目检查只读 `~/Documents/haigeerlab/*` 的约定块与命令引用 |

## 执行方式

### 派活（Codex 只读）

- 派活前先跑一次 `/delegate:doctor`，确认 Codex 接入正常；不正常就停下报告，不换通道。
- 每个维度一次 `/delegate:delegate --model gpt-5.6-sol --effort high`，只读，工作目录为上述 worktree；
  同时最多 3 个，共 6 次，每次放在后台运行（不受单条前台命令 10 分钟上限约束），完成后回收。花的是 Codex 额度。
- 某个维度在核验中需要多轮追问时，才针对该维度改用 agent-relay 的 session-delegation 开一个只读审查会话；
  不为此改变其余维度的方式。
- 每次的提示词包含：基线提交、该维度的问题与重点位置、lenses 的相关条目、本计划「不在范围」一节，以及固定输出格式：

  ```
  ID: D<n>-<序号>
  严重程度: high | medium | low | info
  位置: <文件:行>（可多个）
  问题: 一句话
  证据: 代码摘录或命令输出（不超过 10 行）
  复现/验证方法: 可执行的命令或步骤；做不到写"仅源码推导"
  对应 lens: <条目或"无">
  把握: confirmed（跑过）| inferred（源码推导）
  ```

- 明确禁止：写文件、提交、联网（连接 Codex 服务除外）、读取会话记录正文、读取或输出凭据。

### 核验（主会话）

- 每条发现由我复核：`confirmed` 的重跑复现；`inferred` 的读代码确认或写临时夹具验证，做不到就降级为「未验证」并在报告里标明。
- 合并重复项、剔除误报（误报和理由也记入报告附录，防止下次重复提出）。
- 严重程度口径：**high** = 破坏不变量、可能误删或泄露数据、把环境故障报成事实；**medium** = 宿主不一致、判据可绕过、测试守不住；**low** = 冗余、文档漂移、可读性；**info** = 观察，不建议修。

### 产出

`docs/reports/2026-10-08-architecture-audit.md`：范围与基线、方法（含 Codex 派活记录与模型）、
按严重程度排序的问题清单（每项带核验状态、收口条件、建议归属模块）、建议修复顺序、误报附录、
未验证边界。报告与本计划一起走一个文档 PR，由用户合并；之后修复按模块逐个立项。

## 检查点

1. **本计划评审（gate）**：用户批准后才派活。
2. **派活回收（report）**：6 份结果回来后，告诉用户原始发现数与 Codex 实际用的模型，直接进入核验。
3. **报告评审（gate）**：核验完的报告给用户看；批准后开文档 PR（推送与开 PR 由此批准授权，合并归用户）。

## 成本

- Codex：6 次 `gpt-5.6-sol` high 只读任务。
- Claude：汇总与核验在主会话；预计核验占大头。核验时用 `sed -n` 取局部、只看需要的行，不整份读入日志。
