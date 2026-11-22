#!/bin/bash
# Install videolock for the current user.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/videolock"
VIDEO=""
PATCH_HYPRIDLE=0
PREPARE=0

usage() {
  cat <<EOF
Usage: ./install.sh [options]

Options:
  --prefix DIR       install prefix (default: ~/.local)
  --video PATH       source video; run prepare-assets into XDG data dir
  --prepare          prepare assets if --video given (implied by --video)
  --hypridle         patch ~/.config/hypr/hypridle.conf LOCK/UNLOCK cmds
  -h, --help         show this help

Installs:
  \$PREFIX/bin/videolock
  \$PREFIX/bin/videolock.sh
  \$PREFIX/bin/videolock-unlock.sh
  \$PREFIX/bin/videolock-prepare-assets  (symlink to scripts/prepare-assets.sh)

After install, bind Super+L / hypridle to videolock.sh — see examples/.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --prefix) PREFIX="$2"; BIN_DIR="$PREFIX/bin"; shift 2 ;;
    --video) VIDEO="$2"; PREPARE=1; shift 2 ;;
    --prepare) PREPARE=1; shift ;;
    --hypridle) PATCH_HYPRIDLE=1; shift ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

echo "==> checking dependencies"
need=()
command -v python3 >/dev/null || need+=(python3)
command -v ffmpeg >/dev/null || true  # optional until --video
python3 - <<'PY' || need+=("python-gobject/gi")
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: F401
PY
python3 - <<'PY' || need+=("gtk4-session-lock (Gtk4SessionLock)")
import gi
gi.require_version("Gtk4SessionLock", "1.0")
from gi.repository import Gtk4SessionLock  # noqa: F401
PY
python3 - <<'PY' || need+=("python-pam")
import pam  # noqa: F401
PY
if [ "${#need[@]}" -gt 0 ]; then
  echo "Missing dependencies:" >&2
  printf '  - %s\n' "${need[@]}" >&2
  echo "Arch: pacman -S python python-gobject gtk4 python-pam ffmpeg" >&2
  echo "      + gtk4-session-lock (AUR / your DE package)" >&2
  exit 1
fi

echo "==> install binaries → $BIN_DIR"
mkdir -p "$BIN_DIR"
install -m 0755 "$ROOT/bin/videolock" "$BIN_DIR/videolock"
install -m 0755 "$ROOT/bin/videolock.sh" "$BIN_DIR/videolock.sh"
install -m 0755 "$ROOT/bin/videolock-unlock.sh" "$BIN_DIR/videolock-unlock.sh"
install -m 0755 "$ROOT/scripts/prepare-assets.sh" "$BIN_DIR/videolock-prepare-assets"
install -m 0755 "$ROOT/scripts/warm-video.sh" "$BIN_DIR/videolock-warm-video"

mkdir -p "$DATA_DIR"
chmod 700 "$DATA_DIR" 2>/dev/null || true

if [ "$PREPARE" -eq 1 ]; then
  if [ -z "$VIDEO" ]; then
    echo "error: --prepare requires --video PATH" >&2
    exit 1
  fi
  command -v ffmpeg >/dev/null || { echo "error: ffmpeg required for --video" >&2; exit 1; }
  echo "==> prepare assets from $VIDEO"
  "$BIN_DIR/videolock-prepare-assets" --video "$VIDEO" --out "$DATA_DIR"
fi

if [ "$PATCH_HYPRIDLE" -eq 1 ]; then
  CONF="${XDG_CONFIG_HOME:-$HOME/.config}/hypr/hypridle.conf"
  if [ ! -f "$CONF" ]; then
    echo "warn: $CONF not found — skip hypridle patch" >&2
  else
    echo "==> patch hypridle.conf"
    python3 - "$CONF" "$BIN_DIR/videolock.sh" "$BIN_DIR/videolock-unlock.sh" <<'PY'
from pathlib import Path
import re, sys
conf, lock, unlock = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
t = conf.read_text()
if re.search(r"^\$LOCK_CMD\s*=", t, re.M):
    t = re.sub(r"^\$LOCK_CMD\s*=.*", f"$LOCK_CMD = {lock}", t, flags=re.M)
else:
    t = f"$LOCK_CMD = {lock}\n$UNLOCK_CMD = {unlock}\n" + t
if re.search(r"^\$UNLOCK_CMD\s*=", t, re.M):
    t = re.sub(r"^\$UNLOCK_CMD\s*=.*", f"$UNLOCK_CMD = {unlock}", t, flags=re.M)
else:
    t = re.sub(r"(^\$LOCK_CMD\s*=.*$)", rf"\1\n$UNLOCK_CMD = {unlock}", t, count=1, flags=re.M)
t = re.sub(r"(^\s*lock_cmd\s*=\s*).*$", r"\1$LOCK_CMD", t, flags=re.M)
t = re.sub(r"(^\s*unlock_cmd\s*=\s*).*$", r"\1$UNLOCK_CMD", t, flags=re.M)
conf.write_text(t)
print(f"updated {conf}")
PY
  fi
fi

echo "==> self-check"
# --check may report "lock not supported" when run outside a Wayland session — that is OK.
"$BIN_DIR/videolock" --check || true

cat <<EOF

Installed.

Next steps:
  1. Point hypridle lock_cmd at:  $BIN_DIR/videolock.sh
     unlock_cmd at:               $BIN_DIR/videolock-unlock.sh
     (or re-run: ./install.sh --hypridle)
  2. Bind Super+L — see examples/hyprland.lua / examples/hyprland.conf
  3. Assets live in: $DATA_DIR
     prepare with: videolock-prepare-assets --video /path/to/wall.mp4

EOF
