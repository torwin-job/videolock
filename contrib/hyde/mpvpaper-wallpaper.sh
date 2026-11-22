#!/bin/bash
# Optional video wallpaper via mpvpaper (NOT part of the lockscreen core).
set -euo pipefail
export HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"

WALL="${VIDEOLOCK_WALLPAPER:-${XDG_DATA_HOME:-$HOME/.local/share}/videolock/video.mp4}"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

[ -f "$WALL" ] || { echo "no wallpaper video: $WALL" >&2; exit 1; }
command -v mpvpaper >/dev/null || { echo "mpvpaper not installed" >&2; exit 1; }

if [ "$FORCE" -eq 0 ] && pgrep -x mpvpaper >/dev/null; then
  exit 0
fi
pkill -x hyprpaper >/dev/null 2>&1 || true
pkill -x mpvpaper >/dev/null 2>&1 || true
sleep 0.2

MON=$(hyprctl monitors -j 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["name"])' 2>/dev/null || true)
[ -n "$MON" ] || MON='eDP-1'

OPTS='no-audio loop --hwdec=auto --vo=gpu --gpu-api=opengl --framedrop=vo --video-sync=desync --profile=fast --scale=bilinear --cscale=bilinear --dscale=bilinear --geometry=100%:100% --panscan=1.0 --osd-level=0 --really-quiet'
mpvpaper -p "$MON" "$WALL" --fork --mpv-options "$OPTS" >/dev/null 2>&1
