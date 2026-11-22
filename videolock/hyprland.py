"""hyprctl helpers: layout reset / keymap / caps."""
from __future__ import annotations

import json
import os
import subprocess

from .logutil import log


def hyprctl(args: list[str], timeout: float = 1.5) -> str:
    try:
        r = subprocess.run(
            ["hyprctl", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if r.returncode != 0:
            return ""
        return (r.stdout or "").strip()
    except Exception:
        return ""


def reset_keyboard_layout() -> None:
    """Force primary layout (usually us) so password entry is not stuck on RU."""
    if os.environ.get("VIDEOLOCK_RESET_LAYOUT", "1") != "1":
        return
    out = hyprctl(["switchxkblayout", "all", "0"])
    log(f"reset layout → primary (all 0) {out!r}")


def active_keymap_raw() -> str:
    raw = hyprctl(["devices", "-j"])
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    keyboards = data.get("keyboards") or []
    main = next((k for k in keyboards if k.get("main")), None)
    kb = main or (keyboards[0] if keyboards else None)
    if not kb:
        return ""
    return str(kb.get("active_keymap") or kb.get("layout") or "")


def short_layout(keymap: str) -> str:
    n = (keymap or "").lower()
    if not n:
        return "?"
    if "russian" in n or n.startswith("ru") or ",ru" in n or n == "ru":
        return "RU"
    if "english" in n or "us" in n or n.startswith("en"):
        return "US"
    if "german" in n or n.startswith("de"):
        return "DE"
    if "french" in n or n.startswith("fr"):
        return "FR"
    if "ukrain" in n or n.startswith("ua") or n.startswith("uk"):
        return "UA"
    token = keymap.split(",")[0].strip()
    if "(" in token:
        token = token.split("(")[0].strip()
    return (token[:3] or "?").upper()


def caps_lock_on(fallback: bool = False) -> bool:
    try:
        from .gi_bootstrap import Gdk

        display = Gdk.Display.get_default()
        if display is None:
            return fallback
        seat = display.get_default_seat()
        if seat is None:
            return fallback
        kb = seat.get_keyboard()
        if kb is not None and hasattr(kb, "get_caps_lock_state"):
            return bool(kb.get_caps_lock_state())
    except Exception:
        pass
    return fallback
