"""Crash-releasing file locks shared by Local handoff and restore."""
from __future__ import annotations

import fcntl
import os
import stat
import tempfile
from pathlib import Path

from local_ticket_inventory import InventoryError


MAGIC = b"spec-guard-flock-v1\n"


def acquire_lock(path: Path, busy_code: str) -> int:
    """Publish an initialized private inode, then lock it until descriptor close."""
    path = Path(path)
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        try:
            temporary_fd, temporary = tempfile.mkstemp(
                prefix=".spec-guard-lock-", dir=path.parent)
            try:
                os.write(temporary_fd, MAGIC)
                os.fsync(temporary_fd)
                try:
                    os.link(temporary, path)
                except FileExistsError:
                    pass
            finally:
                os.close(temporary_fd)
                os.unlink(temporary)
            descriptor = os.open(path, flags)
        except OSError as error:
            raise InventoryError(busy_code + ": lock file cannot be created") from error
    except OSError as error:
        raise InventoryError(busy_code + ": lock file is unsafe") from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise InventoryError(busy_code + ": lock file is unsafe")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise InventoryError(busy_code + ": operation is already running") from error
        if os.read(descriptor, len(MAGIC) + 1) != MAGIC:
            raise InventoryError(busy_code + ": legacy or damaged lock needs manual review")
        current = os.stat(path, follow_symlinks=False)
        if current.st_ino != info.st_ino or current.st_dev != info.st_dev:
            raise InventoryError(busy_code + ": lock file changed")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise
