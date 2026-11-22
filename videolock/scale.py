"""HiDPI / density UI scale."""
from __future__ import annotations

import json
import os

from .hyprland import hyprctl


def ui_scale() -> float:
    """Logical UI scale for HiDPI / Hyprland fractional scale (0.7–2.5)."""
    env = os.environ.get("VIDEOLOCK_SCALE", "").strip()
    if env:
        try:
            return max(0.7, min(2.5, float(env)))
        except ValueError:
            pass
    raw = hyprctl(["monitors", "-j"])
    base = 1.0
    if raw:
        try:
            mons = json.loads(raw)
            scales = [float(m.get("scale") or 1.0) for m in mons if m]
            if scales:
                base = max(scales)
        except Exception:
            pass
    else:
        try:
            from .gi_bootstrap import Gdk

            display = Gdk.Display.get_default()
            if display is not None:
                mon = display.get_monitors().get_item(0)
                if mon is not None and hasattr(mon, "get_scale_factor"):
                    base = float(mon.get_scale_factor())
        except Exception:
            pass
    density = 0.95
    dens_env = os.environ.get("VIDEOLOCK_DENSITY", "").strip()
    if dens_env:
        try:
            density = max(0.7, min(1.2, float(dens_env)))
        except ValueError:
            pass
    return max(0.7, min(2.5, base * density))


def px(n: float, scale: float) -> str:
    return f"{max(1, int(round(n * scale)))}px"
