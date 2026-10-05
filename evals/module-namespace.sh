#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# module-namespace —— 验「多模块产物互不覆盖」这条承诺
#
# 被测性质（单一、可机械判定）：在同一项目里连续推进两个模块后，
#   ① 两个模块的 plan+todo 各自落在能从 module id 推出来的路径；
#   ② 第一个模块的产物没有被第二轮运行改动；
#   ③ 没有产物落在共用的 tasks/plan.md、tasks/todo.md。
#
# 为什么是两个模块：README 问题① 说的是**第二个**模块和第一个撞车。
# 旧版夹具只推进 identity 一个模块，那次碰撞在它的夹具里结构上不可能出现 ——
# 也就是说旧判据从来观察不到它命名的那件事。这与上游行为变没变无关。
#
# 退出码只由**有约定组**决定（0 性质成立 / 1 性质被破坏 / 2 没跑起来或无结论）。
# 对照组（无约定）只作信息输出，不参与退出码。
#   旧版把「约定成立」和「对照组更差」压进同一个退出码，于是对照组一变好它就只能
#   永远退 2 —— 正是 docs/lenses.md A4 说的「永远在降级的探测器等于坏掉的探测器」。
#   按 B2，对照组是「不装 / 不用」的基线：它表现得一样好**不是产品缺陷**，
#   不该让产品判据变红。2026-10-02 与 2026-10-05 两次实测都是两组同样分目录。
#
# 为什么挑 local 模式：
#   - local 模式没有 skill 兜底，声明块就是全部约定 —— 它不 work 就是真不 work
#   - local 是上游原生路径，新用户更可能从这儿进来
#
# ⚠️ 非 scaffold 模式会真的调模型（4 次：两组 × 两轮）并允许它写文件（写在临时目录里）。
#    不接进 validate.sh；--selftest 不调模型，继续接在 validate.sh 里。
#
# 用法:
#   bash evals/module-namespace.sh
#   bash evals/module-namespace.sh --scaffold-only
#   bash evals/module-namespace.sh --selftest
# ─────────────────────────────────────────────────────────────
set -uo pipefail

MODE=run
case "${1:-}" in
  --scaffold-only) MODE=scaffold ;;
  --selftest) MODE=selftest ;;
  "") ;;
  *) echo "用法: $0 [--scaffold-only|--selftest]" >&2; exit 2 ;;
esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUG="$(cd "$HERE/.." && pwd)/plugins/spec-guard"
REPO="$(cd "$HERE/.." && pwd)"
M1=identity
M2=billing
PROMPT1="为 ${M1} 模块拆任务，产出计划和任务清单文件"
PROMPT2="现在为 ${M2} 模块拆任务，产出它的计划和任务清单文件"
WORK="${TMPDIR:-/tmp}/spec-guard-ns-$$"
# shellcheck source=evals/_preflight.sh
. "${HERE}/_preflight.sh"

mk() {  # $1=目录 $2=with|without
  rm -rf "$1"; mkdir -p "$1/spec"; ( cd "$1" && git init -q )
  printf '# CLAUDE.md\n\n身份服务。构建 `npm run build`，测试 `npm test`。\n' > "$1/CLAUDE.md"
  if [ "$2" = with ]; then
    {
      echo ""
      echo "<!-- BEGIN:agent-skills-convention -->"
      cat "$PLUG/templates/claude-block-local.md"
      echo "<!-- END:agent-skills-convention -->"
    } >> "$1/CLAUDE.md"
    mkdir -p "$1/.agent"
    printf '{"activeModule":"%s"}\n' "$M1" > "$1/.agent/state.json"
  fi
  printf '# 能力图\n\n## 目标\n\n让用户管理身份与账单。\n\n## 模块\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n| %s | 认证 | — |\n| %s | 计费 | %s |\n\nBuild order: %s → %s\n\n- [x] 已评审\n' "$M1" "$M2" "$M1" "$M1" "$M2" > "$1/spec/CAPABILITY-MAP.md"
  printf '# %s\n\n验收：用户能注册、登录、登出。会话 30 天过期。\n' "$M1" > "$1/spec/$M1.md"
  # 第二个模块也要有已评审的 Spec，否则它停在 NEEDS_SPEC，第二轮无从推进。
  printf '# %s\n\n验收：能按月出账、支持退款。\n' "$M2" > "$1/spec/$M2.md"
  ( cd "$1" && git add -A >/dev/null && git -c user.email=t@t -c user.name=t commit -qm init )
}

snapshot() {  # $1=目录 -> stdout: 每行「相对路径 sha256」
  python3 - "$1" <<'PY'
import hashlib, pathlib, sys
root = pathlib.Path(sys.argv[1]); tasks = root / "tasks"
if tasks.is_dir():
    for p in sorted(tasks.rglob("*")):
        if p.is_file():
            print("%s %s" % (p.relative_to(root),
                             hashlib.sha256(p.read_bytes()).hexdigest()))
PY
}

isolated() {  # $1=目录 $2=第一轮后的快照文件 $3=组名
              # 0=隔离成立 1=隔离被破坏 2=无结论（任一轮没产出）
  python3 - "$1" "$2" "$3" "$M1" "$M2" <<'PY'
import hashlib, pathlib, sys

root = pathlib.Path(sys.argv[1]); snap, label, m1, m2 = sys.argv[2:6]

now = {}
tasks = root / "tasks"
if tasks.is_dir():
    for p in sorted(tasks.rglob("*")):
        if p.is_file():
            now[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()

before = {}
try:
    for line in pathlib.Path(snap).read_text(encoding="utf-8").splitlines():
        if line.strip():
            path, digest = line.rsplit(" ", 1)
            before[path] = digest
except OSError:
    pass


def pair(module):
    return ["tasks/%s/%s" % (module, name) for name in ("plan.md", "todo.md")]


first = [p for p in pair(m1) if p in before]
one = [p for p in pair(m1) if p in now]
two = [p for p in pair(m2) if p in now]
flat = [p for p in ("tasks/plan.md", "tasks/todo.md") if p in now]
changed = [p for p in pair(m1) if p in before and now.get(p) != before[p]]
added = sorted(set(now) - set(before))

print("  [%s] 第二轮后 tasks/ 下：%s" % (label, " ".join(sorted(now)) or "(空)"))
print("  [%s] 模块1 %d/2 · 模块2 %d/2 · 根下单例 %d · 模块1 被改动 %d · 新增 %d"
      % (label, len(one), len(two), len(flat), len(changed), len(added)))

# 第一轮没交付模块1，第二轮的「隔离」就是空话 —— 判无结论，不判通过也不判失败。
if len(first) != 2:
    print("  [%s] ⏭  第一轮没有产出模块1 的 plan+todo（%d/2），隔离无从判断" % (label, len(first)))
    raise SystemExit(2)
if not added and not changed:
    print("  [%s] ⏭  第二轮既没有新文件也没有改动 —— 模型没推进，这一组没有结论" % label)
    raise SystemExit(2)
if changed:
    print("  [%s] ❌ 第二轮改动了模块1 的产物：%s" % (label, " ".join(changed)))
    raise SystemExit(1)
if flat:
    print("  [%s] ❌ 产物落在共用的根路径：%s" % (label, " ".join(flat)))
    raise SystemExit(1)
if len(two) != 2:
    print("  [%s] ❌ 模块2 的 plan+todo 不完整（%d/2）；新增的是：%s"
          % (label, len(two), " ".join(added) or "(无)"))
    raise SystemExit(1)
if len(one) != 2:
    print("  [%s] ❌ 模块1 的 plan+todo 在第二轮后不完整（%d/2）" % (label, len(one)))
    raise SystemExit(1)
print("  [%s] ✅ 两个模块各自隔离，模块1 未被第二轮改动" % label)
raise SystemExit(0)
PY
}

conclude() {  # $1=有约定组判据 $2=对照组判据
  local W="$1" N="$2"
  case "$W" in
    0) echo "  ✅ 有约定组满足隔离性质：两个模块各自落位，第一个模块未被第二轮改动" ;;
    1) echo "  ❌ 有约定组违反隔离性质 —— 这是产品缺陷" ;;
    *) echo "  ⏭  有约定组没有结论 —— 不要读成「隔离不成立」" ;;
  esac
  # 对照组不参与退出码。它是「不装 / 不用」的基线（docs/lenses.md B2）：
  # 表现得一样好不是产品缺陷，不该让产品判据变红。
  case "$N" in
    0) echo "  ℹ  对照组同样隔离 —— **未观察到差异**。这不削弱上面的结论：约定给的是保证，不是行为改变" ;;
    1) echo "  ℹ  对照组未能隔离 —— **观察到差异**" ;;
    *) echo "  ℹ  对照组没有结论（任一轮没产出）" ;;
  esac
  return "$W"
}

check_scaffold() {
  local output
  output="$(CLAUDE_PROJECT_DIR="$WORK/withblk" CLAUDE_PLUGIN_ROOT="$PLUG" bash "$PLUG/hooks/phase-guard.sh")"
  if ! python3 -c '
import json, sys
context = json.loads(sys.stdin.read())["hookSpecificOutput"]["additionalContext"]
assert "当前阶段: **NEEDS_PLAN**" in context
' <<< "$output"; then
    echo "  ❌ 有块脚手架未得到有效的 NEEDS_PLAN 阶段；评测无意义"
    return 1
  fi
  echo "  ✅ 有块脚手架得到有效的 NEEDS_PLAN 阶段"
}

# ── selftest：喂合成目录树，不调模型 ──────────────────────────────
fake() {  # $1=目录 $2...=要创建的相对路径
  local dir="$1"; shift
  rm -rf "$dir"
  local f
  for f in "$@"; do mkdir -p "$dir/$(dirname "$f")"; printf 'x\n' > "$dir/$f"; done
}

want() {  # $1=期望退出码 $2=用例名 $3...=命令
  local exp="$1" name="$2"; shift 2
  "$@" >/dev/null 2>&1
  local rc=$?
  if [ "$rc" -eq "$exp" ]; then
    printf '  ✅ %s\n' "$name"
  else
    printf '  ❌ %s（期望 %s，实际 %s）\n' "$name" "$exp" "$rc"
    return 1
  fi
}

selftest() {
  SMOKE="${TMPDIR:-/tmp}/spec-guard-ns-self-$$"
  trap 'rm -rf "$SMOKE" "$WORK"' EXIT
  mkdir -p "$SMOKE"
  local F=0 D="$SMOKE/t" SNAP="$SMOKE/snap"

  # 第一轮交付了模块1 的两份产物 —— 之后所有用例共用这份快照
  fake "$D" "tasks/$M1/plan.md" "tasks/$M1/todo.md"
  snapshot "$D" > "$SNAP"

  fake "$D" "tasks/$M1/plan.md" "tasks/$M1/todo.md" "tasks/$M2/plan.md" "tasks/$M2/todo.md"
  want 0 "isolated: 两模块各自落位 → 隔离成立" isolated "$D" "$SNAP" 自检 || F=1

  fake "$D" "tasks/$M1/plan.md" "tasks/$M1/todo.md"
  printf 'changed\n' > "$D/tasks/$M1/plan.md"
  mkdir -p "$D/tasks/$M2"; printf 'x\n' > "$D/tasks/$M2/plan.md"; printf 'x\n' > "$D/tasks/$M2/todo.md"
  want 1 "isolated: 第二轮改动了模块1 → 失败" isolated "$D" "$SNAP" 自检 || F=1

  # 两个模块都落位，只多出共用根路径 —— 这样只有 flat 这一条检查能让它失败。
  # 早先这个夹具里模块2 是空的，于是去掉 flat 检查后它仍因「模块2 不完整」退 1，
  # 变异体活了下来：断言只看退出码，分不出失败原因（docs/lenses.md B1b）。
  fake "$D" "tasks/$M1/plan.md" "tasks/$M1/todo.md" "tasks/$M2/plan.md" "tasks/$M2/todo.md" \
       "tasks/plan.md" "tasks/todo.md"
  want 1 "isolated: 两模块都落位但同时有共用根路径 → 失败" isolated "$D" "$SNAP" 自检 || F=1

  fake "$D" "tasks/$M1/plan.md" "tasks/$M1/todo.md" "tasks/$M2/plan.md"
  want 1 "isolated: 模块2 只有一半 → 失败" isolated "$D" "$SNAP" 自检 || F=1

  fake "$D" "tasks/$M1/plan.md" "tasks/$M1/todo.md" "tasks/$M2-plan.md"
  want 1 "isolated: 模块2 产物换了名字 → 失败" isolated "$D" "$SNAP" 自检 || F=1

  fake "$D" "tasks/$M1/plan.md" "tasks/$M1/todo.md"
  want 2 "isolated: 第二轮零产出 → 无结论（不是失败）" isolated "$D" "$SNAP" 自检 || F=1

  # 第一轮本身没交付 → 第二轮的隔离是空话，必须判无结论而不是通过
  fake "$SMOKE/empty"
  snapshot "$SMOKE/empty" > "$SMOKE/snap-empty"
  fake "$D" "tasks/$M2/plan.md" "tasks/$M2/todo.md"
  want 2 "isolated: 第一轮没交付模块1 → 无结论，不得空过" isolated "$D" "$SMOKE/snap-empty" 自检 || F=1

  # conclude：只有有约定组参与退出码
  want 0 "conclude: 约定成立 + 对照组也隔离 → 仍然通过" conclude 0 0 || F=1
  want 0 "conclude: 约定成立 + 对照组未隔离 → 通过" conclude 0 1 || F=1
  want 0 "conclude: 约定成立 + 对照组无结论 → 通过" conclude 0 2 || F=1
  want 1 "conclude: 约定被破坏 → 失败（无论对照组）" conclude 1 0 || F=1
  want 2 "conclude: 约定组无结论 → 无结论" conclude 2 1 || F=1
  grep -q "未观察到差异" <<<"$(conclude 0 0)" || { echo "  ❌ 对照组同样隔离时应明说未观察到差异"; F=1; }
  grep -q "观察到差异" <<<"$(conclude 0 1)" || { echo "  ❌ 对照组未隔离时应明说观察到差异"; F=1; }
  grep -q "产品缺陷" <<<"$(conclude 1 1)" || { echo "  ❌ 约定被破坏时应明说是产品缺陷"; F=1; }

  # 脚手架自身必须被验证有效（docs/lenses.md A4：脚手架建完要验它真的建成了）
  mkdir -p "$WORK"; mk "$WORK/withblk" with
  check_scaffold >/dev/null || { echo "  ❌ 干净脚手架应通过 check_scaffold"; F=1; }
  sed 's/Responsibility/职责/' "$WORK/withblk/spec/CAPABILITY-MAP.md" > "$WORK/withblk/spec/broken.md"
  mv "$WORK/withblk/spec/broken.md" "$WORK/withblk/spec/CAPABILITY-MAP.md"
  check_scaffold >/dev/null 2>&1 && { echo "  ❌ 能力图坏掉时 check_scaffold 必须失败"; F=1; }

  # 读不到安装版插件时必须报环境未就绪（退 2），不能当成产品结论
  mkdir -p "$SMOKE/empty-home"
  HOME="$SMOKE/empty-home" /bin/bash "$HERE/module-namespace.sh" >/dev/null 2>&1
  [ "$?" -eq 2 ] || { echo "  ❌ 读不到安装版插件时应报环境未验证"; F=1; }

  [ "$F" -eq 0 ] || return 1
  echo "  ✅ selftest: 两模块隔离判据、对照组只作信息、脚手架有效性与环境未就绪"
}

if [ "$MODE" = selftest ]; then
  selftest
  exit $?
fi

if [ "$MODE" != scaffold ]; then
  preflight_installed_matches_repo "$REPO" || exit 2
fi

trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK"
mk "$WORK/withblk" with
mk "$WORK/noblk" without
echo "  脚手架: $WORK"
echo "  有块 CLAUDE.md $(wc -l < "$WORK/withblk/CLAUDE.md" | tr -d ' ') 行 · 无块 $(wc -l < "$WORK/noblk/CLAUDE.md" | tr -d ' ') 行"
check_scaffold || exit 1

[ "$MODE" = scaffold ] && { echo "  --scaffold-only：到此为止，未调用模型"; exit 0; }

TOOLS="Read Glob Grep Skill Write Edit"
RUNFAIL=0
for d in withblk noblk; do
  echo "  跑 $d 第一轮（${M1}）…"
  # 原先两轮都把 claude 的输出丢掉 —— 跑不起来时 tasks/ 空着，判据于是打「卖点不成立」。
  # 拿工具故障去指控产品，正是本仓最忌的那类（docs/lenses.md B5）。
  if ! run_headless "$WORK/$d" "$WORK/$d.r1.out" -p "$PROMPT1" --max-turns 12 --allowedTools $TOOLS; then
    RUNFAIL=1; continue
  fi
  snapshot "$WORK/$d" > "$WORK/$d.snap1"
  # 有约定组按约定切换 activeModule；对照组没有这个文件，也不替它造一个 ——
  # 那会把约定的一部分偷偷装给对照组。
  if [ -f "$WORK/$d/.agent/state.json" ]; then
    printf '{"activeModule":"%s"}\n' "$M2" > "$WORK/$d/.agent/state.json"
  fi
  echo "  跑 $d 第二轮（${M2}）…"
  run_headless "$WORK/$d" "$WORK/$d.r2.out" -p "$PROMPT2" --max-turns 12 --allowedTools $TOOLS || RUNFAIL=1
done
if [ "${RUNFAIL}" -ne 0 ]; then
  echo ""
  echo "  ⏭  评测没跑起来 —— **没有结论**，不要读成「隔离不成立」"
  exit 2
fi

echo ""
isolated "$WORK/withblk" "$WORK/withblk.snap1" 有块; W=$?
isolated "$WORK/noblk"   "$WORK/noblk.snap1"   无块; N=$?
echo ""
conclude "$W" "$N"
exit $?
