"""Monthly report rendering."""


def format_cents(cents):
    """Format integer cents as a plain decimal string, e.g. -5 -> '-0.05'."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return "%s%d.%02d" % (sign, whole, frac)


def _fmt(value):
    if value == 0:
        value = 0.0
    return "%.2f" % value


def monthly_report(ledger, year, month):
    """Per-account totals and a grand total for one month, as text."""
    per_account = {}
    for entry in ledger.entries_in_month(year, month):
        per_account.setdefault(entry.account, []).append(entry.amount_cents / 100.0)

    lines = ["Report %04d-%02d" % (year, month)]
    grand = 0.0
    for name in sorted(per_account):
        total = round(sum(per_account[name]), 2)
        grand += total
        lines.append("%s: %s" % (name, _fmt(total)))
    lines.append("TOTAL: %s" % _fmt(round(grand, 2)))
    return "\n".join(lines)
