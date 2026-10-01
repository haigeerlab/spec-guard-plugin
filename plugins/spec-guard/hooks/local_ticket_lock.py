"""Crash-releasing file locks shared by Local handoff and restore."""
from __future__ import annotations

import fcntl
import os
import stat
from pathlib import Path

from local_ticket_portability import InventoryError


MAGIC = b"spec-guard-flock-v1\n"


def acquire_lock(path: Path, busy_code: str) -> int:
    """Keep a private lock inode; closing the descriptor releases ownership."""
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
    except FileExistsError:
        try:
            descriptor = os.open(path, flags)
        except OSError as error:
            raise InventoryError(busy_code + ": lock file is unsafe") from error
        created = False
    except OSError as error:
        raise InventoryError(busy_code + ": lock file cannot be created") from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise InventoryError(busy_code + ": lock file is unsafe")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise InventoryError(busy_code + ": operation is already running") from error
        if created:
            os.write(descriptor, MAGIC)
            os.fsync(descriptor)
        elif os.read(descriptor, len(MAGIC) + 1) != MAGIC:
            raise InventoryError(busy_code + ": legacy or damaged lock needs manual review")
        current = os.stat(path, follow_symlinks=False)
        if current.st_ino != info.st_ino or current.st_dev != info.st_dev:
            raise InventoryError(busy_code + ": lock file changed")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise
