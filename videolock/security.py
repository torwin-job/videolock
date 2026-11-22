"""Password wipe + flock singleton."""
from __future__ import annotations

import fcntl
import os

from .logutil import log
from .paths import LOCKFILE

_lock_fd = None


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def read_lock_pid() -> int | None:
    try:
        raw = LOCKFILE.read_text().strip()
        return int(raw) if raw else None
    except Exception:
        return None


def clear_stale_lockfile() -> bool:
    """Remove lockfile if owner PID is dead. Returns True if cleared/absent."""
    pid = read_lock_pid()
    if pid is not None and pid_alive(pid):
        return False
    try:
        if LOCKFILE.exists():
            LOCKFILE.unlink()
            if pid is not None:
                log(f"cleared stale lockfile (dead pid {pid})")
        return True
    except OSError:
        return False


def wipe_bytearray(buf: bytearray) -> None:
    for i in range(len(buf)):
        buf[i] = 0
    buf.clear()


def acquire_singleton() -> bool:
    """Flock singleton; clears stale PID lockfiles once."""
    global _lock_fd
    for attempt in range(2):
        try:
            _lock_fd = open(LOCKFILE, "w")
            fcntl.flock(_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            _lock_fd.seek(0)
            _lock_fd.truncate()
            _lock_fd.write(str(os.getpid()))
            _lock_fd.flush()
            try:
                os.chmod(LOCKFILE, 0o600)
            except OSError:
                pass
            return True
        except OSError:
            try:
                if _lock_fd is not None:
                    _lock_fd.close()
            except Exception:
                pass
            _lock_fd = None
            if attempt == 0 and clear_stale_lockfile():
                continue
            return False
    return False
