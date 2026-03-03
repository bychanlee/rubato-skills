"""Advisory file locking for concurrent access safety.

Uses fcntl.flock() to provide exclusive locks on files being written.
Lock files are created as <path>.lock to avoid interfering with the actual files.
"""

from __future__ import annotations

import fcntl
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


@contextmanager
def locked_write(path: str | Path, timeout: float = 30.0) -> Generator[Path, None, None]:
    """Context manager that acquires an exclusive lock before yielding.

    Usage:
        with locked_write("calc_db/index.md") as p:
            # read, modify, write p safely
            ...

    The lock file is <path>.lock. It is NOT deleted after release
    (harmless empty file, avoids race on cleanup).
    """
    p = Path(path)
    lock_path = p.with_suffix(p.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_fd = open(lock_path, "w")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except (OSError, BlockingIOError):
            if time.monotonic() >= deadline:
                lock_fd.close()
                raise TimeoutError(f"Could not acquire lock on {lock_path} within {timeout}s")
            time.sleep(0.05)

    try:
        yield p
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
