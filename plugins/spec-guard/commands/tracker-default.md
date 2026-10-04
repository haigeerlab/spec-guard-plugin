---
description: 查看或按明确确认设置项目默认的事项后端与精确目标；默认只预填预览，不决定也不执行任何写入
allowed-tools: Bash
---

阶段交接、确认或停止前，读取并遵循 `spec-guard-ops` 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问。

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
if [ -z "$ROOT" ] && command -v codex >/dev/null 2>&1; then
  ROOT="$(codex plugin list --available --json 2>/dev/null | python3 -c '
import json, sys
try:
    plugins = json.load(sys.stdin).get("installed", [])
except (TypeError, ValueError):
    plugins = []
for plugin in plugins:
    if plugin.get("name") == "spec-guard" and plugin.get("installed") and plugin.get("enabled"):
        source = plugin.get("source")
        path = source.get("path") if isinstance(source, dict) else None
        if isinstance(path, str) and path:
            print(path)
            break
')"
fi
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "spec-guard 插件未安装或未启用" >&2; exit 2; }
PROJECT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
python3 -B "$ROOT/hooks/tracker_default.py" show --project "$PROJECT" --format json
```

## 这个默认值是什么

它回答一个问题：**这个项目的新事项默认写去哪。** 取值是 `local`、`github` 或 `gitlab`，
连同一个精确目标，存在 `.agent/tracker.json`。

| 后端 | 精确目标 |
|---|---|
| `github` | `{"host": "<主机>", "repo": "<owner>/<name>"}` |
| `gitlab` | `{"host": "<主机>", "projectId": <正整数>}` |
| `local` | `{"projectId": "<Epiq projectId>"}` |

GitLab 用正整数 project id，与 Proposal 命令的 `--target` 形态一致，全仓库只有这一种写法。

## 它不是什么

- **不是权威。** 它只在调用方没有显式给出后端与目标时**预填预览**。预览始终完整显示后端和
  精确目标，并注明来源是 `explicit` 还是 `project-default`；每一次外部写入仍然逐次授权。
- **不改变已有事项。** 已经创建的事项绑定在它创建时的后端与目标上。改默认值只影响**此后新建**
  的事项，不移动、不复制、不关闭任何既有事项。要把一条事项换到另一个平台，走
  `/spec-guard:local-ticket-portability` 的显式交接。
- **不是激活信号。** 这个文件在不在，与阶段提示是否注入完全无关。激活信号是 `CLAUDE.md`／
  `AGENTS.md` 里的声明块，或 `.agent/state.json` 中的 `activeModule`。
- **不决定共享事实。** 能力图结构、Proposal 正文与 baseline、晋级提交、Spec/Plan/todo 的位置
  与完成判据，全都只来自远端默认分支与本地文件，与后端无关。

## 读到的状态

- `configured` —— 有可用默认值，给出后端与规范化后的目标；
- `absent` —— 没有这个文件。**不是错误**，只表示没有默认值，调用方须逐次显式给出目标；
- `invalid` —— 文件存在但不可用（JSON 坏、版本不是 1、后端未知、目标形状不符、有多余字段）。
  诊断码 `tracker-default-invalid`。**绝不会被当成 `absent`**，免得一个拼写错误被读成「没配过」。

`invalid` 时照实报告并指出要修哪一项，不要替用户猜一个默认值。

## 设置或切换

先预览，确认后再加 `--confirm`：

```bash
python3 -B "$ROOT/hooks/tracker_default.py" set --project "$PROJECT" \
  --backend github --host github.com --repo owner/name
```

```bash
python3 -B "$ROOT/hooks/tracker_default.py" set --project "$PROJECT" \
  --backend gitlab --host gitlab.example.com --project-id 17
```

```bash
python3 -B "$ROOT/hooks/tracker_default.py" set --project "$PROJECT" \
  --backend local --project-id 01XXXXXXXXXXXXXXXXXXXXXXXX
```

不带 `--confirm` 只打印改前/改后的差异，**什么都不写**；`--confirm` 只原子写回
`.agent/tracker.json` 这一个文件（保留既有权限），不碰 `.agent/state.json`、`spec/`、
`tasks/` 或 Git。目标形状不合法时退出码 2 且不写文件。

典型场景是平台不可用时的紧急切换：把默认改成 `local`，此后**新建**的事项走本地账本；
已经开在 GitHub 上的事项仍绑定在 GitHub，命令会如实报告它们当前读不到，不会在本地重建一条。
