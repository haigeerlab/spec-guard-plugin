# Spec: agent-relay-interface-2

## Objective

Spec Guard 用 `hooks/agent_relay_probe.py` 只读地检测 agent-relay，现在只接受接口 `>=1.0,<2.0`。agent-relay 0.6.0 会把接口
升到 2.0（第二轮联调修复批次，破坏性变更），届时用户装了新版 agent-relay，Spec Guard 会报 `incompatible`。本模块把
接受范围放宽到 `>=1.0,<3.0`，并作为 0.56.0 的最后一个模块，在同一个 PR 里带上 0.56.0 的发版改动。来源：第二轮联调
提议，用户 2026-10-09 在本会话直接确认"加进 0.56.0"；排期上 0.56.0 须先于 agent-relay 0.6.0 发布。

读者：同时使用 Spec Guard 与 agent-relay 的开发者；本仓库维护者。

## 现状与查证（2026-10-09）

- `agent_relay_probe.py`：`REQUIRED = ">=1.0,<2.0"`、`MIN_VERSION, MAX_VERSION = (1, 0), (2, 0)`，判定为
  `MIN_VERSION <= version < MAX_VERSION`；文件头说明、`test_agent_relay_probe.py` 两处断言（`required` 字段与
  incompatible 消息）、`docs/collaboration-interface.md:15`、`docs/migrations/2026-10-07-collaboration-split.md:29`
  写着同一范围。`spec/collaboration-boundary.md` 是已完成模块的历史 Spec，不改。
- Spec Guard 对 agent-relay 只依赖两样：插件根目录 `interface.json` 的 `interface` 版本号，与其中可选的 `status`
  命令（输出 `{"ready": …, "setup": …}`）。不调用任何信箱工具。
- agent-relay 主线当前接口 1.4；接口 2.0 尚未发布。已知的第一项破坏性改动在 agent-relay PR #56：`bridge_send`
  的结果不再回显正文——属于信箱工具，Spec Guard 不用。按 agent-relay 的约定，`interface.json` 在这一批最后一个模块
  才升到 2.0。

## Assumptions

用户 2026-10-09 批准：

1. **前提**：接口 2.0 不改 `interface.json` 的格式与 `status` 命令的约定（字段、输出、语义）。agent-relay 的负责会话
   （"你好"）2026-10-09 确认：这一批对 `interface.json` 唯一的计划改动是把 `"interface"` 从 `"1.4"` 改为 `"2.0"`（仍为
   x.y，在最后一个模块里改），`status` 仍为 `["python3", "-B", "hooks/relay_status.py"]`，`relay_status.py` 的输出
   `{"ready": bool, "setup": str}` 与含义不变；后续若要改这两样会先停下通知。本会话核对：`09b317a` 到
   `origin/claude/long-messages` 之间这两个文件 diff 为空。若前提将来不成立，本模块的放宽要另行评审适配。
2. **范围**：`>=1.0,<3.0`。`2.x` 判为 `ready`（其余条件照旧），`3.0` 及以上与 `1.0` 以下判 `incompatible`，`1.x` 行为
   不变；`required` 字段与 incompatible 消息里的范围文字随之改为 `>=1.0,<3.0`。只改两个常量，不改判定逻辑。
3. **回归**：现有"范围外判 incompatible"用例的取值由 `0.9、2.0` 改为 `0.9、3.0`（另加 `3.1`）；新增 `2.0`、`2.4`
   判 `ready`；两处范围断言改为新文字；1.x 各用例不动。变异：上限改回 `(2, 0)` 时 `2.0` 用例变红；上限改为 `(4, 0)`
   时 `3.0` 用例变红。
4. **文档**：探针文件头说明、`docs/collaboration-interface.md:15`、迁移说明 `:29` 改为新范围；迁移说明里"接口 1.x
   内各自升级即可"一句改为"接口 1.x、2.x 内"。
5. **随 0.56.0 发出**（按 docs/release-process.md"版本号放在最后一个模块的 PR"）：
   - 两份清单版本号与中英 README 的 `--ref` 改为 0.56.0；
   - CHANGELOG `[0.56.0]`：修复（codex-command-wording）、兼容（本模块）、维护者工具（validate-parallel-files、
     verify-and-commit-untracked-warning、phase-guard-test-parallel）；
   - 拣入未进 main 的 `a54ecdc`（phase-guard-test-parallel 的 CI 耗时记录）；
   - 勾掉四个模块已合并的 Checkpoint 1 与写 CHANGELOG 的项；要在安装副本上核验的项留到发版后的证据 PR。

## Requirements

1. 按假设 2 改探针常量与说明；按假设 3 补回归并做变异证明；按假设 4 改文档。
2. 按假设 5 带上 0.56.0 的发版改动。

## Commands

```bash
python3 -B plugins/spec-guard/hooks/test_agent_relay_probe.py
/usr/bin/python3 -B plugins/spec-guard/hooks/test_agent_relay_probe.py
/bin/bash scripts/validate.sh
```

## Boundaries

- Always：探针仍只读；检测失败仍报 `unknown`，不当作"未安装"。
- Ask first：推送、PR；假设 1 不成立时的任何适配；改 agent-relay 仓库。
- Never：放宽到不设上限；为通过检测改动 agent-relay 的 `interface.json`。

## Success criteria

1. 接口 2.x 判 `ready`，3.0 及以上判 `incompatible`，1.x 不变；回归与变异证明通过。
2. 0.56.0 的发版改动齐全，`check-readme-sync.py` 等检查通过。

## Open questions

无。
