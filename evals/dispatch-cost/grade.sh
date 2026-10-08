#!/bin/bash
# 给一次运行判分并计价：隐藏测试（防止“便宜是因为活没干完”）+ module_cost_report.py。
# 用法：grade.sh <运行目录> [--json]          例：grade.sh "$RUNS/C-N1"
set -u
HERE="$(cd "$(dirname "$0")" && pwd -P)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)" || exit 2
P="${1:?usage: grade.sh <run-dir> [--json]}"; shift
P="$(cd "$P" && pwd -P)" || exit 2
PY="${PYTHON:-python3}"
echo "== hidden tests =="
# 只显示末尾三行，但保留隐藏测试自己的退出码：失败时先照常计价，最后以非零退出（审查 F10）。
( cd "$HERE" && LEDGERLITE_REPO="$P" TZ=Asia/Shanghai PYTHONDONTWRITEBYTECODE=1 $PY -m unittest hidden.test_hidden 2>&1 | tail -3
  exit "${PIPESTATUS[0]}" )
HIDDEN_RC=$?
echo "== cost =="
$PY -B "$REPO/plugins/spec-guard/hooks/module_cost_report.py" --project "$P" --prices "$HERE/prices.json" "$@" ledgerlite
COST_RC=$?
if [ "$HIDDEN_RC" -ne 0 ]; then
  echo "hidden tests failed (exit ${HIDDEN_RC}): this run did not finish the work" >&2
  exit 1
fi
exit "$COST_RC"
