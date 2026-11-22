# Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User / compositor                                           │
│   Super+L  ──►  videolock.sh  ──►  videolock (Python/GTK4)  │
│   hypridle lock_cmd ─────────────►           │               │
│   hypridle unlock_cmd ► videolock-unlock.sh  │               │
└──────────────────────────────────────────────┼───────────────┘
                                               ▼
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
| Core locker | `bin/videolock` | Session lock UI, PAM, backoff, flock, assets |
| Lock wrapper | `bin/videolock.sh` | Wayland/Hyprland env only |
| Unlock helper | `bin/videolock-unlock.sh` | Graceful SIGTERM by PID lockfile |
| Assets tool | `scripts/prepare-assets.sh` | ffmpeg → poster + frames + compact mp4 |
| Installer | `install.sh` / `uninstall.sh` | User-local install + optional hypridle patch |
| Examples | `examples/` | hypridle / hyprland snippets |
| Contrib | `contrib/hyde/` | Optional wallpaper / HyDE glue — **not required** |

## Data locations (XDG)

| Kind | Default |
|------|---------|
| Binaries | `~/.local/bin/` |
| Assets | `~/.local/share/videolock/{poster.png,video.mp4,frames/}` |
| Cache/log/lock | `~/.cache/videolock/` |
| Config (reserved) | `~/.config/videolock/` |

Env overrides: `VIDEOLOCK_VIDEO`, `VIDEOLOCK_POSTER`, `VIDEOLOCK_FRAMES`, `VIDEOLOCK_GST`, `VIDEOLOCK_LANG`, `VIDEOLOCK_FONT`.

## Why JPEG frames by default

Under `ext-session-lock`, many compositors do not composite live GStreamer/`Gtk.Video` surfaces reliably. A short JPEG strip is CPU-light and visible. Set `VIDEOLOCK_GST=1` to experiment with real video.

## Out of scope

- Display managers (SDDM/GDM/Plymouth)
- Desktop video wallpaper (`contrib/hyde/mpvpaper-wallpaper.sh`)
- Distro packaging (AUR PKGBUILD welcome as contrib)
