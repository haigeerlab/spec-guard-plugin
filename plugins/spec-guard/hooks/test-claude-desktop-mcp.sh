#!/usr/bin/env bash
# Claude Desktop MCPB 的 stdio 回归：每个工具都必须真的调用对应 hook，
# 并把 hook 的失败原样传成 isError，而不是返回成功形状的文本。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER="$ROOT/mcp/claude_desktop_server.mjs"
MANIFEST="$ROOT/manifest.json"
REPO="$(cd "$ROOT/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! command -v node >/dev/null 2>&1; then
  echo "  ❌ node 不可用，无法运行 Claude Desktop MCP 回归（环境未就绪，不是产品通过）"
  exit 2
fi

mkproject() {  # $1=目录
  mkdir -p "$1/spec"
  git -C "$1" init -q
  printf '%s\n' '<!-- BEGIN:agent-skills-convention -->' '<!-- END:agent-skills-convention -->' >"$1/CLAUDE.md"
  printf '%s\n' '# Capability Map: Desktop Fixture' '' '## 目标' '' '验证 Desktop MCP 只读工具。' '' '## 模块' '' \
    '| Module id | Responsibility | Depends on |' '| --- | --- | --- |' '| fixture-module | 夹具模块 | — |' '' \
    'Build order: fixture-module' >"$1/spec/CAPABILITY-MAP.md"
  printf '# fixture-module\n' >"$1/spec/fixture-module.md"
}
GOOD="$TMP/good"
BAD="$TMP/bad"
mkproject "$GOOD"
mkproject "$BAD"
printf '# drift\n' >"$BAD/SPEC.md"

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

call() {  # $1=id $2=tool $3=project
  printf '{"jsonrpc":"2.0","id":%s,"method":"tools/call","params":{"name":"%s","arguments":{"project":"%s"}}}\n' "$1" "$2" "$3"
}

echo "═══ Claude Desktop MCP 回归测试 ═══"

{
  printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"test","version":"1"},"capabilities":{}}}'
  printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
  printf '%s\n' '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"write_operation","arguments":{"project":"/not/a/project","operation":"teardown"}}}'
  printf '%s\n' '{"jsonrpc":"2.0","id":4,"method":"unknown/method","params":{}}'
  call 5 phase "$GOOD"
  call 6 verify "$GOOD"
  call 7 verify "$BAD"
  call 8 verify_history "$REPO"
  call 9 audit_history "$REPO"
  call 10 audit_history "$GOOD"
  call 11 phase "relative/path"
  call 12 sync_map_preview "$GOOD"
} >"$TMP/stdin"

if env -u HOME -u XDG_STATE_HOME -u XDG_CONFIG_HOME node "$SERVER" <"$TMP/stdin" >"$TMP/stdout" 2>"$TMP/stderr"; then
  ok "server accepts JSON-RPC stream"
else
  bad "server accepts JSON-RPC stream"
fi

if python3 - "$TMP/stdout" "$MANIFEST" <<'PY'
import json, sys
lines = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
manifest = json.load(open(sys.argv[2], encoding="utf-8"))
by_id = {line["id"]: line for line in lines}
assert sorted(by_id) == list(range(1, 13)), sorted(by_id)

def result(i):
    value = by_id[i]["result"]
    return value["isError"], value["content"][0]["text"]

assert by_id[1]["result"]["capabilities"] == {"tools": {}}
assert by_id[1]["result"]["serverInfo"] == {"name": "spec-guard", "version": manifest["version"]}
assert [tool["name"] for tool in by_id[2]["result"]["tools"]] == [
    "phase", "verify", "verify_history", "audit_history", "write_operation"]
error, text = result(3)
assert error is True and "will not execute writes" in text
assert by_id[4]["error"]["code"] == -32601

error, text = result(5)
context = json.loads(text)["hookSpecificOutput"]["additionalContext"]
assert error is False and "SPECED" in context and "Module specs: 1" in context, text

error, text = result(6)
assert error is False and "0 失败" in text, text
error, text = result(7)
assert error is True and "SPEC.md" in text, text

error, text = result(8)
assert error is False and "历史证据校验通过" in text, text
error, text = result(9)
assert error is False and json.loads(text)["readOnly"] is True, text
error, text = result(10)
assert error is False and text.startswith("未验证"), text

error, text = result(11)
assert error is True and "absolute path" in text, text
error, text = result(12)
assert error is True and "Unknown tool" in text, text
PY
then
  ok "tools dispatch to their hooks and propagate hook failures"
else
  bad "tools dispatch to their hooks and propagate hook failures"
fi

if python3 - "$TMP/stdout" <<'PY'
import json, sys
for line in open(sys.argv[1], encoding="utf-8"):
    json.loads(line)
PY
then
  ok "stdout contains JSON-RPC only"
else
  bad "stdout contains JSON-RPC only"
fi

if test ! -e "$GOOD/.local" && test -z "$(git -C "$GOOD" status --porcelain --untracked-files=all -- .agent tasks)"; then
  ok "read-only tools leave the project unchanged"
else
  bad "read-only tools leave the project unchanged"
fi

if python3 - "$MANIFEST" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
assert manifest["manifest_version"] == "0.2"
assert manifest["name"] == "spec-guard"
# 描述只能宣称 Desktop 实际提供的只读工具；这些能力只在 Claude Code 与 Codex 中提供。
for absent in ("Proposal", "collaboration", "ticket", "ledger"):
    assert absent.lower() not in manifest["description"].lower(), absent
assert manifest["server"] == {
    "type": "node",
    "entry_point": "mcp/claude_desktop_server.mjs",
    "mcp_config": {"command": "node", "args": ["${__dirname}/mcp/claude_desktop_server.mjs"], "env": {}},
}
PY
then
  ok "Claude Desktop MCPB manifest points at the stdio server"
else
  bad "Claude Desktop MCPB manifest points at the stdio server"
fi

echo
echo "  总计 $PASS 通过 / $FAIL 失败"
test "$FAIL" -eq 0
