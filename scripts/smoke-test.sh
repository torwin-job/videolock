#!/bin/bash
# Smoke tests for videolock. Safe to run over SSH; lock/unlock only if Wayland session present.
set -u
PASS=0
FAIL=0
SKIP=0

ok()   { PASS=$((PASS+1)); echo "  PASS  $*"; }
fail() { FAIL=$((FAIL+1)); echo "  FAIL  $*"; }
skip() { SKIP=$((SKIP+1)); echo "  SKIP  $*"; }

HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"
BIN="${HOME}/.local/bin"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/videolock"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/videolock"

echo "=== videolock smoke-test ==="
echo "host=$(uname -n) user=$(id -un) time=$(date -Iseconds)"

# --- binaries ---
echo "-- binaries"
for f in videolock videolock.sh videolock-unlock.sh videolock-prepare-assets videolock-warm-video; do
  if [ -x "$BIN/$f" ]; then ok "$f executable"
  else fail "$f missing/not executable in $BIN"
  fi
done

# --- python syntax / version ---
echo "-- python"
if "$BIN/videolock" --version 2>/dev/null | grep -q 'videolock'; then
  ok "version: $($BIN/videolock --version 2>&1)"
else
  fail "videolock --version"
fi
python3 -m py_compile "$BIN/videolock" 2>/dev/null && ok "py_compile" || fail "py_compile"

# --- deps ---
echo "-- dependencies"
python3 -c 'import pam' 2>/dev/null && ok "python-pam" || fail "python-pam"
python3 - <<'PY' 2>/dev/null && ok "Gtk 4" || fail "Gtk 4"
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
PY
python3 - <<'PY' 2>/dev/null && ok "Gtk4SessionLock" || fail "Gtk4SessionLock"
import gi
gi.require_version("Gtk4SessionLock", "1.0")
from gi.repository import Gtk4SessionLock
PY
command -v ffmpeg >/dev/null && ok "ffmpeg" || skip "ffmpeg (only needed for prepare-assets)"

# --- assets ---
echo "-- assets"
[ -f "$DATA/poster.png" ] || [ -f "$DATA/poster.jpg" ] && ok "poster" || fail "poster missing in $DATA"
[ -d "$DATA/frames" ] && n=$(ls "$DATA/frames"/f-*.jpg 2>/dev/null | wc -l) || n=0
[ "$n" -ge 8 ] && ok "frames ($n)" || fail "frames ($n) — need >= 8 in $DATA/frames"
[ -f "$DATA/video.mp4" ] && ok "video.mp4" || skip "video.mp4 optional"

# --- cache perms ---
echo "-- cache permissions"
mkdir -p "$CACHE"
mode=$(stat -c '%a' "$CACHE" 2>/dev/null || echo '?')
case "$mode" in
  700|1700) ok "cache dir mode $mode" ;;
  *) skip "cache dir mode $mode (will be set on first run)" ;;
esac

# --- hypridle ---
echo "-- hypridle"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}/hypr/hypridle.conf"
if [ -f "$CONF" ]; then
  grep -q 'videolock.sh' "$CONF" && ok "LOCK_CMD → videolock.sh" || fail "LOCK_CMD not videolock.sh"
  grep -q 'videolock-unlock' "$CONF" && ok "UNLOCK_CMD → unlock helper" || fail "UNLOCK_CMD not unlock helper"
  grep -q 'pkill -f' "$CONF" && fail "still using pkill -f unlock" || ok "no pkill -f unlock"
else
  skip "hypridle.conf not found"
fi

# --- session / lock protocol ---
echo "-- wayland session"
# Attach to Hyprland env if running
pid=$(pgrep -x Hyprland | head -1 || true)
if [ -z "$pid" ]; then
  skip "Hyprland not running — cannot test lock/unlock/layout"
  echo
  echo "RESULT: $PASS pass, $FAIL fail, $SKIP skip"
  [ "$FAIL" -eq 0 ] && exit 0 || exit 1
fi

while IFS= read -r line; do
  case "$line" in
    WAYLAND_DISPLAY=*|HYPRLAND_INSTANCE_SIGNATURE=*|XDG_RUNTIME_DIR=*|DBUS_SESSION_BUS_ADDRESS=*)
      export "$line"
      ;;
  esac
done < <(tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(WAYLAND_DISPLAY|HYPRLAND_INSTANCE_SIGNATURE|XDG_RUNTIME_DIR|DBUS_SESSION_BUS_ADDRESS)=' || true)

# Fallbacks if environ was not readable yet
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [ -z "${WAYLAND_DISPLAY:-}" ]; then
  for cand in wayland-1 wayland-0; do
    [ -S "${XDG_RUNTIME_DIR}/${cand}" ] && WAYLAND_DISPLAY=$cand && break
  done
  export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"
fi
if [ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ] && [ -d "${XDG_RUNTIME_DIR}/hypr" ]; then
  HYPRLAND_INSTANCE_SIGNATURE=$(ls -1t "${XDG_RUNTIME_DIR}/hypr" 2>/dev/null | head -1 || true)
  export HYPRLAND_INSTANCE_SIGNATURE
fi

ok "Hyprland pid=$pid wayland=${WAYLAND_DISPLAY:-?} sig=${HYPRLAND_INSTANCE_SIGNATURE:-?}"

check_out=$("$BIN/videolock" --check 2>&1 || true)
echo "$check_out" | grep -q 'lock:   supported' && ok "ext-session-lock supported" || fail "ext-session-lock not supported in session"

# --- live lock → graceful unlock (no password; SIGTERM path) ---
echo "-- live lock/unlock (5s)"
# Ensure nothing stuck
"$BIN/videolock-unlock.sh" >/dev/null 2>&1 || true
sleep 0.3
rm -f "$CACHE/videolock.log"

# Arm lock in background
"$BIN/videolock.sh" >/dev/null 2>&1 &
locker_bg=$!
# Wait until lockfile appears / process exists
armed=0
for i in $(seq 1 30); do
  if [ -f "$CACHE/videolock.lock" ]; then
    lpid=$(tr -d '[:space:]' < "$CACHE/videolock.lock" || true)
    if [ -n "$lpid" ] && kill -0 "$lpid" 2>/dev/null; then
      armed=1
      break
    fi
  fi
  sleep 0.2
done

if [ "$armed" -eq 1 ]; then
  ok "locker armed pid=$(cat "$CACHE/videolock.lock")"
  sleep 2
  # frames should tick — log evidence
  if [ -f "$CACHE/videolock.log" ]; then
    grep -qE 'locked|frame|textures|surface' "$CACHE/videolock.log" && ok "log activity" || skip "log sparse"
    # never log password-ish
    if grep -qiE 'password=|passwd=|secret' "$CACHE/videolock.log"; then
      fail "log may contain secret-like tokens"
    else
      ok "log has no password tokens"
    fi
  else
    fail "no log after arm"
  fi
  "$BIN/videolock-unlock.sh"
  sleep 0.8
  if [ -f "$CACHE/videolock.lock" ]; then
    lpid=$(tr -d '[:space:]' < "$CACHE/videolock.lock" || true)
    if [ -n "$lpid" ] && kill -0 "$lpid" 2>/dev/null; then
      fail "locker still alive after unlock helper"
      kill -KILL "$lpid" 2>/dev/null || true
    else
      ok "locker exited after unlock helper"
    fi
  else
    ok "lockfile gone / locker exited"
  fi
else
  fail "locker did not arm within timeout"
  "$BIN/videolock-unlock.sh" >/dev/null 2>&1 || true
fi

# wait bg
wait "$locker_bg" 2>/dev/null || true

# --- crash recovery (SIGKILL without unlock()) ---
echo "-- crash recover"
"$BIN/videolock-unlock.sh" >/dev/null 2>&1 || true
sleep 0.2
"$BIN/videolock.sh" >/dev/null 2>&1 &
crash_bg=$!
armed=0
for i in $(seq 1 30); do
  if [ -f "$CACHE/videolock.lock" ]; then
    lpid=$(tr -d '[:space:]' <"$CACHE/videolock.lock" || true)
    if [ -n "$lpid" ] && kill -0 "$lpid" 2>/dev/null; then
      armed=1
      break
    fi
  fi
  sleep 0.2
done
if [ "$armed" -eq 1 ]; then
  lpid=$(tr -d '[:space:]' <"$CACHE/videolock.lock")
  sleep 1
  kill -KILL "$lpid" 2>/dev/null || true
  sleep 0.3
  # stale lockfile should remain or be empty-owner
  "$BIN/videolock" --recover >/tmp/videolock-recover.out 2>&1
  rec_ec=$?
  [ "$rec_ec" -eq 0 ] && ok "videolock --recover exit 0" || fail "videolock --recover exit $rec_ec"
  if [ -f "$CACHE/videolock.lock" ]; then
    spid=$(tr -d '[:space:]' <"$CACHE/videolock.lock" || true)
    if [ -n "$spid" ] && kill -0 "$spid" 2>/dev/null; then
      fail "locker still alive after --recover"
    else
      ok "no live locker after --recover"
    fi
  else
    ok "lockfile removed after --recover"
  fi
  # new lock should work (stale flock cleared)
  "$BIN/videolock.sh" >/dev/null 2>&1 &
  rearm=0
  for i in $(seq 1 25); do
    if [ -f "$CACHE/videolock.lock" ]; then
      npid=$(tr -d '[:space:]' <"$CACHE/videolock.lock" || true)
      if [ -n "$npid" ] && kill -0 "$npid" 2>/dev/null; then
        rearm=1
        break
      fi
    fi
    sleep 0.2
  done
  [ "$rearm" -eq 1 ] && ok "re-lock after recover" || fail "could not re-lock after recover"
  "$BIN/videolock-unlock.sh" >/dev/null 2>&1 || true
else
  skip "crash recover (could not arm)"
fi
wait "$crash_bg" 2>/dev/null || true

# HiDPI scale reported
echo "-- hidpi"
scale_line=$("$BIN/videolock" --check 2>/dev/null | grep 'scale:' || true)
[ -n "$scale_line" ] && ok "$scale_line" || skip "scale not reported"

# layout note (cannot fully automate Alt+Shift without uinput)
echo "-- layout"
kb=$(hyprctl getoption input:kb_layout -j 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("str",""))' 2>/dev/null || true)
if echo "$kb" | grep -q ','; then
  ok "kb_layout=$kb (Alt+Shift via kb_options — manual verify on lock screen)"
else
  skip "kb_layout=$kb"
fi
opts=$(hyprctl getoption input:kb_options -j 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("str",""))' 2>/dev/null || true)
echo "$opts" | grep -q 'grp:' && ok "kb_options=$opts" || skip "kb_options=$opts"

echo
echo "RESULT: $PASS pass, $FAIL fail, $SKIP skip"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
