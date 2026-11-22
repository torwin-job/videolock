"""Display (Pixelon) + UI (Cyrillic-capable mono) font stacks."""
from __future__ import annotations

import os
import subprocess

_FONT_AVAIL_CACHE: dict[str, bool] = {}


def font_available(family: str) -> bool:
    key = family.lower()
    if key in _FONT_AVAIL_CACHE:
        return _FONT_AVAIL_CACHE[key]
    ok = False
    try:
        r = subprocess.run(
            ["fc-list", "-q", f"{family}:family"],
            capture_output=True,
            timeout=1.0,
            check=False,
        )
        ok = r.returncode == 0
    except Exception:
        ok = False
    _FONT_AVAIL_CACHE[key] = ok
    return ok


def quote_font(name: str) -> str:
    return f'"{name}"'


def font_stack() -> str:
    """Display/pixel stack — clock & password dots (Latin/digits)."""
    custom = os.environ.get("VIDEOLOCK_FONT", "").strip()
    if custom:
        return f'{quote_font(custom)}, "Pixelon", monospace'
    return '"Pixelon", "pixelon", "ArcadeClassic", monospace'


def ui_font_stack() -> str:
    """UI stack with Cyrillic — Pixelon has no RU glyphs."""
    custom = os.environ.get("VIDEOLOCK_UI_FONT", "").strip()
    if custom:
        return f'{quote_font(custom)}, "DejaVu Sans Mono", monospace'
    for name in (
        "JetBrainsMono Nerd Font",
        "JetBrainsMonoNL Nerd Font",
        "Maple Mono",
        "CaskaydiaCove Nerd Font",
        "Adwaita Mono",
        "DejaVu Sans Mono",
        "Noto Sans Mono",
    ):
        if font_available(name):
            return f'{quote_font(name)}, "DejaVu Sans Mono", monospace'
    return '"DejaVu Sans Mono", "Noto Sans Mono", monospace'
