#!/usr/bin/env bash
set -euo pipefail

HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0

fail() { echo "  ❌ $1" >&2; exit 1; }

# $1=用例名 $2=期望退出码(0|1) $3=输出必须包含的文本；项目目录取 ${PROJECT}，可用 ${RUN_PATH} 替换 PATH
check() {
  local out rc
  set +e
  out="$(PATH="${RUN_PATH:-$PATH}" CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$HOOKDIR/verify-artifacts.sh" 2>&1)"
  rc=$?
  set -e
  [ "$rc" -eq "$2" ] || fail "$1: 退出码 ${rc}，期望 $2
$out"
  grep -F -- "$3" >/dev/null <<<"$out" || fail "$1: 输出缺少「$3」
$out"
  echo "  ✅ $1"; PASS=$((PASS + 1))
}

# $1=用例名 $2=不得出现的文本
check_absent() {
  local out
  out="$(CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$HOOKDIR/verify-artifacts.sh" 2>&1)" || true
  ! grep -F -- "$2" >/dev/null <<<"$out" || fail "$1: 输出不应包含「$2」
$out"
  echo "  ✅ $1"; PASS=$((PASS + 1))
}

# $1=目录 $2...=额外追加到能力图末尾的行
project() {
  PROJECT="$WORK/$1"; shift
  mkdir -p "$PROJECT/spec"
  printf '%s\n' '# Capability Map: fixture' '' '## 目标' '' 'Verify artifacts.' '' '## 模块' '' \
    '| Module id | Responsibility | Depends on |' '| --- | --- | --- |' '| alpha | x | — |' '' \
    'Build order: alpha' "$@" > "$PROJECT/spec/CAPABILITY-MAP.md"
  touch "$PROJECT/spec/alpha.md"
}

project valid
check "有效能力图与对应 spec 通过" 0 "能力图通过严格解析"

# change-source-record：能力图末尾的「变更记录」一节不影响解析与校验结果。
project change-log '' '## 变更记录' '' '- 2026-10-16：alpha 的职责改一处说法。原因：测试。来源：用户本人。'
check "能力图末尾带变更记录时照常通过" 0 "0 警告 · 0 失败"

project root-spec
touch "$PROJECT/SPEC-alpha.md"
check "根目录 spec 失败" 1 "根目录有不受支持的 spec 文件"

project orphan
touch "$PROJECT/spec/beta.md"
check "能力图上没有的 spec 失败" 1 "能力图上没有的模块 spec: beta"

# 自带正则曾把围栏示例和第二张表的首列当成模块 id。
project fenced '' '```markdown' '| ghost | 示例 | — |' '```'
touch "$PROJECT/spec/ghost.md"
check "围栏示例中的 id 不算模块" 1 "能力图上没有的模块 spec: ghost"

project second-table '' '## Risks' '' '| Risk | Mitigation |' '| --- | --- |' '| risk-one | watch |'
touch "$PROJECT/spec/risk-one.md"
check "其他表格首列不算模块" 1 "能力图上没有的模块 spec: risk-one"

project no-build-order
printf '%s\n' '# Capability Map: fixture' '' '## 模块' '' '| Module id | Responsibility | Depends on |' \
  '| --- | --- | --- |' '| alpha | x | missing |' > "$PROJECT/spec/CAPABILITY-MAP.md"
check "无效能力图失败并给出解析原因" 1 "能力图无效: "

# 两张模块表：报错指出两张表头所在行（map-table-count-diagnostic）。
project two-module-tables '' '| Module id | Responsibility | Depends on |' '| --- | --- | --- |' '| beta | x | — |'
check "两张模块表时报错列出表头行号" 1 "能力图无效: 必须恰好有一个模块表，找到 2 张：第 9、15 行"

# 表头下面一行若不是分隔行（审查 F9：此前没有反向断言），能力图无效。
project no-separator
python3 - "$PROJECT/spec/CAPABILITY-MAP.md" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
assert "| --- | --- | --- |" in text
open(path, "w", encoding="utf-8").write(text.replace("| --- | --- | --- |", "| x | y | z |", 1))
PY
check "表头下面不是分隔行时能力图无效" 1 "模块表缺少有效的表头分隔行"

# 能力图读不了是读取故障，不是内容无效：报“未验证”并附原因，不判失败。
project unreadable-map
chmod 000 "$PROJECT/spec/CAPABILITY-MAP.md"
if [ -r "$PROJECT/spec/CAPABILITY-MAP.md" ]; then
  echo "  ⏭️  不可读能力图：以 root 运行时 000 仍可读，跳过"
else
  check "不可读能力图报读取失败而非无效" 0 "未验证：能力图读取失败（"
  check_absent "不可读能力图不报能力图无效" "能力图无效"
fi
project directory-map
rm -f "$PROJECT/spec/CAPABILITY-MAP.md"; mkdir "$PROJECT/spec/CAPABILITY-MAP.md"
check "能力图路径是目录时报读取失败" 0 "未验证：能力图读取失败（"
project non-utf8-map
printf '\377\376 not utf-8\n' > "$PROJECT/spec/CAPABILITY-MAP.md"
check "非 UTF-8 能力图仍是内容无效" 1 "能力图无效: "

# 环境故障只能报“未验证”，不能把合法 spec 判成违规。
project orphan-without-python
touch "$PROJECT/spec/beta.md"
mkdir -p "$WORK/nopy"
for tool in dirname grep; do ln -sf "$(command -v "$tool")" "$WORK/nopy/$tool"; done
RUN_PATH="$WORK/nopy" check "缺 python3 时报未验证而非失败" 0 "未验证：python3 不可用"

mkdir -p "$WORK/brokenpy"
printf '%s\n' '#!/bin/sh' 'echo broken; exit 1' > "$WORK/brokenpy/python3"
chmod +x "$WORK/brokenpy/python3"
RUN_PATH="$WORK/brokenpy:$PATH" check "解析器异常时报未验证而非失败" 0 "未验证：能力图解析器没有正常运行"

# 主解析器成功、仅 Plan/todo 二次汇总失败时不能把零结果冒充为零警告。
project summary-helper-fails
mkdir -p "$PROJECT/tasks/alpha"
touch "$PROJECT/tasks/alpha/plan.md"
mkdir -p "$WORK/summary-fails"
cat > "$WORK/summary-fails/python3" <<'SH'
#!/bin/sh
if [ "$1" = -c ]; then
  case "$2" in
    *'from module_stage import module_state'*)
      printf 'called\n' > "$SPEC_GUARD_TEST_SENTINEL"
      exit 29
      ;;
  esac
fi
exec "$SPEC_GUARD_TEST_REAL_PYTHON" "$@"
SH
chmod +x "$WORK/summary-fails/python3"
SPEC_GUARD_TEST_REAL_PYTHON="$(command -v python3)" \
SPEC_GUARD_TEST_SENTINEL="$WORK/summary-helper-called" \
RUN_PATH="$WORK/summary-fails:$PATH" \
  check "二次汇总失败时明确报未验证" 0 "未验证：有 Plan 无 todo.md 汇总脚本没有正常运行"
[ -f "$WORK/summary-helper-called" ] || fail "二次汇总失败用例没有运行目标 helper"

# 有 Plan 无 todo.md 的模块按已完成计：汇总成一条警告，不改退出码。
# $1=目录 $2=模块数；每个模块都有 spec，m01..mNN 全部在 Build order 内。
many_modules() {
  local i id ids="" rows=()
  PROJECT="$WORK/$1"; mkdir -p "$PROJECT/spec"
  for i in $(seq 1 "$2"); do
    id="$(printf m%02d "$i")"; ids="${ids}${ids:+, }${id}"
    rows+=("| ${id} | x | — |"); touch "$PROJECT/spec/${id}.md"
  done
  printf '%s\n' '# Capability Map: fixture' '' '## 模块' '' '| Module id | Responsibility | Depends on |' \
    '| --- | --- | --- |' "${rows[@]}" '' "Build order: ${ids}" > "$PROJECT/spec/CAPABILITY-MAP.md"
}
# $1=模块 id：只放 plan.md
plan_only() { mkdir -p "$PROJECT/tasks/$1"; touch "$PROJECT/tasks/$1/plan.md"; }

many_modules no-todo-none 3
plan_only m01; touch "$PROJECT/tasks/m01/todo.md"
check "0 个缺 todo 的模块时警告数为 0" 0 "0 警告"
check_absent "0 个缺 todo 的模块时没有汇总警告" "没有 todo.md"

many_modules no-todo-one 3
plan_only m02
check "1 个缺 todo 的模块发一条警告并点名" 0 "1 个模块有 Plan 但没有 todo.md，按已完成计：m02"
check "1 个缺 todo 的模块警告数为 1、退出码不变" 0 "1 警告"

many_modules no-todo-twelve 12
for i in 01 02 03 04 05 06 07 08 09 10 11 12; do plan_only "m$i"; done
check "12 个缺 todo 的模块只列前 10 个并以等 12 个结尾" 0 \
  "12 个模块有 Plan 但没有 todo.md，按已完成计：m01, m02, m03, m04, m05, m06, m07, m08, m09, m10 等 12 个"
check "12 个缺 todo 的模块仍只多一条警告" 0 "1 警告"
check_absent "12 个缺 todo 的模块不列出第 11 个 id" "m11,"

# plan.md 里独占一行的 no-todo 声明：汇总只列没有声明的模块，全有声明时不发警告。
many_modules no-todo-marked 3
plan_only m01; plan_only m02; plan_only m03
printf '%s\n' '# Plan' '<!-- spec-guard: no-todo -->' | tee "$PROJECT/tasks/m01/plan.md" "$PROJECT/tasks/m03/plan.md" >/dev/null
printf '%s\n' '# Plan' '> 登记说明：没有 todo 是有意的。' > "$PROJECT/tasks/m02/plan.md"
check "只列没有 no-todo 声明的模块" 0 "1 个模块有 Plan 但没有 todo.md，按已完成计：m02"
printf '%s\n' '# Plan' '<!-- spec-guard: no-todo -->' > "$PROJECT/tasks/m02/plan.md"
check "全部带声明时警告数为 0" 0 "0 警告"
check_absent "全部带声明时没有汇总警告" "没有 todo.md"

# tracker 字段已退役，不再抑制任何判断：缺 todo 汇总只看文件，与 state.json 的内容无关。
many_modules no-todo-github 3
plan_only m02; mkdir -p "$PROJECT/.agent"
SUMMARY="1 个模块有 Plan 但没有 todo.md，按已完成计：m02"
printf '{"tracker":"github","modules":{}}\n' > "$PROJECT/.agent/state.json"
check "退役 tracker github 不再抑制缺 todo 汇总" 0 "$SUMMARY"
printf '{"tracker":"gitlab","modules":{}}\n' > "$PROJECT/.agent/state.json"
check "退役 tracker gitlab 不再抑制缺 todo 汇总" 0 "$SUMMARY"
printf '{"activeModule":""}\n' > "$PROJECT/.agent/state.json"
check "当前格式的 state.json 同样发缺 todo 汇总" 0 "$SUMMARY"

# 历史状态文件告警只针对真正的退役字段，不对插件自己刚装的 state.json 报警。
LEGACY="检测到已退役的 tracker 字段"
project legacy-state; mkdir -p "$PROJECT/.agent"
printf '{"activeModule":""}\n' > "$PROJECT/.agent/state.json"
check_absent "当前格式的 state.json 不发历史状态告警" "$LEGACY"
check "当前格式的 state.json 没有警告" 0 "0 警告"
printf '{"tracker":"none","modules":{},"activeModule":""}\n' > "$PROJECT/.agent/state.json"
check "含 tracker 键时发退役字段告警" 0 "$LEGACY"
rm -f "$PROJECT/.agent/state.json"
check_absent "没有 state.json 时不发退役字段告警" "$LEGACY"

# 项目配置只由 project_config.py 判定；没有配置文件时不输出这一项。
project config-absent
check_absent "没有配置文件时不报告项目配置" "项目配置"
project config-valid; mkdir -p "$PROJECT/.agent"
printf '{"version": 1, "artifactLanguage": "zh-CN", "reviewCadence": "combined"}\n' > "$PROJECT/.agent/config.json"
check "合法的项目配置通过" 0 "项目配置有效"
# hint-language-follow：阶段提示的语言与这里同一判据（project_config.load）。zh-CN 有效（上一例），不合规的
# zh_CN 判无效——阶段提示在同一份配置下出英文并带 invalid 行。
printf '{"version": 1, "artifactLanguage": "zh_CN"}\n' > "$PROJECT/.agent/config.json"
check "不合规的语言标签判无效" 1 "项目配置无效: artifactLanguage-invalid"
printf '{"version": 1, "reviewCadence": "both", "extra": 1}\n' > "$PROJECT/.agent/config.json"
check "无效的项目配置失败并列出原因" 1 "项目配置无效: unknown-key, reviewCadence-invalid"
printf '{"version": 1, "moduleConcurrency": "on"}\n' > "$PROJECT/.agent/config.json"
check "并行开关 on 的项目配置通过" 0 "项目配置有效"
printf '{"version": 1, "moduleConcurrency": "yes"}\n' > "$PROJECT/.agent/config.json"
check "并行开关取值无效时失败" 1 "项目配置无效: moduleConcurrency-invalid"

# module-scope-boundary：开关不是 on 时，并行边界一节（哪怕格式错误）不影响任何输出；on 时正确、缺失、格式错三种。
scope_out() { CLAUDE_PROJECT_DIR="$PROJECT" /bin/bash "$HOOKDIR/verify-artifacts.sh" 2>&1 || true; }
project scope-off; mkdir -p "$PROJECT/.agent"
printf '{"version": 1, "moduleConcurrency": "off"}\n' > "$PROJECT/.agent/config.json"
plain_scope="$(scope_out)"
printf '# alpha\n\n## 并行边界\n\n- 独占：apps/alpha/\n' > "$PROJECT/spec/alpha.md"
[ "$(scope_out)" = "$plain_scope" ] || fail "开关 off 时并行边界不应改变输出
$(scope_out)"
echo "  ✅ 并行开关 off：格式错误的并行边界也不改变输出"; PASS=$((PASS + 1))
printf '{"version": 1, "moduleConcurrency": "on"}\n' > "$PROJECT/.agent/config.json"
check "并行开关 on：并行边界格式错误时失败" 1 "alpha 的并行边界格式错误: bad-path"
printf '# alpha\n\n## 并行边界\n\n- 独占：`apps/alpha/`\n' > "$PROJECT/spec/alpha.md"
check "并行开关 on：并行边界有效时通过" 0 "并行边界格式有效（1 个未完成模块）"
printf '# alpha\n' > "$PROJECT/spec/alpha.md"
check "并行开关 on：缺并行边界只警告" 0 "alpha 的 Spec 没有并行边界一节"
printf '{broken' > "$PROJECT/.agent/config.json"
check "无法解析的项目配置失败" 1 "项目配置无效: not-json"

# module-suspend：挂起标记只在 todo.md 中计数；重复判失败，过期（没有未勾选项）只警告。
SUSPEND_LINE='<!-- spec-guard: suspended -->'
project suspend-ok; mkdir -p "$PROJECT/tasks/alpha"
printf '%s\n' '- [x] a' '- [ ] b' "$SUSPEND_LINE" > "$PROJECT/tasks/alpha/todo.md"
check "正常的挂起标记通过" 0 "挂起标记有效：alpha"
printf '%s\n' '- [ ] b' "$SUSPEND_LINE" "$SUSPEND_LINE" > "$PROJECT/tasks/alpha/todo.md"
check "重复的挂起标记失败" 1 "挂起标记重复：tasks/alpha/todo.md"
printf '%s\n' '- [x] a' "$SUSPEND_LINE" > "$PROJECT/tasks/alpha/todo.md"
check "过期的挂起标记只警告" 0 "挂起标记过期：alpha 已没有未勾选项"
project suspend-none
check_absent "没有挂起标记时不报告挂起" "挂起标记"

# review-approval-marker：评审标记写法无效判失败；待审核却已有勾选项、Spec 批准后被改只警告；没有标记时不输出。
RV_PENDING='<!-- spec-guard: review pending -->'
rv_project() {  # $1=目录：alpha 有 Spec、Plan 与一份带勾选项的 todo
  project "$1"; mkdir -p "$PROJECT/tasks/alpha"
  printf '# Spec: alpha\n\n正文\n' > "$PROJECT/spec/alpha.md"
  printf '# Plan\n' > "$PROJECT/tasks/alpha/plan.md"
  printf '%s\n' '- [x] a' '- [ ] b' > "$PROJECT/tasks/alpha/todo.md"
}
rv_approve() {  # 把 Spec 标为带当前指纹的 approved
  python3 -B "$HOOKDIR/review_mark.py" --project "$PROJECT" --module alpha --target "$1" --state approved --confirm >/dev/null
}
rv_project review-none
check_absent "没有批准标记时不报告批准标记" "批准标记"
rv_project review-ok; rv_approve both
check "评审标记有效时通过并汇总" 0 "批准标记有效：2 个文件"
check_absent "批准标记有效时没有待批准警告" "待批准"
rv_project review-pending-clean; printf '%s\n' '- [ ] b' > "$PROJECT/tasks/alpha/todo.md"
printf '# Plan\n\n%s\n' "$RV_PENDING" > "$PROJECT/tasks/alpha/plan.md"
check "待审核且没有勾选项不警告" 0 "批准标记有效：1 个文件"
check_absent "待审核且没有勾选项时没有矛盾警告" "已有勾选项"
rv_project review-invalid
printf '# Spec: alpha\n\n%s\n%s\n' "$RV_PENDING" "$RV_PENDING" > "$PROJECT/spec/alpha.md"
check "重复的评审标记失败" 1 "批准标记无效：spec/alpha.md"
printf '# Spec: alpha\n\n正文\n' > "$PROJECT/spec/alpha.md"
printf '# Plan\n\n%s\n' '<!-- spec-guard: review approved 0123456789ab -->' > "$PROJECT/tasks/alpha/plan.md"
check "Plan 的批准标记带指纹判无效" 1 "批准标记无效：tasks/alpha/plan.md"
rv_project review-plan-built
printf '# Plan\n\n%s\n' "$RV_PENDING" > "$PROJECT/tasks/alpha/plan.md"
check "Plan 待审核却已有勾选项只警告" 0 "tasks/alpha/plan.md 待批准，但 tasks/alpha/todo.md 已有勾选项"
rv_project review-spec-built
printf '# Spec: alpha\n\n%s\n\n正文\n' "$RV_PENDING" > "$PROJECT/spec/alpha.md"
check "Spec 待审核却已有勾选项只警告" 0 "spec/alpha.md 待批准，但 tasks/alpha/todo.md 已有勾选项"
rv_project review-revised; rv_approve spec
printf '补一条\n' >> "$PROJECT/spec/alpha.md"
check "Spec 批准后被改只警告" 0 "spec/alpha.md 在批准后已修订，需要用户复审"
rv_project review-fenced
printf '# Spec: alpha\n\n```text\n%s\n%s\n```\n' "$RV_PENDING" "$RV_PENDING" > "$PROJECT/spec/alpha.md"
check_absent "围栏代码块里的示例不算标记" "批准标记"
rv_project review-helper-fails; rv_approve both
mkdir -p "$WORK/review-fails"
cat > "$WORK/review-fails/python3" <<'SH'
#!/bin/sh
case "$*" in *file_review_state*) exit 29 ;; esac
exec "$SPEC_GUARD_TEST_REAL_PYTHON" "$@"
SH
chmod +x "$WORK/review-fails/python3"
SPEC_GUARD_TEST_REAL_PYTHON="$(command -v python3)" RUN_PATH="$WORK/review-fails:$PATH" \
  check "评审标记检查没有正常运行时报未验证" 0 "未验证：批准标记检查没有正常运行"

# rework-in-place：tasks/<id>/ 下 plan.md、todo.md 之外的清单文件里有未勾选项时警告——阶段判定只数 todo.md。
side_project() {  # $1=目录：alpha 已完成（plan 与全勾的 todo）
  project "$1"; mkdir -p "$PROJECT/tasks/alpha"
  printf '# Plan\n' > "$PROJECT/tasks/alpha/plan.md"
  printf '%s\n' '- [x] a' > "$PROJECT/tasks/alpha/todo.md"
}
side_project side-open
printf '%s\n' '# 修正' '- [x] 已做' '- [ ] 没做一' '* [ ] 没做二' > "$PROJECT/tasks/alpha/review-remediation.md"
check "旁路清单有未勾选项时警告并给出路径与项数" 0 "tasks/alpha/review-remediation.md 有 2 个未勾选项"
check "旁路清单的警告说明这些项不计入阶段" 0 "不计入阶段"
side_project side-done
printf '%s\n' '- [x] 已做' > "$PROJECT/tasks/alpha/review-remediation.md"
check_absent "旁路清单全部勾选时不输出" "未勾选项"
side_project side-prose
printf '%s\n' '# 验收记录' '没有清单。' > "$PROJECT/tasks/alpha/acceptance.md"
check_absent "没有清单项的旁路文件不输出" "未勾选项"
side_project side-own
printf '%s\n' '- [ ] a' '- [x] b' > "$PROJECT/tasks/alpha/todo.md"
printf '# Plan\n\n- [ ] 计划里的清单\n' > "$PROJECT/tasks/alpha/plan.md"
check_absent "plan.md 与 todo.md 自己的未勾选项不触发" "未勾选项"
side_project side-nested
mkdir -p "$PROJECT/tasks/alpha/browser-acceptance"
printf '%s\n' '- [ ] 子目录里的' > "$PROJECT/tasks/alpha/browser-acceptance/notes.md"
printf '%s\n' '- [ ] 不是 md' > "$PROJECT/tasks/alpha/notes.txt"
check_absent "子目录里的文件与非 md 文件不看" "未勾选项"
project side-no-tasks
check_absent "没有 tasks 目录时不报告旁路清单" "未勾选项"
side_project side-helper-fails
printf '%s\n' '- [ ] 没做' > "$PROJECT/tasks/alpha/extra.md"
mkdir -p "$WORK/side-fails"
cat > "$WORK/side-fails/python3" <<'SH'
#!/bin/sh
case "$*" in *side_checklists*) exit 29 ;; esac
exec "$SPEC_GUARD_TEST_REAL_PYTHON" "$@"
SH
chmod +x "$WORK/side-fails/python3"
SPEC_GUARD_TEST_REAL_PYTHON="$(command -v python3)" RUN_PATH="$WORK/side-fails:$PATH" \
  check "旁路清单检查没有正常运行时报未验证" 0 "未验证：旁路清单检查没有正常运行"

# 验收标准编号（stop-rule-and-ac）：未完成模块的验收标准缺 AC 编号只提示、不失败；已完成模块不追溯。
ac_spec() { project "$1"; shift; printf '%s\n' '# alpha' '' "$@" > "$PROJECT/spec/alpha.md"; }
AC_HINT="的验收标准有"
ac_spec ac-missing '## Success criteria' '' '- AC1：第一条' '- 第二条没有编号' '  - 子项不算' '' '## Open questions' '' '- 不在验收标准里'
check "未编号的验收标准给提示且不失败" 0 "alpha 的验收标准有 1 条没有编号（AC1、AC2…）；最终验收要按编号对证据"
ac_spec ac-all '## Success Criteria' '' '- AC1：a' '* **AC2**：b' '1. AC3：c'
check_absent "全部编号时不提示" "$AC_HINT"
ac_spec ac-zh '## 验收标准' '' '- 没编号一' '- 没编号二'
check "中文标题同样识别" 0 "alpha 的验收标准有 2 条没有编号"
ac_spec ac-en '### Acceptance criteria' '' '+ no id'
check "Acceptance criteria 标题同样识别" 0 "alpha 的验收标准有 1 条没有编号"
ac_spec ac-none '## Objective' '' '- 没有验收标准一节'
check_absent "没有验收标准一节时不提示" "$AC_HINT"
ac_spec ac-fence '## Success criteria' '' '```markdown' '- 示例里的条目' '```' '- AC1：真的条目'
check_absent "围栏代码块里的示例不算" "$AC_HINT"
ac_spec ac-done '## Success criteria' '' '- 已完成模块没有编号'
mkdir -p "$PROJECT/tasks/alpha"; printf '# Plan\n' > "$PROJECT/tasks/alpha/plan.md"; printf '%s\n' '- [x] 做完' > "$PROJECT/tasks/alpha/todo.md"
check_absent "已完成模块不追溯" "$AC_HINT"

# 装包放宽（install-by-scope）：Plan 不再要求「需要的外部条件」，依赖清单不逐项对比——进行中模块新增依赖也不提示。
project relaxed; mkdir -p "$PROJECT/tasks/alpha"
printf '%s\n' '# alpha' > "$PROJECT/spec/alpha.md"
printf '%s\n' '# Plan' '' '## Task List' '' '- a' > "$PROJECT/tasks/alpha/plan.md"
printf '%s\n' '- [ ] a' > "$PROJECT/tasks/alpha/todo.md"
git -C "$PROJECT" -c init.defaultBranch=main init -q
printf '%s\n' '{"dependencies": {"react": "18"}}' > "$PROJECT/package.json"
git -C "$PROJECT" add -A && git -C "$PROJECT" -c user.name=t -c user.email=t@example.invalid -c commit.gpgsign=false \
  -c core.hooksPath=/dev/null commit -qm base
printf '%s\n' '{"dependencies": {"react": "18", "zod": "3"}}' > "$PROJECT/package.json"
check "未完成模块没有这一节、清单新增依赖时照常通过" 0 "0 警告 · 0 失败"
check_absent "不再提示「需要的外部条件」" "需要的外部条件"
check_absent "不再逐项报新增依赖" "依赖改动"

echo "verify-artifacts regression passed ($PASS cases)"
