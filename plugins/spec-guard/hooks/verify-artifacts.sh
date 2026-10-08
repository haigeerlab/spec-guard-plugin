#!/usr/bin/env bash
# Read-only structural validation. Remote tracker projection was retired.
set -u

HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" 2>/dev/null || exit 2
FAIL=0
WARN=0
PASS=0

ok() { printf '  ✅ %s\n' "$1"; PASS=$((PASS + 1)); }
warn() { printf '  ⚠️  %s\n' "$1"; WARN=$((WARN + 1)); }
bad() { printf '  ❌ %s\n' "$1"; FAIL=$((FAIL + 1)); }

if [ ! -e spec/CAPABILITY-MAP.md ]; then
  warn 'spec/CAPABILITY-MAP.md 不存在；单模块项目可忽略'
else
  ok '能力图存在'
fi

STRAY=""
for file in SPEC*.md; do
  [ -e "$file" ] || continue
  STRAY="${STRAY}${STRAY:+、}${file}"
done
if [ -n "$STRAY" ]; then
  bad "根目录有不受支持的 spec 文件: ${STRAY}"
else
  ok '没有根目录 spec 漂移'
fi

# 能力图只用 capability-map.py 这一个严格解析器；解析器跑不起来是环境问题，报“未验证”而不是违规。
if [ -e spec/CAPABILITY-MAP.md ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    warn '未验证：python3 不可用，没有检查能力图结构与模块 spec 的对应关系'
  else
    MAP_OUT="$(python3 "$HOOKDIR/capability-map.py" spec/CAPABILITY-MAP.md 2>/dev/null </dev/null |
      python3 -c '
import json, sys
try:
    value = json.load(sys.stdin)
except ValueError:
    raise SystemExit(4)
if not isinstance(value, dict) or not isinstance(value.get("ok"), bool):
    raise SystemExit(4)
if not value["ok"]:
    print(value.get("error") or "unknown parse error")
    raise SystemExit(5 if value.get("kind") == "unreadable" else 3)
for module in value.get("modules", []):
    print(module["id"])
' 2>/dev/null)"
    MAP_RC=$?
    if [ "$MAP_RC" -eq 3 ]; then
      bad "能力图无效: ${MAP_OUT}"
      warn '能力图无效，未检查模块 spec 的对应关系'
    elif [ "$MAP_RC" -eq 5 ]; then
      # 读不了是环境故障，不是能力图内容的状态。
      warn "未验证：能力图读取失败（${MAP_OUT}），没有检查能力图结构与模块 spec 的对应关系"
    elif [ "$MAP_RC" -ne 0 ]; then
      warn '未验证：能力图解析器没有正常运行，没有检查模块 spec 的对应关系'
    else
      ok '能力图通过严格解析'
      for file in spec/*.md; do
        [ -e "$file" ] || continue
        name="${file##*/}"; [ "$name" = CAPABILITY-MAP.md ] && continue
        module="${name%.md}"
        if ! grep -Fx "$module" >/dev/null 2>&1 <<<"$MAP_OUT"; then
          bad "能力图上没有的模块 spec: ${module}"
        fi
      done
      # 有 Plan 无 todo.md、且 Plan 未声明 no-todo 的模块（判据来自 module_stage.py）；这里只汇总，不判失败。
      if ! NOTODO="$(python3 -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from capability_map import parse_map
from module_stage import module_state, plan_without_todo
root = Path(".")
parsed = parse_map(root / "spec" / "CAPABILITY-MAP.md")
order = list(parsed.order) or [row.module_id for row in parsed.rows]
ids = [s["id"] for s in (module_state(root, m) for m in order) if plan_without_todo(s)]
if ids:
    listed = ", ".join(ids[:10]) + (" 等 %d 个" % len(ids) if len(ids) > 10 else "")
    print("%d 个模块有 Plan 但没有 todo.md，按已完成计：%s" % (len(ids), listed))
' "$HOOKDIR" 2>/dev/null </dev/null)"; then
        warn '未验证：有 Plan 无 todo.md 汇总脚本没有正常运行'
        NOTODO=""
      fi
      [ -z "$NOTODO" ] || warn "$NOTODO"
    fi
  fi
fi

# `tracker` 字段已随远端 tracker 模式退役（docs/retirements/state-tracker-field.md），
# 不再被任何代码读取。只对真正残留该字段的文件提醒，不对插件自己装的 state.json 报警。
if grep -Eq '"tracker"[[:space:]]*:' .agent/state.json 2>/dev/null; then
  warn '检测到已退役的 tracker 字段；它不再被读取，可从 .agent/state.json 中删除'
fi

# 项目配置只由 project_config.py 判定（与阶段提示同一判据）；没有配置文件时不输出这一项。
if [ -e .agent/config.json ] || [ -L .agent/config.json ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    warn '未验证：python3 不可用，没有检查 .agent/config.json'
  else
    CONFIG_OUT="$(python3 -B "$HOOKDIR/project_config.py" check --project . 2>/dev/null </dev/null)"
    CONFIG_RC=$?
    if [ "$CONFIG_RC" -eq 0 ]; then
      ok '项目配置有效'
    elif [ "$CONFIG_RC" -eq 1 ]; then
      bad "项目配置无效: ${CONFIG_OUT#*invalid: }（用 /spec-guard:config 查看）"
    else
      warn '未验证：项目配置检查没有正常运行'
    fi
  fi
fi

# 挂起标记（module-suspend）：标记与“未勾选项”的判据来自 module_stage.py；没有标记时不输出这一项。
if command -v python3 >/dev/null 2>&1 && [ -d tasks ]; then
  if SUSPEND_OUT="$(python3 -B -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from module_stage import SUSPEND_MARKER, UNCHECKED
for todo in sorted(Path("tasks").glob("*/todo.md")):
    text = todo.read_text(encoding="utf-8")
    count = sum(line.strip() == SUSPEND_MARKER for line in text.splitlines())
    if count > 1:
        print("DUP %s" % todo.as_posix())
    elif count == 1:
        print(("OK %s" if UNCHECKED.search(text) else "STALE %s") % todo.parent.name)
' "$HOOKDIR" 2>/dev/null </dev/null)"; then
    while IFS=' ' read -r kind item; do
      case "$kind" in
        OK) ok "挂起标记有效：${item}" ;;
        DUP) bad "挂起标记重复：${item}（只能有一行）" ;;
        STALE) warn "挂起标记过期：${item} 已没有未勾选项，按完成计；可用 /spec-guard:module-suspend --resume ${item} 去掉" ;;
      esac
    done <<<"$SUSPEND_OUT"
  else
    warn '未验证：挂起标记检查没有正常运行'
  fi
fi

printf '\n结果: %s 通过 · %s 警告 · %s 失败\n' "$PASS" "$WARN" "$FAIL"
[ "$FAIL" -eq 0 ]
