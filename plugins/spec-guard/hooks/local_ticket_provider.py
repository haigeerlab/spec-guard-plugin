"""Small JSON CLI transport for explicit GitHub/GitLab handoff targets."""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Callable

from local_ticket_inventory import InventoryError


PAGE_SIZE = 100
MAX_PAGES = 50
DEFINITE_REJECTIONS = {400, 401, 403, 404, 405, 410, 413, 414, 422}


class ProviderRejected(InventoryError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"provider-rejected: API returned HTTP {status_code}")


def _included_response(stdout: str) -> tuple[int | None, str]:
    normalized = stdout.replace("\r\n", "\n")
    header, separator, payload = normalized.partition("\n\n")
    match = re.match(r"^HTTP/\S+\s+(\d{3})(?:\s|$)", header)
    return (int(match.group(1)), payload) if match and separator else (None, stdout)


def run_json(arguments: list[str], body: dict[str, Any] | None = None) -> Any:
    """Return decoded JSON without exposing CLI stderr or credentials."""
    command = [*arguments, "--include"] if body is not None else arguments
    try:
        result = subprocess.run(
            command, input=json.dumps(body) if body is not None else None,
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise InventoryError("provider-unavailable: API request did not complete") from error
    status, payload = _included_response(result.stdout) if body is not None else (None, result.stdout)
    if result.returncode != 0:
        if status in DEFINITE_REJECTIONS:
            raise ProviderRejected(status)
        raise InventoryError("provider-unavailable: API request failed")
    try:
        return json.loads(payload)
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
