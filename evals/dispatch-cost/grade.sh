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
( cd "$HERE" && LEDGERLITE_REPO="$P" TZ=Asia/Shanghai PYTHONDONTWRITEBYTECODE=1 $PY -m unittest hidden.test_hidden 2>&1 | tail -3 )
echo "== cost =="
$PY -B "$REPO/plugins/spec-guard/hooks/module_cost_report.py" --project "$P" --prices "$HERE/prices.json" "$@" ledgerlite
