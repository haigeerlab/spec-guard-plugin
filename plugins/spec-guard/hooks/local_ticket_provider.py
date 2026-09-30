"""Small JSON CLI transport for explicit GitHub/GitLab handoff targets."""
from __future__ import annotations

import json
import subprocess
from typing import Any, Callable

from local_ticket_portability import InventoryError


PAGE_SIZE = 100
MAX_PAGES = 50


def run_json(arguments: list[str], body: dict[str, Any] | None = None) -> Any:
    """Return decoded JSON without exposing CLI stderr or credentials."""
    try:
        result = subprocess.run(
            arguments, input=json.dumps(body) if body is not None else None,
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise InventoryError("provider-unavailable: API request did not complete") from error
    if result.returncode != 0:
        raise InventoryError("provider-unavailable: API request failed")
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise InventoryError("provider-unavailable: API returned invalid JSON") from error


def pages(fetch: Callable[[int], Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for number in range(1, MAX_PAGES + 1):
        batch = fetch(number)
        if not isinstance(batch, list) or len(batch) > PAGE_SIZE or any(
                not isinstance(item, dict) for item in batch):
            raise InventoryError("publication-uncertain: provider page is malformed")
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            return items
    raise InventoryError("publication-uncertain: provider pagination limit reached")
