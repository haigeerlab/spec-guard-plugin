"""Local handoff's view of the shared GitHub/GitLab transport in hosted_ticket_provider.

The transport, page limit and write verdict live there; this module only keeps the
error vocabulary the Local publisher branches on (`InventoryError`, its own
`ProviderRejected`, `publication-uncertain` for an incomplete listing).
"""
from __future__ import annotations

from typing import Any, Callable

import hosted_ticket_provider as shared
from hosted_ticket_provider import MAX_PAGES, PAGE_SIZE  # noqa: F401 - re-exported
from local_ticket_inventory import InventoryError


# Shared messages whose Local wording differs; the prefix is what callers branch on.
_LOCAL_WORDING = {
    "provider-unavailable: malformed page": "publication-uncertain: provider page is malformed",
    "provider-unavailable: pagination limit reached":
        "publication-uncertain: provider pagination limit reached",
    "comment-marker-ambiguous: marker is in private note":
        "conflict: Local marker is in an internal GitLab note",
}
_LOCAL_PREFIX = {"target-invalid": "provider-unsupported", "target-unknown": "provider-unavailable"}


class ProviderRejected(InventoryError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"provider-rejected: API returned HTTP {status_code}")


def call(function: Callable[..., Any], *arguments: Any) -> Any:
    """Run one shared-transport step, speaking the Local error vocabulary."""
    try:
        return function(*arguments)
    except shared.ProviderRejected as error:
        raise ProviderRejected(error.status_code) from error
    except shared.HostedTicketError as error:
        message = str(error)
        code, _, detail = message.partition(": ")
        message = _LOCAL_WORDING.get(message) or (
            _LOCAL_PREFIX[code] + ": " + detail if code in _LOCAL_PREFIX else message)
        raise InventoryError(message) from error


def run_json(arguments: list[str], body: dict[str, Any] | None = None) -> Any:
    """Read, or write when a body is given, through the shared transport."""
    if body is None:
        return call(shared.run_json, arguments)
    return call(shared.run_write_json, arguments, body)


def pages(fetch: Callable[[int], Any]) -> list[dict[str, Any]]:
    return call(shared.pages, fetch)


def split(runner: Callable[[list[str], dict[str, Any] | None], Any] | None):
    """A Local runner `(argv, body)` as the shared client's separate reader and writer."""
    if runner is None:
        return shared.run_json, shared.run_write_json
    return (lambda arguments: runner(arguments, None),
            lambda arguments, body: runner(arguments, body))
