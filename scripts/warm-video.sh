#!/bin/bash
# Optional: prime VAAPI/GStreamer decoder so first lock is snappier.
set -euo pipefail
VID="${1:-${VIDEOLOCK_VIDEO:-${XDG_DATA_HOME:-$HOME/.local/share}/videolock/video.mp4}}"
[ -f "$VID" ] || exit 0
command -v gst-launch-1.0 >/dev/null 2>&1 || exit 0
gst-launch-1.0 -q filesrc location="$VID" ! qtdemux ! h264parse ! vah264dec ! fakesink sync=false num-buffers=8 >/dev/null 2>&1 || \
gst-launch-1.0 -q filesrc location="$VID" ! decodebin ! fakesink sync=false num-buffers=8 >/dev/null 2>&1 || true
