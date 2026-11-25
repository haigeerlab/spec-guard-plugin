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
      # flow-doc-skeletons：新流程模块（spec 里有 flow v2 标记）按档位查文档与章节；判据在 module_stage.flow_doc_problems。
      # design-review：技术方案的批准标记与审查轮次行；判据在 module_stage.design_review_problems（与阶段提示同一份）。
      if ! FLOWDOCS="$(python3 -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from capability_map import parse_map
from module_stage import design_review_problems, flow_doc_problems, plan_auto_problems
root = Path(".")
parsed = parse_map(root / "spec" / "CAPABILITY-MAP.md")
for module in list(parsed.order) or [row.module_id for row in parsed.rows]:
    for level, message in flow_doc_problems(root, module) + design_review_problems(root, module) + plan_auto_problems(root, module):
        print("%s\t%s" % (level, message))
' "$HOOKDIR" 2>/dev/null </dev/null)"; then
        warn '未验证：新流程文档检查脚本没有正常运行'
        FLOWDOCS=""
      fi
      while IFS=$'\t' read -r level message; do
        [ -n "$level" ] || continue
        if [ "$level" = fail ]; then bad "新流程文档：${message}"; else warn "新流程文档：${message}"; fi
      done <<<"$FLOWDOCS"
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
    if [ "$CONFIG_RC" -eq 0 ] && [ "${CONFIG_OUT#*ignored}" != "$CONFIG_OUT" ]; then
      # config-per-key：只有不认识的键或已退役的键时 check 退出 0 并写 ignored；其余设置照常生效。
      case "$CONFIG_OUT" in
        *unknown-key*) warn '项目配置里有不认识的键，已忽略（可能来自更新版本的 spec-guard）' ;;
      esac
      case "$CONFIG_OUT" in
        *retired-key*) warn '项目配置里有已退役的 autonomyTier 或 moduleAutonomy，已不生效；改设 takeover／moduleTakeover，可用 unset 删除（用 /spec-guard:config 查看）' ;;
      esac
    elif [ "$CONFIG_RC" -eq 0 ]; then
      ok '项目配置有效'
    elif [ "$CONFIG_RC" -eq 1 ]; then
      bad "项目配置无效: ${CONFIG_OUT#*invalid: }（用 /spec-guard:config 查看）"
    else
      warn '未验证：项目配置检查没有正常运行'
    fi
    # takeover-config（沿用 module-autonomy 的做法）：按模块的接管档位写了能力图上没有的模块时逐个警告（模块可能稍后插入或刚改名），不判失败。
    # 配置或能力图读不了时这里不报：前者已由上面的 check 判定，后者由能力图检查报告。
    if [ "$CONFIG_RC" -eq 0 ] && [ -f spec/CAPABILITY-MAP.md ]; then
      UNKNOWN_IDS="$(python3 -B -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from capability_map import parse_map
from project_config import load
try:
    mapped = {row.module_id for row in parse_map(Path("spec/CAPABILITY-MAP.md")).rows}
except Exception:
    sys.exit(0)
for module in load(Path("."))[0].get("moduleTakeover", {}):
    if module not in mapped:
        print(module)
' "$HOOKDIR" 2>/dev/null </dev/null)" || UNKNOWN_IDS=""
      while IFS= read -r module; do
        [ -n "$module" ] && warn "项目配置 moduleTakeover 里的模块 ${module} 不在能力图上（用 /spec-guard:config 查看）"
      done <<<"$UNKNOWN_IDS"
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

# 批准标记（review-approval-marker）：状态判据来自 module_stage.py，与阶段提示同一份；没有标记时不输出这一项。
if command -v python3 >/dev/null 2>&1 && { [ -d spec ] || [ -d tasks ]; }; then
  if REVIEW_OUT="$(python3 -B -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from module_stage import CHECKED, file_review_state, requirement_wait
files = [(path, "spec", path.stem) for path in sorted(Path("spec").glob("*.md")) if path.name != "CAPABILITY-MAP.md"]
files += [(path, "plan", path.parent.name) for path in sorted(Path("tasks").glob("*/plan.md"))]
valid = 0
for path, kind, module in files:
    state = file_review_state(path, kind)
    if state == "none":
        continue
    # requirement-confirm-gate: Codex never confirms a flow v2 requirement, its digest matching or not.
    if kind == "spec" and state in ("codex-approved", "revised") and requirement_wait(Path("."), module) == "codex":
        print("CODEX %s" % path.as_posix())
        continue
    if state in ("invalid", "unreadable", "revised"):
        print("%s %s" % (state.upper(), path.as_posix()))
        continue
    valid += 1
    todo = Path("tasks") / module / "todo.md"
    if state == "pending" and todo.is_file() and CHECKED.search(todo.read_text(encoding="utf-8")):
        print("BUILT %s %s" % (path.as_posix(), todo.as_posix()))
if valid:
    print("VALID %d" % valid)
' "$HOOKDIR" 2>/dev/null </dev/null)"; then
    while IFS=' ' read -r kind item extra; do
      case "$kind" in
        VALID) ok "批准标记有效：${item} 个文件" ;;
        INVALID) bad "批准标记无效：${item}（每个文件至多一行，写法见共享检查点规则「批准标记」）" ;;
        REVISED) warn "${item} 在批准后已修订，需要用户复审；复审通过后用 /spec-guard:review-mark 重新记录" ;;
        CODEX) warn "新流程需求文档：${item} 只有 Codex 的批准，需求要用户在对话里确认；确认后用 /spec-guard:review-mark 记录" ;;
        BUILT) warn "${item} 待批准，但 ${extra} 已有勾选项；确认用户是否已批准，批准后用 /spec-guard:review-mark 记录" ;;
        UNREADABLE) warn "未验证：${item} 读取失败，没有检查它的批准标记" ;;
      esac
    done <<<"$REVIEW_OUT"
  else
    warn '未验证：批准标记检查没有正常运行'
  fi
fi

# 并行边界（module-scope-boundary）：判据只在 module_scope.py；开关不是 on 时它什么都不输出，这一项也就不出现。
if command -v python3 >/dev/null 2>&1 && [ -e .agent/config.json ]; then
  if SCOPE_OUT="$(python3 -B "$HOOKDIR/module_scope.py" validate --project . 2>/dev/null </dev/null)"; then
    while IFS=' ' read -r kind first second; do
      case "$kind" in
        ok) ok "并行边界格式有效（${first} 个未完成模块）" ;;
        warn) warn "${second} 的 Spec 没有并行边界一节，无法判断与其他模块是否冲突" ;;
        bad) bad "${second} 的并行边界格式错误: ${first}" ;;
        unverified)
          if [ "$first" = map ]; then warn '未验证：能力图读不了，没有检查并行边界'
          else warn "未验证：spec/${first}.md 读取失败，没有检查它的并行边界"; fi ;;
      esac
    done <<<"$SCOPE_OUT"
  else
    warn '未验证：并行边界检查没有正常运行'
  fi
fi

# 预先声明（pre-declared-scope）：判据只在 module_scope.py，不看并行开关；没有这一节的 Plan 不出现这一项。
if command -v python3 >/dev/null 2>&1 && [ -f spec/CAPABILITY-MAP.md ] && [ -d tasks ]; then
  if DECLARED_OUT="$(python3 -B "$HOOKDIR/module_scope.py" validate-declared --project . 2>/dev/null </dev/null)"; then
    while IFS=' ' read -r kind first second; do
      case "$kind" in
        ok) ok "预先声明格式正确（${first} 个未完成模块）" ;;
        bad) bad "${second} 的预先声明格式错误: ${first}" ;;
        ignored) warn "${first} 是新流程模块：Plan 的预先声明不起作用，不授权任何路径（plan-auto-approve）" ;;
        unverified) warn '未验证：能力图读不了，没有检查预先声明' ;;
      esac
    done <<<"$DECLARED_OUT"
  else
    warn '未验证：预先声明检查没有正常运行'
  fi
fi

# usage-draft-gate：同一提交插入能力图、尚未完成的模块有 2 个及以上而没有草案覆盖时警告；只警告不判失败（已开工的项目先补写）。
# 判据在 usage_draft.missing；没有这样的批次时不输出这一项。
if command -v python3 >/dev/null 2>&1 && [ -f spec/CAPABILITY-MAP.md ]; then
  BATCH_OUT="$(python3 -B "$HOOKDIR/usage_draft.py" missing --project . 2>&1 </dev/null)" || true
  while IFS=' ' read -r kind first rest; do
    case "$kind" in
      ok) ok "多模块批次都有用法草案（${first} 批）" ;;
      missing)
        [ "$first" = uncommitted ] && where='未提交' || where="提交 ${first:0:8}"
        warn "多模块批次缺用法草案：${rest//,/、}（${where}）——写 Spec 前先出 spec/usage/<需求>.md，覆盖这批全部模块" ;;
      unverified) warn "未判定：多模块批次的草案覆盖（${first}${rest:+ ${rest}}）" ;;
    esac
  done <<<"$BATCH_OUT"
fi

# 用法草案（usage-draft）：判据只在 usage_draft.py；没有 spec/usage/*.md 时不输出这一项。
if command -v python3 >/dev/null 2>&1 && [ -d spec/usage ]; then
  # stderr is kept (#21443): when the script fails, the last line it printed is the reason, and the warning carries it.
  USAGE_OUT="$(python3 -B "$HOOKDIR/usage_draft.py" validate --project . 2>&1 </dev/null)"
  USAGE_RC=$?
  USAGE_SEEN=0
  if [ "$USAGE_RC" -le 1 ]; then
    while IFS=' ' read -r kind rest; do
      case "$kind" in
        ok) USAGE_SEEN=1; ok "用法草案结构正确（${rest} 份）" ;;
        bad) USAGE_SEEN=1; bad "用法草案: ${rest}" ;;
        warn) USAGE_SEEN=1; warn "用法草案提醒: ${rest}" ;;
        unverified) USAGE_SEEN=1; warn "未验证：能力图读不了，没有检查用法草案（${rest}）" ;;
        absent) USAGE_SEEN=1 ;;
      esac
    done <<<"$USAGE_OUT"
  fi
  if [ "$USAGE_SEEN" -eq 0 ]; then
    USAGE_WHY="$(printf '%s\n' "$USAGE_OUT" | awk 'NF { line = $0 } END { print substr(line, 1, 200) }')"
    warn "未验证：用法草案检查没有正常运行（${USAGE_WHY:-没有输出，退出码 ${USAGE_RC}}）"
  fi
fi

# regression-doc-check（Q1 A）：多模块需求的整体联调回归 spec/usage/<需求>.regression.md；判据在 regression_view.usage_report。
if command -v python3 >/dev/null 2>&1 && [ -d spec/usage ] && compgen -G 'spec/usage/*.regression.md' >/dev/null; then
  if ! USAGE_REG="$(python3 -B -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import regression_view
root = Path(".")
for path in sorted((root / "spec" / "usage").glob("*.regression.md")):
    name = path.name[: -len(".regression.md")]
    label = "spec/usage/%s" % path.name
    if not regression_view.USAGE_NAME.fullmatch(name):
        print("fail\t`%s` 文件名不是有效的需求名" % label)
        continue
    try:
        report = regression_view.usage_report(root, name)
    except regression_view.ViewError as error:
        print("fail\t`%s` 读不了（%s）" % (label, error.code))
        continue
    for problem in report["problems"]:
        print("fail\t`%s` 联调回归问题：%s（%s）" % (label, problem["code"], problem["where"]))
    if not report["problems"]:
        print("ok\t联调回归格式正确：`%s`（%d 条用例）" % (label, len(report["cases"])))
' "$HOOKDIR" 2>/dev/null </dev/null)"; then
    warn '未验证：联调回归检查脚本没有正常运行'
    USAGE_REG=""
  fi
  while IFS=$'\t' read -r level message; do
    [ -n "$level" ] || continue
    if [ "$level" = ok ]; then ok "$message"; else bad "$message"; fi
  done <<<"$USAGE_REG"
fi

# 延期写法（formal-deferral）：判据来自 module_stage.py 的 DEFERRED；格式不对与检查点延期判失败（照旧算未完成），
# 像延期的自由文本只给改写提示。没有延期写法时不输出这一项。
if command -v python3 >/dev/null 2>&1 && [ -d tasks ]; then
  if DEFER_OUT="$(python3 -B -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from module_stage import deferral_lint
for todo in sorted(Path("tasks").glob("*/todo.md")):
    found = deferral_lint(todo.read_text(encoding="utf-8"))
    formal = sum(kind == "formal" for kind, _ in found)
    if formal:
        print("FORMAL %s %d" % (todo.parent.name, formal))
    for kind, number in found:
        if kind != "formal":
            print("%s %s:%d 0" % (kind.upper(), todo.as_posix(), number))
' "$HOOKDIR" 2>/dev/null </dev/null)"; then
    EXAMPLE='- [ ] 延期：<事项>；恢复条件：<条件>（英文 Deferred: <item>; Resume when: <condition>）'
    while IFS=' ' read -r kind item count; do
      case "$kind" in
        FORMAL) ok "延期项写法有效：${item}（${count} 项）" ;;
        MALFORMED) bad "${item} 带延期前缀但格式不对（缺事项或恢复条件），照旧算未完成；正确写法：${EXAMPLE}" ;;
        CHECKPOINT) bad "${item} 检查点不能延期，照旧算未完成" ;;
        INFORMAL) warn "${item} 像是延期，但不是正式写法，照旧算未完成；要让它不挡下游，改成：${EXAMPLE}" ;;
      esac
    done <<<"$DEFER_OUT"
  else
    warn '未验证：延期写法检查没有正常运行'
  fi
fi

# 旁路清单（rework-in-place）：阶段判定只数 todo.md，所以 tasks/<id>/ 下别的清单文件里没做完的项没人看得见。
# 只看直接子文件里的 *.md；判据是 module_stage.py 的 UNCHECKED（合格延期项另数，它们在这里同样不计入阶段）。
# 没有可报告的内容时不输出这一项。
if command -v python3 >/dev/null 2>&1 && [ -d tasks ]; then
  if SIDE_OUT="$(python3 -B -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from module_stage import DEFERRED, UNCHECKED, deferral_lint
side_checklists = sorted(path for path in Path("tasks").glob("*/*.md") if path.name not in ("plan.md", "todo.md"))
for path in side_checklists:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        print("UNREADABLE 0 %s" % path.as_posix())
        continue
    count = len(UNCHECKED.findall(text)) + len(DEFERRED.findall(text))
    if count:
        print("OPEN %d %s" % (count, path.as_posix()))
    deferrals = len(deferral_lint(text))
    if deferrals:
        print("DEFER %d %s" % (deferrals, path.as_posix()))
' "$HOOKDIR" 2>/dev/null </dev/null)"; then
    while IFS=' ' read -r kind count item; do
      case "$kind" in
        OPEN) warn "${item} 有 ${count} 个未勾选项，它们不计入阶段（阶段判定只数 todo.md）；返工或修订请写进该模块的 todo.md" ;;
        DEFER) warn "${item} 有 ${count} 项延期写法，延期只在该模块的 todo.md 里才算数，这里不算延期；请挪回 todo.md" ;;
        UNREADABLE) warn "未验证：${item} 读取失败，没有检查它的清单项" ;;
      esac
    done <<<"$SIDE_OUT"
  else
    warn '未验证：旁路清单检查没有正常运行'
  fi
fi

printf '\n结果: %s 通过 · %s 警告 · %s 失败\n' "$PASS" "$WARN" "$FAIL"
[ "$FAIL" -eq 0 ]
