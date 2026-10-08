#!/bin/bash
# 证明种子有效：自带测试全绿、隐藏测试在种子上全红而在参考实现上全绿、缺陷 A 恰好差 0.01。
J="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
SEED="$J/seed"
rc=0

echo "== 1. seed tests (TZ=Asia/Shanghai, $PY) =="
( cd "$SEED" && TZ=Asia/Shanghai $PY -m unittest discover -s tests -t . 2>&1 | tail -4 ) || rc=1
( cd "$SEED" && TZ=Asia/Shanghai $PY -m unittest discover -s tests -t . >/dev/null 2>&1 ) || { echo "FAIL: seed tests not green"; rc=1; }

echo "== 2. hidden tests against untouched seed (each class must FAIL) =="
for cls in Task1FormatAmount Task2CliMonth Task3Rounding Task4Category Task5UtcMonths; do
  if ( cd "$J" && LEDGERLITE_REPO="$SEED" TZ=Asia/Shanghai $PY -m unittest hidden.test_hidden.$cls >/dev/null 2>&1 ); then
    echo "  $cls: PASS (unexpected!)"; rc=1
  else
    echo "  $cls: FAIL (expected)"
  fi
done

echo "== 2b. hidden tests against reference (must PASS) =="
( cd "$J" && LEDGERLITE_REPO="$J/reference" TZ=Asia/Shanghai $PY -m unittest hidden.test_hidden >/dev/null 2>&1 ) \
  && echo "  reference: PASS" || { echo "  reference: FAIL"; rc=1; }

echo "== 3. defect A at seed =="
out=$( cd "$SEED" && TZ=UTC $PY -m ledgerlite.cli report --csv "$J/defects/defect_a.csv" --month 2026-01 )
echo "$out" | sed 's/^/  /'
got=$(echo "$out" | sed -n 's/^TOTAL: //p')
true_total=$($PY - "$J/defects/defect_a.csv" <<'PYEOF'
import sys
from decimal import Decimal
print(sum(Decimal(l.split(",")[2]) for l in open(sys.argv[1]) if l.strip()))
PYEOF
)
diff=$($PY -c "from decimal import Decimal as D; print(D('$true_total')-D('$got'))")
echo "  true=$true_total reported=$got diff=$diff"
[ "$diff" = "0.01" ] || { echo "FAIL: diff is not exactly 0.01"; rc=1; }

echo "== 4. defect B at seed =="
for tz in Asia/Shanghai America/New_York UTC; do
  r=$( cd "$SEED" && TZ=$tz $PY -c "from ledgerlite.timeutil import month_key as m; print(m('2026-01-31T23:30:00Z'), m('2026-02-01T00:00:00Z'))" )
  echo "  TZ=$tz -> $r"
done

echo "== 5. line counts (seed, excl .git) =="
( cd "$SEED" && find . -type f -not -path './.git/*' | sort | xargs wc -l | tail -1 | sed 's/^/  all files: /'
  find . -name '*.py' -not -path './.git/*' -print0 | xargs -0 wc -l | tail -1 | sed 's/^/  python only: /' )

[ $rc -eq 0 ] && echo "VERIFY OK" || echo "VERIFY FAILED"
exit $rc
