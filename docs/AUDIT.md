# Security & product audit

## Audit #1 — 2026-11-22 (personal dump)

Focused on the first laptop export. Critical issues (password list, `/tmp` log, `pkill -f` unlock, missing PAM gate, hardcodes) were fixed in-tree before public packaging. See git history / CHANGELOG.

## Audit #2 — 2026-11-22 (public packaging)

Scope: readiness for open-source install by third parties; remaining risk; architecture cleanliness.

### Verdict

**Ready for public 0.2.x** as a *personal Hyprland session locker*, with clear docs of threat model.  
Not a drop-in replacement for `hyprlock` ecosystem maturity, but structurally installable and de-personalized.

---

### Findings (Audit #2)

#### Fixed in 0.2.0 packaging

| ID | Severity | Issue | Resolution |
|----|----------|-------|------------|
| A2-1 | High (product) | Flat personal dump: weather/dunst/SDDM Astronaut/`/home/void` | Split **core** vs `contrib/hyde/`; XDG data paths; no theme hardcodes |
| A2-2 | Medium | No LICENSE / SECURITY / install story | MIT + `SECURITY.md` + `install.sh` / `uninstall.sh` |
| A2-3 | Medium | Assets only under `~/Videos/wallpapers` | `~/.local/share/videolock` + env overrides + legacy fallback |
| A2-4 | Low | RU-only UI | `VIDEOLOCK_LANG` + locale auto (`en`/`ru`) |
| A2-5 | Low | No `--version` / `--check` | Added |
| A2-6 | Low | App id `local.void.videolock` | `org.videolock.VideoLock` |
| A2-7 | Info | Dual Super+L documented only | `examples/` + SECURITY tip |

#### Remaining accepted risks

| ID | Severity | Issue | Notes |
|----|----------|-------|-------|
| R1 | Info | Session lock ≠ FDE | Documented |
| R2 | Low | PAM password briefly as Python `str` | Inherent to `python-pam` API; bytearray wiped around call |
| R3 | Low | `unlock.sh` may `SIGKILL` hung locker | Last resort after SIGTERM wait; may leave compositor crash-lock overlay (cleared best-effort) |
| R4 | Low | Frame textures in RAM (~24×1280p) | Bounded; configurable by fewer source frames |
| R5 | Medium (ops) | Installer patches hypridle with regex | Opt-in `--hypridle`; backup configs before use |
| R6 | Info | Gst path unreliable under lock | Default remains JPEG frames |
| R7 | Low | No sandboxed / privileged helper | Runs as user — correct for session lock |

#### Non-issues / intentional

- Escape does not cancel lock.
- Fail-fast without `python-pam` (will not arm lock).
- Flock singleton inside the Python process.
- Contrib wallpaper may `pkill mpvpaper` — isolated from core locker.

---

### Threat model (summary)

| Attacker | Protection |
|----------|------------|
| Casual shoulder-surfer | UI lock + PAM |
| Local user without password | Blocked by PAM + backoff |
| Same-user malware | Can already `ptrace`/inject — outside scope |
| Physical + reboot | None (no FDE) |
| Remote SSH | Unrelated to graphical lock |

---

### Checklist before tagging a public release

- [x] No secrets / hostnames / LAN IPs in repo docs (README is generic)
- [x] MIT LICENSE
- [x] `install.sh` works without HyDE
- [x] Core has zero hard dependency on SDDM Astronaut / Catppuccin paths
- [x] `videolock --check` documents missing deps
- [x] Maintainer: push to public remote (`torwin-job/videolock`)
- [ ] Optional: tag `v0.2.1` + AUR PKGBUILD in `contrib/packaging/`

### Audit note — keyboard layout (fixed in 0.2.1)

Under session-lock, plain Hyprland `bind` for `switchxkblayout` is inactive; need `bindl`.
Auto-reset to primary layout + on-screen indicator closes the “stuck on RU” unlock failure mode.
