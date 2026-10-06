"""Timestamp helpers."""

import calendar
import re
from datetime import datetime, timezone

_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}):(\d{2})Z)?$"
)


def parse_timestamp(ts):
    """Parse ``2026-01-31T23:30:00Z`` or ``2026-01-31`` into an aware UTC datetime."""
    if not isinstance(ts, str):
        raise ValueError("timestamp must be a string")
    match = _TS_RE.match(ts.strip())
    if not match:
        raise ValueError("invalid timestamp: %r" % (ts,))
    parts = [int(p) if p is not None else 0 for p in match.groups()]
    try:
        return datetime(*parts, tzinfo=timezone.utc)
    except ValueError:
        raise ValueError("invalid timestamp: %r" % (ts,))


def month_key(ts):
    """Return the UTC ``YYYY-MM`` for a timestamp."""
    local = parse_timestamp(ts)
    return "%04d-%02d" % (local.year, local.month)


def days_in_month(year, month):
    """Number of days in the given month."""
    return calendar.monthrange(year, month)[1]


def to_iso(dt):
    """Format an aware datetime as ``YYYY-MM-DDTHH:MM:SSZ`` in UTC."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
