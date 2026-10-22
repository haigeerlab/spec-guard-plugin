---
description: 只读的模块进度表：按开发顺序看每个模块的状态（含挂起原因、阻塞等谁）、审查状态与关键卡点；可输出 JSON
argument-hint: "[--all] [--json]"
allowed-tools: Bash
---

阶段交接、确认或停止前，读取并遵循 `spec-guard-ops` 的共享检查点规则；按实际路径预告下一步，已有授权不重复询问。

只读：读能力图、各模块的 Spec／Plan／todo、`.agent/state.json` 与本地 git 引用，不写文件、不联网、不 fetch。

```bash
ROOT="${CLAUDE_PLUGIN_ROOT}"
[ -n "$ROOT" ] || ROOT="${PLUGIN_ROOT:-}"
WHY="宿主没有把插件根目录代入命令，环境里也没有 CLAUDE_PLUGIN_ROOT 或 PLUGIN_ROOT"
if [ -z "$ROOT" ]; then
  if ! command -v codex >/dev/null 2>&1; then
    WHY="${WHY}；也没有 codex 可查询"
  else
    LIST="$(codex plugin list --available --json 2>/dev/null)"; RC=$?
    ROOT="$(printf '%s' "$LIST" | python3 -c '
import json, sys
try:
    plugins = json.load(sys.stdin).get("installed", [])
except (AttributeError, TypeError, ValueError):
    sys.exit(3)
for plugin in plugins:
    if isinstance(plugin, dict) and plugin.get("name") == "spec-guard" and plugin.get("installed") and plugin.get("enabled"):
        source = plugin.get("source")
        path = source.get("path") if isinstance(source, dict) else None
        if isinstance(path, str) and path:
            print(path)
            sys.exit(0)
sys.exit(4)
')"
    case $? in
      0) ;;
      4) WHY="${WHY}；codex plugin list 没有列出已启用且带路径的 spec-guard" ;;
      *) WHY="${WHY}；codex plugin list 查询失败（退出码 ${RC}）或输出无法解析" ;;
    esac
  fi
fi
[ -n "$ROOT" ] || { echo "spec-guard 无法定位插件根目录：${WHY}。这是定位失败，不代表插件未安装。" >&2; exit 2; }
[ -d "$ROOT" ] || { echo "spec-guard 插件根目录不存在：${ROOT}（插件可能刚更新或被移除，重开会话后再试）。" >&2; exit 2; }
FROM="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PROJECT="$(python3 -B "$ROOT/hooks/project_link.py" follow --from "$FROM" --session "${CLAUDE_CODE_SESSION_ID:-}")" || exit 2
python3 -B "$ROOT/hooks/map_view.py" --project "$PROJECT" $ARGUMENTS
```

有项目指向时 `follow` 会跟随到被指向的项目：stderr 出现「本次操作的是被指向的项目」时，回复用户时照原文转述这一句；它退出 2 时照原文报告诊断，不要改用会话目录重试。

**把表格原样给用户**（它本身就是给人看的），不要改写成段落或另做总结；用户问到某一行再解释。

- 表头：合计、**关键卡点**（挂起的模块和它按依赖链挡住的模块）、**待批准**的 Spec／Plan、当前模块的下一个 `gate`、
  还没合进主线与还没推送的提交数（"判断不了"表示没有远端或上游，不是 0）。
- 状态：✅ 已完成；🔨 进行中（写 Spec／写 Plan／已勾数/总数）；⏸ 挂起（原因）；⛔ 阻塞：等某个被挂起的模块；
  🟢 可以开始；○ 未就绪：缺哪个依赖。"阻塞"只指被挂起的模块挡住，外部等待（等人交付、等审查结论）这里看不到。
- 进行中与挂起两格带"距今多久"（上次勾选几天前、已挂几天），取自已提交的 git 历史；工作区里没提交的勾选看不到。
  表头末行注明浅克隆或没有 git 历史时这两项不全或不显示。只给时间，不判断算不算卡住。JSON 另有每个模块第一次勾选的
  时间与勾选过的提交次数，供其他插件自己算这个模块平时的节奏。
- 工作区比 HEAD 多勾了几项时，进行中一格再加"N 项勾选未提交（最后一次提交几天前）"，同样不设阈值。JSON 里对应每个模块的
  `uncommittedTicks` 与 `startedAt`（第一次提交 Spec 的时间；Spec 批准后才提交的项目，它会比实际开工晚）、`head.committedAt`，以及顶层 `reviewCadence`（批准节奏的生效值
  与来源，和 `/spec-guard:config` 一致）。每个模块还有 `gates`：todo 里 gate 检查点的总数与已勾数（标 gate 的算，report 不计，没标级别的只有
  最后一个检查点算；最终验收通常已在其中；没有 todo 时为 `null`），表格不显示。含义见 `interface.json` 的 `progressFacts`。
- 已完成与未就绪的模块默认折叠；`--all` 全部展开。
- `--json` 给全量、不折叠的机器可读结果（`schemaVersion` 1，字段与稳定性承诺见 `spec/map-view.md` 的 Contract），
  供其他插件读取；给用户看时用表格。
- 退出码：3 表示这个项目没有能力图（没启用多模块约定），4 表示能力图或模块文件读不出（先跑
  `/spec-guard:verify-artifacts`），2 是参数或项目路径错误。

想看某个挂起的原因却显示"未记原因"：用 `/spec-guard:module-suspend` 带 `--reason` 补一行，原因只按用户说的写。
