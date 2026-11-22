"""Append-only cache log (mode 0600)."""
from __future__ import annotations

import os
from datetime import datetime

from .paths import LOG


def log(msg: str) -> None:
    line = f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} {msg}"
    try:
        fd = os.open(str(LOG), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
