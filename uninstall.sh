#!/bin/bash
# Remove videolock user install. Does not delete your media assets unless --purge-data.
set -euo pipefail
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/videolock"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/videolock"
PURGE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --purge-data) PURGE=1; shift ;;
    --prefix) PREFIX="$2"; BIN_DIR="$PREFIX/bin"; shift 2 ;;
    -h|--help)
      echo "Usage: ./uninstall.sh [--prefix DIR] [--purge-data]"
      exit 0
      ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done

for f in videolock videolock.sh videolock-unlock.sh videolock-prepare-assets videolock-warm-video; do
  rm -f "$BIN_DIR/$f"
  echo "removed $BIN_DIR/$f"
done

if [ "$PURGE" -eq 1 ]; then
  rm -rf "$DATA_DIR" "$CACHE_DIR"
  echo "purged $DATA_DIR and $CACHE_DIR"
else
  echo "kept data: $DATA_DIR (use --purge-data to delete)"
fi

echo "Note: revert hypridle / keybinds manually if you patched them."
