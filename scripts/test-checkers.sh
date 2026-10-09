#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# scripts/check-*.py 的回归测试。
#
# 为什么需要它：本仓一轮之内出过**四次**「新加的防线自己有毛病」——
#   1. check-command-names 漏了双引号前缀，抓不到 NEXT="/plan …"，
#      也就抓不到它本该抓的那个 bug
#   2. check-readme-sync 第一版没跑过反向用例
#   3. 发版流程的 sha 核对拿 HEAD 比，文档提交就误报
#   4. evals 的判分把 skill 名写死成裸名，把一次成功判成失败
#
# 四次同一个形状：**判据写完没有当场用真实数据跑一遍。**
# 「防线本身也要被测试」这条一直写在 CLAUDE.md 里，但它是句口号，
# 不是套件 —— 所以每次都靠人自觉，而四次里零次做到。
#
# 每个校验器两个用例：喂已知坏输入必须**非零退出**，喂好输入必须**零退出**。
# 反向用例是重点：一个永远返回 0 的校验器和没有校验器没区别。
# ─────────────────────────────────────────────────────────────
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

want() {  # $1=期望(fail|pass) $2=用例名 $3...=命令
  local exp="$1" name="$2"; shift 2
  "$@" >/dev/null 2>&1; local rc=$?
  if { [ "$exp" = fail ] && [ "$rc" -ne 0 ]; } || { [ "$exp" = pass ] && [ "$rc" -eq 0 ]; }; then
    printf '  ✅ %s\n' "$name"; PASS=$((PASS+1))
  else
    printf '  ❌ %s（期望 %s，实际退出码 %s）\n' "$name" "$exp" "$rc"; FAIL=$((FAIL+1))
  fi
}

echo "═══ check-*.py 回归 ═══"

# ── check-bash32.py ──
# 踩过的真 bug：$VAR 紧跟全角字符时，bash 3.2 把首字节吃进变量名
# 坏样本在**运行时拼装**，不让这个模式出现在本文件源码里 ——
# 否则 validate.sh 里的 check-bash32 会抓自己的测试脚本。
# 用豁免（跳过 test-*.sh）也能过，但那会削掉真实覆盖：测试脚本本身
# 也得能在 bash 3.2 上跑。
D='$'
printf 'X=1\necho "（#%sISSUE）"\n'    "$D" > "$TMP/bad32.sh"
printf 'X=1\necho "（#%s{ISSUE}）"\n' "$D" > "$TMP/good32.sh"
want fail "bash32: \$VAR 紧跟全角括号 → 报错" python3 "$ROOT/scripts/check-bash32.py" "$TMP/bad32.sh"
want pass "bash32: \${VAR} 写法 → 放行"       python3 "$ROOT/scripts/check-bash32.py" "$TMP/good32.sh"

# ── check-grep-pipe.py ──
# 踩过的真 bug（三次）：`cmd | grep -q` 里 grep 命中即关管道，上游吃 SIGPIPE(141)，
# pipefail 传出 → 判断永远为假。坏样本同样**运行时拼装**，理由和上面那条一样：
# 写成字面量的话 validate.sh 里的 check-grep-pipe 会抓自己的测试脚本。
Q='q'
printf 'f(){ head -1 x | grep -%s pat; }\n' "$Q" > "$TMP/badgp.sh"
printf 'f(){ grep -%s pat <<<"$(head -1 x)"; }\n' "$Q" > "$TMP/goodgp.sh"
printf '# 注释里写 cmd | grep -%s 是允许的\necho ok\n' "$Q" > "$TMP/cmtgp.sh"
want fail "grep-pipe: 管道 + grep -q → 报错"   python3 "$ROOT/scripts/check-grep-pipe.py" "$TMP/badgp.sh"
want pass "grep-pipe: herestring 写法 → 放行"  python3 "$ROOT/scripts/check-grep-pipe.py" "$TMP/goodgp.sh"
want pass "grep-pipe: 注释里提到不算 → 放行"   python3 "$ROOT/scripts/check-grep-pipe.py" "$TMP/cmtgp.sh"

# ── check-gh-json-fields.py ──
# 踩过的真 bug（两次同一形状）：`gh issue list --parent`，以及 SKILL.md 里
# 一个并不存在的 issue view JSON 字段 —— 都是**每次跑都硬失败**的命令，
# 都在文档里躺了很久。这个校验器的判据不是冻结清单，是问 gh 本人。
# （这里刻意不写出那个字段名：校验器不跳过注释，写了会抓到本文件自己。）
# 坏样本**运行时拼装**，不让那个字段名以完整形态出现在本文件源码里 ——
# 否则 validate.sh 里的 check-gh-json-fields 会抓自己的测试脚本（同 bash32 那条）。
BADF='depend''encies'
printf 'gh issue view 5 --json title,%s\n' "$BADF" > "$TMP/badjson.md"
printf 'gh issue view 5 --json title,blockedBy\n'   > "$TMP/goodjson.md"
# 这里不能依赖 runner 预装 gh 的网络/认证状态。某些 CI 环境有 gh，但拿不到
# 字段表，校验器按设计会降级跳过，反向用例便会误判为通过。用最小 fake 固定
# `Available fields:` 输出，专门验证校验器的字段判定本身。
mkdir -p "$TMP/ghjson-bin"
printf '%s\n' '#!/bin/sh' \
  'printf "%s\\n" "Available fields:" "title" "blockedBy" >&2' \
  'exit 1' > "$TMP/ghjson-bin/gh"
chmod +x "$TMP/ghjson-bin/gh"
GHJSON_PATH="$TMP/ghjson-bin:$PATH"
want fail "gh-json: 不存在的字段 → 报错" \
  env PATH="$GHJSON_PATH" python3 "$ROOT/scripts/check-gh-json-fields.py" "$TMP/badjson.md"
want pass "gh-json: 真实字段 → 放行" \
  env PATH="$GHJSON_PATH" python3 "$ROOT/scripts/check-gh-json-fields.py" "$TMP/goodjson.md"
# Python 参数列表写法（插件里现存唯一的 --json 调用就是这种）同样要查，且可以跨行。
printf '%s\n' 'run(["gh", "issue", "list", "--repo", target,' "    \"--json\", \"title,$BADF\"])" > "$TMP/badjson.py"
printf '%s\n' 'run(["gh", "issue", "list", "--repo", target,' '    "--json", "title,blockedBy"])' > "$TMP/goodjson.py"
want fail "gh-json: Python 参数列表里的不存在字段 → 报错" \
  env PATH="$GHJSON_PATH" python3 "$ROOT/scripts/check-gh-json-fields.py" "$TMP/badjson.py"
want pass "gh-json: Python 参数列表里的真实字段 → 放行" \
  env PATH="$GHJSON_PATH" python3 "$ROOT/scripts/check-gh-json-fields.py" "$TMP/goodjson.py"
# gh 不可用时必须干净跳过退 0，不能假阻塞。
# PATH 清空后 python3 也找不着了，所以用绝对路径调它 —— 这里要屏蔽的只有 gh。
mkdir -p "$TMP/nogh"
PY3="$(command -v python3)"
want pass "gh-json: gh 不可用时干净跳过" \
  env PATH="$TMP/nogh" "$PY3" "$ROOT/scripts/check-gh-json-fields.py" "$TMP/badjson.md"

# ── check-manifests.py ──
mkm() {  # $1=目录 $2=plugin.json 里的 name
  rm -rf "$1"; mkdir -p "$1/.claude-plugin" "$1/plugins/demo/.claude-plugin"
  printf '{"name":"m","owner":{"name":"t"},"plugins":[{"name":"demo","source":"./plugins/demo"}]}\n' \
    > "$1/.claude-plugin/marketplace.json"
  printf '{"name":"%s","version":"1.0.0","description":"d"}\n' "$2" > "$1/plugins/demo/.claude-plugin/plugin.json"
}
mkm "$TMP/mfbad" wrong-name
mkm "$TMP/mfgood" demo
want fail "manifests: marketplace 与 plugin.json 名称不一致 → 报错" \
  bash -c "cd '$TMP/mfbad' && python3 '$ROOT/scripts/check-manifests.py'"
want pass "manifests: 名称一致 → 放行" \
  bash -c "cd '$TMP/mfgood' && python3 '$ROOT/scripts/check-manifests.py'"

# Codex 清单在过渡期仍是可选的；一旦存在，就必须是 Claude 清单的镜像。
mkspecguard() {
  rm -rf "$1"; mkdir -p "$1/.claude-plugin" "$1/plugins/spec-guard/.claude-plugin"
  printf '{"name":"m","owner":{"name":"t"},"plugins":[{"name":"spec-guard","source":"./plugins/spec-guard"}]}\n' \
    > "$1/.claude-plugin/marketplace.json"
  printf '{"name":"spec-guard","version":"1.0.0","description":"d"}\n' \
    > "$1/plugins/spec-guard/.claude-plugin/plugin.json"
}
mkcodex() {  # $1=目录 $2=name $3=version $4=skills $5=hooks
  mkdir -p "$1/plugins/spec-guard/.codex-plugin"
  printf '{"name":"%s","version":"%s","skills":"%s","hooks":"%s"}\n' "$2" "$3" "$4" "$5" \
    > "$1/plugins/spec-guard/.codex-plugin/plugin.json"
}
mkspecguard "$TMP/codex-name-bad"
mkcodex "$TMP/codex-name-bad" wrong-name 1.0.0 ./skills/ ./hooks/hooks.json
want fail "codex manifest: 名称漂移 → 报错" \
  bash -c "cd '$TMP/codex-name-bad' && python3 '$ROOT/scripts/check-manifests.py'"
mkspecguard "$TMP/codex-version-bad"
mkcodex "$TMP/codex-version-bad" spec-guard 0.0.0 ./skills/ ./hooks/hooks.json
want fail "codex manifest: 版本漂移 → 报错" \
  bash -c "cd '$TMP/codex-version-bad' && python3 '$ROOT/scripts/check-manifests.py'"
mkspecguard "$TMP/codex-skills-bad"
mkcodex "$TMP/codex-skills-bad" spec-guard 1.0.0 skills/ ./hooks/hooks.json
want fail "codex manifest: skills 路径漂移 → 报错" \
  bash -c "cd '$TMP/codex-skills-bad' && python3 '$ROOT/scripts/check-manifests.py'"
mkspecguard "$TMP/codex-hooks-bad"
mkcodex "$TMP/codex-hooks-bad" spec-guard 1.0.0 ./skills/ hooks/hooks.json
want fail "codex manifest: hooks 路径漂移 → 报错" \
  bash -c "cd '$TMP/codex-hooks-bad' && python3 '$ROOT/scripts/check-manifests.py'"
mkspecguard "$TMP/codex-good"
mkcodex "$TMP/codex-good" spec-guard 1.0.0 ./skills/ ./hooks/hooks.json
want pass "codex manifest: 名称和版本一致 → 放行" \
  bash -c "cd '$TMP/codex-good' && python3 '$ROOT/scripts/check-manifests.py'"


# ── check-acceptance-immutable.py ──
ACC="$TMP/acc"
mkdir -p "$ACC/spec/proposal-acceptances"
git -C "$ACC" init -q
printf '{"decision":"accept"}\n' > "$ACC/spec/proposal-acceptances/gamma-1.json"
git -C "$ACC" add -A && git -C "$ACC" -c user.email=t@e -c user.name=t commit -qm base
want pass "acceptance: 已有记录未改动 → 放行" \
  python3 "$ROOT/scripts/check-acceptance-immutable.py" "$ACC" --base HEAD
printf '{"decision":"accept"}\n' > "$ACC/spec/proposal-acceptances/delta-1.json"
want pass "acceptance: 新增记录 → 放行" \
  python3 "$ROOT/scripts/check-acceptance-immutable.py" "$ACC" --base HEAD
printf '{"decision":"reject"}\n' > "$ACC/spec/proposal-acceptances/gamma-1.json"
want fail "acceptance: 改写已有记录 → 报错" \
  python3 "$ROOT/scripts/check-acceptance-immutable.py" "$ACC" --base HEAD
rm "$ACC/spec/proposal-acceptances/gamma-1.json"
want fail "acceptance: 删除已有记录 → 报错" \
  python3 "$ROOT/scripts/check-acceptance-immutable.py" "$ACC" --base HEAD
want pass "acceptance: 没有基准分支时降级跳过" \
  python3 "$ROOT/scripts/check-acceptance-immutable.py" "$ACC" --base refs/heads/absent

# ── check-no-parallel-surface.py ──
mkdir -p "$TMP/par-good/plugins/spec-guard/commands" "$TMP/par-bad/plugins/spec-guard/commands" \
  "$TMP/par-file/plugins/spec-guard/commands"
printf 'phase\n' > "$TMP/par-good/plugins/spec-guard/commands/phase.md"
printf 'run the parallel-%s worker\n' worktree > "$TMP/par-bad/plugins/spec-guard/commands/phase.md"
: > "$TMP/par-file/plugins/spec-guard/commands/parallel-run.md"
want pass "parallel-surface: 干净的插件 → 放行" \
  python3 "$ROOT/scripts/check-no-parallel-surface.py" "$TMP/par-good"
want fail "parallel-surface: 现行文件引用已退役的并行流程 → 报错" \
  python3 "$ROOT/scripts/check-no-parallel-surface.py" "$TMP/par-bad"
want fail "parallel-surface: 残留已退役的并行命令文件 → 报错" \
  python3 "$ROOT/scripts/check-no-parallel-surface.py" "$TMP/par-file"

# ── check-command-names.py ──
mkc() {  # $1=目录 $2=模板里引用的命令名
  rm -rf "$1"; mkdir -p "$1/plugins/demo/commands" "$1/plugins/demo/templates" "$1/plugins/demo/skills"
  printf -- '---\ndescription: d\n---\n内容\n' > "$1/plugins/demo/commands/real.md"
  printf '跑一下 `/%s` 就好。\n' "$2" > "$1/plugins/demo/templates/t.md"
}
mkc "$TMP/cnbad" totally-made-up
mkc "$TMP/cngood" real
want fail "command-names: 模板引用不存在的命令 → 报错" \
  bash -c "cd '$TMP/cnbad' && python3 '$ROOT/scripts/check-command-names.py'"
want pass "command-names: 引用本插件真实命令 → 放行" \
  bash -c "cd '$TMP/cngood' && python3 '$ROOT/scripts/check-command-names.py'"
printf '跑一下 `/demo:real` 就好。\n' >> "$TMP/cngood/plugins/demo/templates/t.md"
want pass "command-names: Claude 插件命名空间命令 → 放行" \
  bash -c "cd '$TMP/cngood' && python3 '$ROOT/scripts/check-command-names.py'"
printf '转交给 `/agent-relay:collaboration`。\n' >> "$TMP/cngood/plugins/demo/templates/t.md"
want pass "command-names: 登记过的外部插件命令 → 放行" \
  bash -c "cd '$TMP/cngood' && python3 '$ROOT/scripts/check-command-names.py'"
mkc "$TMP/cnext" real
printf '转交给 `/agent-relay:not-a-command`。\n' >> "$TMP/cnext/plugins/demo/templates/t.md"
want fail "command-names: 外部插件里不存在的命令 → 报错" \
  bash -c "cd '$TMP/cnext' && python3 '$ROOT/scripts/check-command-names.py'"
printf '跑一下 `/demo:not-real` 就好。\n' >> "$TMP/cngood/plugins/demo/templates/t.md"
want fail "command-names: 命名空间里的不存在命令 → 报错" \
  bash -c "cd '$TMP/cngood' && python3 '$ROOT/scripts/check-command-names.py'"

# 它自己声明「不查 hooks/test-*.sh」—— 这条豁免也要有用例，
# 否则下次有人收紧范围时会静默把它去掉（这正是 0.7.3 修过的那次）
mkc "$TMP/cnskip" real
mkdir -p "$TMP/cnskip/plugins/demo/hooks"
printf 'CLAUDE_PLUGIN_ROOT=/x/spec-guard/9.9.9 bash h.sh\n' > "$TMP/cnskip/plugins/demo/hooks/test-fake.sh"
want pass "command-names: hooks/test-*.sh 里的假路径被豁免" \
  bash -c "cd '$TMP/cnskip' && python3 '$ROOT/scripts/check-command-names.py'"
printf 'NEXT="/totally-made-up"\n' > "$TMP/cnskip/plugins/demo/hooks/real.sh"
want fail "command-names: 非 test- 的 hook 仍然要查" \
  bash -c "cd '$TMP/cnskip' && python3 '$ROOT/scripts/check-command-names.py'"

# 上游清单不再是冻结快照，而是问本机装着的上游本人。
# 危险方向是**上游删名/改名**：快照里还有、上游已经没有 —— 检查器照样放行，
# 而文档里那条命令已经会报 Unknown。0.4.1 的 /planning 就是这么来的。
UPS=$(SPEC_GUARD_UPSTREAM_REGISTRY="" python3 -c "
import json,pathlib,sys
try:
    d=json.loads((pathlib.Path.home()/'.claude/plugins/installed_plugins.json').read_text())
    print(next(v[0]['installPath'] for k,v in d['plugins'].items() if 'agent-skills' in k and v))
except Exception: pass" 2>/dev/null)
if [ -n "${UPS}" ] && [ -d "${UPS}/.claude/commands" ]; then
  mkfake() {  # $1=目标目录 $2=要删掉的命令名（空=全留）
    rm -rf "$1"; mkdir -p "$1/.claude/commands" "$1/skills"
    for f in "${UPS}"/.claude/commands/*.md; do
      b=$(basename "$f"); [ "$b" = "$2.md" ] || : > "$1/.claude/commands/$b"
    done
    for d in "${UPS}"/skills/*/; do mkdir -p "$1/skills/$(basename "$d")"; done
    printf '{"plugins":{"agent-skills@x":[{"installPath":"%s"}]}}\n' "$1" > "$1.json"
  }
  mkfake "$TMP/upfull" ""
  mkfake "$TMP/upgone" plan
  want pass "command-names: 对照上游本人 → 放行" \
    bash -c "cd '$ROOT' && SPEC_GUARD_UPSTREAM_REGISTRY='$TMP/upfull.json' python3 '$ROOT/scripts/check-command-names.py'"
  # 用自带夹具引用 /plan，不依赖仓库文案恰好提到它。
  mkdir -p "$TMP/cmdref/plugins/demo/commands"
  printf '%s\n' '---' 'description: d' '---' '完成后运行 `/plan` 拆任务。' \
    > "$TMP/cmdref/plugins/demo/commands/demo.md"
  want pass "command-names: 夹具引用 /plan，上游齐全 → 放行" \
    bash -c "cd '$TMP/cmdref' && SPEC_GUARD_UPSTREAM_REGISTRY='$TMP/upfull.json' python3 '$ROOT/scripts/check-command-names.py'"
  want fail "command-names: 上游删了 /plan → 报快照过期" \
    bash -c "cd '$TMP/cmdref' && SPEC_GUARD_UPSTREAM_REGISTRY='$TMP/upgone.json' python3 '$ROOT/scripts/check-command-names.py'"
else
  printf '  ⏭  本机没装上游 agent-skills，跳过「对照上游本人」的一正一反（不代表通过）\n'
fi

# ── 零文件不算通过 ────────────────────────────────────────
# 「0 处违规」和「0 个文件」在退出码上长得一样（lenses A5）。
# validate.sh 里这三个都靠仓库文件列表喂文件，列表一旦为空就会全绿。
for c in check-bash32 check-grep-pipe check-gh-json-fields; do
  want fail "$c: 零个文件 → 不算通过" python3 "$ROOT/scripts/$c.py"
done

# ── check-readme-sync.py ──
# docs-reorganization：约定块从 README 移到 docs/convention-block.md；--ref 检查覆盖中英两份 README。
mkr() {  # $1=目录 $2=docs/convention-block.md 内嵌块要不要跟模板一致(same|drift)
  rm -rf "$1"; mkdir -p "$1/plugins/spec-guard/templates" "$1/docs"
  printf '## 约定\n\n- 本地模式\n' > "$1/plugins/spec-guard/templates/claude-block-local.md"
  printf '# README\n\n约定块见 docs/convention-block.md\n' > "$1/README.md"
  {
    echo "# 约定块"; echo
    echo "<!-- SYNC:claude-block-local BEGIN -->"
    echo '````markdown'
    echo "<!-- BEGIN:agent-skills-convention -->"
    printf '## 约定\n\n- 本地模式\n'
    [ "$2" = drift ] && echo "- 多出来的一行（模板里没有）"
    echo "<!-- END:agent-skills-convention -->"
    echo '````'
    echo "<!-- SYNC:claude-block-local END -->"
  } > "$1/docs/convention-block.md"
}
mkr "$TMP/rsbad" drift
mkr "$TMP/rsgood" same
want fail "readme-sync: 约定块文档与模板分叉 → 报错" python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsbad"
want pass "readme-sync: 逐字节一致 → 放行"           python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsgood"
rm -rf "$TMP/rsmissing"; mkdir -p "$TMP/rsmissing/plugins/spec-guard/templates" "$TMP/rsmissing/docs"
printf 'y\n' > "$TMP/rsmissing/plugins/spec-guard/templates/claude-block-local.md"
printf '# README\n' > "$TMP/rsmissing/README.md"
printf '# 约定块\n没有 SYNC 标记\n' > "$TMP/rsmissing/docs/convention-block.md"
want fail "readme-sync: 约定块文档里缺 SYNC 标记 → 报错" python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsmissing"
mkr "$TMP/rsnodoc" same; rm "$TMP/rsnodoc/docs/convention-block.md"
want fail "readme-sync: 没有 docs/convention-block.md → 报错" python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsnodoc"
# SYNC 区只留在 README、约定块文档里没有：说明检查器读的是新位置，不是 README
mkr "$TMP/rsreadmeonly" same
cp "$TMP/rsreadmeonly/docs/convention-block.md" "$TMP/rsreadmeonly/README.md"
printf '# 约定块\n' > "$TMP/rsreadmeonly/docs/convention-block.md"
want fail "readme-sync: SYNC 区只在 README 里 → 报错" python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsreadmeonly"
mkrref() {  # $1=目录 $2=README 里写的 --ref 版本 $3=README.en.md 里写的版本（可省略，省略则不建英文版）；清单固定为 1.2.3
  mkr "$1" same
  mkdir -p "$1/plugins/spec-guard/.claude-plugin"
  printf '{"name":"spec-guard","version":"1.2.3"}\n' > "$1/plugins/spec-guard/.claude-plugin/plugin.json"
  printf 'codex plugin marketplace add o/r --ref v%s\n' "$2" >> "$1/README.md"
  if [ -n "${3:-}" ]; then printf 'codex plugin marketplace add o/r --ref v%s\n' "$3" > "$1/README.en.md"; fi
}
mkrref "$TMP/rsrefbad" 1.2.2
mkrref "$TMP/rsrefgood" 1.2.3
want fail "readme-sync: 安装命令的 --ref 落后于清单版本 → 报错" python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsrefbad"
want pass "readme-sync: 安装命令的 --ref 等于清单版本 → 放行" python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsrefgood"
mkrref "$TMP/rsrefenbad" 1.2.3 1.2.2
mkrref "$TMP/rsrefengood" 1.2.3 1.2.3
want fail "readme-sync: 英文 README 的 --ref 落后于清单版本 → 报错" python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsrefenbad"
want pass "readme-sync: 中英 README 的 --ref 都等于清单版本 → 放行" python3 "$ROOT/scripts/check-readme-sync.py" "$TMP/rsrefengood"

# ── check-command-parity.py ──
# Task 8 / R4 后半：commands/*.md 引用的每个 hooks/<脚本> 都要在至少一个
# skill 里有路由，否则 Codex（只读 skills/*/SKILL.md）永远够不到它。
mkparity() {  # $1=目录
  rm -rf "$1"
  mkdir -p "$1/plugins/spec-guard/commands" "$1/plugins/spec-guard/skills/ops"
  printf -- '---\ndescription: d\n---\n运行 `hooks/covered.py` 完成检查。\n' \
    > "$1/plugins/spec-guard/commands/covered.md"
  printf -- '---\nname: ops\n---\n用 `"$ROOT/hooks/covered.py"` 处理。\n' \
    > "$1/plugins/spec-guard/skills/ops/SKILL.md"
}
mkparity "$TMP/paritygood"
want pass "command-parity: 命令引用的 hook 在 skill 里有路由 → 放行" \
  python3 "$ROOT/scripts/check-command-parity.py" "$TMP/paritygood"

mkparity "$TMP/paritybad"
printf -- '---\ndescription: d\n---\n运行 `hooks/uncovered.py` 完成检查。\n' \
  > "$TMP/paritybad/plugins/spec-guard/commands/uncovered.md"
want fail "command-parity: 新命令引用的 hook 没有任何 skill 提供 → 报错" \
  python3 "$ROOT/scripts/check-command-parity.py" "$TMP/paritybad"

# 参数级：命令传给脚本的 --flag（续行拼接后）必须出现在某个也引用该脚本的 skill 里。
mkparity "$TMP/parityflaggood"
printf -- '---\ndescription: d\n---\n```bash\npython3 "$ROOT/hooks/covered.py" \\\n  --prove --format json\n```\n' \
  > "$TMP/parityflaggood/plugins/spec-guard/commands/covered.md"
printf -- '---\nname: ops\n---\n```bash\npython3 "$ROOT/hooks/covered.py" --format json\n# 合并后加 --prove 做证明\n```\n' \
  > "$TMP/parityflaggood/plugins/spec-guard/skills/ops/SKILL.md"
want pass "command-parity: 命令的参数在引用同一脚本的 skill 里都出现 → 放行" \
  python3 "$ROOT/scripts/check-command-parity.py" "$TMP/parityflaggood"

mkparity "$TMP/parityflagbad"
printf -- '---\ndescription: d\n---\n```bash\npython3 "$ROOT/hooks/covered.py" \\\n  --prove --format json\n```\n' \
  > "$TMP/parityflagbad/plugins/spec-guard/commands/covered.md"
printf -- '---\nname: ops\n---\n```bash\npython3 "$ROOT/hooks/covered.py" --format json\n```\n' \
  > "$TMP/parityflagbad/plugins/spec-guard/skills/ops/SKILL.md"
# 另一个 skill 写了 --prove 但不引用该脚本：不算覆盖。
mkdir -p "$TMP/parityflagbad/plugins/spec-guard/skills/other"
printf -- '---\nname: other\n---\n别的脚本 `hooks/elsewhere.py` 才用 --prove。\n' \
  > "$TMP/parityflagbad/plugins/spec-guard/skills/other/SKILL.md"
want fail "command-parity: 续行上的 --prove 在引用该脚本的 skill 里缺失 → 报错" \
  python3 "$ROOT/scripts/check-command-parity.py" "$TMP/parityflagbad"

rm -rf "$TMP/parityempty"; mkdir -p "$TMP/parityempty/plugins/spec-guard/skills/ops"
printf -- '---\nname: ops\n---\n什么都没有。\n' > "$TMP/parityempty/plugins/spec-guard/skills/ops/SKILL.md"
want fail "command-parity: 零个命令文件 → 不算通过" \
  python3 "$ROOT/scripts/check-command-parity.py" "$TMP/parityempty"

# ── check-acceptance-wired.py ──
# 2026-10-05 审计 P1-1：验收测试需要固定外部运行时，不该进 CI —— 但也不能没有任何
# 地方告诉维护者跑它。最关键的是第二条反例：只被 docs/reports/ 提到**不算**运行指引，
# 否则这条判据会被历史证据喂饱而永远绿（docs/lenses.md A3「太宽」）。
mkacc() {  # $1=目录 $2=验收测试文件名
  rm -rf "$1"
  mkdir -p "$1/plugins/spec-guard/hooks" "$1/docs" "$1/scripts"
  printf '# acceptance\n' > "$1/plugins/spec-guard/hooks/$2"
  printf '# 维护者工作流\n' > "$1/docs/maintainer-workflow.md"
  printf '#!/usr/bin/env bash\necho validate\n' > "$1/scripts/validate.sh"
}

mkacc "$TMP/accgood" test_demo_acceptance.py
printf '跑 `plugins/spec-guard/hooks/test_demo_acceptance.py`，需 SPEC_GUARD_EPIQ_RUNTIME。\n' \
  >> "$TMP/accgood/docs/maintainer-workflow.md"
want pass "acceptance-wired: 维护者文档里有运行指引 → 放行" \
  python3 "$ROOT/scripts/check-acceptance-wired.py" "$TMP/accgood"

mkacc "$TMP/accrunner" test_demo_acceptance.py
printf 'python3 -B plugins/spec-guard/hooks/test_demo_acceptance.py\n' \
  >> "$TMP/accrunner/scripts/validate.sh"
want pass "acceptance-wired: 接进运行器 → 放行" \
  python3 "$ROOT/scripts/check-acceptance-wired.py" "$TMP/accrunner"

mkacc "$TMP/accreport" test_demo_acceptance.py
mkdir -p "$TMP/accreport/docs/reports"
printf '本轮已实测 `test_demo_acceptance.py`，退出 0。\n' \
  > "$TMP/accreport/docs/reports/2026-10-03-audit.md"
want fail "acceptance-wired: 只被 docs/reports/ 当历史证据提到 → 报错" \
  python3 "$ROOT/scripts/check-acceptance-wired.py" "$TMP/accreport"

mkacc "$TMP/accorphan" test_demo_acceptance.py
want fail "acceptance-wired: 全仓库零引用 → 报错" \
  python3 "$ROOT/scripts/check-acceptance-wired.py" "$TMP/accorphan"

rm -rf "$TMP/accnone"; mkdir -p "$TMP/accnone/plugins/spec-guard/hooks" "$TMP/accnone/docs"
printf '# 维护者工作流\n' > "$TMP/accnone/docs/maintainer-workflow.md"
printf '# 普通测试\n' > "$TMP/accnone/plugins/spec-guard/hooks/test_demo.py"
want fail "acceptance-wired: 零个验收测试文件 → 不算通过" \
  python3 "$ROOT/scripts/check-acceptance-wired.py" "$TMP/accnone"

rm -rf "$TMP/accnosrc"; mkdir -p "$TMP/accnosrc/plugins/spec-guard/hooks"
printf '# acceptance\n' > "$TMP/accnosrc/plugins/spec-guard/hooks/test_demo_acceptance.py"
want fail "acceptance-wired: 读不到任何运行器或维护者文档 → 不算通过" \
  python3 "$ROOT/scripts/check-acceptance-wired.py" "$TMP/accnosrc"

# ── check-decision-supersession.py ──
# 2026-10-05：native-only 决策取代了 xats-sunset 与 a10 两份门槛，但两份旧文件的状态行
# 仍写着「XATS 仍是默认传输」「其余条款继续有效」，也都不指回取代者 —— 搜 XATS 的人第一眼
# 读到的是一个 v0.40.0 就不成立的现在时事实。最关键的是第三个反例：**指回去了但状态行
# 没承认**，那正是这次真实缺陷的另一半；只查链接的版本会把它判过。
mkdec() {  # $1=目录；拼出一对最小决策文件，$2 决定旧文件的状态行怎么写
  rm -rf "$1"
  mkdir -p "$1/docs/decisions"
  printf '# 新决策\n\n状态：已接受。本决策取代\n[`old.md`](old.md)。\n' \
    > "$1/docs/decisions/new.md"
  printf '# 旧决策\n\n%s\n' "$2" > "$1/docs/decisions/old.md"
}

mkdec "$TMP/decgood" '状态：已批准，已被取代。见 [`new.md`](new.md)。本文件保留原方案作为记录。'
want pass "decision-supersession: 旧决策状态行承认被取代并指回取代者 → 放行" \
  python3 "$ROOT/scripts/check-decision-supersession.py" "$TMP/decgood"

mkdec "$TMP/decnolink" '状态：已批准，已被取代。本文件保留原方案作为记录。'
want fail "decision-supersession: 旧决策不指回取代者 → 报错" \
  python3 "$ROOT/scripts/check-decision-supersession.py" "$TMP/decnolink"

mkdec "$TMP/decstale" '状态：已批准。尚未触发，仍然生效。另见 [`new.md`](new.md)。'
want fail "decision-supersession: 指回去了但状态行仍读作生效中 → 报错" \
  python3 "$ROOT/scripts/check-decision-supersession.py" "$TMP/decstale"

mkdec "$TMP/decnostatus" '本文件开头没有那一段，只有 [`new.md`](new.md) 的链接。'
want fail "decision-supersession: 被取代的决策没有状态行 → 报错" \
  python3 "$ROOT/scripts/check-decision-supersession.py" "$TMP/decnostatus"

rm -rf "$TMP/deconeway"; mkdir -p "$TMP/deconeway/docs/decisions"
printf '# 新决策\n\n状态：已接受。与旧方案无关。\n' > "$TMP/deconeway/docs/decisions/new.md"
printf '# 旧决策\n\n状态：已被取代。见 [`new.md`](new.md)。\n' \
  > "$TMP/deconeway/docs/decisions/old.md"
want fail "decision-supersession: 取代者不提被取代者 → 报错" \
  python3 "$ROOT/scripts/check-decision-supersession.py" "$TMP/deconeway"

rm -rf "$TMP/decnone"; mkdir -p "$TMP/decnone/docs/decisions"
want fail "decision-supersession: 零个决策文件 → 不算通过" \
  python3 "$ROOT/scripts/check-decision-supersession.py" "$TMP/decnone"

rm -rf "$TMP/decquiet"; mkdir -p "$TMP/decquiet/docs/decisions"
printf '# 决策\n\n状态：已接受。没有任何取代关系。\n' > "$TMP/decquiet/docs/decisions/only.md"
want fail "decision-supersession: 零条取代声明 → 不算通过（声明丢了，不是没问题）" \
  python3 "$ROOT/scripts/check-decision-supersession.py" "$TMP/decquiet"

# ── check-collaboration-boundary.py ──
# 协作已迁到 agent-relay：迁走的路径不得再出现，范围内（含 README 等用户文档）不得引用协作内部实现。
# 坏样本**运行时拼装**，理由同 bash32：本文件在检查范围内，写成字面量会被检查抓到自己。
CB="$TMP/collab-boundary"
cb_fixture() {  # 每个用例一棵干净的夹具树：一份迁走清单（其中路径不存在）、一个技能文件、一份 README
  rm -rf "$CB"; mkdir -p "$CB/scripts" "$CB/plugins/spec-guard/skills/ticket"
  printf '# removed\nplugins/spec-guard/hooks/moved_impl.py\n' > "$CB/scripts/collaboration-owned.txt"
  printf '通过 agent-relay 的协作信箱发 mailbox 消息；legacy_bridge_marker 不是工具名。\n' \
    > "$CB/plugins/spec-guard/skills/ticket/SKILL.md"
  printf '# 项目\n协作已移到 agent-relay，安装后运行 /agent-relay:collaboration。\n' > "$CB/README.md"
}
cb_plant() {  # $1=用例名 $2=违规行
  cb_fixture; printf '%s\n' "$2" >> "$CB/plugins/spec-guard/skills/ticket/SKILL.md"
  want fail "collab-boundary: $1 → 报错" python3 "$ROOT/scripts/check-collaboration-boundary.py" "$CB"
}
cb_fixture
want pass "collab-boundary: 普通词、agent-relay 与转交命令 → 放行" python3 "$ROOT/scripts/check-collaboration-boundary.py" "$CB"
cb_plant "模块名" "python3 -B hooks/test_session""_routing.py"
cb_plant "skill 路径" "见 skills/session""-delegation/SKILL.md"
cb_plant "裸 skill 名" "使用 \`col""lab\` 发送"
cb_plant "带 spec-guard 前缀的 skill 名" "使用 spec-guard:col""lab"
cb_fixture; printf '使用 agent-relay:col''lab 与 agent-relay:session-routing\n' >> "$CB/plugins/spec-guard/skills/ticket/SKILL.md"
want pass "collab-boundary: agent-relay 的 skill 名 → 放行" python3 "$ROOT/scripts/check-collaboration-boundary.py" "$CB"
cb_plant "信箱工具名" "调用 mcp__x__bridge""_send"
cb_plant "MCP 服务名" "[mcp_servers.spec_guard_native""_collaboration]"
cb_plant "状态路径" "rm ~/.spec-guard/native""-collaboration"
cb_fixture; printf '见 `session''-routing` skill\n' >> "$CB/README.md"
want fail "collab-boundary: README 里引用协作 skill → 报错" python3 "$ROOT/scripts/check-collaboration-boundary.py" "$CB"
cb_fixture; mkdir -p "$CB/plugins/spec-guard/hooks"; printf 'x = 1\n' > "$CB/plugins/spec-guard/hooks/moved_impl.py"
want fail "collab-boundary: 迁走的路径重新出现 → 报错" python3 "$ROOT/scripts/check-collaboration-boundary.py" "$CB"
cb_fixture; printf '# only comments\n' > "$CB/scripts/collaboration-owned.txt"
want fail "collab-boundary: 空清单 → 不算通过" python3 "$ROOT/scripts/check-collaboration-boundary.py" "$CB"

# ── test-retire-legacy-tracker-bridge.sh（广度扫描，R6）──
# 扩大后的扫描要能对着一棵干净夹具树全绿，对反例喂 gh issue create 和
# 残留在 hook 脚本里的 /sync-map 各报一次，而带理由的允许清单不受影响。
mkretire() {  # $1=目录：拼出让原有断言也能全绿的最小干净树
  rm -rf "$1"
  mkdir -p "$1/plugins/spec-guard/commands" "$1/plugins/spec-guard/skills" \
    "$1/plugins/spec-guard/templates" "$1/plugins/spec-guard/hooks" \
    "$1/plugins/spec-guard/references" "$1/docs"
  printf 'phase\n' > "$1/plugins/spec-guard/commands/phase.md"
  : > "$1/plugins/spec-guard/hooks/hooks.json"
  for f in proposal_contract proposal_publication proposal_tracker_read \
           proposal_review proposal_promotion_proof; do
    printf '# clean\n' > "$1/plugins/spec-guard/hooks/$f.py"
  done
  printf '# README\n' > "$1/README.md"
  printf '# AGENTS\n' > "$1/AGENTS.md"
  printf '# design\n' > "$1/docs/design.md"
  printf '# maintainer workflow\n' > "$1/docs/maintainer-workflow.md"
  mkdir -p "$1/spec"
  printf '| Module id | Responsibility | Depends on |\n| --- | --- | --- |\n| alpha | x | — |\n' > "$1/spec/CAPABILITY-MAP.md"
}

mkretire "$TMP/retiregood"
want pass "retire-scan: 干净夹具树 → 放行" \
  bash "$ROOT/plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh" "$TMP/retiregood"

mkretire "$TMP/retirebad-ghissue"
printf 'run `gh issue create --title x`\n' > "$TMP/retirebad-ghissue/plugins/spec-guard/commands/bad.md"
want fail "retire-scan: 命令文件含 gh issue create → 报错" \
  bash "$ROOT/plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh" "$TMP/retirebad-ghissue"

mkretire "$TMP/retirebad-map"
printf '| beta | user runs /spec-guard:handoff | — |\n' >> "$TMP/retirebad-map/spec/CAPABILITY-MAP.md"
want fail "retire-scan: 能力图模块行描述已退役命令 → 报错" \
  bash "$ROOT/plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh" "$TMP/retirebad-map"

mkretire "$TMP/retirebad-syncmap"
printf '#!/usr/bin/env bash\necho "/sync-map"\n' > "$TMP/retirebad-syncmap/plugins/spec-guard/hooks/phase-guard.sh"
want fail "retire-scan: hook 脚本里出现 /sync-map → 报错" \
  bash "$ROOT/plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh" "$TMP/retirebad-syncmap"

# 允许清单按「路径 + 该行原文」匹配，不认行号——本模块已经因为 Task 1 改动
# proposal-promotion-proof.md 而把这一行从 30 挪到 33，按行号匹配的话，
# 任何未来在这行**之上**的编辑都会重演一次同样的漂移，把合法的否定说明误判成
# 新增违规（docs/lenses.md A1）。下面三个用例分别验证：原文在别的行号上依然
# 放行、同一文件里新增一条不同文本的违规依然被抓、以及正常情形不受影响。
ALLOWED_TEXT='`.agent/state.json`. It does not invoke `spec-github-bridge` or `/sync-map`.'

mkretire "$TMP/retireallow"
{
  echo "# 前面插入几行无关内容，让允许的这句话落在跟真实仓库不同的行号上"
  echo ""
  printf '%s\n' "$ALLOWED_TEXT"
} > "$TMP/retireallow/plugins/spec-guard/references/proposal-promotion-proof.md"
want pass "retire-scan: 允许清单按「路径+原文」匹配，同一句话换了行号仍放行" \
  bash "$ROOT/plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh" "$TMP/retireallow"

mkretire "$TMP/retireallow-newhit"
{
  echo "# 同一个允许清单文件"
  echo ""
  printf '%s\n' "$ALLOWED_TEXT"
  printf '%s\n' 'call spec-github-bridge directly from here'
} > "$TMP/retireallow-newhit/plugins/spec-guard/references/proposal-promotion-proof.md"
want fail "retire-scan: 同一允许清单文件里新增一条不同文本的违规仍报错" \
  bash "$ROOT/plugins/spec-guard/hooks/test-retire-legacy-tracker-bridge.sh" "$TMP/retireallow-newhit"


# ── check-digest-single-source.py ──
# 审查 F13：spec-digest.py 是唯一指纹算法；复制一份实现必须被拦下。
mkdigest() {  # $1=目录
  rm -rf "$1"; mkdir -p "$1/plugins/spec-guard/hooks" "$1/scripts"
  printf '%s\n' 'import hashlib' 'def _h(t): return hashlib.sha256(t.encode()).hexdigest()[:12]' \
    > "$1/plugins/spec-guard/hooks/spec-digest.py"
  printf '%s\n' 'import hashlib' 'def key(b): return hashlib.sha256(b).hexdigest()' \
    > "$1/plugins/spec-guard/hooks/other.py"
}
mkdigest "$TMP/digestgood"
want pass "digest-single-source: 只有 spec-digest.py 实现指纹，别处整文件哈希 → 放行" \
  python3 "$ROOT/scripts/check-digest-single-source.py" "$TMP/digestgood"
mkdigest "$TMP/digestcopy"
printf '%s\n' 'import hashlib' 'def row(r): return hashlib.sha256(r.normalized_row.encode()).hexdigest()' \
  > "$TMP/digestcopy/plugins/spec-guard/hooks/copy.py"
want fail "digest-single-source: 别处对 normalized_row 取哈希 → 报错" \
  python3 "$ROOT/scripts/check-digest-single-source.py" "$TMP/digestcopy"
mkdigest "$TMP/digesttrunc"
printf '%s\n' 'import hashlib' 'def h(t): return hashlib.sha256(t).hexdigest() [ :12]' \
  > "$TMP/digesttrunc/scripts/trunc.py"
want fail "digest-single-source: 别处做截断摘要 → 报错" \
  python3 "$ROOT/scripts/check-digest-single-source.py" "$TMP/digesttrunc"
mkdigest "$TMP/digesttest"
printf '%s\n' 'import hashlib' 'EXPECTED = hashlib.sha256(b"x").hexdigest()[:12]' \
  > "$TMP/digesttest/plugins/spec-guard/hooks/test_digest.py"
want pass "digest-single-source: 测试文件里的期望值不算实现 → 放行" \
  python3 "$ROOT/scripts/check-digest-single-source.py" "$TMP/digesttest"
rm -rf "$TMP/digestempty"; mkdir -p "$TMP/digestempty/plugins/spec-guard/hooks"
want fail "digest-single-source: 一个 Python 文件都没有 → 不算通过" \
  python3 "$ROOT/scripts/check-digest-single-source.py" "$TMP/digestempty"

# ── check-command-table.py ──
# 审查 F18：docs/workflow.md 的命令对照表要列出每个命令（前缀可省，允许 `documentation-*` 这样的通配）。
mktable() {  # $1=目录 $2=对照表正文
  rm -rf "$1"; mkdir -p "$1/plugins/spec-guard/commands" "$1/docs"
  for c in phase documentation-impact documentation-baseline; do printf 'x\n' > "$1/plugins/spec-guard/commands/$c.md"; done
  printf '# Workflow\n\n## 命令对照\n\n%s\n\n## 移除\n\n`cost-report` 在别的节里不算。\n' "$2" > "$1/docs/workflow.md"
}
mktable "$TMP/tablegood" '| 查看阶段 | `/spec-guard:phase` | x |
| 文档 | `/spec-guard:documentation-*` 两条 | x |'
want pass "command-table: 每个命令都在表里（含通配） → 放行" python3 "$ROOT/scripts/check-command-table.py" "$TMP/tablegood"
mktable "$TMP/tablebad" '| 查看阶段 | `/spec-guard:phase` | x |
| 文档 | `/spec-guard:documentation-impact` | x |'
printf 'x\n' > "$TMP/tablebad/plugins/spec-guard/commands/cost-report.md"
want fail "command-table: 漏了命令（只在别的节出现） → 报错" python3 "$ROOT/scripts/check-command-table.py" "$TMP/tablebad"
mktable "$TMP/tablenone" '| 查看阶段 | `/spec-guard:phase` | x |'
rm -f "$TMP/tablenone/plugins/spec-guard/commands/"*.md
want fail "command-table: 零个命令文件 → 不算通过" python3 "$ROOT/scripts/check-command-table.py" "$TMP/tablenone"

# ── evals/dispatch-cost/grade.sh ──
# 审查 F10：隐藏测试经 `| tail -3` 运行且没有 pipefail，失败时判分仍退出 0。
# 用替身 PYTHON：unittest 按 GRADE_HIDDEN_RC 退出，成本报告恒成功（不跑付费评测）。
mkdir -p "$TMP/grade-run"
printf '%s\n' '#!/bin/sh' 'case "$*" in *unittest*) echo "hidden: rc=${GRADE_HIDDEN_RC}"; exit "${GRADE_HIDDEN_RC}" ;; esac' \
  'echo "cost: ok"' > "$TMP/grade-python"
chmod +x "$TMP/grade-python"
want pass "grade.sh: 隐藏测试通过 → 退出 0" \
  env PYTHON="$TMP/grade-python" GRADE_HIDDEN_RC=0 /bin/bash "$ROOT/evals/dispatch-cost/grade.sh" "$TMP/grade-run"
want fail "grade.sh: 隐藏测试失败 → 非零退出" \
  env PYTHON="$TMP/grade-python" GRADE_HIDDEN_RC=1 /bin/bash "$ROOT/evals/dispatch-cost/grade.sh" "$TMP/grade-run"
GRADE_OUT="$(PYTHON="$TMP/grade-python" GRADE_HIDDEN_RC=1 /bin/bash "$ROOT/evals/dispatch-cost/grade.sh" "$TMP/grade-run" 2>&1)"
want pass "grade.sh: 隐藏测试失败时仍输出成本部分" grep -Fq "cost: ok" <<<"$GRADE_OUT"

# ── check-state-paths.py ──
# runtime-state-layout：本机状态只经 state_paths.py；hooks 里其他家目录用法必须在允许清单内（读宿主配置、epiq 自己的目录）。
mkstate() {  # $1=目录
  rm -rf "$1"; mkdir -p "$1/plugins/spec-guard/hooks"
  printf '%s\n' 'from pathlib import Path' 'def state_root(): return Path.home() / ".spec-guard"' \
    > "$1/plugins/spec-guard/hooks/state_paths.py"
  printf '%s\n' 'from pathlib import Path' 'CLAUDE = Path.home() / ".claude" / "settings.json"' \
    'import os' 'G = os.path.join(os.path.expanduser("~"), ".epiq-global")' > "$1/plugins/spec-guard/hooks/reader.py"
  printf '%s\n' 'from pathlib import Path' 'X = Path.home() / ".anything"' > "$1/plugins/spec-guard/hooks/test_reader.py"
}
mkstate "$TMP/stategood"
want pass "state-paths: 只有 state_paths 与允许清单用到家目录 → 放行" \
  python3 "$ROOT/scripts/check-state-paths.py" "$TMP/stategood"
mkstate "$TMP/statebad"
printf '%s\n' 'from pathlib import Path' 'ROOT = Path.home() / ".local" / "state" / "other"' \
  > "$TMP/statebad/plugins/spec-guard/hooks/rogue.py"
STATE_OUT="$(python3 "$ROOT/scripts/check-state-paths.py" "$TMP/statebad" 2>&1)"
want fail "state-paths: 新增家目录写入 → 报错" python3 "$ROOT/scripts/check-state-paths.py" "$TMP/statebad"
want pass "state-paths: 报错给出文件与行号" grep -Fq "rogue.py:2" <<<"$STATE_OUT"
mkstate "$TMP/stateexp"
printf '%s\n' 'import os' 'D = os.path.expanduser("~/.cache/spec-guard")' > "$TMP/stateexp/plugins/spec-guard/hooks/rogue2.py"
want fail "state-paths: expanduser 写法同样拦下" python3 "$ROOT/scripts/check-state-paths.py" "$TMP/stateexp"
rm -rf "$TMP/stateempty"; mkdir -p "$TMP/stateempty"
want fail "state-paths: 0 个文件是没找到，不是没问题" python3 "$ROOT/scripts/check-state-paths.py" "$TMP/stateempty"

echo ""
echo "  总计 $PASS 通过 / $FAIL 失败"
[ "$FAIL" -eq 0 ] || exit 1
