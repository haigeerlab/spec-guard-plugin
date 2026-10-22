#!/usr/bin/env bash
# setup-convention / teardown-convention 的回归：它们是插件里唯二写用户文件的操作，
# teardown 还是唯一的破坏性操作。每个用例都核对退出码、文件字节与目录状态。
set -euo pipefail

HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0
TEMPLATES="$HOOKDIR/../templates"
BEGIN='<!-- BEGIN:agent-skills-convention -->'
END='<!-- END:agent-skills-convention -->'

fail() { echo "  ❌ $1" >&2; exit 1; }
ok() { echo "  ✅ $1"; PASS=$((PASS + 1)); }

project() {  # $1=名字；新建一个 git 项目并设为 $P
  P="$WORK/$1"
  mkdir -p "$P"
  git -C "$P" init -q
}

run() {  # $1=脚本 其余=参数；在 $P 中运行，返回退出码，输出存到 $OUT
  local script="$1"; shift
  set +e
  OUT="$(CLAUDE_PROJECT_DIR="$P" /bin/bash "$HOOKDIR/$script" "$@" </dev/null 2>&1)"
  RC=$?
  set -e
}

snapshot() {  # 目录树与文件内容的指纹，用来证明“什么都没改”
  (cd "$P" && find . -path ./.git -prune -o -print | LC_ALL=C sort && \
    find . -path ./.git -prune -o -type f -print | LC_ALL=C sort | while read -r f; do cksum "$f"; done)
}

markers() { grep -Ec "^[[:space:]]*($BEGIN|$END)[[:space:]]*$" "$1" || true; }

# D17：派活规则段已退役。$1=文件 $2=END 标记 $3=规则模板：照旧版 setup --dispatch 的样子，把规则段插到块尾。
add_retired_rule() { python3 - "$@" <<'PY'
import sys
path, end, rule = sys.argv[1:4]
lines = [l for l in open(rule, encoding="utf-8").read().splitlines() if not l.startswith("<!-- spec-guard: retired")]
text = open(path, encoding="utf-8").read()
text = text.replace("\n" + end, "\n" + "\n".join(lines) + "\n\n" + end, 1)
open(path, "w", encoding="utf-8").write(text)
PY
}

# ── setup ──────────────────────────────────────────────
project dry
printf '# Mine\n' > "$P/CLAUDE.md"
before="$(snapshot)"
run setup-convention.sh local --dry-run
[ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] || fail "dry-run 不应改动任何文件
$OUT"
ok "dry-run 只预览"

project fresh
printf '# Mine\n' > "$P/CLAUDE.md"
run setup-convention.sh local
[ "$RC" -eq 0 ] || fail "首次 setup 失败
$OUT"
[ -f "$P/spec/CAPABILITY-MAP.md" ] && [ -d "$P/tasks" ] && [ -f "$P/.agent/state.json" ] || fail "setup 没有建好约定目录"
[ "$(markers "$P/CLAUDE.md")" -eq 2 ] || fail "setup 应恰好写入一对标记"
head -1 "$P/CLAUDE.md" | grep -Fx '# Mine' >/dev/null || fail "setup 改动了用户原有内容"
grep -F 'MAP_ONLY' >/dev/null <<<"$(CLAUDE_PROJECT_DIR="$P" /bin/bash "$HOOKDIR/phase-guard.sh" </dev/null)" || fail "setup 后 hook 未激活"
ok "首次 setup 建好目录与声明块，hook 激活"
# review-handoff-content：接入完成时说明批准节奏的两种取值，让用户知道有合并审这个选项。
for phrase in 'Review cadence:' '`separate` (default)' '`combined`' 'one approval' '/spec-guard:config (Codex: spec-guard-ops config)' 'artifact language'; do
  grep -F -- "$phrase" >/dev/null <<<"$OUT" || fail "setup 完成时的输出应说明批准节奏，缺少「${phrase}」
$OUT"
done
ok "setup 完成时说明批准节奏的两种取值"

# state.json 只存当前模块书签：退役的 tracker 与无人读取的 modules 都不再写入。
[ "$(cat "$P/.agent/state.json")" = '{"activeModule":""}' ] \
  || fail "setup 写下的 state.json 应恰为 {\"activeModule\":\"\"}，实际: $(cat "$P/.agent/state.json")"
ok "setup 写下的 state.json 只含 activeModule"

cp "$P/CLAUDE.md" "$WORK/installed"
run setup-convention.sh local
[ "$RC" -eq 0 ] && cmp -s "$P/CLAUDE.md" "$WORK/installed" && grep -F 'already has a convention block' >/dev/null <<<"$OUT" || fail "重复 setup 不应改动声明块
$OUT"
ok "已有声明块时不带 --replace 不改动"

python3 - "$P/CLAUDE.md" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
p.write_text(t.replace("能力图", "被手改的能力图", 1) + "\n# Tail\n", encoding="utf-8")
PY
# convention-block-local-lines：手改过的行是用户的行，删掉它要先经用户接受。
before="$(snapshot)"
run setup-convention.sh local --replace
[ "$RC" -eq 1 ] && [ "$(snapshot)" = "$before" ] && grep -F '被手改的能力图' >/dev/null <<<"$OUT" \
  && grep -F -- '--accept-removals' >/dev/null <<<"$OUT" || fail "块内有手改行时 --replace 应拒绝、列出该行且不改文件
$OUT"
ok "--replace 遇到手改行：拒绝、列出该行、不改文件"
run setup-convention.sh local --replace --accept-removals
[ "$RC" -eq 0 ] || fail "--replace --accept-removals 失败
$OUT"
[ "$(tail -1 "$P/CLAUDE.md")" = "# Tail" ] && ! grep -F '被手改的能力图' "$P/CLAUDE.md" >/dev/null && [ "$(markers "$P/CLAUDE.md")" -eq 2 ] || fail "--replace 应恢复模板并保留标记外内容"
ok "--replace --accept-removals 恢复模板正文，标记外内容不动"

# 本地段：块内用标记圈出的行在 --replace 后原样保留，放在新块末尾。
LB='<!-- BEGIN:spec-guard-local -->'; LE='<!-- END:spec-guard-local -->'
project local-keep
run setup-convention.sh local
python3 - "$P/CLAUDE.md" "$BEGIN" "$LB" "$LE" <<'PY'
import sys
from pathlib import Path
p, begin, lb, le = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
t = p.read_text(encoding="utf-8")
t = t.replace(begin + "\n", begin + "\n" + lb + "\n- 本项目自己的规则\n" + le + "\n", 1)
p.write_text(t, encoding="utf-8")
PY
before="$(snapshot)"
run setup-convention.sh local --replace --dry-run
[ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] && ! grep -F 'will remove' >/dev/null <<<"$OUT" || fail "只有本地段时预览不应列出删除，也不应改文件
$OUT"
run setup-convention.sh local --replace
[ "$RC" -eq 0 ] || fail "只有本地段时 --replace 不需要接受
$OUT"
python3 - "$P/CLAUDE.md" "$BEGIN" "$END" "$LB" "$LE" "$TEMPLATES/claude-block-local.md" <<'PY' || fail "本地段应原样保留在新块末尾，模板正文完整"
import sys
from pathlib import Path
p, begin, end, lb, le, tpl = sys.argv[1:7]
lines = Path(p).read_text(encoding="utf-8").splitlines()
body = lines[lines.index(begin) + 1:lines.index(end)]
# convention-block-blank-lines: one blank line inside each block marker and before the local section.
assert body[-4:] == [lb, "- 本项目自己的规则", le, ""], body[-4:]
assert body[0] == "" and body[-5] == "", (body[0], body[-5])
assert body[1:-5] == Path(tpl).read_text(encoding="utf-8").splitlines(), "template part differs"
PY
ok "本地段原样保留在新块末尾，模板正文完整"

# 预览逐行列出将删除与将新增的行。
python3 - "$P/CLAUDE.md" "$END" <<'PY'
import sys
from pathlib import Path
p, end = Path(sys.argv[1]), sys.argv[2]
t = p.read_text(encoding="utf-8").replace("能力图", "被手改的能力图", 1)
p.write_text(t.replace(end, "- 一行手写规则\n" + end, 1), encoding="utf-8")
PY
before="$(snapshot)"
run setup-convention.sh local --replace --dry-run
[ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] && grep -F 'will remove: - 一行手写规则' >/dev/null <<<"$OUT" \
  && grep -F 'will add:' >/dev/null <<<"$OUT" && ! grep -F 'will remove: - 本项目自己的规则' >/dev/null <<<"$OUT" || fail "预览应逐行列出将删除与将新增的行，不列本地段
$OUT"
ok "预览逐行列出将删除与将新增的行，本地段不在其中"

# 本地段标记无效时拒绝、不改文件。
for case in two-sections reversed unpaired; do
  project "local-$case"
  run setup-convention.sh local
  python3 - "$P/CLAUDE.md" "$BEGIN" "$LB" "$LE" "$case" <<'PY'
import sys
from pathlib import Path
p, begin, lb, le, case = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
extra = {"two-sections": [lb, "a", le, lb, "b", le], "reversed": [le, "a", lb], "unpaired": [lb, "a"]}[case]
t = p.read_text(encoding="utf-8")
p.write_text(t.replace(begin + "\n", begin + "\n" + "\n".join(extra) + "\n", 1), encoding="utf-8")
PY
  before="$(snapshot)"
  run setup-convention.sh local --replace --accept-removals
  [ "$RC" -ne 0 ] && [ "$(snapshot)" = "$before" ] || fail "${case}：本地段标记无效应拒绝且不改文件
$OUT"
  ok "${case}：本地段标记无效时拒绝，不改文件"
done

project accept-alone
run setup-convention.sh local --accept-removals
[ "$RC" -eq 2 ] || fail "--accept-removals 不配合 --replace 应是用法错误
$OUT"
ok "--accept-removals 单独给出是用法错误"

for case in duplicate missing-end; do
  project "$case"
  if [ "$case" = duplicate ]; then
    printf '%s\n' '# Mine' "$BEGIN" 'a' "$END" "$BEGIN" 'b' "$END" > "$P/CLAUDE.md"
  else
    printf '%s\n' '# Mine' "$BEGIN" 'a' > "$P/CLAUDE.md"
  fi
  before="$(snapshot)"
  run setup-convention.sh local --replace
  [ "$RC" -ne 0 ] && [ "$(snapshot)" = "$before" ] || fail "${case}：无效标记应拒绝且不留下任何文件
$OUT"
  ok "${case} 标记被拒绝，没有建目录或改文件"
done

project prose
printf '%s\n' "正文提到 \`$BEGIN\` 不算声明块。" > "$P/CLAUDE.md"
run setup-convention.sh local
[ "$RC" -eq 0 ] && [ "$(markers "$P/CLAUDE.md")" -eq 2 ] || fail "正文提及标记时应正常追加声明块
$OUT"
ok "正文提及标记不影响 setup"

# ── teardown ───────────────────────────────────────────
project roundtrip
printf '# Mine\n\nkeep me\n' > "$P/CLAUDE.md"
cp "$P/CLAUDE.md" "$WORK/original"
run setup-convention.sh local
touch "$P/spec/alpha.md"; mkdir -p "$P/tasks/alpha"; printf 'plan\n' > "$P/tasks/alpha/plan.md"
printf '%s\n' '{"activeModule":"alpha"}' > "$P/.agent/state.json"
before="$(snapshot)"
run teardown-convention.sh --dry-run
[ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] || fail "teardown --dry-run 不应改动任何文件
$OUT"
ok "teardown dry-run 只预览"

run teardown-convention.sh
[ "$RC" -eq 0 ] || fail "teardown 失败
$OUT"
cmp -s "$P/CLAUDE.md" "$WORK/original" || fail "setup→teardown 往返后 CLAUDE.md 应逐字节还原"
[ ! -e "$P/.agent/state.json" ] && [ -f "$P/.agent/state.json.disabled" ] || fail "teardown 应停用 state.json"
[ -f "$P/spec/alpha.md" ] && [ -f "$P/tasks/alpha/plan.md" ] && [ -f "$P/spec/CAPABILITY-MAP.md" ] || fail "teardown 不应删除用户的 spec 与 tasks"
[ -z "$(CLAUDE_PROJECT_DIR="$P" /bin/bash "$HOOKDIR/phase-guard.sh" </dev/null)" ] || fail "teardown 后 hook 应静默"
grep -F '已验证：hook 不再注入任何内容' >/dev/null <<<"$OUT" || fail "teardown 应实际核对 hook 已停止"
ok "teardown 逐字节还原声明块外内容，保留用户产物，hook 静默"

run teardown-convention.sh
[ "$RC" -eq 2 ] || fail "未启用的项目 teardown 应退出 2（实际 ${RC}）"
ok "未启用的项目 teardown 什么都不做"

before="$(snapshot)"
run setup-convention.sh local --dry-run
[ "$RC" -ne 0 ] && [ "$(snapshot)" = "$before" ] && grep -F 'state.json.disabled' >/dev/null <<<"$OUT" || fail "停用状态存在时 dry-run 应明确拒绝且不写入\n$OUT"
run setup-convention.sh local
[ "$RC" -ne 0 ] && [ "$(snapshot)" = "$before" ] || fail "重新 setup 不得新建空 state 覆盖停用上下文\n$OUT"
mv "$P/.agent/state.json.disabled" "$P/.agent/state.json"
run setup-convention.sh local
[ "$RC" -eq 0 ] && grep -F '"activeModule":"alpha"' "$P/.agent/state.json" >/dev/null && [ ! -e "$P/.agent/state.json.disabled" ] || fail "显式恢复后 setup 应保留原活动模块\n$OUT"
ok "停用状态阻止静默重建，显式恢复后上下文不变"

project state-conflict
mkdir -p "$P/.agent"
printf '%s\n' '{"activeModule":""}' > "$P/.agent/state.json"
printf '%s\n' '{"activeModule":"alpha"}' > "$P/.agent/state.json.disabled"
before="$(snapshot)"
run setup-convention.sh local
[ "$RC" -ne 0 ] && [ "$(snapshot)" = "$before" ] || fail "活动和停用状态并存时应拒绝且不写入\n$OUT"
ok "并存状态要求人工处理，不选择任一副本"

project keep
run setup-convention.sh local
run teardown-convention.sh --keep-state
[ "$RC" -eq 0 ] && [ -f "$P/.agent/state.json" ] && [ "$(markers "$P/CLAUDE.md")" -eq 0 ] || fail "--keep-state 应移除声明块但保留 state
$OUT"
ok "--keep-state 保留 state.json"

project bad-teardown
run setup-convention.sh local
printf '%s\n' "$BEGIN" 'dup' "$END" >> "$P/CLAUDE.md"
before="$(snapshot)"
run teardown-convention.sh
[ "$RC" -ne 0 ] && [ "$(snapshot)" = "$before" ] || fail "重复标记时 teardown 应拒绝且不停用 state
$OUT"
ok "重复标记时 teardown 拒绝，state 保持原样"

project prose-teardown
mkdir -p "$P/.agent"
printf '%s\n' '{"activeModule":""}' > "$P/.agent/state.json"
printf '%s\n' "正文提到 \`$BEGIN\` 不算声明块。" > "$P/CLAUDE.md"
cp "$P/CLAUDE.md" "$WORK/prose-original"
run teardown-convention.sh
[ "$RC" -eq 0 ] && cmp -s "$P/CLAUDE.md" "$WORK/prose-original" && [ -f "$P/.agent/state.json.disabled" ] || fail "正文提及标记时 teardown 应只停用 state
$OUT"
ok "正文提及标记不影响 teardown"

project codex
printf '# Agents\n' > "$P/AGENTS.md"
cp "$P/AGENTS.md" "$WORK/agents-original"
run setup-convention.sh local --host=codex
[ "$RC" -eq 0 ] && grep -Fx '<!-- BEGIN:spec-guard-codex-convention -->' "$P/AGENTS.md" >/dev/null || fail "Codex setup 应写入 AGENTS.md
$OUT"
run teardown-convention.sh --host=codex
[ "$RC" -eq 0 ] && cmp -s "$P/AGENTS.md" "$WORK/agents-original" || fail "Codex 往返后 AGENTS.md 应逐字节还原
$OUT"
ok "Codex 主机的 setup 与 teardown 往返"

# teardown-local-section：本地段的内容留在原位置；其余手写行要 --accept-removals。
add_local() {  # $1=文件 $2=END 标记 其余=本地段里的行
  local file="$1" end="$2"; shift 2
  python3 - "$file" "$end" "$@" <<'PY'
import sys
path, end, rows = sys.argv[1], sys.argv[2], sys.argv[3:]
text = open(path, encoding="utf-8").read()
local = "<!-- BEGIN:spec-guard-local -->\n" + "".join(r + "\n" for r in rows) + "<!-- END:spec-guard-local -->\n"
open(path, "w", encoding="utf-8").write(text.replace(end, local + end, 1))
PY
}
add_hand() {  # $1=文件 $2=BEGIN 标记 $3=手写行：放在块正文第一行
  python3 - "$1" "$2" "$3" <<'PY'
import sys
path, begin, row = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
open(path, "w", encoding="utf-8").write(text.replace(begin + "\n", begin + "\n" + row + "\n", 1))
PY
}

project teardown-local
printf '# Mine\n' > "$P/CLAUDE.md"
run setup-convention.sh local
add_local "$P/CLAUDE.md" "$END" '- 本地规则一' '- 本地规则二'
before="$(snapshot)"
run teardown-convention.sh --dry-run
[ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] || fail "本地段 teardown 预览应成功且不改文件
$OUT"
grep -F 'keeps the local section in place (2 lines)' >/dev/null <<<"$OUT" || fail "预览应说明本地段 2 行留在原位置
$OUT"
grep -F 'needs --accept-removals' >/dev/null <<<"$OUT" && fail "只有本地段时预览不应要求 --accept-removals
$OUT"
run teardown-convention.sh
[ "$RC" -eq 0 ] || fail "只有本地段时 teardown 不需要 --accept-removals
$OUT"
[ "$(cat "$P/CLAUDE.md")" = "$(printf '# Mine\n\n- 本地规则一\n- 本地规则二')" ] || fail "本地段内容应留在块原位置、标记去掉，实际:
$(cat "$P/CLAUDE.md")"
[ -f "$P/.agent/state.json.disabled" ] || fail "本地段 teardown 仍应停用 state.json"
grep -F '2' >/dev/null <<<"$(grep -F '本地段' <<<"$OUT")" || fail "完成提示应说明本地段留在原位置的行数
$OUT"
ok "teardown 把本地段内容留在原位置，去掉本地段标记"

project teardown-hand
printf '# Mine\n' > "$P/CLAUDE.md"
run setup-convention.sh local
add_local "$P/CLAUDE.md" "$END" '- 本地规则'
add_hand "$P/CLAUDE.md" "$BEGIN" '- 一行手写规则'
before="$(snapshot)"
run teardown-convention.sh --dry-run
[ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] || fail "有手写行时 teardown 预览也不改文件
$OUT"
grep -F 'will remove: - 一行手写规则   [needs --accept-removals]' >/dev/null <<<"$OUT" || fail "预览应逐行列出需接受的手写行
$OUT"
grep -F 'will remove: - 本地规则' >/dev/null <<<"$OUT" && fail "预览不应把本地段的行列为删除
$OUT"
run teardown-convention.sh
[ "$RC" -eq 1 ] && [ "$(snapshot)" = "$before" ] || fail "有手写行时 teardown 不带参数应退出 1，指令文件与 state 都不变（实际 ${RC}）
$OUT"
grep -F -- '- 一行手写规则' >/dev/null <<<"$OUT" && grep -F -- '--accept-removals' >/dev/null <<<"$OUT" || fail "拒绝时应列出手写行并提示 --accept-removals
$OUT"
run teardown-convention.sh --accept-removals
[ "$RC" -eq 0 ] && [ "$(cat "$P/CLAUDE.md")" = "$(printf '# Mine\n\n- 本地规则')" ] && [ -f "$P/.agent/state.json.disabled" ] \
  || fail "带 --accept-removals 后应移除手写行、保留本地段内容并停用 state
$OUT
$(cat "$P/CLAUDE.md")"
ok "teardown 遇到手写行先拒绝，--accept-removals 后移除"

for case in two reversed unpaired; do
  project "teardown-local-$case"
  printf '# Mine\n' > "$P/CLAUDE.md"
  run setup-convention.sh local
  case "$case" in
    two) add_local "$P/CLAUDE.md" "$END" '- a'; add_local "$P/CLAUDE.md" "$END" '- b' ;;
    reversed) python3 - "$P/CLAUDE.md" "$END" <<'PY'
import sys
p, end = sys.argv[1:3]
t = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(t.replace(end, "<!-- END:spec-guard-local -->\n- a\n<!-- BEGIN:spec-guard-local -->\n" + end, 1))
PY
    ;;
    unpaired) python3 - "$P/CLAUDE.md" "$END" <<'PY'
import sys
p, end = sys.argv[1:3]
t = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(t.replace(end, "<!-- BEGIN:spec-guard-local -->\n- a\n" + end, 1))
PY
    ;;
  esac
  before="$(snapshot)"
  run teardown-convention.sh --accept-removals
  [ "$RC" -ne 0 ] && [ "$(snapshot)" = "$before" ] || fail "本地段标记损坏（${case}）时 teardown 应拒绝且不改任何文件
$OUT"
done
ok "本地段标记损坏时 teardown 拒绝，state 保持原样"

project teardown-accept-noblock
mkdir -p "$P/.agent"
printf '%s\n' '{"activeModule":""}' > "$P/.agent/state.json"
before="$(snapshot)"
run teardown-convention.sh --accept-removals
[ "$RC" -eq 2 ] && [ "$(snapshot)" = "$before" ] || fail "没有约定块时 --accept-removals 应是用法错误（退出 2，实际 ${RC}）
$OUT"
ok "没有约定块时 --accept-removals 退出 2"

project teardown-dispatch
printf '# Mine\n' > "$P/CLAUDE.md"
cp "$P/CLAUDE.md" "$WORK/dispatch-original"
run setup-convention.sh local
add_retired_rule "$P/CLAUDE.md" "$END" "$TEMPLATES/claude-dispatch-rule.md"
run teardown-convention.sh
[ "$RC" -eq 0 ] && cmp -s "$P/CLAUDE.md" "$WORK/dispatch-original" || fail "只有派活规则段时 teardown 不需要接受，且逐字节还原
$OUT"
ok "派活规则段属于已知行，teardown 不需要接受"

project teardown-codex-local
printf '# Agents\n' > "$P/AGENTS.md"
run setup-convention.sh local --host=codex
add_local "$P/AGENTS.md" '<!-- END:spec-guard-codex-convention -->' '- codex 本地规则'
add_hand "$P/AGENTS.md" '<!-- BEGIN:spec-guard-codex-convention -->' '- codex 手写'
before="$(snapshot)"
run teardown-convention.sh --host=codex
[ "$RC" -eq 1 ] && [ "$(snapshot)" = "$before" ] || fail "Codex：有手写行时 teardown 应拒绝且不改文件
$OUT"
run teardown-convention.sh --host=codex --accept-removals
[ "$RC" -eq 0 ] && [ "$(cat "$P/AGENTS.md")" = "$(printf '# Agents\n\n- codex 本地规则')" ] || fail "Codex：接受后应只留下本地段内容
$OUT
$(cat "$P/AGENTS.md")"
ok "Codex 主机的 teardown 同样保留本地段、拒绝手写行"

# 删掉声明块后仍只凭 state.json 的 activeModule 激活：激活信号不因删除 tracker 字段而减少。
# 放在最后，避免改写 $P 影响前面依赖同一个项目的用例。
project signal-only
run setup-convention.sh local
[ "$RC" -eq 0 ] || fail "signal-only 夹具的 setup 失败
$OUT"
rm -f "$P/CLAUDE.md"
grep -F 'MAP_ONLY' >/dev/null <<<"$(CLAUDE_PROJECT_DIR="$P" /bin/bash "$HOOKDIR/phase-guard.sh" </dev/null)" \
  || fail "没有声明块时，仅凭 state.json 的 activeModule 应仍然激活"
ok "仅凭 activeModule 激活，不依赖声明块"

# ── build-task-dispatch 规则段已退役（D17）──────────────
DISPATCH_MARKER='<!-- spec-guard: build-task-dispatch -->'
RETIRED_LINE='  • retired build-task-dispatch rule section will be removed'
for host in claude codex; do
  tpl="$TEMPLATES/${host}-dispatch-rule.md"
  [ -f "$tpl" ] || fail "规则段模板 ${host}-dispatch-rule.md 应保留（只供识别旧声明块）"
  grep -F 'retired' <<<"$(head -n 1 "$tpl")" >/dev/null || fail "${host} 规则段模板首行应注明已退役"
  [ "$(grep -Fxc "$DISPATCH_MARKER" "$tpl")" -eq 1 ] || fail "${host} 规则段模板应仍含旧开关标记，供识别旧块"
done
ok "规则段模板保留且注明已退役"

# $1=文件 $2=BEGIN $3=END：输出两条标记之间的正文（不含标记行）
block_body() { awk -v b="$2" -v e="$3" '{s=$0; gsub(/^[ \t\r]+|[ \t\r]+$/, "", s)} s==e{inb=0} inb{print} s==b{inb=1}' "$1"; }
host_run() { run setup-convention.sh local ${HOSTARG:+"$HOSTARG"} "$@"; }
# $1=期望内容文件（模板按序拼接）：块的非空行与它的非空行逐字相同，且块按标准写法排空行。
block_is() { block_body "$P/$HT" "$HB" "$HE" > "$WORK/actual-body"; blank_lines_ok "$P/$HT" "$HB" "$HE" \
  && python3 -c 'import sys; t=lambda f: [l for l in open(f, encoding="utf-8").read().splitlines() if l.strip()]; sys.exit(t(sys.argv[1]) != t(sys.argv[2]))' \
     "$WORK/actual-body" "$1"; }
# convention-block-blank-lines：$1=文件 $2=BEGIN $3=END。块标记与本地段标记前后各恰好一个空行
# （文件开头与末尾除外；本地段只查外侧），标记前不留两个空行。
blank_lines_ok() { python3 - "$@" <<'PY'
import sys
path, begin, end = sys.argv[1:4]
lines = [l.rstrip("\r") for l in open(path, encoding="utf-8").read().split("\n")]
if lines and lines[-1] == "":
    lines.pop()
marks = {begin, end, "<!-- BEGIN:spec-guard-local -->", "<!-- END:spec-guard-local -->",
         "<!-- spec-guard: build-task-dispatch -->"}
start = next(i for i, l in enumerate(lines) if l.strip() == begin)
finish = next(i for i, l in enumerate(lines) if l.strip() == end)
for i in range(start, finish + 1):
    if lines[i].strip() not in marks:
        continue
    # The local section's inside belongs to the project: only its outside is checked.
    mark = lines[i].strip()
    if i > 0 and lines[i - 1].strip() and mark != "<!-- END:spec-guard-local -->":
        sys.exit("no blank line before line %d: %s" % (i + 1, lines[i]))
    if i + 1 < len(lines) and lines[i + 1].strip() and mark != "<!-- BEGIN:spec-guard-local -->":
        sys.exit("no blank line after line %d: %s" % (i + 1, lines[i]))
    if i > 1 and i - 1 > start and not lines[i - 2].strip() and lines[i].strip() != begin:
        sys.exit("two blank lines before line %d" % (i + 1))
PY
}
for host in claude codex; do
  if [ "$host" = codex ]; then
    HB='<!-- BEGIN:spec-guard-codex-convention -->'; HE='<!-- END:spec-guard-codex-convention -->'
    HT=AGENTS.md; HOSTARG=--host=codex
  else
    HB="$BEGIN"; HE="$END"; HT=CLAUDE.md; HOSTARG=""
  fi
  BASE="$TEMPLATES/${host}-block-local.md"; RULE="$TEMPLATES/${host}-dispatch-rule.md"
  base_body="$WORK/${host}-base-body"
  cat "$BASE" > "$base_body"

  project "${host}-dispatch-default"
  host_run
  [ "$RC" -eq 0 ] && block_is "$base_body" && ! grep -F "$DISPATCH_MARKER" "$P/$HT" >/dev/null || fail "${host}：setup 的块应与基础模板逐字相同、不含派活标记
$OUT"
  ok "${host}：setup 不写规则段，块与基础模板逐字相同"

  for flag in --dispatch --no-dispatch; do
    project "${host}${flag}-retired"
    before="$(snapshot)"
    host_run "$flag"
    [ "$RC" -eq 2 ] && [ "$(snapshot)" = "$before" ] && grep -F 'retired' >/dev/null <<<"$OUT" || fail "${host}：${flag} 应退出 2、说明已退役且不改文件
$OUT"
  done
  ok "${host}：--dispatch 与 --no-dispatch 都已退役，退出 2，不改文件"

  project "${host}-dispatch-old-block"
  host_run
  add_retired_rule "$P/$HT" "$HE" "$RULE"
  grep -Fx "$DISPATCH_MARKER" "$P/$HT" >/dev/null || fail "${host}：测试夹具应带旧规则段"
  before="$(snapshot)"
  host_run --replace --dry-run
  [ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] && grep -Fx "$RETIRED_LINE" >/dev/null <<<"$OUT" \
    && ! grep -F 'needs --accept-removals' >/dev/null <<<"$OUT" || fail "${host}：旧块带规则段时预览应单列退役行、不需要 --accept-removals
$OUT"
  host_run --replace
  [ "$RC" -eq 0 ] && block_is "$base_body" && grep -Fx "$RETIRED_LINE" >/dev/null <<<"$OUT" || fail "${host}：--replace 应移除旧规则段，块回到基础模板
$OUT"
  host_run --replace --dry-run
  ! grep -F "$RETIRED_LINE" >/dev/null <<<"$OUT" || fail "${host}：规则段移除后预览不应再有退役行
$OUT"
  ok "${host}：--replace 自动移除旧规则段，预览单列一行"

  # 标记行带缩进、文件是 CRLF 时，仍认作旧规则段。
  project "${host}-dispatch-crlf"
  host_run
  add_retired_rule "$P/$HT" "$HE" "$RULE"
  python3 - "$P/$HT" "$DISPATCH_MARKER" <<'PY'
import sys
from pathlib import Path
p, mark = Path(sys.argv[1]), sys.argv[2]
t = p.read_text(encoding="utf-8").replace(mark, "  " + mark + " ")
p.write_bytes(t.replace("\n", "\r\n").encode("utf-8"))
PY
  host_run --replace --dry-run
  grep -Fx "$RETIRED_LINE" >/dev/null <<<"$OUT" || fail "${host}：CRLF 与缩进的标记行应仍认作旧规则段
$OUT"
  ok "${host}：CRLF 文件与带缩进的标记行仍认作旧规则段"

  # 正文里提到标记、或标记不在块内，都不算旧规则段。
  project "${host}-dispatch-prose"
  host_run
  python3 - "$P/$HT" "$HE" "$DISPATCH_MARKER" <<'PY'
import sys
from pathlib import Path
p, end, mark = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
t = p.read_text(encoding="utf-8")
t = t.replace(end, "正文提到 `%s` 不算开启。\n%s" % (mark, end), 1) + "\n%s\n" % mark
p.write_text(t, encoding="utf-8")
PY
  host_run --replace --accept-removals
  [ "$RC" -eq 0 ] && block_is "$base_body" && ! grep -F "$RETIRED_LINE" >/dev/null <<<"$OUT" || fail "${host}：块内行中提及或块外的标记不应算旧规则段
$OUT"
  ok "${host}：块内正文提及或块外的标记不算旧规则段"
done

# ── convention-block-blank-lines：标准空行写法、旧写法升级、本地段 ──
for host in claude codex; do
  if [ "$host" = codex ]; then
    HB='<!-- BEGIN:spec-guard-codex-convention -->'; HE='<!-- END:spec-guard-codex-convention -->'
    HT=AGENTS.md; HOSTARG=--host=codex
  else
    HB="$BEGIN"; HE="$END"; HT=CLAUDE.md; HOSTARG=""
  fi
  mode=off; {
    project "${host}-blank-${mode}-fresh"
    host_run
    [ "$RC" -eq 0 ] && blank_lines_ok "$P/$HT" "$HB" "$HE" || fail "${host}/${mode}：新建文件里的块每条标记前后应各一个空行
$(cat "$P/$HT")"
    cp "$P/$HT" "$WORK/${host}-${mode}-canonical"
    project "${host}-blank-${mode}-existing"
    printf '# Mine\n\ntext\n' > "$P/$HT"
    host_run
    [ "$RC" -eq 0 ] && blank_lines_ok "$P/$HT" "$HB" "$HE" || fail "${host}/${mode}：追加到已有文件的块每条标记前后应各一个空行
$(cat "$P/$HT")"
    ok "${host}/${mode}：新建块每条标记前后各一个空行"

    cp "$P/$HT" "$WORK/canonical"
    host_run --replace --dry-run
    [ "$RC" -eq 0 ] && grep -F 'block content unchanged' >/dev/null <<<"$OUT" && ! grep -F 'will adjust blank lines' >/dev/null <<<"$OUT" \
      || fail "${host}/${mode}：标准写法再预览应为 block content unchanged
$OUT"
    host_run --replace
    [ "$RC" -eq 0 ] && cmp -s "$P/$HT" "$WORK/canonical" || fail "${host}/${mode}：标准写法再 --replace 应逐字节不变"
    ok "${host}/${mode}：标准写法再 --replace 不变，预览报 unchanged"

    # 旧写法：去掉每条标记内侧／两侧紧邻的空行（块外 BEGIN 前那一行保留）。
    python3 - "$P/$HT" "$HB" "$HE" <<'PY'
import sys
path, begin, end = sys.argv[1:4]
lines = open(path, encoding="utf-8").read().split("\n")
marks = {begin, end, "<!-- spec-guard: build-task-dispatch -->"}
keep = []
for i, l in enumerate(lines):
    after_mark = i > 0 and lines[i - 1].strip() in marks
    before_inner_mark = i + 1 < len(lines) and lines[i + 1].strip() in marks - {begin}
    if not l.strip() and (after_mark or before_inner_mark) and i != len(lines) - 1:
        continue
    keep.append(l)
open(path, "w", encoding="utf-8").write("\n".join(keep))
PY
    blank_lines_ok "$P/$HT" "$HB" "$HE" 2>/dev/null && fail "${host}/${mode}：测试夹具应是旧写法"
    before="$(snapshot)"
    host_run --replace --dry-run
    [ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] && grep -E 'will adjust blank lines: add [1-9][0-9]*, remove 0' >/dev/null <<<"$OUT" \
      && ! grep -F 'needs --accept-removals' >/dev/null <<<"$OUT" && ! grep -F 'block content unchanged' >/dev/null <<<"$OUT" \
      || fail "${host}/${mode}：旧写法预览应列出补空行、不需要 --accept-removals
$OUT"
    host_run --replace
    [ "$RC" -eq 0 ] && cmp -s "$P/$HT" "$WORK/canonical" || fail "${host}/${mode}：旧写法 --replace 后应与新建块逐字节相同
$(diff "$WORK/canonical" "$P/$HT")"
    ok "${host}/${mode}：旧写法升级预览如实列出空行，写入后与新建块相同"
  }

  # 本地段：旧写法紧贴着，--replace 后前后有空行、内部原样；内部已被格式化器补过空行时再替换不变。
  project "${host}-blank-local"
  host_run
  python3 - "$P/$HT" "$HE" <<'PY'
import sys
path, end = sys.argv[1:3]
t = open(path, encoding="utf-8").read()
t = t.replace("\n\n" + end, "\n<!-- BEGIN:spec-guard-local -->\n- 本地一\n<!-- END:spec-guard-local -->\n" + end, 1)
open(path, "w", encoding="utf-8").write(t)
PY
  host_run --replace
  [ "$RC" -eq 0 ] && blank_lines_ok "$P/$HT" "$HB" "$HE" && grep -Fx -- '- 本地一' "$P/$HT" >/dev/null \
    && python3 -c 'import sys; t=open(sys.argv[1],encoding="utf-8").read(); sys.exit("<!-- BEGIN:spec-guard-local -->\n\n- 本地一" in t)' "$P/$HT" \
    || fail "${host}：本地段前后应有空行、内部原样
$(cat "$P/$HT")"
  ok "${host}：本地段前后补空行，内部原样保留"
  python3 - "$P/$HT" <<'PY'
import sys
path = sys.argv[1]
t = open(path, encoding="utf-8").read()
t = t.replace("<!-- BEGIN:spec-guard-local -->\n- 本地一\n<!-- END:spec-guard-local -->",
              "<!-- BEGIN:spec-guard-local -->\n\n- 本地一\n\n<!-- END:spec-guard-local -->", 1)
open(path, "w", encoding="utf-8").write(t)
PY
  cp "$P/$HT" "$WORK/formatted"
  host_run --replace --dry-run
  grep -F 'block content unchanged' >/dev/null <<<"$OUT" || fail "${host}：格式化过的本地段预览应为 unchanged
$OUT"
  host_run --replace
  [ "$RC" -eq 0 ] && cmp -s "$P/$HT" "$WORK/formatted" || fail "${host}：格式化过的本地段再 --replace 应逐字节不变
$(diff "$WORK/formatted" "$P/$HT")"
  ok "${host}：格式化器整理过的本地段再 --replace 不变"
done

echo "setup/teardown regression passed (${PASS} cases)"
