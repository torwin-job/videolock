# Screenshots

Preview shots for README / r/unixporn style posts.

| File | Notes |
|------|--------|
| `hero.jpg` | Full lock composition |
| `wide.jpg` | Wide wallpaper + panel |
| `panel.jpg` | Closer panel crop |

To capture **live** frames from your session (Hyprland):

```bash
# while unlocked:
grim assets/screenshots/desktop.png

# lock, wait ~1s, shoot (may be blocked by session-lock on some setups):
videolock.sh &
sleep 1
grim assets/screenshots/lock-live.png
videolock-unlock.sh
```

If `grim` is blocked under session-lock, use a second machine / phone photo, or a short screen recording export.
