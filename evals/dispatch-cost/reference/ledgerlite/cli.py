"""Command line interface.

    python3 -m ledgerlite.cli report --csv FILE --month 2026-01 [--category NAME]
    python3 -m ledgerlite.cli balance --csv FILE --account NAME [--category NAME]
"""

import argparse
import re
import sys

from .ledger import Ledger
from .parser import parse_file
from .report import format_cents, monthly_report


_MONTH_RE = re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])")


def _month(text):
    if not _MONTH_RE.fullmatch(text):
        raise argparse.ArgumentTypeError(
            "invalid month %r: expected YYYY-MM (01-12)" % (text,)
        )
    return text


def build_parser():
    parser = argparse.ArgumentParser(prog="ledgerlite")
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser("report", help="monthly report")
    rep.add_argument("--csv", required=True, help="CSV file path")
    rep.add_argument("--month", required=True, type=_month, help="month as YYYY-MM")
    rep.add_argument("--category", help="only count this category")

    bal = sub.add_parser("balance", help="balance of one account")
    bal.add_argument("--csv", required=True, help="CSV file path")
    bal.add_argument("--account", required=True, help="account name")
    bal.add_argument("--category", help="only count this category")
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
        print(monthly_report(ledger, year, month, args.category))
        return 0

    if args.command == "balance":
        print("%s: %s" % (args.account, format_cents(ledger.balance(args.account, args.category))))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
