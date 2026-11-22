"""Crash recover: kill hung locker + clear Hyprland crash overlay."""
from __future__ import annotations

import os
import signal
import time

from . import __version__
from .hyprland import hyprctl
from .paths import LOCKFILE
from .security import clear_stale_lockfile, pid_alive, read_lock_pid


def recover_session() -> int:
    print(f"videolock {__version__} — recover")
    pid = read_lock_pid()
    if pid is not None and pid_alive(pid):
        print(f"  signaling locker pid={pid} (SIGTERM)")
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            print(f"  SIGTERM failed: {e}")
        for _ in range(10):
            if not pid_alive(pid):
                break
            time.sleep(0.1)
        if pid_alive(pid):
            print(f"  SIGKILL pid={pid}")
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    elif pid is not None:
        print(f"  stale lockfile pid={pid} (not running)")
    else:
        print("  no live locker pid in lockfile")

    clear_stale_lockfile()
    try:
        if LOCKFILE.exists():
            LOCKFILE.unlink()
    except OSError:
        pass

    out = hyprctl(["eval", "hl.clear_crashed_lockscreen()"])
    if out:
        print(f"  clear_crashed_lockscreen: {out}")
    else:
        hyprctl(["dispatch", "forcerendererreload"])
        print("  attempted forcerendererreload (HyDE clear may be unavailable)")
    print("  recover done")
    return 0
