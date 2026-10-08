#!/usr/bin/env bash
# 命令的插件根目录定位（spec/command-plugin-root.md）。
# Claude Code 不把 CLAUDE_PLUGIN_ROOT 导出给 Bash 工具，只在命令 Markdown 里把精确的
# `${CLAUDE_PLUGIN_ROOT}` 原地代入；`${CLAUDE_PLUGIN_ROOT:-…}` 不会被代入（2026-10-07 实测）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN="$ROOT/plugins/spec-guard"
COMMANDS_DIR="$PLUGIN/commands"
fail() { echo "FAIL: $1" >&2; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 规范引导段：每个用到 $ROOT 的命令都必须在第一次用到 $ROOT 之前逐字包含它。
cat > "$WORK/canon.sh" <<'CANON'
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
CANON

# ── 静态规则 ──
python3 - "$WORK/canon.sh" "$PLUGIN" <<'PY' || fail "静态规则"
import pathlib, re, sys
canon = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
plugin = pathlib.Path(sys.argv[2])
bad = []
# 不带规范引导段的命令必须登记在这里并写明理由；其余每个命令都必须带（丢掉整段引导会变红）。
EXEMPT = {
    "setup-convention.md": "直接调用会被代入的 ${CLAUDE_PLUGIN_ROOT}/hooks/setup-convention.sh",
    "teardown-convention.md": "直接调用会被代入的 ${CLAUDE_PLUGIN_ROOT}/hooks/teardown-convention.sh",
    "ticket.md": "只转交 ticket skill，不调用 hooks/ 脚本",
    "local-ticket-portability.md": "只转交 local-ticket-portability skill，不调用 hooks/ 脚本",
}
commands = sorted((plugin / "commands").glob("*.md"))
names = {path.name for path in commands}
for name in sorted(set(EXEMPT) - names):
    bad.append(f"豁免名单里的 {name} 不存在：删掉这条豁免")
for path in commands:
    if path.name in EXEMPT:
        continue
    text = path.read_text(encoding="utf-8")
    at = text.find(canon)
    if at < 0:
        bad.append(f"{path.name}: 没有逐字的规范引导段（不需要时登记进 EXEMPT 并写明理由）")
    elif "$ROOT" in text and text.find("$ROOT") < at:
        bad.append(f"{path.name}: 第一次用 $ROOT 之前没有逐字的规范引导段")
banned = {
    "${CLAUDE_PLUGIN_ROOT:-": "宿主不会代入带默认值的写法",
    "插件未安装或未启用": "定位失败不能说成未安装",
    "插件根目录不可用": "旧的不可诊断提示",
}
targets = sorted((plugin / "commands").glob("*.md")) + sorted((plugin / "skills").glob("*/SKILL.md"))
for path in targets:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(plugin)
    for needle, why in banned.items():
        if needle in text:
            bad.append(f"{rel}: 含 {needle!r}（{why}）")
    if re.search(r"\$CLAUDE_PLUGIN_ROOT\b", text) or re.search(r"`CLAUDE_PLUGIN_ROOT`", text):
        bad.append(f"{rel}: 让 Claude 读环境变量 CLAUDE_PLUGIN_ROOT（Bash 里为空），应写会被代入的 ${{CLAUDE_PLUGIN_ROOT}}")
# skill 与命令同一套根解析（spec/codex-skill-root.md）：spec-guard-ops 逐字带规范引导段；其余用 $ROOT 的
# skill 要么也带，要么写明 Codex 用 spec-guard-ops 的解析环境、Claude 用代入的 ROOT="${CLAUDE_PLUGIN_ROOT}"。
ops = (plugin / "skills" / "spec-guard-ops" / "SKILL.md").read_text(encoding="utf-8")
at = ops.find(canon)
if at < 0 or ops.find("$ROOT") < at:
    bad.append("skills/spec-guard-ops/SKILL.md: 第一次用 $ROOT 之前没有逐字的规范引导段")
for path in sorted((plugin / "skills").glob("*/SKILL.md")):
    text = path.read_text(encoding="utf-8")
    if "$ROOT" not in text or canon in text:
        continue
    if "spec-guard-ops" not in text or 'ROOT="${CLAUDE_PLUGIN_ROOT}"' not in text:
        bad.append(f"{path.relative_to(plugin)}: 用了 $ROOT，却没写明 Codex 用 spec-guard-ops 的解析环境、"
                   f"Claude 用代入的 ROOT=\"${{CLAUDE_PLUGIN_ROOT}}\"")
for name in ("ticket", "hosted-ticket-workflow"):
    text = (plugin / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    if 'ROOT="${CLAUDE_PLUGIN_ROOT}"' not in text:
        bad.append(f"skills/{name}/SKILL.md: 缺少 Claude 可代入的 ROOT=\"${{CLAUDE_PLUGIN_ROOT}}\"")
if not commands:
    bad.append("0 个命令文件：这是没找到，不是没问题")
for line in bad:
    print(line, file=sys.stderr)
sys.exit(1 if bad else 0)
PY

for command in phase verify-artifacts; do
  if grep -Fq '../references/workflow-checkpoints.md' "$COMMANDS_DIR/$command.md"; then
    fail "$command retains a reference path invalid after Codex command migration"
  fi
done

# ── 运行时：从 phase.md 取出第一段 bash ──
PROJECT="$WORK/project"
mkdir -p "$PROJECT/spec"
printf '%s\n' '<!-- BEGIN:spec-guard-codex-convention -->' '<!-- END:spec-guard-codex-convention -->' > "$PROJECT/AGENTS.md"
printf '%s\n' '# Capability Map' '| Module id | Responsibility | Depends on |' '|---|---|---|' '| alpha | x | — |' '' 'Build order: alpha' > "$PROJECT/spec/CAPABILITY-MAP.md"
touch "$PROJECT/spec/alpha.md"
awk '/^```bash$/{capture=1; next} capture && /^```$/{exit} capture{print}' \
  "$COMMANDS_DIR/phase.md" > "$WORK/phase-raw.sh"
# Claude Code 加载命令时做的代入：只替换精确的 ${CLAUDE_PLUGIN_ROOT}。
python3 - "$WORK/phase-raw.sh" "$PLUGIN" > "$WORK/phase-claude.sh" <<'PY'
import sys
print(open(sys.argv[1], encoding="utf-8").read().replace("${CLAUDE_PLUGIN_ROOT}", sys.argv[2]), end="")
PY

# 一个没有 codex 的 PATH：只放 git 与 python3。
mkdir -p "$WORK/base"
ln -s "$(command -v git)" "$WORK/base/git"
ln -s "$(command -v python3)" "$WORK/base/python3"
BASEPATH="$WORK/base:/usr/bin:/bin"
PATH="$BASEPATH" command -v codex >/dev/null 2>&1 && fail "测试 PATH 里不应有 codex"

fake_codex() { # $1 = 目录，$2 = 退出码，$3 = 输出
  mkdir -p "$1"
  printf '#!/bin/sh\nprintf "%%s\\n" '"'%s'"'\nexit %s\n' "$3" "$2" > "$1/codex"
  chmod +x "$1/codex"
}

run() { # $1 = 脚本，$2 = PATH，其余 = 额外环境
  local script="$1" path="$2"; shift 2
  set +e
  OUT="$(cd "$PROJECT" && env -u CLAUDE_PLUGIN_ROOT -u PLUGIN_ROOT -u CLAUDE_PROJECT_DIR PATH="$path" "$@" /bin/bash "$script" 2>&1)"
  RC=$?
  set -e
}
expect_ok() { [ "$RC" -eq 0 ] && grep -q 'NEEDS_PLAN' <<<"$OUT" || fail "$1（rc=${RC}）: $OUT"; }
expect_fail() { # $1 = 用例名，$2 = 应出现的原因
  [ "$RC" -eq 2 ] || fail "$1: 应退出 2，实际 $RC: $OUT"
  grep -Fq -- "$2" <<<"$OUT" || fail "$1: 缺少原因「$2」: $OUT"
  if grep -q '未安装' <<<"${OUT//不代表插件未安装/}"; then fail "$1: 把定位失败说成未安装: $OUT"; fi
}

run "$WORK/phase-claude.sh" "$BASEPATH"
expect_ok "Claude 代入后，空环境、无 codex 也应跑到插件自带的 hook"

run "$WORK/phase-raw.sh" "$BASEPATH" CLAUDE_PLUGIN_ROOT="$PLUGIN"
expect_ok "不代入的宿主经环境变量 CLAUDE_PLUGIN_ROOT 解析"

run "$WORK/phase-raw.sh" "$BASEPATH" PLUGIN_ROOT="$PLUGIN"
expect_ok "不代入的宿主经环境变量 PLUGIN_ROOT 解析"

fake_codex "$WORK/codex-ok" 0 "{\"installed\":[{\"name\":\"spec-guard\",\"installed\":true,\"enabled\":true,\"source\":{}},{\"name\":\"spec-guard\",\"installed\":true,\"enabled\":true,\"source\":{\"path\":\"$PLUGIN\"}}]}"
run "$WORK/phase-raw.sh" "$WORK/codex-ok:$BASEPATH"
expect_ok "环境变量都为空时回退到已启用的 Codex 插件"

run "$WORK/phase-raw.sh" "$BASEPATH"
expect_fail "无代入、无环境变量、无 codex" "也没有 codex 可查询"
grep -Fq '不代表插件未安装' <<<"$OUT" || fail "失败提示应说明这是定位失败: $OUT"

fake_codex "$WORK/codex-broken" 7 ""
run "$WORK/phase-raw.sh" "$WORK/codex-broken:$BASEPATH"
expect_fail "codex 查询失败" "查询失败（退出码 7）"

fake_codex "$WORK/codex-none" 0 '{"installed":[{"name":"other","installed":true,"enabled":true,"source":{"path":"/x"}}]}'
run "$WORK/phase-raw.sh" "$WORK/codex-none:$BASEPATH"
expect_fail "codex 未列出 spec-guard" "没有列出已启用且带路径的 spec-guard"

fake_codex "$WORK/codex-list" 0 '[]'
run "$WORK/phase-raw.sh" "$WORK/codex-list:$BASEPATH"
expect_fail "codex 输出不是对象" "或输出无法解析"

run "$WORK/phase-raw.sh" "$BASEPATH" PLUGIN_ROOT="$WORK/missing"
expect_fail "根目录不存在" "插件根目录不存在：$WORK/missing"

# ── 运行时：spec-guard-ops 的「解析环境」段（审查 F5：结构异常的列表曾抛 traceback）──
awk '/^## 解析环境/{section=1} section && /^```bash$/{capture=1; next} capture && /^```$/{exit} capture{print}' \
  "$PLUGIN/skills/spec-guard-ops/SKILL.md" > "$WORK/ops-raw.sh"
[ -s "$WORK/ops-raw.sh" ] || fail "spec-guard-ops 没有「解析环境」bash 段"
printf '%s\n' 'printf "ROOT=%s\n" "$ROOT"' >> "$WORK/ops-raw.sh"
python3 - "$WORK/ops-raw.sh" "$PLUGIN" > "$WORK/ops-claude.sh" <<'PY'
import sys
print(open(sys.argv[1], encoding="utf-8").read().replace("${CLAUDE_PLUGIN_ROOT}", sys.argv[2]), end="")
PY
expect_root() { # $1 = 用例名
  [ "$RC" -eq 0 ] && grep -Fxq "ROOT=$PLUGIN" <<<"$OUT" || fail "$1（rc=${RC}）: $OUT"
}
no_traceback() { if grep -q 'Traceback' <<<"$OUT"; then fail "$1: 出现 traceback: $OUT"; fi; }

fake_codex "$WORK/codex-trap" 9 "codex must not be called"
run "$WORK/ops-claude.sh" "$WORK/codex-trap:$BASEPATH"
expect_root "skill：Claude 代入后直接用代入的根目录，不调 codex"

run "$WORK/ops-raw.sh" "$WORK/codex-ok:$BASEPATH"
expect_root "skill：Codex 从已启用的插件列表解析根目录"

for case in "codex-list|或输出无法解析|列表是 []" "codex-broken|查询失败（退出码 7）|查询失败" "codex-none|没有列出已启用且带路径的 spec-guard|未列出 spec-guard"; do
  dir="${case%%|*}"; rest="${case#*|}"; reason="${rest%%|*}"; label="${rest#*|}"
  run "$WORK/ops-raw.sh" "$WORK/$dir:$BASEPATH"
  no_traceback "skill：$label"
  expect_fail "skill：$label" "$reason"
done
fake_codex "$WORK/codex-text" 0 'not json at all'
run "$WORK/ops-raw.sh" "$WORK/codex-text:$BASEPATH"
no_traceback "skill：输出不是 JSON"
expect_fail "skill：输出不是 JSON" "或输出无法解析"
run "$WORK/ops-raw.sh" "$BASEPATH"
expect_fail "skill：没有 codex" "也没有 codex 可查询"

echo 'Command plugin-root regression passed'
