#!/bin/bash
# Env wrapper for Hyprland / Wayland. Singleton flock lives inside bin/videolock.
set -euo pipefail
export HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"
export PATH="${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"
export GDK_BACKEND=wayland
export GTK_IM_MODULE=none

if [ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ] && [ -d "${XDG_RUNTIME_DIR}/hypr" ]; then
  # Prefer newest instance dir
  HYPRLAND_INSTANCE_SIGNATURE=$(ls -1t "${XDG_RUNTIME_DIR}/hypr" 2>/dev/null | head -1 || true)
  export HYPRLAND_INSTANCE_SIGNATURE
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
SELF="${HERE}/videolock"
if [ ! -x "$SELF" ]; then
  SELF="${HOME}/.local/bin/videolock"
fi
exec "$SELF" "$@"
