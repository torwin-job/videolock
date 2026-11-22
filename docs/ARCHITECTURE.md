# Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User / compositor                                           │
│   Super+L  ──►  videolock.sh  ──►  videolock (launcher)     │
│   hypridle lock_cmd ─────────────►           │               │
│   hypridle unlock_cmd ► videolock-unlock.sh  │               │
└──────────────────────────────────────────────┼───────────────┘
                                               ▼
                                    videolock/ Python package
                                               │
                              Gtk4SessionLock (ext-session-lock-v1)
                                               │
                    ┌──────────────────────────┼──────────────────┐
                    ▼                          ▼                  ▼
              poster / frames            PAM authenticate    SIGTERM→unlock()
           (~/.local/share/videolock)     (python-pam)
```

## Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| Launcher | `bin/videolock` | Resolve package path + `videolock.cli.run` |
| Core package | `videolock/` | Modular lock logic (see below) |
| Lock wrapper | `bin/videolock.sh` | Wayland/Hyprland env only |
| Unlock helper | `bin/videolock-unlock.sh` | Graceful SIGTERM by PID lockfile |
| Assets tool | `scripts/prepare-assets.sh` | ffmpeg → poster + frames + compact mp4 |
| Installer | `install.sh` / `uninstall.sh` | User-local install + optional hypridle patch |
| Examples | `examples/` | hypridle / hyprland snippets |
| Contrib | `contrib/hyde/` | Optional wallpaper / HyDE glue — **not required** |

## Package modules (`videolock/`)

| Module | Role |
|--------|------|
| `cli.py` | argparse, `--check` / `--recover`, Gtk app bootstrap |
| `locker.py` | `VideoLock` — surfaces, PAM, keys, frames/video |
| `gi_bootstrap.py` | GTK4 / Gdk / SessionLock / pam imports |
| `paths.py` | XDG dirs + asset resolution |
| `i18n.py` | en/ru strings |
| `style.py` / `theme.py` / `fonts.py` / `scale.py` | CSS, wallbash, fonts, HiDPI |
| `systeminfo.py` / `widgets.py` | battery/net/power + icon chips |
| `hyprland.py` | hyprctl layout / keymap |
| `security.py` / `recover.py` / `logutil.py` | flock, wipe, crash recover, log |

Installed copy: `~/.local/share/videolock/python/videolock/`.  
Dev / repo: launcher finds `<repo>/videolock/` next to `bin/`.

## Data locations (XDG)

| Kind | Default |
|------|---------|
| Binaries | `~/.local/bin/` |
| Python package | `~/.local/share/videolock/python/videolock/` |
| Assets | `~/.local/share/videolock/{poster.png,video.mp4,frames/}` |
| Cache/log/lock | `~/.cache/videolock/` |
| Config (reserved) | `~/.config/videolock/` |

Env overrides: `VIDEOLOCK_VIDEO`, `VIDEOLOCK_POSTER`, `VIDEOLOCK_FRAMES`, `VIDEOLOCK_GST`, `VIDEOLOCK_LANG`, `VIDEOLOCK_FONT`, `VIDEOLOCK_UI_FONT`, `VIDEOLOCK_PYTHONPATH`.

## Why JPEG frames by default

Under `ext-session-lock`, many compositors do not composite live GStreamer/`Gtk.Video` surfaces reliably. A short JPEG strip is CPU-light and visible. Set `VIDEOLOCK_GST=1` to experiment with real video.

## Out of scope

- Display managers (SDDM/GDM/Plymouth)
- Desktop video wallpaper (`contrib/hyde/mpvpaper-wallpaper.sh`)
- Distro packaging (AUR PKGBUILD welcome as contrib)
