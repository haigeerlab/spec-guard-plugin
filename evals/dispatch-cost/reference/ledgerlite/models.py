"""Data models for ledgerlite."""


class Account:
    """A named bucket that entries are posted to."""

    __slots__ = ("name",)

    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("account name must be a string")
        name = name.strip()
        if not name:
            raise ValueError("account name must not be empty")
        if "," in name:
            raise ValueError("account name must not contain a comma")
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, Account):
            return NotImplemented
        return self.name == other.name

    def __hash__(self):
        return hash(("Account", self.name))

    def __repr__(self):
        return "Account(%r)" % (self.name,)

    def __str__(self):
        return self.name


class Entry:
    """One bookkeeping line.

    date          ISO timestamp string such as ``2026-01-31T23:30:00Z`` or a
                  plain ``YYYY-MM-DD`` date (midnight UTC).
    account       account name (non-empty string, no commas)
    amount_cents  signed integer number of cents
    memo          free text (no commas)
    category      required non-empty string (no commas)
    """

    __slots__ = ("date", "account", "amount_cents", "memo", "category")

    def __init__(self, date, account, amount_cents, memo, category):
        if not isinstance(date, str) or not date.strip():
            raise ValueError("entry date must be a non-empty string")
        if not isinstance(account, str) or not account.strip():
            raise ValueError("entry account must be a non-empty string")
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
            raise TypeError("amount_cents must be an int")
        if not isinstance(memo, str):
            raise TypeError("memo must be a string")
        if not isinstance(category, str):
            raise TypeError("category must be a string")
        category = category.strip()
        if not category:
            raise ValueError("category must not be empty")
        if "," in category:
            raise ValueError("category must not contain a comma")
        self.date = date.strip()
        self.account = account.strip()
        self.amount_cents = amount_cents
        self.memo = memo.strip()
        self.category = category

    def as_tuple(self):
        return (self.date, self.account, self.amount_cents, self.memo, self.category)

    def __eq__(self, other):
        if not isinstance(other, Entry):
            return NotImplemented
        return self.as_tuple() == other.as_tuple()

    def __hash__(self):
        return hash(self.as_tuple())

    def __repr__(self):
        return "Entry(date=%r, account=%r, amount_cents=%r, memo=%r, category=%r)" % self.as_tuple()
