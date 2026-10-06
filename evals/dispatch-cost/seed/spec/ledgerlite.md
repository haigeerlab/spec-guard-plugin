# Spec: ledgerlite

## Objective

对记账库 ledgerlite 做五项修改与修复。本 spec 把每项的验收标准、边界情况与示例写全，
实现者不需要再向任何人提问；spec 未提及的既有行为保持不变。全部任务完成后，
`python3 -m unittest discover -s tests -t .` 必须全绿（含新增与更新的测试）。

通用约定：

- 金额一律用整数分（cents）；展示用两位小数的十进制字符串，负数前缀 `-`，零显示 `0.00`。
- 仅用 Python 3 标准库，需在 Python 3.9 运行。
- 月份按 UTC 月份计算（见 Task 5）。

## Task 1：currency.format_amount

新增 `currency.format_amount(cents: int, code: str) -> str`。

- 输入 `cents` 是该币种最小单位的整数（USD/EUR/GBP 为分，JPY 为日元整数）。
- 符号：USD `$`，EUR `€`，GBP `£`，JPY `¥`。
- 千位分隔用英文逗号；USD/EUR/GBP 固定两位小数；JPY 无小数。
- 负数把 `-` 放在货币符号之前；零不带符号。
- 未知币种代码抛 `ValueError`；`cents` 不是 int（含 bool、float）抛 `TypeError`。

示例：

| 调用 | 结果 |
| --- | --- |
| `format_amount(123456, "USD")` | `"$1,234.56"` |
| `format_amount(-5, "EUR")` | `"-€0.05"` |
| `format_amount(0, "GBP")` | `"£0.00"` |
| `format_amount(1234567, "JPY")` | `"¥1,234,567"` |
| `format_amount(-5, "JPY")` | `"-¥5"` |
| `format_amount(100000000, "USD")` | `"$1,000,000.00"` |
| `format_amount(1, "XXX")` | 抛 `ValueError` |
| `format_amount(1.5, "USD")` | 抛 `TypeError` |

## Task 2：cli 校验 --month

`report` 子命令的 `--month` 必须严格是 `YYYY-MM`：恰好 4 位数字年份、连字符、恰好 2 位数字月份，
月份范围 `01`–`12`。

- 非法值（例如 `2026-13`、`2026-00`、`26-01`、`2026-1`、`2026/01`、`abc`、空字符串）：
  向 stderr 打印一行清晰的错误信息（包含出错的值），stdout 不输出，进程退出码为 `2`；
  不得出现 Python traceback。
- 合法值行为不变，退出码 `0`。
- 该校验发生在读取 CSV 之前：即使 `--csv` 文件不存在，非法 `--month` 也以退出码 `2` 结束。

## Task 3：月报合计与逐笔之和差 1 分

症状：输入某些金额时，月报的合计与这些流水逐笔金额之和差 1 分（0.01）。
复现输入（同一月内 6 笔，账户 cash 与 bank）：

```
2026-01-05T12:00:00Z,cash,0.29,coffee
2026-01-09T12:00:00Z,cash,12.50,lunch
2026-01-12T12:00:00Z,bank,19.00,fee
2026-01-18T12:00:00Z,bank,1.25,interest
2026-01-22T12:00:00Z,cash,7.75,market
2026-01-27T12:00:00Z,cash,-3.00,refund
```

逐笔之和为 37.79，月报却给出别的数字。期望的正确行为：

- 任意输入下，各账户小计与总计都精确等于相应流水十进制金额之和，不允许任何 1 分误差。
- 金额字符串允许：可选的 `+`/`-` 号、整数部分、可选的 1 或 2 位小数（`12`、`7.5`、`0.29`、`-3.00`）。
- 超过 2 位小数（`1.005`）、科学计数法（`1e3`）、`nan`/`inf`、空串、缺少整数部分（`.5`）、
  缺少小数数字（`5.`）一律视为非法输入，抛出带行号的 `ValueError`，CLI 以退出码 `1` 报错。
- 余额查询（`balance`）同样必须精确。
- 报表输出格式不变：

```
Report 2026-01
bank: 20.25
cash: 17.54
TOTAL: 37.79
```

## Task 4：Entry 增加必填字段 category

- `Entry(date, account, amount_cents, memo, category)`：`category` 是第 5 个位置参数，**必填**，
  不提供时抛 `TypeError`；必须是非空字符串（去除首尾空白后），不得含逗号，否则 `ValueError`
  （传入非字符串抛 `TypeError`）。
- CSV 新格式 `date,account,amount,memo,category`，每行恰好 5 个字段；字段数不是 5（含旧的 4 字段行）
  一律 `ValueError`，错误信息带行号。memo 与 category 都不得含逗号。
- `Ledger.balance(account, category=None)`：给定 category 时只累计该分类的流水。
  `Ledger.entries(account=None, category=None)`：两个过滤条件可同时使用（取交集）。
  `Ledger.categories()` 返回排序后的分类名列表。
- 月报在每个账户行之后，增加该账户各分类的小计行：缩进两个空格，格式 `  分类: 金额`，
  按分类名升序。示例：

```
Report 2026-01
bank: 20.25
  fees: 19.00
  interest: 1.25
cash: 17.54
  food: 9.54
  rent: 8.00
TOTAL: 37.79
```

- cli：`report` 与 `balance` 都新增可选参数 `--category NAME`。给出时，只统计该分类的流水
  （报表的账户行、分类行与 TOTAL 都只含该分类；`balance` 输出该账户该分类的余额，
  格式仍为 `NAME: 金额`）。分类名区分大小写；没有匹配流水时输出相应的 `0.00` / `TOTAL: 0.00`，退出码 `0`。
- 所有既有测试与示例数据同步更新为 5 字段/5 参数形式，README 同步。

## Task 5：月末流水被归到下个月

规则：**月份就是 UTC 月份**。流水时间戳按其 UTC 时间取年月，不受运行机器时区（含 `TZ` 环境变量）影响。
纯日期 `YYYY-MM-DD` 视为当天 UTC 零点。`timeutil.month_key(ts)` 返回 `"YYYY-MM"`，
`Ledger.entries_in_month(year, month)` 与月报都必须遵守同一规则。

失败用例（当前行为错误）：设 `TZ=Asia/Shanghai`，时间戳 `2026-01-31T23:30:00Z` 的流水必须属于
2026 年 1 月（`month_key` 为 `"2026-01"`，且出现在 `--month 2026-01` 的月报里、不出现在 `--month 2026-02` 的月报里）。

补充边界（同一规则的推论，不是新规则）：

| 时间戳 | 任何时区下 month_key |
| --- | --- |
| `2025-12-31T23:59:59Z` | `2025-12` |
| `2026-02-01T00:00:00Z` | `2026-02` |
| `2026-01-31` | `2026-01` |

## Checkpoint

全量测试通过；用 Task 3 的复现输入加上 Task 4 的分类列，`report` 输出与 Task 4 示例一致；
在 `TZ=Asia/Shanghai` 与 `TZ=America/New_York` 下结果相同。

## 补充约定（消除歧义，实现时照此执行，不需要再确认）

- Task 1：`cents` 不是 `int` 时抛 `TypeError`，先于币种检查；币种未知抛 `ValueError`。
- Task 2：`--month` 在读取 CSV 之前校验（参数解析阶段即可），非法时 stderr 给出含该值的错误信息，退出码 `2`；
  只接受 ASCII 数字形式的 `YYYY-MM`，`MM` 为 `01`–`12`。
- Task 3：金额字段先去除首尾空白再校验，只接受 `-?\d+(\.\d{1,2})?` 形式。
- Task 4：`Entry` 的 5 个参数全部必填、按位置顺序（`memo` 不再有默认值）；`--category` 过滤时，没有匹配流水的账户
  不出现在报表中。
- Task 5：月份取 UTC 时间的年和月，任何地方都不做本地时区转换。
