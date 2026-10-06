"""Monthly report rendering."""


def format_cents(cents):
    """Format integer cents as a plain decimal string, e.g. -5 -> '-0.05'."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return "%s%d.%02d" % (sign, whole, frac)


def monthly_report(ledger, year, month, category=None):
    """Per-account totals with per-category subtotals and a grand total, as text."""
    per_account = {}
    for entry in ledger.entries_in_month(year, month):
        if category is not None and entry.category != category:
            continue
        cats = per_account.setdefault(entry.account, {})
        cats[entry.category] = cats.get(entry.category, 0) + entry.amount_cents

    lines = ["Report %04d-%02d" % (year, month)]
    grand = 0
    for name in sorted(per_account):
        cats = per_account[name]
        total = sum(cats.values())
        grand += total
        lines.append("%s: %s" % (name, format_cents(total)))
        for cat in sorted(cats):
            lines.append("  %s: %s" % (cat, format_cents(cats[cat])))
    lines.append("TOTAL: %s" % format_cents(grand))
    return "\n".join(lines)
