"""Where spec-guard keeps machine state: one root, one override, whole-directory fallback.

Every machine-level path the plugin writes comes from here (runtime-state-layout); the
file layout in docs/design.md lists them and scripts/check-state-paths.py keeps other home
paths out of the hooks.  This module only computes paths -- callers create directories
with their own permission rules.

A fallback is all or nothing: while `<root>/<name>` does not exist and the legacy directory
does, the legacy directory is used, so one kind of record never ends up split across two
directories.  Nothing here moves or deletes anything.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV = "SPEC_GUARD_STATE_DIR"


def legacy_root() -> Path:
    """Where two kinds of record lived before the root was unified (2026-10-08)."""
    return Path.home() / ".local" / "state" / "spec-guard"


LEGACY_NAMES = ("hosted-ticket-intents", "proposal-closeout")


def state_root() -> Path:
    override = os.environ.get(ENV)
    return Path(override) if override else Path.home() / ".spec-guard"


def state_dir(name: str, legacy: Path | None = None) -> Path:
    current = state_root() / name
    if legacy is not None and not current.exists() and legacy.exists():
        return legacy
    return current


def legacy_in_use() -> list[Path]:
    """Legacy directories the fallback is currently reading from."""
    return [legacy_root() / name for name in LEGACY_NAMES
            if state_dir(name, legacy_root() / name) == legacy_root() / name]
