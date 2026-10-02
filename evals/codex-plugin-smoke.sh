#!/usr/bin/env bash
# Codex 插件真实宿主 smoke。--selftest 只验证判决器，绝不调用 Codex。
# 退出码：0=宿主机器记录含有效阶段注入；1=行为失败；2=未观察到执行或环境未就绪。
set -uo pipefail

MODE=run
PLUGIN_ID=""
EXPECTED_SOURCE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --selftest) MODE=--selftest; shift ;;
    --plugin-id)
      [ "$#" -ge 2 ] || { echo '缺少 --plugin-id 的值' >&2; exit 2; }
      PLUGIN_ID="$2"; shift 2
      ;;
    --expected-source)
      [ "$#" -ge 2 ] || { echo '缺少 --expected-source 的值' >&2; exit 2; }
      EXPECTED_SOURCE="$2"; shift 2
      ;;
    *) echo "用法: $0 [--selftest] [--plugin-id <id> --expected-source <plugin-dir>]" >&2; exit 2 ;;
  esac
done

plugin_state() { # $1=插件清单 $2=目标插件 ID（可选）$3=候选插件目录（可选）
  python3 - "$1" "${2:-}" "${3:-}" <<'PY'
import json
import os
import sys

try:
    with open(sys.argv[1]) as f:
        plugins = json.load(f).get("installed", [])
except (OSError, ValueError, TypeError):
    print("unknown")
    raise SystemExit

plugin_id, expected_source = sys.argv[2:]
candidates = [
    plugin for plugin in plugins
    if plugin.get("name") == "spec-guard" and plugin.get("installed") is True
]
if plugin_id:
    candidates = [plugin for plugin in candidates if plugin.get("pluginId") == plugin_id]
if not candidates:
    print("missing")
    raise SystemExit
enabled = [plugin for plugin in candidates if plugin.get("enabled") is True]
if not enabled:
    print("disabled")
    raise SystemExit
if len(enabled) != 1:
    print("ambiguous")
    raise SystemExit
plugin = enabled[0]
if expected_source:
    installed_source = (plugin.get("source") or {}).get("path")
    if not isinstance(installed_source, str) or os.path.realpath(installed_source) != os.path.realpath(expected_source):
        print("source-mismatch")
        raise SystemExit
print("ready")
PY
}

# codex exec 会把运行目录记为受信任项目（实测加 -c 覆盖也照样写入），smoke 结束后临时目录已删除，
# 这条记录就成了残留。只删除本次新增、且内容只有 trust_level = "trusted" 的那张表。
forget_project_trust() { # $1=Codex config.toml $2=项目真实路径
  python3 - "$1" "$2" <<'PY'
import os
import sys
import tempfile

path, project = sys.argv[1:]
if os.path.islink(path) or not os.path.isfile(path):
    raise SystemExit
with open(path, encoding="utf-8") as handle:
    lines = handle.read().split("\n")
header = '[projects."%s"]' % project
kept, removed, i = [], False, 0
while i < len(lines):
    if lines[i].strip() == header:
        j = i + 1
        while j < len(lines) and not lines[j].lstrip().startswith("["):
            j += 1
        if [line.strip() for line in lines[i + 1:j] if line.strip()] == ['trust_level = "trusted"']:
            removed, i = True, j
            continue
    kept.append(lines[i])
    i += 1
if removed:
    descriptor, temporary = tempfile.mkstemp(prefix=".config.toml.", dir=os.path.dirname(path))
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write("\n".join(kept))
    os.chmod(temporary, os.stat(path).st_mode & 0o777)
    os.replace(temporary, path)
PY
}

print_plugin_repair() {
  echo "     codex plugin marketplace add /path/to/spec-guard-plugin"
  echo "     codex plugin add spec-guard@spec-guard-marketplace"
}

grade() { # $1=exec 机器事件；$2=消费者目录、$3=会话目录（真实运行时）；模型回复不算证据
  python3 - "$1" "${2:-}" "${3:-}" <<'PY'
import json
import os
from pathlib import Path
import re
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        events = [json.loads(line) for line in handle if line.strip()]
except (OSError, UnicodeError, ValueError):
    print("  ⏭  无法读取 Codex 机器事件；没有宿主 hook 结论")
    raise SystemExit(2)

observed = False
stage = re.compile(r"当前阶段:\s*\*\*(?:IDLE|MAP_ONLY|NEEDS_SPEC|NEEDS_PLAN|BUILDING|MODULE_DONE|DONE)\*\*")
for event in events:
    if not isinstance(event, dict):
        continue
    output = event.get("hookSpecificOutput")
    if output is None and str(event.get("type", "")).startswith("hook."):
        nested = event.get("output")
        if isinstance(nested, dict):
            output = nested.get("hookSpecificOutput")
    if not isinstance(output, dict) or output.get("hookEventName") != "UserPromptSubmit":
        continue
    observed = True
    context = output.get("additionalContext")
    if isinstance(context, str) and "## spec-guard local workflow" in context and stage.search(context):
        print("  ✅ Codex 机器事件包含有效的 spec-guard 阶段注入")
        raise SystemExit(0)

if observed:
    print("  ❌ hook 已执行，但没有有效的 spec-guard 阶段注入")
    raise SystemExit(1)

# exec --json 不一定公开 hook 事件；只读取本次 thread id 对应的宿主会话记录。
project, sessions = sys.argv[2:]
ids = [event.get("thread_id") for event in events
       if isinstance(event, dict) and event.get("type") == "thread.started"]
if project and sessions and len(ids) == 1 and isinstance(ids[0], str) \
        and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", ids[0]):
    matches = list(Path(sessions).glob(f"**/*-{ids[0]}.jsonl"))
    if len(matches) == 1 and matches[0].is_file() and not matches[0].is_symlink():
        try:
            with matches[0].open(encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle if line.strip()]
        except (OSError, UnicodeError, ValueError):
            records = []
        metadata = [record["payload"] for record in records
                    if isinstance(record, dict) and record.get("type") == "session_meta"
                    and isinstance(record.get("payload"), dict)]
        if len(metadata) == 1 and metadata[0].get("id") == ids[0] \
                and metadata[0].get("source") == "exec" \
                and isinstance(metadata[0].get("cwd"), str) \
                and os.path.realpath(metadata[0]["cwd"]) == os.path.realpath(project):
            contexts = []
            for record in records:
                if not isinstance(record, dict) or record.get("type") != "response_item":
                    continue
                item = record.get("payload", {})
                if not isinstance(item, dict) or item.get("type") != "message" or item.get("role") != "developer":
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "input_text" \
                            and isinstance(part.get("text"), str) \
                            and "## spec-guard local workflow" in part["text"]:
                        contexts.append(part["text"])
            if contexts:
                if all(stage.search(context) for context in contexts):
                    print("  ✅ Codex 会话机器记录包含有效的 spec-guard 阶段注入")
                    raise SystemExit(0)
                print("  ❌ 宿主已注入 spec-guard 上下文，但阶段事实无效")
                raise SystemExit(1)

print("  ⏭  未观察到宿主 hook 事件或匹配的会话注入；模型复述不能证明 hook 执行")
types = sorted({event.get("type", "<missing>") for event in events
                if isinstance(event, dict) and isinstance(event.get("type"), str)})
if types:
    print("  观察到的机器事件类型: " + ", ".join(types))
raise SystemExit(2)
PY
}

selftest() {
  local rc
  SMOKE_TMP="$(mktemp -d)"; trap 'rm -rf "$SMOKE_TMP"' EXIT
  printf '%s\n' '{"type":"hook.completed","hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"## spec-guard local workflow\n当前阶段: **NEEDS_PLAN**"}}' > "$SMOKE_TMP/valid"
  grade "$SMOKE_TMP/valid"; rc=$?
  [ "$rc" -eq 0 ] || return 1
  printf '%s\n' '{"type":"item.completed","item":{"type":"agent_message","text":"当前阶段：IDLE"}}' > "$SMOKE_TMP/model-echo"
  grade "$SMOKE_TMP/model-echo"; rc=$?
  [ "$rc" -eq 2 ] || return 1
  python3 - "$SMOKE_TMP/model-json" <<'PY'
import json
import sys
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump({"type": "item.completed", "item": {"type": "agent_message",
              "text": '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit"}}'}}, handle)
PY
  grade "$SMOKE_TMP/model-json"; rc=$?
  [ "$rc" -eq 2 ] || return 1
  mkdir -p "$SMOKE_TMP/consumer" "$SMOKE_TMP/sessions/2026/10/02"
  python3 - "$SMOKE_TMP" <<'PY'
import json
import os
import sys

root = sys.argv[1]
thread_id = "01a0fa36-50b0-7be1-af18-f533b846423c"
with open(os.path.join(root, "rollout-events"), "w", encoding="utf-8") as handle:
    handle.write(json.dumps({"type": "thread.started", "thread_id": thread_id}) + "\n")
rollout = os.path.join(root, "sessions", "2026", "10", "02", f"rollout-selftest-{thread_id}.jsonl")
records = [
    {"type": "session_meta", "payload": {"id": thread_id, "cwd": os.path.join(root, "consumer"), "source": "exec"}},
    {"type": "response_item", "payload": {"type": "message", "role": "developer", "content": [
        {"type": "input_text", "text": "## spec-guard local workflow\n当前阶段: **NEEDS_PLAN**"}
    ]}},
]
with open(rollout, "w", encoding="utf-8") as handle:
    for record in records:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
with open(os.path.join(root, "rollout-invalid"), "w", encoding="utf-8") as handle:
    for record in [records[0], {**records[1], "payload": {**records[1]["payload"], "content": [
        {"type": "input_text", "text": "## spec-guard local workflow\n当前阶段: **BROKEN**"}
    ]}}]:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
with open(os.path.join(root, "rollout-model-echo"), "w", encoding="utf-8") as handle:
    for record in [records[0], {**records[1], "payload": {**records[1]["payload"], "role": "assistant"}}]:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
PY
  grade "$SMOKE_TMP/rollout-events" "$SMOKE_TMP/consumer" "$SMOKE_TMP/sessions"; rc=$?
  [ "$rc" -eq 0 ] || return 1
  grade "$SMOKE_TMP/rollout-events" "$SMOKE_TMP/other" "$SMOKE_TMP/sessions"; rc=$?
  [ "$rc" -eq 2 ] || return 1
  mv "$SMOKE_TMP/sessions/2026/10/02/rollout-selftest-01a0fa36-50b0-7be1-af18-f533b846423c.jsonl" "$SMOKE_TMP/sessions/held.jsonl"
  grade "$SMOKE_TMP/rollout-events" "$SMOKE_TMP/consumer" "$SMOKE_TMP/sessions"; rc=$?
  [ "$rc" -eq 2 ] || return 1
  mv "$SMOKE_TMP/rollout-invalid" "$SMOKE_TMP/sessions/2026/10/02/rollout-selftest-01a0fa36-50b0-7be1-af18-f533b846423c.jsonl"
  grade "$SMOKE_TMP/rollout-events" "$SMOKE_TMP/consumer" "$SMOKE_TMP/sessions"; rc=$?
  [ "$rc" -eq 1 ] || return 1
  mv "$SMOKE_TMP/rollout-model-echo" "$SMOKE_TMP/sessions/2026/10/02/rollout-selftest-01a0fa36-50b0-7be1-af18-f533b846423c.jsonl"
  grade "$SMOKE_TMP/rollout-events" "$SMOKE_TMP/consumer" "$SMOKE_TMP/sessions"; rc=$?
  [ "$rc" -eq 2 ] || return 1
  printf '%s\n' '{"installed":[]}' > "$SMOKE_TMP/missing-plugin.json"
  [ "$(plugin_state "$SMOKE_TMP/missing-plugin.json")" = missing ] || return 1
  printf '%s\n' '{"installed":[{"name":"spec-guard","installed":true,"enabled":false}]}' > "$SMOKE_TMP/disabled-plugin.json"
  [ "$(plugin_state "$SMOKE_TMP/disabled-plugin.json")" = disabled ] || return 1
  printf '%s\n' '{"installed":[{"name":"spec-guard","installed":true,"enabled":true}]}' > "$SMOKE_TMP/ready-plugin.json"
  [ "$(plugin_state "$SMOKE_TMP/ready-plugin.json")" = ready ] || return 1
  printf '%s\n' '{"installed":[{"pluginId":"spec-guard@stable","name":"spec-guard","installed":true,"enabled":true,"source":{"path":"/tmp/stable"}},{"pluginId":"spec-guard@candidate","name":"spec-guard","installed":true,"enabled":true,"source":{"path":"/tmp/candidate"}}]}' > "$SMOKE_TMP/ambiguous-plugin.json"
  [ "$(plugin_state "$SMOKE_TMP/ambiguous-plugin.json")" = ambiguous ] || return 1
  [ "$(plugin_state "$SMOKE_TMP/ambiguous-plugin.json" spec-guard@candidate /tmp/candidate)" = ready ] || return 1
  [ "$(plugin_state "$SMOKE_TMP/ambiguous-plugin.json" spec-guard@candidate /tmp/other)" = source-mismatch ] || return 1
  printf '%s\n' '{"type":"hook.completed","hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"spec-guard: phase-guard.sh 执行失败"}}' > "$SMOKE_TMP/invalid"
  grade "$SMOKE_TMP/invalid"; rc=$?
  [ "$rc" -eq 1 ] || return 1
  printf '%s\n' 'model = "x"' '' '[projects."/keep"]' 'trust_level = "trusted"' '' \
    '[projects."/smoke"]' 'trust_level = "trusted"' '' '[projects."/custom"]' 'trust_level = "trusted"' 'note = "mine"' \
    > "$SMOKE_TMP/config.toml"
  chmod 640 "$SMOKE_TMP/config.toml"
  forget_project_trust "$SMOKE_TMP/config.toml" /smoke
  forget_project_trust "$SMOKE_TMP/config.toml" /custom
  [ "$(printf '%s\n' 'model = "x"' '' '[projects."/keep"]' 'trust_level = "trusted"' '' \
    '[projects."/custom"]' 'trust_level = "trusted"' 'note = "mine"')" = "$(cat "$SMOKE_TMP/config.toml")" ] || return 1
  # GNU `stat -f` reports the file system (and prints it) instead of failing, so BSD/GNU stat
  # fallbacks are not portable; read the mode through python3, which the smoke already requires.
  [ "$(python3 -c 'import os, stat, sys; print(format(stat.S_IMODE(os.stat(sys.argv[1]).st_mode), "o"))' \
    "$SMOKE_TMP/config.toml")" = 640 ] || return 1
  echo "  ✅ selftest: 只接受机器事件或匹配本次会话的宿主注入；0=通过、1=行为失败、2=未观察到执行"
}

[ "$MODE" = "--selftest" ] && { selftest; exit $?; }
if { [ -n "$PLUGIN_ID" ] && [ -z "$EXPECTED_SOURCE" ]; } \
  || { [ -z "$PLUGIN_ID" ] && [ -n "$EXPECTED_SOURCE" ]; }; then
  echo '--plugin-id 与 --expected-source 必须同时指定' >&2
  exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "  ⏭  找不到 codex：先安装 Codex CLI，再从本地 marketplace 安装 spec-guard"
  print_plugin_repair
  exit 2
fi

PLUGIN_LIST="$(mktemp)"
trap 'rm -f "$PLUGIN_LIST"' EXIT
if ! codex plugin list --available --json > "$PLUGIN_LIST" 2>/dev/null; then
  echo "  ⏭  无法读取 Codex 插件清单：先登录后重试"
  exit 2
fi
case "$(plugin_state "$PLUGIN_LIST" "$PLUGIN_ID" "$EXPECTED_SOURCE")" in
  ready) ;;
  missing)
    echo "  ⏭  spec-guard 未从本地 marketplace 安装：先安装并启用插件"
    print_plugin_repair
    exit 2
    ;;
  disabled)
    echo "  ⏭  spec-guard 未启用：重新添加插件以启用"
    print_plugin_repair
    exit 2
    ;;
  ambiguous)
    echo "  ⏭  检测到多个已启用的 spec-guard：用 --plugin-id 与 --expected-source 指定本次候选"
    exit 2
    ;;
  source-mismatch)
    echo "  ⏭  已安装 spec-guard 的来源不是当前候选：先从该候选安装，再运行 smoke"
    exit 2
    ;;
  *)
    echo "  ⏭  无法判定 spec-guard 的安装状态：检查 codex plugin list --available --json"
    exit 2
    ;;
esac

WORK="$(cd "$(mktemp -d)" && pwd -P)"
CODEX_CONFIG="${CODEX_HOME:-$HOME/.codex}/config.toml"
if grep -Fqx "[projects.\"$WORK\"]" "$CODEX_CONFIG" 2>/dev/null; then HAD_TRUST=1; else HAD_TRUST=0; fi
trap 'rm -f "$PLUGIN_LIST"; rm -rf "$WORK"; [ "$HAD_TRUST" = 1 ] || forget_project_trust "$CODEX_CONFIG" "$WORK"' EXIT
( cd "$WORK" && git init -q && git config user.email smoke@example.invalid && git config user.name smoke )
printf '%s\n' '<!-- BEGIN:spec-guard-codex-convention -->' > "$WORK/AGENTS.md"
printf '%s\n' '<!-- END:spec-guard-codex-convention -->' >> "$WORK/AGENTS.md"
OUT="$WORK/transcript" ERR="$WORK/transcript.err"
PROMPT='请只复述你收到的 spec-guard 当前阶段事实；若没有收到，输出 HOOK_NOT_RUN。'
if ! ( cd "$WORK" && codex exec --json "$PROMPT" ) > "$OUT" 2> "$ERR"; then
  if grep -qi 'trust\|untrusted\|login\|auth' "$ERR"; then
    echo "  ⏭  Codex、登录或 hook trust 未就绪；用 /hooks 审核并信任后重试"
  else
    echo "  ⏭  Codex 非交互执行失败；这次 smoke 没跑起来，不是产品结论"
    sed -n '1,5p' "$ERR" | sed 's/^/     /'
  fi
  exit 2
fi
grade "$OUT" "$WORK" "${CODEX_HOME:-$HOME/.codex}/sessions"
