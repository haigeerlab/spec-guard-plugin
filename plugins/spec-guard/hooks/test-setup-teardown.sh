#!/usr/bin/env bash
# setup-convention / teardown-convention 的回归：它们是插件里唯二写用户文件的操作，
# teardown 还是唯一的破坏性操作。每个用例都核对退出码、文件字节与目录状态。
set -euo pipefail

HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0
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
run setup-convention.sh local --replace
[ "$RC" -eq 0 ] || fail "--replace 失败
$OUT"
[ "$(tail -1 "$P/CLAUDE.md")" = "# Tail" ] && ! grep -F '被手改的能力图' "$P/CLAUDE.md" >/dev/null && [ "$(markers "$P/CLAUDE.md")" -eq 2 ] || fail "--replace 应恢复模板并保留标记外内容"
ok "--replace 恢复模板正文，标记外内容不动"

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

# ── build-task-dispatch 规则段模板 ──────────────────────
DISPATCH_MARKER='<!-- spec-guard: build-task-dispatch -->'
TEMPLATES="$HOOKDIR/../templates"
for host in claude codex; do
  tpl="$TEMPLATES/${host}-dispatch-rule.md"
  [ -f "$tpl" ] || fail "缺少规则段模板 ${host}-dispatch-rule.md"
  [ "$(head -n 1 "$tpl")" = "$DISPATCH_MARKER" ] || fail "${host} 规则段首行必须是开关标记"
  [ "$(grep -Fxc "$DISPATCH_MARKER" "$tpl")" -eq 1 ] || fail "${host} 规则段的开关标记必须恰好出现一次"
  for needle in 'Checkpoint' 'RED → GREEN' '<!-- tier-guard: tier=' 'failures=N' '不提交' '不勾选' '交回'; do
    grep -F -- "$needle" "$tpl" >/dev/null || fail "${host} 规则段缺少「${needle}」"
  done
  # 2026-10-05 验收：不等上一个 task 提交就派下一个；没装 tier-guard 时档位无统一依据。
  grep -F '上一个 task 提交、勾选完再派下一个' "$tpl" >/dev/null || fail "${host} 规则段应要求上一个 task 提交、勾选完再派下一个"
  # 交接内容与不派条件：todo 常只有一行，验收标准等在 plan.md 的任务块里；派活本身不省钱。
  for needle in '完整任务块' 'plan.md' 'Architecture Decisions' '由主代理自己做、不派' '缺验收标准或验证步骤' 'L3' '不比你自己的模型便宜'; do
    grep -F -- "$needle" "$tpl" >/dev/null || fail "${host} 规则段缺少「${needle}」"
  done
  ! grep -F '写入该 task 原文' "$tpl" >/dev/null || fail "${host} 规则段不应只交 task 原文（todo 常只有一行）"
  # 第二轮复验：提交被拦后主代理仍先派了下一个，事后才停掉。
  grep -F '提交受阻时先解决提交或停下问人，不派下一个' "$tpl" >/dev/null || fail "${host} 规则段应写明提交受阻时不派下一个"
  for needle in 'L1 机械、只读' 'L2 单模块内、验收明确的实现' 'L3 跨模块、有歧义、高风险或不可逆' '有 `tier-routing` 时以它为准'; do
    grep -F -- "$needle" "$tpl" >/dev/null || fail "${host} 规则段缺少档位定义「${needle}」"
  done
  ok "${host} 规则段：首行标记，覆盖何时派、子代理四步不提交、tier-guard 标记与停止条件交回"
done
grep -F 'Agent 工具' "$TEMPLATES/claude-dispatch-rule.md" >/dev/null || fail "claude 规则段应指明 Agent 工具"
grep -F 'spawn_agent' "$TEMPLATES/codex-dispatch-rule.md" >/dev/null || fail "codex 规则段应指明 spawn_agent"
grep -F '只作建议' "$TEMPLATES/codex-dispatch-rule.md" >/dev/null || fail "codex 规则段应写明 tier-guard 在 Codex 上只作建议"
ok "规则段按宿主写明派活工具，Codex 段写明只作建议"

# ── setup-convention --dispatch / --no-dispatch（开关状态存在块里）──
# $1=文件 $2=BEGIN $3=END：输出两条标记之间的正文（不含标记行）
block_body() { awk -v b="$2" -v e="$3" '{s=$0; gsub(/^[ \t\r]+|[ \t\r]+$/, "", s)} s==e{inb=0} inb{print} s==b{inb=1}' "$1"; }
host_run() { run setup-convention.sh local ${HOSTARG:+"$HOSTARG"} "$@"; }
# $1=期望内容文件：块正文与它逐字节相同（不经 $(...)，末尾换行也算数）
block_is() { block_body "$P/$HT" "$HB" "$HE" > "$WORK/actual-body"; cmp -s "$WORK/actual-body" "$1"; }
for host in claude codex; do
  if [ "$host" = codex ]; then
    HB='<!-- BEGIN:spec-guard-codex-convention -->'; HE='<!-- END:spec-guard-codex-convention -->'
    HT=AGENTS.md; HOSTARG=--host=codex
  else
    HB="$BEGIN"; HE="$END"; HT=CLAUDE.md; HOSTARG=""
  fi
  BASE="$TEMPLATES/${host}-block-local.md"; RULE="$TEMPLATES/${host}-dispatch-rule.md"
  base_body="$WORK/${host}-base-body"; on_body="$WORK/${host}-on-body"
  cat "$BASE" > "$base_body"; cat "$BASE" "$RULE" > "$on_body"

  project "${host}-dispatch-default"
  host_run
  [ "$RC" -eq 0 ] && block_is "$base_body" || fail "${host}：默认 setup 的块应与基础模板逐字相同
$OUT"
  ok "${host}：默认 setup 不含规则段，块与基础模板逐字相同"

  project "${host}-dispatch-on"
  host_run --dispatch
  [ "$RC" -eq 0 ] && block_is "$on_body" || fail "${host}：--dispatch 应在基础模板之后接规则段
$OUT"
  ok "${host}：--dispatch 新建块＝基础模板＋规则段"

  host_run --replace
  [ "$RC" -eq 0 ] && block_is "$on_body" || fail "${host}：开启的块 --replace 后应保持开启
$OUT"
  ok "${host}：开启的块 --replace 保持开启"

  before="$(snapshot)"
  host_run --dispatch --no-dispatch
  [ "$RC" -eq 2 ] && [ "$(snapshot)" = "$before" ] || fail "${host}：--dispatch 与 --no-dispatch 同时给出应退出 2 且不改文件
$OUT"
  ok "${host}：--dispatch 与 --no-dispatch 互斥，退出 2，不改文件"

  before="$(snapshot)"
  host_run --no-dispatch
  [ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] && grep -F -- 'only take effect together with --replace' >/dev/null <<<"$OUT" || fail "${host}：已有块且无 --replace 时开关不生效，应提示配合 --replace
$OUT"
  ok "${host}：已有块无 --replace 时开关不生效并提示"

  before="$(snapshot)"
  host_run --replace --dry-run
  [ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] && grep -Fx '  • build-task-dispatch rule: on (kept from existing block)' >/dev/null <<<"$OUT" || fail "${host}：预览应写明沿用已有块的开启状态
$OUT"
  host_run --replace --no-dispatch --dry-run
  grep -Fx '  • build-task-dispatch rule: off (--no-dispatch)' >/dev/null <<<"$OUT" || fail "${host}：预览应写明 --no-dispatch
$OUT"
  ok "${host}：预览写明规则段状态与来源，且不改文件"

  host_run --replace --no-dispatch
  [ "$RC" -eq 0 ] && block_is "$base_body" || fail "${host}：--replace --no-dispatch 后块应与基础模板逐字相同
$OUT"
  ok "${host}：--replace --no-dispatch 关闭，块回到基础模板"

  host_run --replace --dry-run
  grep -Fx '  • build-task-dispatch rule: off' >/dev/null <<<"$OUT" || fail "${host}：关闭的块预览应为 off
$OUT"
  host_run --replace --dispatch --dry-run
  grep -Fx '  • build-task-dispatch rule: on (--dispatch)' >/dev/null <<<"$OUT" || fail "${host}：预览应写明 --dispatch
$OUT"
  host_run --replace --dispatch
  [ "$RC" -eq 0 ] && block_is "$on_body" || fail "${host}：关闭的块 --replace --dispatch 应开启
$OUT"
  ok "${host}：关闭的块 --replace --dispatch 开启"

  project "${host}-dispatch-fresh-dry"
  before="$(snapshot)"
  host_run --dispatch --dry-run
  [ "$RC" -eq 0 ] && [ "$(snapshot)" = "$before" ] && grep -Fx '  • build-task-dispatch rule: on (--dispatch)' >/dev/null <<<"$OUT" || fail "${host}：新项目 --dispatch --dry-run 应只预览开启状态
$OUT"
  ok "${host}：新项目 --dispatch --dry-run 只预览，不写文件"

  # 标记行带缩进、文件是 CRLF 时，仍认作开启。
  project "${host}-dispatch-crlf"
  host_run --dispatch
  python3 - "$P/$HT" "$DISPATCH_MARKER" <<'PY'
import sys
from pathlib import Path
p, mark = Path(sys.argv[1]), sys.argv[2]
t = p.read_text(encoding="utf-8").replace(mark, "  " + mark + " ")
p.write_bytes(t.replace("\n", "\r\n").encode("utf-8"))
PY
  host_run --replace --dry-run
  grep -Fx '  • build-task-dispatch rule: on (kept from existing block)' >/dev/null <<<"$OUT" || fail "${host}：CRLF 与缩进的标记行应仍认作开启
$OUT"
  ok "${host}：CRLF 文件与带缩进的标记行仍认作开启"

  # 正文里提到标记、或标记不在块内，都不算开启。
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
  host_run --replace
  [ "$RC" -eq 0 ] && block_is "$base_body" || fail "${host}：块内行中提及或块外的标记不应算开启
$OUT"
  ok "${host}：块内正文提及或块外的标记不算开启"
done

echo "setup/teardown regression passed (${PASS} cases)"
