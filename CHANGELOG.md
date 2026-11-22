# Changelog

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
