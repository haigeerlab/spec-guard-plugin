#!/usr/bin/env python3
"""Read-only selector for the one active collaboration mailbox per new session.

No command in this module creates a marker or changes either transport. A
separate explicit cutover must write the private marker only after old-mail
preflight; until then its absence means the existing XATS entry.
"""
import argparse
import json
import os
from pathlib import Path
import stat
from typing import Any, Sequence

from collaboration_runtime import default_config_dir
from native_collaboration_runtime import BRIDGE_COMMIT, default_root, status as native_status


def default_marker() -> Path:
    return default_config_dir() / "transport.json"


def selected_backend(marker: Path, native_root: Path) -> dict[str, Any]:
    """Fail closed instead of silently returning to XATS after native activation."""
    marker = Path(marker)
    if not marker.exists() and not marker.is_symlink():
        return {"backend": "xats"}
    try:
        metadata = marker.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600):
            raise ValueError("transport marker must be an owner-only regular file")
        value = json.loads(marker.read_text(encoding="utf-8"))
        if value != {"backend": "native", "commit": BRIDGE_COMMIT}:
            raise ValueError("transport marker does not name the audited native runtime")
    except (OSError, UnicodeError, ValueError) as error:
        return {"backend": "invalid", "diagnostic": str(error)}
    native = native_status(native_root)
    if native["state"] != "ready":
        return {"backend": "unavailable", "diagnostic": "native runtime is not ready"}
    return {"backend": "native"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marker", type=Path, default=default_marker())
    parser.add_argument("--native-root", type=Path, default=default_root())
    args = parser.parse_args(argv)
    result = selected_backend(args.marker, args.native_root)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["backend"] in ("xats", "native") else 1


if __name__ == "__main__":
    raise SystemExit(main())
