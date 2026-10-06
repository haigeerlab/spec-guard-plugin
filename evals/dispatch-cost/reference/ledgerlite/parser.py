"""Read CSV lines ``date,account,amount,memo,category`` into Entry objects."""

import re

from .models import Entry
from .timeutil import parse_timestamp

_AMOUNT_RE = re.compile(r"([+-]?)([0-9]+)(?:\.([0-9]{1,2}))?")


def parse_amount(text):
    """Convert an amount string such as ``12.34`` to integer cents."""
    text = text.strip()
    if not text:
        raise ValueError("empty amount")
    match = _AMOUNT_RE.fullmatch(text)
    if not match:
        raise ValueError("invalid amount: %r" % (text,))
    sign, whole, frac = match.groups()
    cents = int(whole) * 100 + int((frac or "").ljust(2, "0"))
    return -cents if sign == "-" else cents


def parse_line(line, lineno=None):
    """Parse one CSV line into an Entry. Raises ValueError on bad input."""
    where = "line %d: " % lineno if lineno is not None else ""
    fields = line.rstrip("\r\n").split(",")
    if len(fields) != 5:
        raise ValueError(where + "expected 5 fields, got %d" % len(fields))
    date, account, amount, memo, category = (f.strip() for f in fields)
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
    try:
        return Entry(date, account, cents, memo, category)
    except ValueError as exc:
        raise ValueError(where + str(exc))


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
