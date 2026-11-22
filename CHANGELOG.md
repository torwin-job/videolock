# Changelog

## 0.3.3 — 2026-11-22

- Split corner into two docks: battery/Wi‑Fi block left of the power block

## 0.3.2 — 2026-11-22

- Bottom-right corner dock: battery + Wi‑Fi as separate icon chips; power buttons with symbolic icons

## 0.3.1 — 2026-11-22

- Move battery/network + power buttons to a bottom-left corner dock (center panel stays lean)

## 0.3.0 — 2026-11-22

- Battery + network line on the lock panel
- Sleep / Reboot / Power buttons (`systemctl`)
- Wallbash theme colors from `~/.cache/hyde/wall.dcol` (disable: `VIDEOLOCK_WALLBASH=0`)
- Updated live screenshots + 5s clip

## 0.2.4 — 2026-11-22

- Pixelon on all labels (window/panel/`label` inheritance, not only clock)
- Slightly larger panel than 0.2.3 (density default **0.95**)

## 0.2.3 — 2026-11-22

- Default font: **Pixelon** (SDDM Astronaut / hyde_unified)
- Slightly smaller panel & type (density 0.88, reduced base sizes); tune with `VIDEOLOCK_DENSITY`

## 0.2.2 — 2026-11-22

### Reliability & HiDPI

- Scale panel/fonts from Hyprland monitor scale (or `VIDEOLOCK_SCALE`)
- `videolock --recover` / `videolock-unlock.sh --recover` clears hung locker + crash overlay + stale lockfile
- Stale flock auto-cleared so lock works again after crash
- `install.sh --hypridle` writes a timestamped `.videolock.bak.*` before patching
- `install.sh --bind` ensures a single Super+L → videolock path and disables competing `loginctl lock-session` binds
- Smoke test covers crash→recover→re-lock

## 0.2.1 — 2026-11-22

### Critical UX (keyboard)

- Reset to primary XKB layout (`hyprctl switchxkblayout all 0`) when arming the lock
- On-screen layout indicator (`US`/`RU`/…) + Caps Lock warning
- Examples use `bindl` / `locked = true` for layout toggle on the lock screen
- `VIDEOLOCK_RESET_LAYOUT=0` to opt out of auto-reset

## 0.2.0 — 2026-11-22

### Public packaging

- Split core locker from personal HyDE glue (`contrib/hyde/`)
- XDG data/cache paths; env overrides for assets
- `install.sh` / `uninstall.sh` with optional `--video` and `--hypridle`
- `videolock --check` / `--version`
- i18n (`en`/`ru`) via locale or `VIDEOLOCK_LANG`
- MIT license, SECURITY.md, architecture + audit docs
- Graceful unlock helper by PID lockfile (no broad `pkill -f`)
- Removed SDDM Astronaut / `/home/void` hardcodes from core

### Security (from audit #1, retained)

- Password `bytearray` + wipe
- Cache log mode 0600
- PAM fail-fast
- PAM exponential backoff
- In-process flock singleton
