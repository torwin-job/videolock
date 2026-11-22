"""XDG paths and asset resolution."""
from __future__ import annotations

import os
from pathlib import Path


def xdg_home(env_key: str, default_under_home: str) -> Path:
    raw = os.environ.get(env_key)
    if raw:
        return Path(raw).expanduser()
    return Path.home() / default_under_home


CACHE_DIR = xdg_home("XDG_CACHE_HOME", ".cache") / "videolock"
DATA_DIR = xdg_home("XDG_DATA_HOME", ".local/share") / "videolock"
CONFIG_DIR = xdg_home("XDG_CONFIG_HOME", ".config") / "videolock"

for _d in (CACHE_DIR, DATA_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
        os.chmod(_d, 0o700)
    except OSError:
        pass

LOG = CACHE_DIR / "videolock.log"
LOCKFILE = CACHE_DIR / "videolock.lock"


def resolve_asset(env_name: str, *candidates: Path) -> Path:
    env = os.environ.get(env_name)
    if env:
        return Path(env).expanduser()
    for c in candidates:
        if c.is_file() or (env_name.endswith("FRAMES") and c.is_dir()):
            return c
    return candidates[0]


POSTER = resolve_asset(
    "VIDEOLOCK_POSTER",
    DATA_DIR / "poster.png",
    DATA_DIR / "poster.jpg",
    Path.home() / "Videos/wallpapers/login-lock.png",
)
VIDEO = resolve_asset(
    "VIDEOLOCK_VIDEO",
    DATA_DIR / "video.mp4",
    Path.home() / "Videos/wallpapers/login-lock.mp4",
)
FRAME_DIR = resolve_asset(
    "VIDEOLOCK_FRAMES",
    DATA_DIR / "frames",
    Path.home() / "Videos/wallpapers/login-frames",
)
