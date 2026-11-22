#!/bin/bash
# Optional HyDE glue: keep hypridle on videolock + migrate legacy assets.
# Not required for a stock install.
set -euo pipefail
export HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"
export PATH="${HOME}/.local/bin:/usr/bin:/bin"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

BIN="${HOME}/.local/bin"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/videolock"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ -x "${BIN}/videolock.sh" ] && [ -x "${BIN}/videolock-unlock.sh" ]; then
  python3 - "${BIN}/videolock.sh" "${BIN}/videolock-unlock.sh" <<'PY'
from pathlib import Path
import re, sys
lock_sh, unlock_sh = sys.argv[1], sys.argv[2]
p = Path.home() / ".config/hypr/hypridle.conf"
if not p.exists():
    raise SystemExit(0)
t = p.read_text()
t = re.sub(r"^\$LOCK_CMD\s*=.*", f"$LOCK_CMD = {lock_sh}", t, flags=re.M)
t = re.sub(r"^\$UNLOCK_CMD\s*=.*", f"$UNLOCK_CMD = {unlock_sh}", t, flags=re.M)
p.write_text(t)
PY
fi

mkdir -p "$DATA/frames"
chmod 700 "$DATA" 2>/dev/null || true

LEGACY="$HOME/Videos/wallpapers"
if [ "$(ls "$DATA/frames"/f-*.jpg 2>/dev/null | wc -l)" -lt 10 ]; then
  if [ -d "$LEGACY/login-frames" ]; then
    cp -n "$LEGACY/login-frames"/f-*.jpg "$DATA/frames/" 2>/dev/null || true
  fi
fi
[ -f "$LEGACY/login-lock.png" ] && [ ! -f "$DATA/poster.png" ] && cp -n "$LEGACY/login-lock.png" "$DATA/poster.png" || true
[ -f "$LEGACY/login-lock.mp4" ] && [ ! -f "$DATA/video.mp4" ] && cp -n "$LEGACY/login-lock.mp4" "$DATA/video.mp4" || true

WP="$HERE/mpvpaper-wallpaper.sh"
if [ -x "$WP" ] && ! pgrep -x mpvpaper >/dev/null; then
  "$WP" >/dev/null 2>&1 &
elif [ -x "${BIN}/start-kath-wallpaper.sh" ] && ! pgrep -x mpvpaper >/dev/null; then
  "${BIN}/start-kath-wallpaper.sh" >/dev/null 2>&1 &
fi

[ -x "${BIN}/videolock-warm-video" ] && "${BIN}/videolock-warm-video" &
true
