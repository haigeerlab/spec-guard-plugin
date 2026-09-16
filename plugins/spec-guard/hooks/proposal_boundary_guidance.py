"""Pure, non-blocking Proposal entry guidance at explicit module boundaries."""


REMINDER_BOUNDARIES = frozenset(("module-deliver", "module-advance"))
ENTRIES = ("intake", "review", "promotion-proof")
MAINLINE_ENTRIES = ENTRIES + ("mainline-candidates", "mainline-review",
                              "promotion-preflight")


class Guidance(object):
    def __init__(self, state, boundary=None, entries=()):
        self.state = state
        self.boundary = boundary
        self.entries = entries


def as_json(result):
    """Serialize only the stable boundary and entry identifiers."""
    data = {"state": result.state}
    if result.boundary is not None:
        data["boundary"] = result.boundary
    if result.entries:
        data["entries"] = list(result.entries)
    return data


def guide(boundary, mainline_declared=False):
    """Return a non-blocking reminder only at an explicit module boundary."""
    if not isinstance(boundary, str) or not boundary:
        return Guidance("invalid")
    if boundary in REMINDER_BOUNDARIES:
        entries = MAINLINE_ENTRIES if mainline_declared is True else ENTRIES
        return Guidance("reminder", boundary, entries)
    return Guidance("not-applicable", boundary)
