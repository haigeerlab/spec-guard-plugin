# Plan: ledgerlite

## Overview

对 ledgerlite 记账库的五项修改与修复，细节与示例见 `spec/ledgerlite.md`。
任务按依赖顺序排列；每个任务单独提交（一个 task 一条 commit），验证全绿后再进入下一个。

## Architecture Decisions

- 金额全程使用整数分，不经过浮点。
- 月份按 UTC 计算，不依赖运行机器的本地时区。
- 不引入第三方依赖，仅标准库，兼容 Python 3.9。
- Task 4 改动面最广（模型、解析、记账、报表、cli、测试），放在 Task 3 之后，
  避免在两处同时调整金额与分类逻辑。

## Task 1：currency.format_amount

**Description:** 在货币模块新增金额格式化函数，按 spec 示例输出带符号、千位分隔的字符串。

**Acceptance criteria:**
- `format_amount(123456, "USD") == "$1,234.56"`，`format_amount(-5, "EUR") == "-€0.05"`
- JPY 无小数；零不带符号；未知币种抛 `ValueError`；非 int 抛 `TypeError`
- spec Task 1 表格中的每个示例都成立

**Verification:** `python3 -m unittest discover -s tests -t .`，新增测试覆盖表格中全部示例。

**Dependencies:** 无

**Files likely touched:** `ledgerlite/currency.py`, `tests/test_currency.py`

**Estimated scope:** Small

## Task 2：cli 校验 --month

**Description:** `report` 的 `--month` 严格校验为 `YYYY-MM`，非法时 stderr 报错并以退出码 2 退出。

**Acceptance criteria:**
- `2026-13`、`2026-00`、`26-01`、`2026-1`、`abc`、空串均退出码 2，stderr 有清晰信息，无 traceback
- 校验先于读取 CSV
- 合法值行为不变

**Verification:** 新增 cli 测试覆盖上述非法值与一个合法值；全量测试通过。

**Dependencies:** 无

**Files likely touched:** `ledgerlite/cli.py`, `tests/test_cli.py`

**Estimated scope:** Small

## Task 3：修复月报合计与逐笔之和差 1 分

**Description:** 月报合计与逐笔金额之和差 1 分。先复现（spec Task 3 的 6 笔输入，期望 37.79），
定位误差来源，再修复，使任意合法金额输入都精确。

**Acceptance criteria:**
- spec Task 3 的复现输入给出 `TOTAL: 37.79`，`cash: 17.54`，`bank: 20.25`
- 小数位超过 2 位、科学计数法、`nan` 等非法输入抛带行号的 `ValueError`，CLI 退出码 1
- `balance` 同样精确

**Verification:** 新增回归测试（含复现输入与至少两组容易产生浮点误差的金额）先红后绿；全量测试通过。

**Dependencies:** 无

**Files likely touched:** 需定位

**Estimated scope:** Medium

## Task 4：Entry 增加必填字段 category

**Description:** 为 Entry 增加必填的 `category`，CSV 增加第 5 列，并贯通解析、记账（按分类余额）、
报表（分类小计行）、cli（`--category` 过滤）与全部测试。

**Acceptance criteria:**
- `Entry(date, account, amount_cents, memo, category)`，缺少 category 抛 `TypeError`
- CSV 每行恰好 5 个字段，否则带行号的 `ValueError`
- `Ledger.balance(account, category=None)`、`Ledger.entries(account=None, category=None)`、`Ledger.categories()`
- 月报输出含缩进两空格的分类小计行，格式与 spec 示例逐字一致
- `report` 与 `balance` 支持 `--category`
- 既有测试全部更新并通过，README 同步

**Verification:** `python3 -m unittest discover -s tests -t .` 全绿；手工用 spec 示例数据跑 `report`。

**Dependencies:** Task 3

**Files likely touched:** `ledgerlite/models.py`, `ledgerlite/parser.py`, `ledgerlite/ledger.py`,
`ledgerlite/report.py`, `ledgerlite/cli.py`, `tests/*.py`, `README.md`

**Estimated scope:** Medium

## Task 5：修复月末流水被归到下个月

**Description:** 月份应为 UTC 月份。`TZ=Asia/Shanghai` 下，`2026-01-31T23:30:00Z` 的流水当前被归入二月，
需修复，使结果与运行机器时区无关。

**Acceptance criteria:**
- `TZ=Asia/Shanghai` 下 `2026-01-31T23:30:00Z` 属于 `2026-01`，且出现在 1 月月报、不出现在 2 月月报
- spec Task 5 边界表中的时间戳在任何时区下结果一致
- `TZ=America/New_York`（含夏令时切换日）下同样成立

**Verification:** 新增测试在测试内以子进程设置不同 `TZ` 值运行；全量测试通过。

**Dependencies:** 无

**Files likely touched:** 需定位

**Estimated scope:** Medium

## Checkpoint

- [ ] 全量测试通过（`TZ=Asia/Shanghai` 与默认时区各跑一次）
- [ ] 月报端到端与 spec Task 4 示例一致
