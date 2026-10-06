"""Command line interface.

    python3 -m ledgerlite.cli report --csv FILE --month 2026-01
    python3 -m ledgerlite.cli balance --csv FILE --account NAME
"""

import argparse
import sys

from .ledger import Ledger
from .parser import parse_file
from .report import format_cents, monthly_report


def build_parser():
    parser = argparse.ArgumentParser(prog="ledgerlite")
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser("report", help="monthly report")
    rep.add_argument("--csv", required=True, help="CSV file path")
    rep.add_argument("--month", required=True, help="month as YYYY-MM")

    bal = sub.add_parser("balance", help="balance of one account")
    bal.add_argument("--csv", required=True, help="CSV file path")
    bal.add_argument("--account", required=True, help="account name")
    return parser


def _load(path):
    try:
        return Ledger(parse_file(path))
    except OSError as exc:
        print("error: cannot read %s: %s" % (path, exc.strerror or exc), file=sys.stderr)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
    return None


def main(argv=None):
    args = build_parser().parse_args(argv)
    ledger = _load(args.csv)
    if ledger is None:
        return 1

    if args.command == "report":
        year_text, month_text = args.month.split("-")
        year, month = int(year_text), int(month_text)
        print(monthly_report(ledger, year, month))
        return 0

    if args.command == "balance":
        print("%s: %s" % (args.account, format_cents(ledger.balance(args.account))))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
