#!/bin/bash
# Install videolock for the current user.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/videolock"
VIDEO=""
PATCH_HYPRIDLE=0
PATCH_BIND=0
PREPARE=0

usage() {
  cat <<EOF
Usage: ./install.sh [options]

Options:
  --prefix DIR       install prefix (default: ~/.local)
  --video PATH       source video; run prepare-assets into XDG data dir
  --prepare          prepare assets if --video given (implied by --video)
  --hypridle         patch ~/.config/hypr/hypridle.conf (with timestamped backup)
  --bind             ensure a single Super+L → videolock path (lua/conf); disable
                     competing loginctl lock-session binds when found
  -h, --help         show this help

Installs:
  \$PREFIX/bin/videolock
  \$PREFIX/bin/videolock.sh
  \$PREFIX/bin/videolock-unlock.sh
  \$PREFIX/bin/videolock-prepare-assets
  \$PREFIX/bin/videolock-warm-video
  \$PREFIX/bin/videolock-smoke-test
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --prefix) PREFIX="$2"; BIN_DIR="$PREFIX/bin"; shift 2 ;;
    --video) VIDEO="$2"; PREPARE=1; shift 2 ;;
    --prepare) PREPARE=1; shift ;;
    --hypridle) PATCH_HYPRIDLE=1; shift ;;
    --bind) PATCH_BIND=1; shift ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

backup_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  local bak="${f}.videolock.bak.$(date +%Y%m%d%H%M%S)"
  cp -a "$f" "$bak"
  echo "  backup → $bak"
}

echo "==> checking dependencies"
need=()
command -v python3 >/dev/null || need+=(python3)
command -v ffmpeg >/dev/null || true
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
install -m 0755 "$ROOT/scripts/smoke-test.sh" "$BIN_DIR/videolock-smoke-test"

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
    backup_file "$CONF"
    python3 - "$CONF" "$BIN_DIR/videolock.sh" "$BIN_DIR/videolock-unlock.sh" <<'PY'
from pathlib import Path
import re, sys
conf, lock, unlock = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
try:
    t = conf.read_text()
    orig = t
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
    # Atomic write
    tmp = conf.with_suffix(conf.suffix + ".tmp")
    tmp.write_text(t)
    tmp.replace(conf)
    print(f"updated {conf}")
except Exception as e:
    print(f"ERROR patching hypridle: {e}", file=sys.stderr)
    # restore newest backup if we failed after write attempt
    raise SystemExit(1)
PY
  fi
fi

if [ "$PATCH_BIND" -eq 1 ]; then
  echo "==> ensure single Super+L → videolock"
  HYPR="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
  python3 - "$BIN_DIR/videolock.sh" "$HYPR" <<'PY'
from pathlib import Path
import re, sys, datetime
lock_sh, hypr = Path(sys.argv[1]), Path(sys.argv[2])
home = str(Path.home())
stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def backup(p: Path):
    if not p.is_file():
        return
    bak = p.with_name(p.name + f".videolock.bak.{stamp}")
    bak.write_bytes(p.read_bytes())
    print(f"  backup → {bak}")

# 1) Classic hyprland.conf: comment loginctl lock-session on Super+L; ensure videolock bindl
conf = hypr / "hyprland.conf"
if conf.is_file():
    t = conf.read_text()
    orig = t
    # Comment competing binds
    t = re.sub(
        r"^(\s*bind[l]?l?\s*=\s*\$?(?:mainMod|SUPER|super)\s*,\s*L\s*,\s*exec\s*,\s*.*loginctl\s+lock-session.*)$",
        r"# videolock: disabled dual path — \1",
        t,
        flags=re.I | re.M,
    )
    t = re.sub(
        r"^(\s*bind[l]?l?\s*=\s*SUPER\s*,\s*L\s*,\s*exec\s*,\s*.*loginctl\s+lock-session.*)$",
        r"# videolock: disabled dual path — \1",
        t,
        flags=re.I | re.M,
    )
    if "videolock.sh" not in t:
        t += f"\n# >>> videolock\nbindl = SUPER, L, exec, {lock_sh}\n# <<< videolock\n"
    elif not re.search(r"bindl?\s*=\s*SUPER\s*,\s*L\s*,\s*exec\s*,\s*.*videolock", t, re.I):
        t += f"\n# >>> videolock\nbindl = SUPER, L, exec, {lock_sh}\n# <<< videolock\n"
    if t != orig:
        backup(conf)
        tmp = conf.with_suffix(conf.suffix + ".tmp")
        tmp.write_text(t)
        tmp.replace(conf)
        print(f"  updated {conf}")
    else:
        print(f"  {conf}: no changes needed")

# 2) HyDE hyprland.lua: ensure direct bind; warn about session.lock
lua = hypr / "hyprland.lua"
if lua.is_file():
    t = lua.read_text()
    orig = t
    # Neutralize common HyDE loginctl lock wrappers if present as plain binds
    t = re.sub(
        r"^(\s*hl\.bind\(\s*\"SUPER \+ L\".*loginctl.*)$",
        r"-- videolock: disabled dual path — \1",
        t,
        flags=re.M,
    )
    block = f'''
-- >>> videolock
local home = os.getenv("HOME") or "{home}"
hl.env("LOCKSCREEN", "videolock")
hl.env("HYDE_LOCKSCREEN", "videolock")
hl.env("HYPRLAND_LOCKSCREEN", "videolock")
hl.bind("SUPER + L", hl.dsp.exec_cmd(home .. "/.local/bin/videolock.sh"), {{ description = "Video lock", locked = true }})
-- <<< videolock
'''
    if "videolock.sh" not in t:
        t += block
    elif 'hl.bind("SUPER + L"' in t and "videolock.sh" in t:
        # already has videolock bind — keep, but ensure LOCKSCREEN env
        if 'hl.env("LOCKSCREEN", "videolock")' not in t:
            t = t.replace("-- >>> videolock", '-- >>> videolock\nhl.env("LOCKSCREEN", "videolock")\nhl.env("HYDE_LOCKSCREEN", "videolock")\nhl.env("HYPRLAND_LOCKSCREEN", "videolock")', 1)
            if 'hl.env("LOCKSCREEN", "videolock")' not in t:
                t += '\nhl.env("LOCKSCREEN", "videolock")\nhl.env("HYDE_LOCKSCREEN", "videolock")\nhl.env("HYPRLAND_LOCKSCREEN", "videolock")\n'
    if t != orig:
        backup(lua)
        tmp = lua.with_suffix(lua.suffix + ".tmp")
        tmp.write_text(t)
        tmp.replace(lua)
        print(f"  updated {lua}")
    else:
        print(f"  {lua}: videolock bind already present")

# 3) Detect remaining dual paths
dual = []
for p in hypr.rglob("*"):
    if not p.is_file():
        continue
    if p.suffix not in {".conf", ".lua", ".txt"} and "hyprland" not in p.name:
        continue
    try:
        text = p.read_text(errors="ignore")
    except Exception:
        continue
    if re.search(r"loginctl\s+lock-session", text, re.I) and re.search(r"SUPER.*\bL\b|Super_L|bind.*\bL\b", text):
        if "videolock: disabled" not in text and "# videolock" not in text.lower():
            dual.append(str(p))
if dual:
    print("  warn: possible remaining Super+L → loginctl paths:")
    for d in dual[:8]:
        print(f"    - {d}")
    print("  tip: keep ONLY videolock bind; idle locks go through hypridle $LOCK_CMD")
else:
    print("  no competing Super+L → loginctl binds detected")
PY
fi

echo "==> self-check"
"$BIN_DIR/videolock" --check || true

cat <<EOF

Installed.

Next steps:
  1. hypridle:  ./install.sh --hypridle
  2. Super+L:   ./install.sh --bind   (single path; disables loginctl duplicates)
  3. Recover:   videolock --recover   (or videolock-unlock.sh --recover)
  4. Assets:    $DATA_DIR

EOF
