# ledgerlite

A tiny bookkeeping library (pure standard library, Python 3.9+).

- `ledgerlite.models`   Entry / Account
- `ledgerlite.parser`   CSV `date,account,amount,memo` -> Entry objects
- `ledgerlite.ledger`   Ledger: add, entries, balance, entries_in_month
- `ledgerlite.report`   monthly_report text
- `ledgerlite.currency` fixed-rate conversion on integer minor units
- `ledgerlite.timeutil` timestamp parsing, month_key
- `ledgerlite.cli`      command line

```
python3 -m ledgerlite.cli report --csv data.csv --month 2026-01
python3 -m ledgerlite.cli balance --csv data.csv --account cash
python3 -m unittest discover -s tests -t .
```
