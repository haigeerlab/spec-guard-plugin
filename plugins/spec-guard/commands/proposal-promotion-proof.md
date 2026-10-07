---
description: 晋级合并后从远端默认分支只读证明 Proposal module 已按声明纳入能力图
allowed-tools: Bash
---

只在 promotion 已合并到远端默认分支后运行。它会重新读取远端 Proposal 与 Issue 阶段
（`proposal-stage:accepted` 或 `proposal-stage:promoted` 均可，所以标签改成 promoted 后可重跑），再证明：

~~~bash
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
python3 -B "$ROOT/hooks/proposal_promotion_proof.py" \
  --project . --proposal-id "<proposal-id>" \
  --platform "<github|gitlab>" --target "<target>" --prove
~~~

原样报告 JSON。只有 `proved` 才是晋级证明，并给出 promotion commit 与 module id。`not-accepted`
表示 Issue 阶段不是 accepted 或 promoted；`invalid` 表示首次纳入该 module 的提交不符合声明（职责、依赖、
位置），或该提交改动了其他模块行；`stale` 表示晋级提交的父提交上评审已不新鲜（如基线漂移）；
`reviewCommit` 是晋级提交的父提交；`not-promoted` 表示至今
没有任何提交把该 module 纳入远端默认分支的能力图——下一步是合并晋级分支，再重新运行本命令；
`unknown` 表示远端无法安全读取。

`invalid` 且 `diagnostic` 为下列两个码时，结果附带 `promotionCommit`（找到的晋级提交），按码处理：

- `promotion-row-mismatch`：晋级行与 Proposal 声明不符，`mismatchedFields` 列出不符项
  （`responsibility`、`dependsOn`、`position` 的子集，按此顺序）。让能力图里该行与 Proposal 声明一致，
  或修订 Proposal 使其与已合并的行一致，再重新晋级／重跑。
- `promotion-other-rows-changed`：该行相符，但晋级提交还改动了其他模块的行或它们的顺序。
  把与晋级无关的能力图改动从晋级中拆出去，再重新晋级／重跑。

其他 `invalid` 仍是 `promotion-invalid`（或下层具体原因）。

`not-accepted`、`invalid`、`stale`、`unknown` 附带的 `diagnostic` 会尽量透传下层已给出的具体原因（例如
`proposal-baseline-drifted`、`proposal-pool-unknown`），只有没有更具体原因时才是折叠后的
`promotion-<state>`；`not-promoted` 固定是 `promotion-not-found`。详见
`references/proposal-promotion-proof.md`。

`unknown` 且 `diagnostic` 以 `snapshot-` 开头时是**远端快照读不到，不是链路失效**：
`snapshot-head-unavailable` / `snapshot-fetch-failed` 是探测失败（内部已重试三次），什么都没读到、
什么都没变，重跑同一条命令即可；`snapshot-tip-moved` 是远端默认分支在读取中途真的前进了，重跑会钉住
新的 tip，所以事实可能确实不同。两者都不要去改 Proposal 或能力图。
本命令不会把结果写回 Issue，也不创建或修改分支、能力图、Spec、Plan、任务或 PR。
