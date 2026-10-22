#!/usr/bin/env bash
# Read-only guidance for the local multi-spec convention.
set -u

# 触发事件由 hooks.json 的注册处用参数告诉本脚本（compact-phase-injection）：SessionStart 一项只在上下文压缩后触发；
# 不带参数或其他值一律按 UserPromptSubmit，输出与改前逐字相同。
# open-commitments：另一项 SessionStart（会话开始与清空后）带第二个参数 fresh，只出账本读回提醒，见下面的 fresh_out。
FRESH=""
case "${1:-}" in
  SessionStart) EVENT=SessionStart; [ "${2:-}" != fresh ] || FRESH=1 ;;
  *) EVENT=UserPromptSubmit ;;
esac

# 只用 bash 内建取脚本目录：本 hook 只能依赖 bash、git 与 python3。
case "${BASH_SOURCE[0]}" in */*) HOOKDIR="${BASH_SOURCE[0]%/*}" ;; *) HOOKDIR=. ;; esac
HOOKDIR="$(cd "$HOOKDIR" && pwd)"
# Claude Code 提供 CLAUDE_PROJECT_DIR；Codex 不提供，并在会话目录里运行 hook。
# 从仓库子目录启动时按 git 仓库根目录判断激活，不在仓库里时才用当前目录。
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  ROOT="$CLAUDE_PROJECT_DIR"
else
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || ROOT=""
  [ -n "$ROOT" ] || ROOT="$(pwd)"
fi
# 激活信号必须是本插件写下的：独占一行的声明块标记（与 managed-block.py 相同），或含
# activeModule 的 state.json。正文里提到标记不算。注意判据是纯文本匹配：别的工具若在自己的
# .agent/state.json 里也用 activeModule 这个键（包括嵌套位置），同样会激活——比此前那条按值匹配
# 的判据宽。代价有限：本 hook 只读文件并打印阶段，不写任何东西。
# activeModule 是本插件写这个文件的唯一理由，所以它是准确的激活证据；此前判据用的
# `tracker` 字段已随远端 tracker 模式退役（docs/retirements/state-tracker-field.md）。
# 逐行匹配只用 bash 内建（不依赖 grep；审查 F12）：$2 是扩展正则，读不到文件即不匹配。
file_has_line() {  # $1=文件 $2=正则
  local line pattern="$2"
  [ -r "$1" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    [[ $line =~ $pattern ]] && return 0
  done < "$1"
  return 1
}

has_block() {  # $1=目录，默认当前目录
  file_has_line "${1:-.}/CLAUDE.md" '^[[:space:]]*<!-- BEGIN:agent-skills-convention -->[[:space:]]*$' ||
    file_has_line "${1:-.}/AGENTS.md" '^[[:space:]]*<!-- BEGIN:spec-guard-codex-convention -->[[:space:]]*$'
}

has_state() {  # $1=目录，默认当前目录
  file_has_line "${1:-.}/.agent/state.json" '"activeModule"[[:space:]]*:'
}

has_link() {  # $1=目录，默认当前目录
  [ -e "${1:-.}/.agent/spec-guard-link.json" ] || [ -L "${1:-.}/.agent/spec-guard-link.json" ]
}

# fact-fixes：启动 python3 之前先在 bash 里判断 hook 输入可能指向的两个根目录（宿主给的 ROOT、输入 cwd 所在 git 仓库）
# 是否都没有激活信号与指向文件；拿得准都没有时返回 0，调用方直接静默退出。bash 的 read 从管道逐字节读，大输入很慢，
# 所以只读前 64KB（RAW_MORE=1 表示后面还有）：没读完、cwd 不是不含转义的普通字符串、或出现不止一次，都算拿不准
# （返回 1），交给 python3 照旧解析。
inactive_before_python() {  # 读 RAW、RAW_MORE 与 ROOT
  local rest cwd top re='"cwd"[[:space:]]*:[[:space:]]*"([^"\\]*)"'
  if has_block "$ROOT" || has_state "$ROOT" || has_link "$ROOT"; then return 1; fi
  [ -z "$RAW_MORE" ] || return 1
  case "$RAW" in *'"cwd"'*) ;; *) return 0 ;; esac
  rest="${RAW#*\"cwd\"}"
  case "$rest" in *'"cwd"'*) return 1 ;; esac
  [[ $RAW =~ $re ]] || return 1
  cwd="${BASH_REMATCH[1]}"
  [ -n "$cwd" ] && [ -d "$cwd" ] || return 0
  top="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null)" || return 0
  [ -n "$top" ] || return 0
  ! { has_block "$top" || has_state "$top" || has_link "$top"; }
}

# 桌面版 worktree 会话里，宿主给的项目目录可能是主检出目录，而会话在 linked worktree 里：hook 输入的 cwd
# 所在 git 仓库优先（session_context.py --resolve-root，最多等 1 秒、上限 1MB）。标准输入只读这一次：bash 读过的前缀
# 与其余部分按原字节交给 python3（其余部分由一个同样最多等 1 秒的拷贝进程转过去），留给后面的会话事实。
# 输入不可用或缺 python3 时根目录不变。
HOOK_INPUT=""
if [ ! -t 0 ] && command -v python3 >/dev/null 2>&1; then
  RAW="" RAW_MORE=""
  if IFS= read -r -n 65536 -d '' -t 1 RAW; then RAW_MORE=1; fi
  inactive_before_python && exit 0
  RESOLVED="$({ printf '%s' "$RAW"
    [ -z "$RAW_MORE" ] || python3 -c '
import os, select, time
deadline = time.monotonic() + 1.0
while True:
    left = deadline - time.monotonic()
    if left <= 0 or not select.select([0], [], [], left)[0]:
        break
    chunk = os.read(0, 65536)
    if not chunk:
        break
    os.write(1, chunk)
' 2>/dev/null
  } | python3 "$HOOKDIR/session_context.py" --resolve-root "$ROOT" 2>/dev/null)" || RESOLVED=""
  case "$RESOLVED" in *$'\n'*) ROOT="${RESOLVED%%$'\n'*}"; HOOK_INPUT="${RESOLVED#*$'\n'}" ;; esac
fi
cd "$ROOT" 2>/dev/null || exit 0

# linked-project-root：会话目录自己没有激活信号时，只有本插件写下的指向文件算数（.agent/spec-guard-link.json，声明
# 这里的工作对应别处的哪个项目）。没有它就照旧静默，而且在启动任何 python3 之前就退出；自己已启用时不看指向文件。
LINKED=""
if ! has_block && ! has_state; then
  has_link || exit 0
  LINKED=1
fi

# open-commitments：会话开始与清空后只出一句读回提醒，不出阶段摘要（随后的 UserPromptSubmit 会给）。只看项目根有没有
# .epiq/project.json，不读账本内容、不调 Epiq；没有就静默。提醒是固定文字，JSON 手写，不依赖 python3 生成。
# record-on-receipt：两处读回提醒末尾都给出调用账本工具要传的 repoRoot。路径来自当前目录（跟随指向时已在目标项目里）；
# 含引号、反斜杠或控制字符时不写路径，免得手写的 JSON 出错。$1 为 zh 时用中文。
ledger_root_note() {
  local root="$PWD"
  if [[ $root == *'"'* || $root == *'\'* || $root =~ [[:cntrl:]] ]]; then
    if [ "${1:-}" = zh ]; then printf '%s' '调用账本工具时都传 `repoRoot` 为项目根目录。'
    else printf '%s' ' Pass `repoRoot` = the project root to every ledger tool call.'; fi
  elif [ "${1:-}" = zh ]; then printf '%s' "调用账本工具时都传 \`repoRoot\` 为 \`${root}\`。"
  else printf '%s' " Pass \`repoRoot\` = \`${root}\` to every ledger tool call."; fi
}
fresh_out() {
  [ -f .epiq/project.json ] || exit 0
  local text='This project has the local ticket ledger enabled: first list the open issues tagged `waiting-on-me`, `waiting-on-them` or `waiting-on-user`; carry on with the `waiting-on-me` ones, follow up once on the `waiting-on-them` ones if needed, and hand the `waiting-on-user` ones to the user, then continue with what the user asked. If there are none, just continue.'
  if command -v python3 >/dev/null 2>&1 &&
    [ "$(python3 "$HOOKDIR/module_stage.py" . --hint-language 2>/dev/null)" = zh-CN ]; then
    text='本项目启用了本地事项账本：先列出带 `waiting-on-me`／`waiting-on-them`／`waiting-on-user` 标签的未关闭事项，`waiting-on-me` 的接着处理，`waiting-on-them` 的按需追问一次，`waiting-on-user` 的交给用户，再继续用户的请求；没有就直接继续。'
    text="${text}$(ledger_root_note zh)"
  else
    text="${text}$(ledger_root_note)"
  fi
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"'"${text}"'"}}'
  exit 0
}
if [ -n "$FRESH" ]; then
  [ -n "$LINKED" ] || fresh_out
  # 跟随指向要用 python3；缺 python3 或指向失效时静默，诊断留给随后的 UserPromptSubmit。
  command -v python3 >/dev/null 2>&1 || exit 0
fi

# 已启用却缺 python3 时不能静默：静默会被当成“未启用”。这段 JSON 手写转义，不依赖 python3。
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"'"$EVENT"'","additionalContext":"spec-guard: 本项目已启用约定，但 python3 不可用，本轮没有阶段注入。这不是「未启用」；安装 python3 后恢复。"}}'
  exit 0
fi

# python3 在 PATH 上却跑不起来时 emit 自己也会失败；同样不能静默，退回一段手写转义的 JSON。
# 压缩后（SessionStart）多一句核对提醒：摘要里较早的请求可能已做完；不说“旧指令不是新任务”，压缩前刚下的指令也可能还没进 todo。
COMPACT_NOTE='Context was just compacted: earlier requests in the summary may already be done; check the todo and the state record before redoing anything, and once checked, carry on with the suggested next step above, if there is one, instead of ending the turn.'
emit() {
  local out text="$1" mark
  # receipt-hint-on-message：提醒行放在建议下一步之前（没有建议下一步时放在末尾）。
  if [ -n "${RECEIPT:-}" ]; then
    case "$text" in
      *$'\n\n建议下一步'*) mark=$'\n\n建议下一步' ;;
      *$'\n\nSuggested next step'*) mark=$'\n\nSuggested next step' ;;
      *) mark="" ;;
    esac
    if [ -n "$mark" ]; then text="${text%%"$mark"*}"$'\n'"${RECEIPT}${mark}${text#*"$mark"}"
    else text="${text}"$'\n\n'"${RECEIPT}"; fi
  fi
  [ "$EVENT" != SessionStart ] || text="${text}

${COMPACT_NOTE}"
  out="$(printf '%s' "$text" | python3 -c '
import json, sys
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": sys.argv[1],
    "additionalContext": sys.stdin.read(),
}}))
' "$EVENT" 2>/dev/null)" || out=""
  case "$out" in
    '{'*) printf '%s\n' "$out" ;;
    *) printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"'"$EVENT"'","additionalContext":"spec-guard: 本项目已启用约定，但 python3 无法运行，本轮没有阶段注入。这不是「未启用」；修复 python3 后恢复。"}}' ;;
  esac
}

# 跟随指向：判定在 project_link.py；目标是否已启用仍用上面的 has_block／has_state（cd 过去后重用）。不连环跟随：
# 只看目标自己的激活信号，不读目标里的指向文件。失效不是「未启用」，所以给诊断而不静默。
if [ -n "$LINKED" ]; then
  # link-per-session：把 hook 输入转交过去，由它取会话标识；本会话的登记优先，其次目录级指向。
  LINK_OUT="$(printf '%s' "$HOOK_INPUT" | python3 -B "$HOOKDIR/project_link.py" resolve --from . --hook-input 2>/dev/null)" || LINK_OUT=""
  LINK_STATUS="${LINK_OUT%%$'\n'*}"
  LINK_REST=""
  case "$LINK_OUT" in *$'\n'*) LINK_REST="${LINK_OUT#*$'\n'}" ;; esac
  LINK_TARGET="${LINK_REST%%$'\n'*}"
  LINK_SHOWN=""; LINK_FROM=""
  case "$LINK_REST" in *$'\n'*) LINK_SHOWN="${LINK_REST#*$'\n'}" ;; esac
  case "$LINK_SHOWN" in *$'\n'*) LINK_FROM="${LINK_SHOWN#*$'\n'}"; LINK_FROM="${LINK_FROM%%$'\n'*}" ;; esac
  LINK_SHOWN="${LINK_SHOWN%%$'\n'*}"
  # 第五行是来源：session（本会话自己的登记）或 directory（目录级指向）。
  LINK_SOURCE=""
  case "$LINK_OUT" in *$'\n'session) LINK_SOURCE=session ;; esac
  if [ "$LINK_SOURCE" = session ]; then LINK_WHICH="其中本会话的登记"; else LINK_WHICH="它"; fi
  LINK_FIX='用 `/spec-guard:link-project`（Codex：`spec-guard-ops` 的 link-project 一节）查看、重新建立或解除指向。这是指向失效，不是「未启用」。'
  LINK_BAD=""
  case "$LINK_STATUS" in
    ok)
      if ! cd "$LINK_TARGET" 2>/dev/null; then
        LINK_BAD="${LINK_WHICH}指向的目录进不去（${LINK_SHOWN}）"
      elif ! has_block && ! has_state; then
        LINK_BAD="${LINK_WHICH}指向的目录没有启用 spec-guard（${LINK_SHOWN}）：那里没有约定块，也没有带 activeModule 的 \`.agent/state.json\`"
      fi ;;
    missing) LINK_BAD="${LINK_WHICH}指向的目录不存在或不是目录（${LINK_SHOWN}）" ;;
    # 文件里只有别的会话的登记、没有目录级指向：对本会话等于没有指向，照旧静默。
    none) exit 0 ;;
    invalid) LINK_BAD="它的格式无效（应为 JSON 对象：版本 1 只含 version 与 project；版本 2 含 version、sessions，可选 project）" ;;
    *) LINK_BAD="没能读取它（检查没有正常运行）" ;;
  esac
  if [ -n "$LINK_BAD" ]; then
    [ -z "$FRESH" ] || exit 0
    emit "## spec-guard local workflow

spec-guard: 本目录有指向文件 \`.agent/spec-guard-link.json\`，但${LINK_BAD}，本轮没有阶段注入。${LINK_FIX}"
    exit 0
  fi
fi
[ -z "$FRESH" ] || fresh_out

# hint-language-follow：说明文字的语言只由 module_stage.py --hint-language 判定（artifactLanguage 恰好是 zh-CN 才是中文）；
# 取不到时按英文，输出与改前逐字相同。跟随指向时这里已在目标项目里，用的是目标项目的配置。
ZH=""
[ "$(python3 "$HOOKDIR/module_stage.py" . --hint-language 2>/dev/null)" != zh-CN ] || ZH=1
[ -z "$ZH" ] || COMPACT_NOTE='上下文刚被压缩：摘要里较早的请求可能已经做完；重做之前先核对 todo 和状态记录，核对后接着做上面的建议下一步（有的话），不要就此结束这一轮。'
# open-commitments：项目启用了本地事项账本时，压缩后的核对也包括账本里未关闭的 waiting-on-* 事项；没有账本时上面两句不变。
if [ -f .epiq/project.json ]; then
  if [ -n "$ZH" ]; then
    COMPACT_NOTE='上下文刚被压缩：摘要里较早的请求可能已经做完；重做之前先核对 todo、状态记录和账本里未关闭的 `waiting-on-*` 事项，核对后接着做上面的建议下一步（有的话），不要就此结束这一轮。'
    COMPACT_NOTE="${COMPACT_NOTE}$(ledger_root_note zh)"
  else
    COMPACT_NOTE='Context was just compacted: earlier requests in the summary may already be done; check the todo, the state record and the open `waiting-on-*` issues in the ledger before redoing anything, and once checked, carry on with the suggested next step above, if there is one, instead of ending the turn.'
    COMPACT_NOTE="${COMPACT_NOTE}$(ledger_root_note)"
  fi
fi

# receipt-hint-on-message：有账本、且这一轮是别的会话转来的消息时，建议下一步之前多一行当场记账的提醒。
# 判定与清理在 session_context.py --received（只读提示词开头的包装与它的两个属性）；其他情形不出这一行。
receipt_hint() {
  [ "$EVENT" = UserPromptSubmit ] && [ -f .epiq/project.json ] || return 0
  local got name session who
  got="$(printf '%s' "$HOOK_INPUT" | python3 "$HOOKDIR/session_context.py" --received 2>/dev/null)" || return 0
  case "$got" in received$'\t'*) ;; *) return 0 ;; esac
  got="${got#received$'\t'}"; name="${got%%$'\t'*}"; session="${got#*$'\t'}"
  if [ -n "$ZH" ]; then
    who=""
    [ -z "$name" ] || who="对方 \`${name}\`"
    [ -z "$session" ] || who="${who:+${who}，}会话 \`${session}\`"
    printf '%s' "- 这一轮是别的会话发来的消息${who:+（${who}）}：先把它记进本地事项账本——对方、来路与回路、内容、球在谁手里（\`waiting-on-me\`／\`waiting-on-user\`）——再决定要不要问用户；记账不是受理，要不要做仍由用户定。$(ledger_root_note zh)"
  else
    who=""
    [ -z "$name" ] || who="sender \`${name}\`"
    [ -z "$session" ] || who="${who:+${who}, }session \`${session}\`"
    printf '%s' "- Message from another session${who:+ (${who})}: record it in the local ticket ledger first -- who sent it, the way it came and the way back, what it asks, whose move it is (\`waiting-on-me\` / \`waiting-on-user\`) -- then decide whether to ask the user; recording is not accepting it, and whether to do it is still the user's call.$(ledger_root_note)"
  fi
}
RECEIPT="$(receipt_hint)"

# 会话事实（session_context.py，只读）：第一行是主会话上下文 token 数，第二行是位置行，读不到为空。
# hook 输入已在上面读过，这里转交那一行原文。
FACTS="$(printf '%s' "$HOOK_INPUT" | python3 "$HOOKDIR/session_context.py" . ${ZH:+--lang zh-CN} 2>/dev/null)" || FACTS=""
TOKENS="${FACTS%%$'\n'*}"
case "$TOKENS" in ''|*[!0-9]*) TOKENS="" ;; esac
# phase-hint-gaps：压缩后那一次（SessionStart）宿主还没把压缩记录写进会话记录，读到的是压缩前最后一轮的用量；
# 刚压缩完大小必然已降，按 0 处理，不出上下文行与边界行。下一轮 UserPromptSubmit 照常读。
[ "$EVENT" != SessionStart ] || TOKENS=0
LOCATION=""
case "$FACTS" in *$'\n'*) LOCATION="${FACTS#*$'\n'}" ;; esac
# 第三行是 Codex 记录里的上下文窗口（Claude 为空）。
WINDOW=""
case "$LOCATION" in *$'\n'*) WINDOW="${LOCATION#*$'\n'}" ;; esac
# 第四行是 unattended（claude -p、codex exec）或空：没人在场时不出「请告诉用户 /compact、/clear」那一行。
# 第五行是宿主（codex 或空），第六行是 over-200k 或空（Claude 尾部有读数超过 200k，quiet-injection 按 1M 估算窗口），
# 第七行是会话记录里最近一次 spec-guard 注入的状态码（quiet-injection；压缩之后、读不到或没有时为空）。
UNATTENDED="" FACT_HOST="" OVER="" LAST=""
REST="$WINDOW"
case "$REST" in *$'\n'*) REST="${REST#*$'\n'}" ;; *) REST="" ;; esac
[ "${REST%%$'\n'*}" != unattended ] || UNATTENDED=1
case "$REST" in *$'\n'*) REST="${REST#*$'\n'}" ;; *) REST="" ;; esac
FACT_HOST="${REST%%$'\n'*}"
case "$REST" in *$'\n'*) REST="${REST#*$'\n'}" ;; *) REST="" ;; esac
[ "${REST%%$'\n'*}" != over-200k ] || OVER=1
case "$REST" in *$'\n'*) REST="${REST#*$'\n'}" ;; *) REST="" ;; esac
LAST="${REST%%$'\n'*}"
case "$LAST" in [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;; *) LAST="" ;; esac
# 压缩后（SessionStart）总是给完整内容。
[ "$EVENT" != SessionStart ] || LAST=""
WINDOW="${WINDOW%%$'\n'*}"
case "$WINDOW" in ''|*[!0-9]*) WINDOW="" ;; esac
LOCATION="${LOCATION%%$'\n'*}"
# 宿主（codex-command-wording）：命令提示按宿主给写法。显式的 SPEC_GUARD_HOST 优先（Codex 的 spec-guard-ops 手动
# 运行时会带 CLAUDE_PROJECT_DIR）；其次是第五行，hook 输入本身说明是 Codex（turn_id 或 session_meta）；再看环境：
# Claude Code 给 hook 设 CLAUDE_PROJECT_DIR，Codex 只设 PLUGIN_ROOT（两边都设的 CLAUDE_PLUGIN_ROOT 不能用）。
# 都判断不了时 HOST 为空，输出与改前逐字相同。
case "${SPEC_GUARD_HOST:-}" in
  codex|claude) HOST="$SPEC_GUARD_HOST" ;;
  *)
    case "$FACT_HOST" in
      codex) HOST=codex ;;
      *) if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then HOST=claude
         elif [ -n "${PLUGIN_ROOT:-}" ]; then HOST=codex
         else HOST=""; fi ;;
    esac ;;
esac
# quiet-injection（Q2 A）：Claude 的记录里没有窗口；有读数时按 200k 估算，尾部有读数超过 200k 就按 1M 估算，并在提示里写明是估算。
WINDOW_ESTIMATED=""
if [ -z "$WINDOW" ] && [ -n "$TOKENS" ] && [ "$HOST" != codex ]; then
  WINDOW_ESTIMATED=1
  if [ -n "$OVER" ]; then WINDOW=1000000; else WINDOW=200000; fi
fi
if [ "$HOST" = codex ]; then VERIFY_CMD='`$spec-guard-ops` verify-artifacts'; else VERIFY_CMD='`/spec-guard:verify-artifacts`'; fi
# 位置行放在标题与“当前阶段”之间，所有阶段都带；不在 git 仓库里时没有这一行。
HEADER="## spec-guard local workflow"
[ -z "$LOCATION" ] || HEADER="${HEADER}

${LOCATION}"
# 跟随指向时写明项目在哪：阶段是那个项目的，位置行也是它的；路径已在 project_link.py 里清洗。
if [ -n "$LINKED" ] && [ -n "$ZH" ] && [ "$LINK_SOURCE" = session ]; then
  HEADER="${HEADER}

关联项目: \`${LINK_SHOWN}\` — 本会话在 \`${LINK_FROM}\` 下的 \`.agent/spec-guard-link.json\` 里有自己的登记，指向这个项目；那个目录里的其他会话不受影响。spec-guard 命令会自动跟随到这个项目。"
elif [ -n "$LINKED" ] && [ -n "$ZH" ]; then
  HEADER="${HEADER}

关联项目: \`${LINK_SHOWN}\` — 本会话的目录 \`${LINK_FROM}\` 通过 \`.agent/spec-guard-link.json\` 指向它。spec-guard 命令会自动跟随到这个项目。这个指向对在该目录里运行的每个会话都生效；如果本会话做的是别的项目，忽略这里的阶段，用 \`link-project\` 给本会话登记自己的项目。"
elif [ -n "$LINKED" ] && [ "$LINK_SOURCE" = session ]; then
  HEADER="${HEADER}

Linked project: \`${LINK_SHOWN}\` — this session is linked to it by its own entry in \`.agent/spec-guard-link.json\` under \`${LINK_FROM}\`; other sessions in that directory are not affected. spec-guard commands follow it automatically."
elif [ -n "$LINKED" ]; then
  HEADER="${HEADER}

Linked project: \`${LINK_SHOWN}\` — this session's directory \`${LINK_FROM}\` points to it through \`.agent/spec-guard-link.json\`. spec-guard commands follow it automatically. The link applies to every session that runs in that directory; if this session works on a different project, ignore this stage and register this session's own project with \`link-project\`."
fi

# quiet-injection（D5）：状态码里本 hook 自己掌握的事实——位置行与跟随指向的项目；其余由 module_stage.py 算。
STATE_EXTRA="${LOCATION}
${LINKED:+${LINK_SOURCE}:${LINK_SHOWN}:${LINK_FROM}}"

SPECS=0
for spec in spec/*.md; do
  [ -e "$spec" ] || continue
  [ "${spec##*/}" = CAPABILITY-MAP.md ] || SPECS=$((SPECS + 1))
done

# 能力图存在却读不了是读取故障，不是能力图的状态：不论有没有模块 spec 都报 UNKNOWN（与 module_stage 同一行）。
if [ -e spec/CAPABILITY-MAP.md ] && { [ ! -f spec/CAPABILITY-MAP.md ] || [ ! -r spec/CAPABILITY-MAP.md ]; }; then
  if [ ! -f spec/CAPABILITY-MAP.md ]; then REASON="not a regular file"; else REASON="no read permission"; fi
  if [ -n "$ZH" ]; then
    if [ ! -f spec/CAPABILITY-MAP.md ]; then REASON="不是普通文件"; else REASON="没有读取权限"; fi
    emit "${HEADER}

当前阶段: **UNKNOWN**

- 能力图: 已有但读不了（${REASON}）
- 模块 Spec: ${SPECS}

建议下一步: 让 \`spec/CAPABILITY-MAP.md\` 成为可读的文件（检查它的权限），然后再发下一条消息；这是读取故障，不是能力图的状态。"
    exit 0
  fi
  emit "${HEADER}

当前阶段: **UNKNOWN**

- Capability map: present but unreadable (${REASON})
- Module specs: ${SPECS}

Suggested next step: make \`spec/CAPABILITY-MAP.md\` a readable file (check its permissions), then send the next prompt; this is a read failure, not a state of the map."
  exit 0
fi

# phase-hint-gaps：IDLE 与 MAP_ONLY 不经 module_stage.py 的完整判定，项目配置行（产物语言、combined 节奏、配置无效）
# 另向它取，与其他阶段同一实现；取不到时不加，阶段输出照旧。
CONFIG_LINES=""
if [ ! -f spec/CAPABILITY-MAP.md ] || [ "$SPECS" -eq 0 ]; then
  CONFIG_LINES="$(python3 "$HOOKDIR/module_stage.py" . --config-lines ${HOST:+--host "$HOST"} 2>/dev/null)" || CONFIG_LINES=""
  [ -z "$CONFIG_LINES" ] || CONFIG_LINES="
${CONFIG_LINES}"
fi

# rules-at-nodes：IDLE 要写能力图、MAP_ONLY 要写第一份 Spec，各附那个节点的停点规则（取自 node-rules.md，经 module_stage.py）；
# 取不到时为空，输出与改前逐字相同。标签的语言跟提示一致，规则正文只有中文。
STOP_RULES=""
if [ ! -f spec/CAPABILITY-MAP.md ] || [ "$SPECS" -eq 0 ]; then
  if [ ! -f spec/CAPABILITY-MAP.md ]; then NODE='map-review'; else NODE='spec-review'; fi
  SECTION="$(python3 "$HOOKDIR/module_stage.py" . --node-rules "$NODE" 2>/dev/null)" || SECTION=""
  if [ -n "$SECTION" ]; then
    case "$NODE${ZH:+-zh}" in
      map-review-zh) LABEL='停点规则（能力图审阅）：' ;;
      spec-review-zh) LABEL='停点规则（Spec 交审）：' ;;
      map-review) LABEL='Stop rules (capability map review):' ;;
      *) LABEL='Stop rules (Spec review):' ;;
    esac
    STOP_RULES="

${LABEL}

${SECTION}"
  fi
  # 状态码（module_stage.py --state-key，与其他阶段同一算法）接在最后；取不到时不加，输出与改前相同。
  if [ ! -f spec/CAPABILITY-MAP.md ]; then KEY_STAGE=IDLE; else KEY_STAGE=MAP_ONLY; fi
  KEY="$(python3 "$HOOKDIR/module_stage.py" . --state-key --stage "$KEY_STAGE" --node "$NODE" --state-extra "$STATE_EXTRA" \
    ${HOST:+--host "$HOST"} 2>/dev/null)" || KEY=""
  BRIEF=""
  case "$KEY" in *$'\n'*) BRIEF="${KEY#*$'\n'}"; KEY="${KEY%%$'\n'*}" ;; esac
  case "$KEY" in [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f])
    # 状态码与上一次相同：只给一行（quiet-injection）。
    if [ "$KEY" = "$LAST" ] && [ -n "$BRIEF" ]; then
      emit "$BRIEF"
      exit 0
    fi
    STOP_RULES="${STOP_RULES}

<!-- spec-guard-state: ${KEY} -->" ;;
  esac
fi

if [ ! -f spec/CAPABILITY-MAP.md ] && [ -n "$ZH" ]; then
  emit "${HEADER}

当前阶段: **IDLE**

- 能力图: 没有
- 模块 Spec: ${SPECS}${CONFIG_LINES}

建议下一步: 先跟用户确认需求已说完，再写能力图并交审，然后做规划。${STOP_RULES}"
  exit 0
fi

if [ ! -f spec/CAPABILITY-MAP.md ]; then
  emit "${HEADER}

当前阶段: **IDLE**

- Capability map: absent
- Module specs: ${SPECS}${CONFIG_LINES}

Suggested next step: confirm with the user that the requirement is complete, then create and review a capability map before planning.${STOP_RULES}"
  exit 0
fi

if [ "$SPECS" -eq 0 ] && [ -n "$ZH" ]; then
  emit "${HEADER}

当前阶段: **MAP_ONLY**

- 能力图: 已有
- 模块 Spec: 没有${CONFIG_LINES}

建议下一步: 先跟用户确认第一个模块的需求已说完，再在 \`spec/\` 下写第一份模块 Spec 并交审。${STOP_RULES}"
  exit 0
fi

if [ "$SPECS" -eq 0 ]; then
  emit "${HEADER}

当前阶段: **MAP_ONLY**

- Capability map: present
- Module specs: absent${CONFIG_LINES}

Suggested next step: confirm with the user that the first module's requirement is complete, then write the first reviewed module spec under \`spec/\`.${STOP_RULES}"
  exit 0
fi

# 按模块判断当前在哪一步（module_stage.py，只读）；它失败时注入诊断，而不是静默。
if STAGE="$(python3 "$HOOKDIR/module_stage.py" . ${TOKENS:+--context-tokens "$TOKENS"} ${WINDOW:+--context-window "$WINDOW"} ${WINDOW_ESTIMATED:+--window-estimated} ${UNATTENDED:+--unattended} ${HOST:+--host "$HOST"} --state-extra "$STATE_EXTRA" ${LAST:+--last-state "$LAST"} 2>/dev/null)"; then
  case "$STAGE" in
    'spec-guard: '*) emit "$STAGE" ;;  # quiet-injection：状态码与上一次相同，只给一行（后面可能附边界行）
    *) emit "${HEADER}

${STAGE}" ;;
  esac
elif [ -n "$ZH" ]; then
  emit "${HEADER}

当前阶段: **UNKNOWN**

- 模块 Spec: ${SPECS}
- 没能算出模块阶段；运行 ${VERIFY_CMD} 查看详情。"
else
  emit "${HEADER}

当前阶段: **UNKNOWN**

- Module specs: ${SPECS}
- The module stage could not be computed; run ${VERIFY_CMD} for details."
fi
