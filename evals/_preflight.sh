# shellcheck shell=bash
# ─────────────────────────────────────────────────────────────
# evals 共用前置检查。被 source，不单独执行。
#
# 为什么需要它：两个评测都用 `claude -p` 在脚手架目录里跑，而那条命令加载的是
# **装着的那份插件**（user scope），不是这个仓库的工作副本。可脚手架的声明块
# 是从仓库的 templates/ 拷的，自检也是拿 CLAUDE_PLUGIN_ROOT 指着仓库跑的 ——
# 两者一旦不一致，「✅ hook 已激活」说的就是另一份代码，评测结论无从解释。
# 这正是 CHANGELOG 里记过的「新约定 + 旧检查器」中间态，只不过发生在评测里。
# ─────────────────────────────────────────────────────────────

# 装着的插件内容必须与仓库一致。不一致就别烧 token 了。
preflight_installed_matches_repo() {  # $1=仓库根
  local repo="$1" inst
  inst=$(python3 -c "
import json, os, sys
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    print(d['plugins']['spec-guard@spec-guard-marketplace'][0]['gitCommitSha'])
except Exception:
    pass" 2>/dev/null)
  if [ -z "${inst}" ]; then
    echo "  ❌ 读不到已安装的 spec-guard —— \`claude -p\` 里 hook 不会跑，评测无意义"
    echo "     先 /plugin install，或跑 claude plugin update"
    return 1
  fi
  if ! git -C "${repo}" merge-base --is-ancestor "${inst}" HEAD 2>/dev/null; then
    echo "  ❌ 装着的 ${inst:0:7} 不是当前 HEAD 的祖先 —— 版本关系不明，评测结论无从解释"
    return 1
  fi
  if ! git -C "${repo}" diff --quiet "${inst}" HEAD -- plugins/spec-guard 2>/dev/null; then
    echo "  ❌ 装着的插件内容与仓库不一致（装着 ${inst:0:7}）——"
    echo "     评测跑的是装着的那份，而脚手架和自检用的是仓库这份。先发版并 update："
    echo "       claude plugin marketplace update spec-guard-marketplace"
    echo "       claude plugin update spec-guard@spec-guard-marketplace   # 之后要重启"
    return 1
  fi
  # **还要工作区干净。** 上面比的是 installed sha 与 HEAD 两个**提交**；
  # 插件文件在工作区里改了没提交的话，两边照样「一致」，而 `claude -p` 加载的
  # 是装着的那份 —— 评测于是安静地测了上一版，结论却会被读成当前版的。
  # 这跟 mutation-check 那个「脏工作区」是同一类洞：判据看的对象和真正生效的
  # 对象不是同一个。
  if ! git -C "${repo}" diff --quiet HEAD -- plugins/spec-guard 2>/dev/null; then
    echo "  ❌ plugins/spec-guard 在工作区里有未提交的改动 ——"
    echo "     \`claude -p\` 加载的是**装着的那份**，测不到你刚改的东西，"
    echo "     而结论会被读成当前版的。先 commit + 发版 + update。"
    return 1
  fi
  echo "  ✅ 装着的插件内容与仓库一致（${inst:0:7}），且工作区干净"
  return 0
}

# CLI 能不能鉴权 —— 不花模型调用。
# 为什么需要它：评测 spawn 的 `claude -p` 是独立的 CLI 进程，读 Keychain 里
# `Claude Code-credentials` 那份 OAuth 会话，**与桌面 app／网页各自独立**。桌面 app 能用
# 不代表 CLI 能用（桌面会话走宿主鉴权，env 里有 CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH）。
# 2026-10-05 实际踩到：CLI 会话在评测跑到一半时失效，4 次调用全白烧，而 preflight 当时
# 只查插件版本，一个字都没提鉴权。
#
# **这条探测只能证明「有登录记录」，不能证明模型调用会成功。** 没有验证过
# 「已登录但 token 刷不动」时 auth status 会报什么 —— 要验它得先登出使用者的 CLI。
# 跑到一半仍可能失败，那一步由 run_headless 负责报得清楚。
preflight_cli_can_authenticate() {  # $1=claude 可执行文件（可选，自检用）
  local binary="${1:-claude}" raw state
  raw="$("${binary}" auth status --json 2>/dev/null </dev/null)"
  state="$(python3 -c "
import json, sys
try:
    value = json.loads(sys.argv[1])
except ValueError:
    value = {}
if not isinstance(value, dict):
    value = {}
print('in' if value.get('loggedIn') is True
      else 'out' if value.get('loggedIn') is False else 'unreadable')
" "${raw}")"
  case "${state}" in
    in)  echo "  ✅ claude CLI 已登录（auth status，未调用模型）"; return 0 ;;
    out)
      echo "  ❌ claude CLI 未登录 —— 4 次模型调用会全部白跑"
      echo "     在交互式 claude 里打斜杠命令 /login（不是 shell 的 claude login）"
      return 1
      ;;
    *)
      # 认不出的输出形状不假阻塞：按本仓库对 check-gh-json-fields 的做法，
      # 干净跳过并声明「跳过不代表通过」。
      echo "  ⏭  读不出 claude auth status 的形状，未检查登录态 —— 跳过不代表通过"
      return 0
      ;;
  esac
}

# 跑一次 headless claude，并把「没跑起来」和「跑了但结果不对」分开。
# 前者是工具故障，绝不能算成产品缺陷 —— 那是本仓最看重的那类误报。
run_headless() {  # $1=工作目录 $2=stdout 落盘路径 ; 其余=claude 参数
  local dir="$1" out="$2"; shift 2
  # `< /dev/null`：非 TTY 的 stdin 会让 claude 等 3 秒再警告（其他宿主上同形的写法会直接挂住）。
  ( cd "${dir}" && claude "$@" < /dev/null ) > "${out}" 2> "${out}.err"
  local rc=$?
  if [ "${rc}" -ne 0 ]; then
    echo "  ❌ claude 退出码 ${rc} —— **评测没跑起来**，这不是产品的结论"
    # stdout 也要打：claude 把致命错误写在 **stdout**，只打 stderr 会把真正的原因吞掉。
    # 2026-10-05 实测踩到：stderr 只有一句 stdin 警告，而
    # 「Failed to authenticate: OAuth session expired」在 stdout 里，于是评测输出里
    # 完全看不出是登录过期（docs/lenses.md A4：失败必须可观察）。
    sed -n '1,5p' "${out}" | sed 's/^/     out: /'
    sed -n '1,5p' "${out}.err" | sed 's/^/     err: /'
    return 2
  fi
  if [ ! -s "${out}" ]; then
    echo "  ❌ claude 退 0 但没有任何输出 —— **评测没跑起来**，这不是产品的结论"
    return 2
  fi
  return 0
}
