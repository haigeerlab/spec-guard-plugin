#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# module-namespace —— 验插件的**头号卖点**
#
#   README 问题①：多个模块共用一份 tasks/plan.md 和 todo.md（上游没有模块概念）。
#   插件的对策是 tasks/<module-id>/ 命名空间。
#   注意 README 的措辞已经不再断言「会互相覆盖」—— 上游 0.6.8 起 /plan 会停下来问而不是
#   静默覆盖（docs/upstream-analysis.md 缺口 B），而本评测最近一次真实运行也没能证明路径差异。
#   本脚本验的是「有约定时产物落进命名空间」，这一条与上游的止损无关，仍然成立。
#
# 2026-10-02 真实 Claude 运行中，有约定时两份产物进入命名空间；
# 无约定组也进入了命名空间。因此只在对照组完整落到根目录时才声称
# 观察到约定带来的路径差异。
#
# 2026-10-05 在 v0.42.0 发布后复跑（这是 _preflight 三条前提首次全部满足的一次：
# 装着的插件 = 仓库 HEAD 的 plugins/spec-guard，且工作区干净），结论相同：
# 两组都是 tasks/identity/{plan,todo}.md，命名空间 2/2、根下 0，判决仍是退出 2。
# 两次独立运行同向，所以「无约定就落到 tasks/plan.md」不能再当作当前上游的默认行为。
# 注意这使本脚本的退出 0 条件（对照组完整落在根目录）在当前上游下可能根本不可达 ——
# 若要让它重新成为有牙的判据，得先重新定义判据，而不是反复跑它。
#
# 为什么挑 local 模式：
#   - github 模式的两条通路已经验过（evals/skill-deferral.sh）
#   - local 模式**没有 skill 兜底**，13 行的块就是全部约定 —— 它不 work 就是真不 work
#   - local 是上游原生路径，新用户更可能从这儿进来
#
# 做法：两个脚手架（有块 / 无块），同一句「为 identity 拆任务」，
#       跑完看产物落在哪。这次判据是**文件系统**，不是 transcript ——
#       比读模型说了什么客观。
#
# ⚠️ 会真的调模型并允许它写文件（写在临时目录里）。不接进 validate.sh。
#
# 用法:
#   bash evals/module-namespace.sh
#   bash evals/module-namespace.sh --scaffold-only
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
PROMPT="为 identity 模块拆任务，产出计划和任务清单文件"
WORK="${TMPDIR:-/tmp}/spec-guard-ns-$$"
REPO="$(cd "$HERE/.." && pwd)"
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
    echo '{"activeModule":"identity"}' > "$1/.agent/state.json"
  fi
  printf '# 能力图\n\n## 目标\n\n让用户管理身份与账单。\n\n## 模块\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n| identity | 认证 | — |\n| billing | 计费 | identity |\n\nBuild order: identity → billing\n\n- [x] 已评审\n' > "$1/spec/CAPABILITY-MAP.md"
  printf '# identity\n\n验收：用户能注册、登录、登出。会话 30 天过期。\n' > "$1/spec/identity.md"
  ( cd "$1" && git add -A >/dev/null && git -c user.email=t@t -c user.name=t commit -qm init )
}

judge() {  # $1=目录 $2=组名 ; 0=落进命名空间 1=落错位置 2=什么都没产出
  local ns=0 flat=0
  [ -f "$1/tasks/identity/plan.md" ] && ns=$((ns+1))
  [ -f "$1/tasks/identity/todo.md" ] && ns=$((ns+1))
  [ -f "$1/tasks/plan.md" ] && flat=$((flat+1))
  [ -f "$1/tasks/todo.md" ] && flat=$((flat+1))
  echo "  [$2] tasks/ 下的产物：$(cd "$1" && find tasks -type f 2>/dev/null | sort | tr '\n' ' ' || echo '(无)')"
  echo "  [$2] 命名空间产物 ${ns}/2 · 根下单例产物 ${flat}"
  # 「一个产物都没有」和「产物落错位置」是两回事。前者多半是模型压根没跑
  # （或没写文件），把它读成「命名空间不成立」就是拿工具故障去指控产品 ——
  # 这个仓库对假警报的态度写在三条不可违反的性质里。
  if [ "${ns}" -eq 0 ] && [ "${flat}" -eq 0 ]; then
    if [ -n "$(find "$1/tasks" -type f -print -quit 2>/dev/null)" ]; then
      echo "  [$2] ❌ 发现任务文件，但不在约定的 plan/todo 路径"
      return 1
    fi
    echo "  [$2] ⏭  tasks/ 下什么都没有 —— 模型没产出任何任务文件，**这一组没有结论**"
    return 2
  fi
  [ "$ns" -eq 2 ] && [ "$flat" -eq 0 ]
}

conclude() {  # $1=有块判据 $2=无块判据 $3=无块目录
  local W="$1" N="$2" control="$3"
  if [ "$W" -eq 2 ]; then
    echo "  ⏭  有块那组什么都没产出 —— **没有结论**，不要读成「卖点不成立」"
    return 2
  fi
  if [ "$W" -ne 0 ]; then
    echo "  ❌ 有约定时产物**没有**落进命名空间 —— 插件的头号卖点不成立"
    return 1
  fi
  echo "  ℹ  有约定时 plan/todo 均落进 tasks/<module>/ 命名空间"
  if [ "$N" -eq 0 ]; then
    echo "  ⏭  两组都进入模块目录：路径可用，但无法证明约定带来了路径差异"
    return 2
  fi
  if [ "$N" -eq 2 ]; then
    echo "  ⏭  对照组零产物：命令虽退出 0，目标路径未获验证"
    return 2
  fi
  if [ "$N" -eq 1 ] &&
     [ -f "$control/tasks/plan.md" ] && [ -f "$control/tasks/todo.md" ] &&
     [ ! -e "$control/tasks/identity/plan.md" ] && [ ! -e "$control/tasks/identity/todo.md" ]; then
    echo "  ✅ 无约定时两份产物落在 tasks/ 根下；观察到约定组与对照组的路径差异"
    return 0
  fi
  echo "  ⏭  对照组未形成完整的根目录单例基线，无法证明路径差异"
  return 2
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

if [ "$MODE" = selftest ]; then
  trap 'rm -rf "$WORK"' EXIT
elif [ "$MODE" != scaffold ]; then
  preflight_installed_matches_repo "$REPO" || exit 2
fi

mkdir -p "$WORK"
mk "$WORK/withblk" with
mk "$WORK/noblk" without
echo "  脚手架: $WORK"
echo "  有块 CLAUDE.md $(wc -l < "$WORK/withblk/CLAUDE.md" | tr -d ' ') 行 · 无块 $(wc -l < "$WORK/noblk/CLAUDE.md" | tr -d ' ') 行"
check_scaffold || exit 1

if [ "$MODE" = selftest ]; then
  judge "$WORK/withblk" "零产物" >/dev/null; [ "$?" -eq 2 ] || exit 1
  mkdir -p "$WORK/withblk/tasks/other"
  touch "$WORK/withblk/tasks/other/plan.md"
  judge "$WORK/withblk" "错误路径" >/dev/null; [ "$?" -eq 1 ] || exit 1
  rm -rf "$WORK/withblk/tasks/other"
  mkdir -p "$WORK/withblk/tasks/identity"
  touch "$WORK/withblk/tasks/identity/plan.md"
  judge "$WORK/withblk" "仅 plan" >/dev/null; [ "$?" -eq 1 ] || exit 1
  rm "$WORK/withblk/tasks/identity/plan.md"
  touch "$WORK/withblk/tasks/identity/todo.md"
  judge "$WORK/withblk" "仅 todo" >/dev/null; [ "$?" -eq 1 ] || exit 1
  touch "$WORK/withblk/tasks/identity/plan.md"
  judge "$WORK/withblk" "两份产物" >/dev/null; [ "$?" -eq 0 ] || exit 1
  touch "$WORK/withblk/tasks/plan.md"
  judge "$WORK/withblk" "根下单例" >/dev/null; [ "$?" -eq 1 ] || exit 1
  rm "$WORK/withblk/tasks/plan.md"
  mkdir -p "$WORK/noblk/tasks/identity"
  touch "$WORK/noblk/tasks/identity/plan.md" "$WORK/noblk/tasks/identity/todo.md"
  judge "$WORK/noblk" "无块也命名空间" >/dev/null; N=$?
  output="$(conclude 0 "$N" "$WORK/noblk")"; result=$?
  [ "$result" -eq 2 ] && [[ "$output" == *"两组都进入模块目录"* ]] || { echo "  ❌ 两组同样命名空间时不应宣称差异"; exit 1; }
  rm -rf "$WORK/noblk/tasks/identity"
  judge "$WORK/noblk" "无块零产物" >/dev/null; N=$?
  output="$(conclude 0 "$N" "$WORK/noblk")"; result=$?
  [ "$result" -eq 2 ] && [[ "$output" == *"对照组零产物"* ]] || { echo "  ❌ 无块零产物不能证明差异"; exit 1; }
  touch "$WORK/noblk/tasks/plan.md"
  judge "$WORK/noblk" "无块仅 plan" >/dev/null; N=$?
  conclude 0 "$N" "$WORK/noblk" >/dev/null; [ "$?" -eq 2 ] || { echo "  ❌ 无块单文件不能证明差异"; exit 1; }
  touch "$WORK/noblk/tasks/todo.md"
  judge "$WORK/noblk" "无块根下两文件" >/dev/null; N=$?
  conclude 0 "$N" "$WORK/noblk" >/dev/null; [ "$?" -eq 0 ] || { echo "  ❌ 完整根目录基线应证明差异"; exit 1; }
  conclude 1 "$N" "$WORK/noblk" >/dev/null; [ "$?" -eq 1 ] || { echo "  ❌ 有块路径错误仍须判失败"; exit 1; }
  sed 's/Responsibility/职责/' "$WORK/withblk/spec/CAPABILITY-MAP.md" > "$WORK/withblk/spec/invalid-map.md"
  mv "$WORK/withblk/spec/CAPABILITY-MAP.md" "$WORK/withblk/spec/valid-map.md"
  mv "$WORK/withblk/spec/invalid-map.md" "$WORK/withblk/spec/CAPABILITY-MAP.md"
  check_scaffold >/dev/null 2>&1; [ "$?" -eq 1 ] || exit 1
  mkdir -p "$WORK/empty-home"
  HOME="$WORK/empty-home" /bin/bash "$HERE/module-namespace.sh" >/dev/null 2>&1
  [ "$?" -eq 2 ] || { echo "  ❌ 读不到安装版插件时应报环境未验证"; exit 1; }
  echo "  ✅ selftest: 有效脚手架、产物路径及有块/无块对照判据"
  exit 0
fi

[ "$MODE" = scaffold ] && { echo "  --scaffold-only：到此为止，未调用模型"; exit 0; }

RUNFAIL=0
for d in withblk noblk; do
  echo "  跑 $d …"
  # 原先是 `>/dev/null 2>&1` —— claude 跑不起来时 tasks/ 空着，judge 于是
  # 打出「插件的头号卖点不成立」。**拿工具故障去指控产品**，正是本仓最忌的那类。
  run_headless "$WORK/$d" "$WORK/$d.out" \
    -p "$PROMPT" --max-turns 12 --allowedTools Read Glob Grep Skill Write Edit \
    || RUNFAIL=1
done
if [ "${RUNFAIL}" -ne 0 ]; then
  echo ""
  echo "  ⏭  评测没跑起来 —— **没有结论**，不要读成「卖点不成立」"
  exit 2
fi

echo ""
judge "$WORK/withblk" "有块"; W=$?
judge "$WORK/noblk"   "无块"; N=$?
echo ""
conclude "$W" "$N" "$WORK/noblk"
exit $?
