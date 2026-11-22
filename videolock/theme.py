"""Wallbash / default color theme."""
from __future__ import annotations

import os
from pathlib import Path

from .logutil import log


def parse_wallbash_dcol(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or "=" not in line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k.startswith("dcol_") and v and "rgba" not in v.lower():
                out[k] = v if v.startswith("#") else f"#{v}"
    except OSError:
        pass
    return out


def wallbash_theme() -> dict[str, str]:
    """Pull accent/panel colors from HyDE wallbash (~/.cache/hyde/wall.dcol)."""
    defaults = {
        "bg": "#0b1020",
        "panel": "rgba(17,22,40,0.62)",
        "border": "rgba(120,160,255,0.35)",
        "dots_bg": "rgba(12,16,28,0.92)",
        "dots_border": "rgba(120,160,255,0.55)",
        "clock": "#e8eeff",
        "date": "#b8c4e0",
        "user": "#89b4fa",
        "dots": "#e8eeff",
        "error": "#f38ba8",
        "hint": "#7f8aad",
        "status": "#a6adc8",
        "accent": "#89b4fa",
        "btn_bg": "rgba(17,22,40,0.85)",
        "btn_fg": "#e8eeff",
        "warn": "#f9e2af",
        "caps": "#fab387",
    }
    if os.environ.get("VIDEOLOCK_WALLBASH", "1") == "0":
        return defaults
    env = os.environ.get("VIDEOLOCK_WALLBASH_FILE", "").strip()
    candidates = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend(
        [
            Path.home() / ".cache/hyde/wall.dcol",
            Path.home() / ".cache/hyde/wallbash/colors.inc",
        ]
    )
    dcol: dict[str, str] = {}
    for p in candidates:
        if p.is_file():
            dcol = parse_wallbash_dcol(p)
            if dcol:
                log(f"wallbash theme from {p}")
                break
    if not dcol:
        return defaults

    def hex_rgba(h: str, a: float) -> str:
        h = h.lstrip("#")
        if len(h) != 6:
            return defaults["panel"]
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{a})"

    pry = dcol.get("dcol_pry1") or dcol.get("dcol_ansi_black")
    txt = dcol.get("dcol_txt1") or dcol.get("dcol_ansi_white") or defaults["clock"]
    accent = (
        dcol.get("dcol_1xa7")
        or dcol.get("dcol_1xa6")
        or dcol.get("dcol_1xa5")
        or defaults["accent"]
    )
    muted = dcol.get("dcol_1xa5") or defaults["date"]
    soft = dcol.get("dcol_1xa4") or defaults["hint"]
    border = dcol.get("dcol_1xa6") or accent
    t = dict(defaults)
    if pry:
        t["bg"] = pry
        t["panel"] = hex_rgba(pry, 0.72)
        t["dots_bg"] = hex_rgba(pry, 0.92)
        t["btn_bg"] = hex_rgba(pry, 0.88)
    t["clock"] = txt
    t["dots"] = txt
    t["btn_fg"] = txt
    t["user"] = accent
    t["accent"] = accent
    t["date"] = muted
    t["hint"] = soft
    t["status"] = soft
    bh = border.lstrip("#")
    if len(bh) == 6:
        t["border"] = hex_rgba("#" + bh, 0.45)
        t["dots_border"] = hex_rgba("#" + bh, 0.55)
    return t
