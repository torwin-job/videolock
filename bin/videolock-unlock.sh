#!/bin/bash
# hypridle unlock_cmd: SIGTERM → SessionLock.unlock(), then clear crash overlay.
set -euo pipefail
export HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"

if [ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ] && [ -d "${XDG_RUNTIME_DIR}/hypr" ]; then
  HYPRLAND_INSTANCE_SIGNATURE=$(ls -1t "${XDG_RUNTIME_DIR}/hypr" 2>/dev/null | head -1 || true)
  export HYPRLAND_INSTANCE_SIGNATURE
fi

CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/videolock"
LOCKFILE="${CACHE}/videolock.lock"

if [ -f "$LOCKFILE" ]; then
  pid=$(tr -d '[:space:]' <"$LOCKFILE" || true)
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
fi

# Best-effort clear of Hyprland crashed-lock overlay (HyDE Lua API)
if command -v hyprctl >/dev/null 2>&1; then
  hyprctl eval 'hl.clear_crashed_lockscreen()' >/dev/null 2>&1 || true
fi
exit 0
