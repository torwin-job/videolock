#!/bin/bash
# Build poster + JPEG frame strip from a source video for session-lock background.
set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") [--video PATH] [--fps N] [--width N] [--out DIR]

Extracts:
  \$OUT/video.mp4   (optional re-encode, scaled)
  \$OUT/poster.png  (first frame)
  \$OUT/frames/f-XXX.jpg

Defaults:
  --video  \$VIDEOLOCK_VIDEO or first arg
  --fps    8
  --width  1280
  --out    \$XDG_DATA_HOME/videolock  (or ~/.local/share/videolock)
EOF
}

OUT="${XDG_DATA_HOME:-$HOME/.local/share}/videolock"
FPS=8
WIDTH=1280
VIDEO="${VIDEOLOCK_VIDEO:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --video) VIDEO="$2"; shift 2 ;;
    --fps) FPS="$2"; shift 2 ;;
    --width) WIDTH="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) VIDEO="$1"; shift ;;
  esac
done

if [ -z "$VIDEO" ] || [ ! -f "$VIDEO" ]; then
  echo "error: provide an existing video with --video PATH" >&2
  usage >&2
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "error: ffmpeg is required" >&2
  exit 1
fi

mkdir -p "$OUT/frames"
chmod 700 "$OUT" 2>/dev/null || true

echo "==> poster"
ffmpeg -y -i "$VIDEO" -frames:v 1 -q:v 2 "$OUT/poster.png" >/dev/null 2>&1

echo "==> frames @${FPS}fps width=${WIDTH}"
rm -f "$OUT"/frames/f-*.jpg
ffmpeg -y -i "$VIDEO" -vf "fps=${FPS},scale=${WIDTH}:-2" -q:v 5 "$OUT/frames/f-%03d.jpg" >/dev/null 2>&1

echo "==> compact video copy"
ffmpeg -y -i "$VIDEO" -vf "scale=${WIDTH}:-2" -c:v libx264 -preset veryfast -crf 23 -an -movflags +faststart "$OUT/video.mp4" >/dev/null 2>&1 || \
  cp -f "$VIDEO" "$OUT/video.mp4"

n=$(ls "$OUT"/frames/f-*.jpg 2>/dev/null | wc -l)
echo "done: $n frames → $OUT"
echo "tip: export VIDEOLOCK_FRAMES=$OUT/frames  (or rely on XDG data dir)"
