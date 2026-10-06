"""Read CSV lines ``date,account,amount,memo`` into Entry objects."""

import math

from .models import Entry
from .timeutil import parse_timestamp


def parse_amount(text):
    """Convert an amount string such as ``12.34`` to integer cents."""
    text = text.strip()
    if not text:
        raise ValueError("empty amount")
    try:
        value = float(text)
    except ValueError:
        raise ValueError("invalid amount: %r" % (text,))
    if not math.isfinite(value):
        raise ValueError("invalid amount: %r" % (text,))
    return int(value * 100)


def parse_line(line, lineno=None):
    """Parse one CSV line into an Entry. Raises ValueError on bad input."""
    where = "line %d: " % lineno if lineno is not None else ""
    fields = line.rstrip("\r\n").split(",", 3)
    if len(fields) != 4:
        raise ValueError(where + "expected 4 fields, got %d" % len(fields))
    date, account, amount, memo = (f.strip() for f in fields)
    try:
        parse_timestamp(date)
    except ValueError as exc:
        raise ValueError(where + str(exc))
    if not account:
        raise ValueError(where + "empty account")
    try:
        cents = parse_amount(amount)
    except ValueError as exc:
        raise ValueError(where + str(exc))
    return Entry(date, account, cents, memo)


def parse_lines(lines):
    """Parse an iterable of CSV lines; blank lines and ``#`` comments skip."""
    entries = []
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(parse_line(line, lineno))
    return entries


def parse_file(path):
    """Parse a CSV file on disk."""
    with open(path, "r", encoding="utf-8") as handle:
        return parse_lines(handle)
