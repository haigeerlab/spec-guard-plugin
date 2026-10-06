# Hidden grading tests

Run from the `joint/` directory (the parent of `hidden/`):

```
LEDGERLITE_REPO=<repo> TZ=Asia/Shanghai /usr/bin/python3 -m unittest hidden/test_hidden.py
```

Run one task: `... -m unittest hidden.test_hidden.Task3Rounding`
(classes: Task1FormatAmount, Task2CliMonth, Task3Rounding, Task4Category, Task5UtcMonths).

Tests drive the repo through subprocesses (`python3 -m ledgerlite.cli`, `python3 -c`), setting TZ
themselves, so the outer TZ does not matter. They read `../defects/defect_a.csv`.
They assume the final state of all five tasks (5-column CSV).
