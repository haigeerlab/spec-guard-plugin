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
  # usage-draft-gate：夹具是 git 仓库，否则每个夹具都多一条「多模块批次未判定」的警告。
  git init -q "$PROJECT"
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
  # usage-draft-gate：每个模块各自一次提交插入，不构成「多模块批次」，警告数只反映 todo 一项。
  git init -q "$PROJECT"
  for i in $(seq 1 "$2"); do
    id="$(printf m%02d "$i")"; ids="${ids}${ids:+, }${id}"
    rows+=("| ${id} | x | — |"); touch "$PROJECT/spec/${id}.md"
    printf '%s\n' '# Capability Map: fixture' '' '## 模块' '' '| Module id | Responsibility | Depends on |' \
      '| --- | --- | --- |' "${rows[@]}" '' "Build order: ${ids}" > "$PROJECT/spec/CAPABILITY-MAP.md"
    git -C "$PROJECT" add spec
    git -C "$PROJECT" -c user.name=t -c user.email=t@example.invalid -c core.hooksPath=/dev/null commit -q -m "$id" >/dev/null
  done
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
# zh_CN 判无效——阶段提示在同一份配置下出英文并带 ignored 行（config-per-key：只丢这个键）。
printf '{"version": 1, "artifactLanguage": "zh_CN"}\n' > "$PROJECT/.agent/config.json"
check "不合规的语言标签判无效" 1 "项目配置无效: artifactLanguage-invalid"
printf '{"version": 1, "reviewCadence": "both", "extra": 1}\n' > "$PROJECT/.agent/config.json"
check "无效的项目配置失败并列出原因" 1 "项目配置无效: unknown-key, reviewCadence-invalid"
# config-per-key：只有不认识的键（多半来自更新版本）只警告；结构问题仍失败。
printf '{"version": 1, "artifactLanguage": "en", "extra": 1}\n' > "$PROJECT/.agent/config.json"
check "只有未知键时警告、不失败" 0 "项目配置里有不认识的键，已忽略（可能来自更新版本的 spec-guard）"
printf '{"version": 2, "artifactLanguage": "en"}\n' > "$PROJECT/.agent/config.json"
check "结构问题的项目配置失败" 1 "项目配置无效: version-invalid"
printf '{"version": 1, "moduleConcurrency": "on"}\n' > "$PROJECT/.agent/config.json"
check "并行开关 on 的项目配置通过" 0 "项目配置有效"
# takeover-config：能力图上没有的模块 id 逐个警告、不判失败；档位写错整个键判无效。
printf '{"version": 1, "moduleTakeover": {"alpha": "plan", "ghost": "none", "zeta": {"merge": "auto"}}}\n' > "$PROJECT/.agent/config.json"
check "moduleTakeover 里能力图上没有的模块警告" 0 "项目配置 moduleTakeover 里的模块 ghost 不在能力图上"
check "每个未知模块各一条警告" 0 "项目配置 moduleTakeover 里的模块 zeta 不在能力图上"
printf '{"version": 1, "moduleTakeover": {"alpha": "fast"}}\n' > "$PROJECT/.agent/config.json"
check "moduleTakeover 取值写错判无效" 1 "项目配置无效: moduleTakeover-invalid"
printf '{"version": 1, "takeover": {"spec": "auto"}}\n' > "$PROJECT/.agent/config.json"
check "takeover 取值写错判无效" 1 "项目配置无效: takeover-invalid"
# takeover-redefine：旧值只读不写，文件里有旧预设 plan、带 spec／plan 的旧自定义时照常有效。
printf '{"version": 1, "takeover": "plan", "moduleTakeover": {"alpha": {"spec": "codex", "plan": "codex", "merge": "auto"}}}\n' > "$PROJECT/.agent/config.json"
check "旧值 plan 与带 spec、plan 的旧自定义照常有效" 0 "项目配置有效"
printf '{"version": 1, "takeover": {"design": "codex"}}\n' > "$PROJECT/.agent/config.json"
check "design 取值写错判无效" 1 "项目配置无效: takeover-invalid"
# takeover-config：已退役的 autonomyTier、moduleAutonomy（哪怕写错）只警告、不判失败。
printf '{"version": 1, "autonomyTier": "fast", "moduleAutonomy": {"ghost": "strict"}}\n' > "$PROJECT/.agent/config.json"
check "已退役的档位键只警告" 0 "项目配置里有已退役的 autonomyTier 或 moduleAutonomy"
check_absent "已退役的 moduleAutonomy 不再按能力图逐个警告" "moduleAutonomy 里的模块"
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

# pre-declared-scope（C3）：Plan 的「预先声明」一节不看并行开关；未完成模块格式错判失败、格式对计数，没有这一节或已完成不提示。
project declared; mkdir -p "$PROJECT/tasks/alpha"
printf '%s\n' '- [ ] a' > "$PROJECT/tasks/alpha/todo.md"
printf '%s\n' '# Plan' '' '## Task List' '' '- a' > "$PROJECT/tasks/alpha/plan.md"
check_absent "没有预先声明一节时不提示" "预先声明"
printf '%s\n' '# Plan' '' '## 预先声明' '' '- 外部依赖：`axe-core`' > "$PROJECT/tasks/alpha/plan.md"
check "预先声明格式错时失败（开关没开也查）" 1 "alpha 的预先声明格式错误: bad-dependency"
printf '%s\n' '# Plan' '' '## 预先声明' '' '- 外部依赖：`axe-core@^4`' '- 补丁：无' > "$PROJECT/tasks/alpha/plan.md"
check "预先声明格式正确时计数" 0 "预先声明格式正确（1 个未完成模块）"
printf '%s\n' '# Plan' '' '## 预先声明' '' '- 外部依赖：`axe-core`' > "$PROJECT/tasks/alpha/plan.md"
printf '%s\n' '- [x] a' > "$PROJECT/tasks/alpha/todo.md"
check_absent "已完成模块不追溯" "预先声明"

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
rv_project review-fenced-nested
printf '# Spec: alpha\n\n````text\n```\n%s\n%s\n````\n' "$RV_PENDING" "$RV_PENDING" > "$PROJECT/spec/alpha.md"
check_absent "代码块（4 包 3）里的示例不算标记" "批准标记"
printf '%s\n%s\n' "$RV_PENDING" "$RV_PENDING" >> "$PROJECT/spec/alpha.md"
check "代码块（4 包 3）外的重复标记照常判无效" 1 "批准标记无效：spec/alpha.md"
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

# AC 编号只推荐（align-upstream-rules）：verify-artifacts 不再对未完成模块缺编号给提示。
project ac-relaxed; printf '%s\n' '# alpha' '' '## Success criteria' '' '- 没有编号' > "$PROJECT/spec/alpha.md"
check_absent "验收标准没编号时不再提示" "的验收标准有"

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

# formal-deferral：todo.md 里的延期写法。合格的报有效；带前缀但格式不对、检查点写成延期的判失败；
# 像延期的自由文本、旁路文件里的延期只警告，并说明照旧算未完成或不算延期。
side_project deferral-ok
printf '%s\n' '- [x] a' '- [ ] 延期：故障注入；恢复条件：Mock 上线' > "$PROJECT/tasks/alpha/todo.md"
check "合格的延期项通过并报数" 0 "延期项写法有效：alpha（1 项）"
side_project deferral-no-condition
printf '%s\n' '- [x] a' '- [ ] 延期：故障注入' > "$PROJECT/tasks/alpha/todo.md"
check "延期项缺恢复条件判失败并给行号" 1 "tasks/alpha/todo.md:2 带延期前缀但格式不对"
check "延期项格式不对时给出正确写法" 1 "- [ ] 延期：<事项>；恢复条件：<条件>"
side_project deferral-checkpoint
printf '%s\n' '- [x] a' '- [ ] 延期：最终验收（gate）；恢复条件：以后' > "$PROJECT/tasks/alpha/todo.md"
check "检查点写成延期判失败" 1 "tasks/alpha/todo.md:2 检查点不能延期"
side_project deferral-informal
printf '%s\n' '- [x] a' '- [ ] D1：延期未验——缺外部授权' > "$PROJECT/tasks/alpha/todo.md"
check "像延期的自由文本只警告并给改写示例" 0 "tasks/alpha/todo.md:2 像是延期，但不是正式写法"
side_project deferral-side
printf '%s\n' '- [ ] 延期：故障注入；恢复条件：Mock 上线' '- [ ] 延期 X-02 缺 Mock' > "$PROJECT/tasks/alpha/deferred.md"
check "旁路文件里的延期写法警告不算延期" 0 "tasks/alpha/deferred.md 有 2 项延期写法，延期只在该模块的 todo.md 里才算数"
check "旁路文件里的合格延期仍按未勾选项报告" 0 "tasks/alpha/deferred.md 有 2 个未勾选项"
side_project deferral-none
check_absent "没有延期写法时不输出延期一节" "延期"

# usage-draft：spec/usage/ 下的用法草案由 usage_draft.py 判定；没有草案时不出现这一项。
usage_draft() {
  mkdir -p "$PROJECT/spec/usage"
  printf '%s\n' '# Usage draft: demo' '' '## Entry points' '' '| Entry | Does | Module |' '|---|---|---|' "| \`/demo\` | run | $1 |" '' \
    '## Typical usage' '' '### U1: run' 'Type it.' '' '## Milestones' '' '| Milestone | Usage | Modules |' '|---|---|---|' "| M1 | $2 | alpha |" \
    > "$PROJECT/spec/usage/demo.md"
}
project usage-none
check_absent "没有用法草案时不输出用法草案一项" "用法草案"
project usage-good
usage_draft alpha U1
check "合格用法草案通过" 0 "用法草案结构正确（1 份）"
# regression-doc-check（Q1 A）：联调回归不当作用法草案；格式与涉及的模块要对。
printf '## 用例清单\n\n### R1: 一起用\n- 步骤：a\n- 预期：b\n- 执行方式：manual\n- 证据：用户原话\n\n## 成功标准 → 联调用例\n\n不涉及\n\n## 涉及的模块\n\n- `alpha`\n' >"$PROJECT/spec/usage/demo.regression.md"
check "联调回归：合格式时通过、草案照常" 0 "联调回归格式正确：\`spec/usage/demo.regression.md\`（1 条用例）"
check "联调回归：不被当作用法草案" 0 "用法草案结构正确（1 份）"
printf '\n- `zeta`\n' >>"$PROJECT/spec/usage/demo.regression.md"
check "联调回归：涉及的模块不在能力图上时失败" 1 "联调回归问题：module-unknown（zeta）"
rm -f "$PROJECT/spec/usage/demo.regression.md"
project usage-bad
usage_draft alpha U2
check "用法草案引用不存在的用法判失败并点名" 1 "spec/usage/demo.md: 里程碑 M1 引用了不存在的典型用法 U2"
project usage-entry
usage_draft beta U1
check "入口归属模块不在里程碑里判失败" 1 "入口 \`/demo\` 归属的模块 beta 不在本草案的里程碑里"
# 「未验证」分支（#21443）：能力图读不了只提醒、带原因；脚本异常时提醒也带上报错的最后一行，不再被吞掉。
# usage-draft-gate：同一提交插入 2 个及以上未完成模块、又没有草案覆盖时警告；不判失败；读不到 git 报未判定。
batch_map() {
  local table="" order="alpha" id
  for id in "$@"; do table="${table}| ${id} | x | alpha |"$'\n'; order="${order} → ${id}"; done
  printf '%s\n' '# Capability Map: fixture' '' '## 目标' '' 'Verify artifacts.' '' '## 模块' '' \
    '| Module id | Responsibility | Depends on |' '| --- | --- | --- |' '| alpha | x | — |' > "$PROJECT/spec/CAPABILITY-MAP.md"
  printf '%s' "$table" >> "$PROJECT/spec/CAPABILITY-MAP.md"
  printf '%s\n' '' "Build order: ${order}" >> "$PROJECT/spec/CAPABILITY-MAP.md"
}
batch_git() { git -C "$PROJECT" -c user.name=t -c user.email=t@example.invalid -c core.hooksPath=/dev/null "$@" >/dev/null; }
project batch-missing
batch_git init -q; batch_git add -A; batch_git commit -q -m first
batch_map beta gamma; batch_git add -A; batch_git commit -q -m two
check "一个提交插入两个模块且无草案：警告不判失败" 0 "多模块批次缺用法草案：beta、gamma"
batch_map beta gamma delta epsilon
check "工作区未提交的新行也算一批" 0 "多模块批次缺用法草案：delta、epsilon（未提交）"
project batch-covered
batch_git init -q; batch_git add -A; batch_git commit -q -m first
batch_map beta gamma; batch_git add -A; batch_git commit -q -m two
mkdir -p "$PROJECT/spec/usage"
printf '%s\n' '# Usage draft: demo' '' '## Entry points' '' '| Entry | Does | Module |' '|---|---|---|' '| `/demo` | run | beta |' '' \
  '## Typical usage' '' '### U1: run' 'Type it.' '' '## Milestones' '' '| Milestone | Usage | Modules |' '|---|---|---|' '| M1 | U1 | beta, gamma |' \
  > "$PROJECT/spec/usage/demo.md"
check "草案覆盖了这一批：通过" 0 "多模块批次都有用法草案（1 批）"
project batch-single
batch_git init -q; batch_git add -A; batch_git commit -q -m first
batch_map beta; batch_git add -A; batch_git commit -q -m one
check_absent "没有批量插入时不输出这一项" "多模块批次"
PROJECT="$WORK/batch-nogit"; mkdir -p "$PROJECT/spec"; touch "$PROJECT/spec/alpha.md"
batch_map beta gamma
check "不是 git 仓库：未判定带原因" 0 "未判定：多模块批次的草案覆盖（not a git work tree）"
project usage-map-broken
usage_draft alpha U1
printf '%s\n' '# broken' > "$PROJECT/spec/CAPABILITY-MAP.md"
check "能力图读不了：用法草案报未验证并带原因" 1 "未验证：能力图读不了，没有检查用法草案（"
project usage-crash
usage_draft alpha U1
REAL_PY="$(command -v python3)"
mkdir -p "$WORK/crash-bin"
printf '%s\n' '#!/bin/bash' 'for a in "$@"; do case "$a" in */usage_draft.py) echo "Traceback (most recent call last):" >&2; echo "RuntimeError: boom in usage draft" >&2; exit 1;; esac; done' \
  "exec \"$REAL_PY\" \"\$@\"" > "$WORK/crash-bin/python3"
chmod +x "$WORK/crash-bin/python3"
RUN_PATH="$WORK/crash-bin:$PATH" check "用法草案脚本异常：未验证提醒带报错原因" 0 "未验证：用法草案检查没有正常运行（RuntimeError: boom in usage draft）"

# flow-doc-skeletons：新流程模块按档位查文档与章节；老模块不查。
flow_doc() {  # $1=文件 $2...=二级标题
  local file="$PROJECT/$1"; shift
  mkdir -p "$(dirname "$file")"
  : >"$file"
  for heading in "$@"; do printf '## %s\n\n不涉及\n\n' "$heading" >>"$file"; done
}
REQ=(目标 给谁用 使用场景 业务规则和异常情形 不做什么 成功标准 待定问题)
good_regression() {  # regression-doc-check：一份合格式的回归文档；$1=command 行（默认 `make test`，传空串表示不写）
  local command="${1-\`make test\`}"
  {
    printf '## 用例清单\n\n### R1: 保存\n- 步骤：点保存\n- 预期：已保存\n- 执行方式：command\n'
    [ -z "$command" ] || printf -- '- 命令：%s\n' "$command"
    printf -- '- 证据：运行输出\n\n## 成功标准对照\n\n不涉及\n\n## 受影响的老功能\n\n不涉及\n'
  } >"$PROJECT/tasks/alpha/regression.md"
}
project flow-ok
flow_doc spec/alpha.md "${REQ[@]}"; printf '<!-- spec-guard: flow v2 tier=normal -->\n' >>"$PROJECT/spec/alpha.md"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍
check "新流程模块：写到技术方案、章节齐全时通过" 0 "能力图通过严格解析"
check_absent "新流程模块：还没写回归不算缺" "缺失（档位"
flow_doc tasks/alpha/plan.md 任务 检查点
check "新流程模块：写了 Plan 却缺回归文档时失败" 1 "tasks/alpha/regression.md\` 缺失（档位 normal"
flow_doc tasks/alpha/regression.md 用例清单 受影响的老功能
check "新流程模块：回归文档缺章节时失败" 1 "tasks/alpha/regression.md\` 缺章节：成功标准对照"
flow_doc tasks/alpha/regression.md Cases "Success criteria coverage" "Affected existing features"
check_absent "新流程模块：英文章节名也认" "缺章节"
# regression-doc-check：回归文档的用例格式问题判失败；合格式时不报。
check "回归用例：没有用例时失败" 1 "tasks/alpha/regression.md\` 回归问题：no-cases"
good_regression
check_absent "回归用例：合格式时不报" "回归问题"
good_regression ""
check "回归用例：command 用例缺命令时失败" 1 "回归问题：case-command-missing（R1）"
project flow-bug
flow_doc spec/alpha.md 复现步骤 预期结果 回归用例; printf '<!-- spec-guard: flow v2 tier=bug -->\n' >>"$PROJECT/spec/alpha.md"
flow_doc tasks/alpha/plan.md 任务 检查点
check_absent "bug 档只要需求文档，不要求技术方案与回归" "缺失（档位"
project flow-tier
flow_doc spec/alpha.md "${REQ[@]}"; printf '<!-- spec-guard: flow v2 tier=huge -->\n' >>"$PROJECT/spec/alpha.md"
check "档位写错时警告并按 normal 处理" 0 "档位无效，按 normal 处理"
# project-sections：声明的追加章节并入骨架；配置不合法时只这一项失效、追加章节不生效。
project flow-sections
mkdir -p "$PROJECT/.agent"; printf '%s\n' '{"version": 1, "projectSections": {"design": ["浏览器兼容"]}}' >"$PROJECT/.agent/config.json"
flow_doc spec/alpha.md "${REQ[@]}"; printf '<!-- spec-guard: flow v2 tier=normal -->\n' >>"$PROJECT/spec/alpha.md"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍
check "追加章节：技术方案缺声明的章节时失败" 1 "tasks/alpha/design.md\` 缺章节：浏览器兼容"
printf '## 浏览器兼容\n\n不涉及\n' >>"$PROJECT/tasks/alpha/design.md"
check_absent "追加章节：补上标题后通过" "缺章节"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍; printf '## 浏览器兼容\n' >>"$PROJECT/tasks/alpha/design.md"
check "追加章节：只有标题没有内容时失败" 1 "章节没有内容（section-empty）：浏览器兼容"
printf '\n不涉及\n' >>"$PROJECT/tasks/alpha/design.md"
check_absent "追加章节：写了不涉及后通过" "section-empty"
printf '%s\n' '{"version": 1, "artifactLanguage": "zh-CN", "projectSections": {"design": ["影响面"]}}' >"$PROJECT/.agent/config.json"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍
check "追加章节配置不合法：报 projectSections-invalid" 1 "projectSections-invalid"
check_absent "追加章节配置不合法：追加章节不生效" "缺章节"
project flow-old
mkdir -p "$PROJECT/tasks/alpha"; printf '# Plan\n' >"$PROJECT/tasks/alpha/plan.md"
check_absent "老模块不查新流程文档" "缺失（档位"
# regression-doc-check（AC9）：老流程夹具的通过／警告／失败计数与退出码与本模块之前相同。
check "老流程夹具：计数与退出码不变" 0 "结果: 3 通过 · 1 警告 · 0 失败"
# design-review：技术方案的批准标记与轮次行写坏、两轮 criteria 不同时失败；重要需求只有第二审查者放行时警告；老模块不查。
design_round() {  # $1=轮次 $2=criteria：在技术方案的外部审查意见一节追加一行轮次行
  printf '<!-- spec-guard: design-review round=%s blocking=0 sha256=aaaaaaaaaaaa vendor=openai same-vendor=false criteria=%s report=%s -->\n' \
    "$1" "$2" "$(printf 'b%.0s' $(seq 64))" >>"$PROJECT/tasks/alpha/design.md"
}
reviewer_mark() {  # 给技术方案写一行按当前正文算的第二审查者放行标记
  python3 -B - "$HOOKDIR" "$PROJECT/tasks/alpha/design.md" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from module_stage import review_codex_digest, review_reviewer_line
path = Path(sys.argv[2])
text = "<!-- spec-guard: review pending -->\n" + path.read_text(encoding="utf-8")
path.write_text(text.replace("<!-- spec-guard: review pending -->", review_reviewer_line(review_codex_digest(text))),
                encoding="utf-8")
PY
}
project design-marks
flow_doc spec/alpha.md "${REQ[@]}"; printf '<!-- spec-guard: flow v2 tier=normal -->\n' >>"$PROJECT/spec/alpha.md"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍 外部审查意见
design_round 1 design-v1
reviewer_mark
check "技术方案：标记与轮次行有效时通过" 0 "能力图通过严格解析"
check_absent "技术方案：有效时不报轮次行" "技术方案审查轮次行写坏"
# takeover-redefine：默认档位 design=human 时，第二审查者放行不算数，警告；takeover=design 时不警告。
check "接管档位 design=human：技术方案只有第二审查者放行时警告" 0 "只有第二审查者的放行：接管档位 design=human的技术方案要用户批"
mkdir -p "$PROJECT/.agent" && printf '{"version": 1, "takeover": "design"}\n' > "$PROJECT/.agent/config.json"
check_absent "接管档位 design=reviewer：第二审查者放行不警告" "只有第二审查者的放行"
printf '<!-- spec-guard: design-review round=2 blocking=x -->\n' >>"$PROJECT/tasks/alpha/design.md"
check "技术方案：轮次行写坏时失败" 1 "有 1 行技术方案审查轮次行写坏了"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍 外部审查意见
design_round 1 design-v1; design_round 2 design-v2
check "技术方案：两轮 criteria 不同时失败" 1 "的审查轮次用了不同的 criteria：design-v1、design-v2"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍
printf '<!-- spec-guard: review approved -->\n' >>"$PROJECT/tasks/alpha/design.md"
check "技术方案：批准标记不带指纹时失败" 1 "tasks/alpha/design.md\` 的批准标记无效"
project design-important
flow_doc spec/alpha.md "${REQ[@]}"; printf '<!-- spec-guard: flow v2 tier=important -->\n' >>"$PROJECT/spec/alpha.md"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍
reviewer_mark
# sg-review-rules（规则 10）：重要需求跟着档位走——design=human 时照旧警告，design=reviewer 时不警告。
check "重要需求：design=human 时技术方案只有第二审查者放行仍警告" 0 "只有第二审查者的放行：接管档位 design=human的技术方案要用户批"
mkdir -p "$PROJECT/.agent" && printf '{"version": 1, "takeover": "design"}\n' > "$PROJECT/.agent/config.json"
check_absent "重要需求：design=reviewer 时第二审查者放行不警告" "只有第二审查者的放行"
project design-old
mkdir -p "$PROJECT/tasks/alpha"; printf '# d\n\n<!-- spec-guard: design-review round=x -->\n' >"$PROJECT/tasks/alpha/design.md"
check_absent "老模块不查技术方案的轮次行" "技术方案审查轮次行"
# plan-auto-approve：新流程 Plan 带标记、预先声明不起作用时警告；新流程并行边界写坏时失败；normal 没有范围时警告；老模块不变。
project plan-auto
flow_doc spec/alpha.md "${REQ[@]}"; printf '<!-- spec-guard: flow v2 tier=normal -->\n' >>"$PROJECT/spec/alpha.md"
flow_doc tasks/alpha/design.md 现状调研 影响面 实现方案 接口和数据改动 风险与回滚 方案取舍
check "新流程：影响面没写路径、也没有并行边界时警告" 0 "影响面也没写出路径：构建时越界检查会停下"
python3 - "$PROJECT/tasks/alpha/design.md" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
path.write_text(path.read_text(encoding="utf-8").replace("## 影响面\n\n不涉及", "## 影响面\n\n- 改 `src/alpha.py`"), encoding="utf-8")
PY
check_absent "新流程：影响面写了路径就不警告" "影响面也没写出路径"
good_regression
printf '# Plan\n\n<!-- spec-guard: review pending -->\n\n## 任务\n\n- t\n\n## 检查点\n\n- c\n\n## 预先声明\n\n- 公共路径：坏了\n' >"$PROJECT/tasks/alpha/plan.md"
printf -- '- [ ] t\n' >"$PROJECT/tasks/alpha/todo.md"
check "新流程：Plan 带批准标记时警告、不判失败" 0 "新流程 Plan 写完即自动批准，标记不起作用"
check "新流程：Plan 的预先声明写坏也只警告不起作用" 0 "Plan 的预先声明不起作用，不授权任何路径"
check_absent "新流程：预先声明不按格式错误判失败" "的预先声明格式错误"
printf '\n## 并行边界\n\n- 独占：\n' >>"$PROJECT/spec/alpha.md"
check "新流程：并行边界写坏时失败" 1 "的并行边界写坏了或读不了"
project plan-auto-old
mkdir -p "$PROJECT/tasks/alpha"; printf '# Plan\n\n<!-- spec-guard: review pending -->\n' >"$PROJECT/tasks/alpha/plan.md"
printf -- '- [ ] t\n' >"$PROJECT/tasks/alpha/todo.md"
check_absent "老模块的 Plan 标记不出新流程警告" "新流程 Plan"
# requirement-confirm-gate：新流程需求文档只有 Codex 的批准（指纹匹配或失配）时警告、不判失败；老模块不出这条。
codex_mark() {  # 给 $PROJECT/spec/alpha.md 写一行按当前正文算的 Codex 批准标记
  python3 -B - "$HOOKDIR" "$PROJECT/spec/alpha.md" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from module_stage import review_codex_digest, review_codex_line
path = Path(sys.argv[2])
text = path.read_text(encoding="utf-8").replace("<!-- spec-guard: review pending -->\n", "")
text = "<!-- spec-guard: review pending -->\n" + text
path.write_text(text.replace("<!-- spec-guard: review pending -->", review_codex_line(review_codex_digest(text))),
                encoding="utf-8")
PY
}
project flow-codex
flow_doc spec/alpha.md "${REQ[@]}"; printf '<!-- spec-guard: flow v2 tier=normal -->\n' >>"$PROJECT/spec/alpha.md"
codex_mark
check "新流程需求文档只有 Codex 批准时警告、不判失败" 0 "只有 Codex 的批准，需求要用户在对话里确认"
printf '补一句。\n' >>"$PROJECT/spec/alpha.md"
check "新流程需求文档 Codex 批准后改过，仍按只有 Codex 批准警告" 0 "只有 Codex 的批准，需求要用户在对话里确认"
project flow-codex-old
flow_doc spec/alpha.md "${REQ[@]}"
codex_mark
check_absent "老模块的 Codex 批准不出新流程警告" "只有 Codex 的批准"

echo "verify-artifacts regression passed ($PASS cases)"
