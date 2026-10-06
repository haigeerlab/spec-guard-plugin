"""In-memory ledger."""

from .models import Entry
from .timeutil import month_key


class Ledger:
    """A collection of entries with simple queries."""

    def __init__(self, entries=None):
        self._entries = []
        if entries:
            self.extend(entries)

    def add(self, entry):
        if not isinstance(entry, Entry):
            raise TypeError("Ledger.add expects an Entry")
        self._entries.append(entry)

    def extend(self, entries):
        for entry in entries:
            self.add(entry)

    def __len__(self):
        return len(self._entries)

    def entries(self, account=None, category=None):
        """All entries in insertion order, optionally filtered by account and/or category."""
        return [
            e for e in self._entries
            if (account is None or e.account == account)
            and (category is None or e.category == category)
        ]

    def categories(self):
        """Sorted list of category names that have at least one entry."""
        return sorted({e.category for e in self._entries})

    def accounts(self):
        """Sorted list of account names that have at least one entry."""
        return sorted({e.account for e in self._entries})

    def balance(self, account, category=None):
        """Sum of one account's entries (optionally one category), in integer cents."""
        return sum(e.amount_cents for e in self.entries(account, category))

    def total(self):
        """Sum of every entry, in integer cents."""
        return sum(e.amount_cents for e in self._entries)

    def entries_in_month(self, year, month):
        """Entries whose date falls in the given (year, month)."""
        key = "%04d-%02d" % (year, month)
        return [e for e in self._entries if month_key(e.date) == key]
