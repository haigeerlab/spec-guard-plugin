#!/usr/bin/env bash
# hooks.json 入口命令的回归：直接取出注册的命令字符串，按宿主的方式用 sh -c 运行。
# 核心约束：插件根目录只来自宿主（PLUGIN_ROOT / CLAUDE_PLUGIN_ROOT），绝不执行项目仓库里的脚本。
set -euo pipefail

HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$(cd "$HOOKDIR/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0
CMD="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"])' "$HOOKDIR/hooks.json")"

fail() { echo "  ❌ $1" >&2; exit 1; }
ok() { echo "  ✅ $1"; PASS=$((PASS + 1)); }

entry() {  # 其余参数=env 赋值；在 $P 中运行入口命令，输出存到 $OUT
  set +e
  OUT="$(cd "$P" && env -u PLUGIN_ROOT -u CLAUDE_PLUGIN_ROOT "$@" CLAUDE_PROJECT_DIR="$P" /bin/sh -c "$CMD" </dev/null 2>&1)"
  RC=$?
  set -e
}

context() {  # 从 $OUT 取 additionalContext；不是宿主接受的 JSON 就失败
  python3 -c 'import json,sys; d=json.loads(sys.argv[1]); h=d["hookSpecificOutput"]; assert h["hookEventName"]=="UserPromptSubmit"; print(h["additionalContext"])' "$OUT" \
    || fail "输出不是宿主接受的 JSON：
$OUT"
}

P="$WORK/active"
mkdir -p "$P/.agent"
git -C "$P" init -q
printf '%s\n' '{"activeModule":""}' > "$P/.agent/state.json"
# 项目里放一个同名脚本：任何情况下都不能被执行。
mkdir -p "$P/.claude/hooks"
printf '#!/bin/sh\ntouch "%s/project-script-ran"\n' "$WORK" > "$P/.claude/hooks/phase-guard.sh"

entry PLUGIN_ROOT="$PLUGIN"
[ "$RC" -eq 0 ] && grep -F '当前阶段' >/dev/null <<<"$(context)" || fail "PLUGIN_ROOT 下应注入阶段"
ok "PLUGIN_ROOT（Codex）下运行插件自带的 phase-guard"

entry CLAUDE_PLUGIN_ROOT="$PLUGIN"
[ "$RC" -eq 0 ] && grep -F '当前阶段' >/dev/null <<<"$(context)" || fail "CLAUDE_PLUGIN_ROOT 下应注入阶段"
ok "CLAUDE_PLUGIN_ROOT（Claude Code）下运行插件自带的 phase-guard"

entry
[ "$RC" -eq 0 ] && grep -F '插件安装或宿主问题' >/dev/null <<<"$(context)" || fail "没有插件根目录时应报告安装问题"
ok "没有插件根目录时报告安装问题"

entry PLUGIN_ROOT="$WORK/empty-root"
[ "$RC" -eq 0 ] && grep -F '插件安装或宿主问题' >/dev/null <<<"$(context)" || fail "插件根目录缺脚本时应报告安装问题"
ok "插件根目录缺脚本时报告安装问题"
[ ! -e "$WORK/project-script-ran" ] || fail "入口命令执行了项目仓库里的 .claude/hooks/phase-guard.sh"
ok "从不执行项目仓库里的同名脚本"

mkdir -p "$WORK/broken/hooks"
printf 'exit 3\n' > "$WORK/broken/hooks/phase-guard.sh"
entry PLUGIN_ROOT="$WORK/broken"
[ "$RC" -eq 0 ] && grep -F '执行失败' >/dev/null <<<"$(context)" || fail "phase-guard 非零退出时应报告执行失败"
ok "phase-guard 非零退出时报告执行失败"

P="$WORK/unrelated"
mkdir -p "$P"
git -C "$P" init -q
entry PLUGIN_ROOT="$PLUGIN"
[ "$RC" -eq 0 ] && [ -z "$OUT" ] || fail "无激活信号的项目应静默
$OUT"
ok "无激活信号的项目静默"

echo "hook entry regression passed (${PASS} cases)"
