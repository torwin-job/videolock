-- HyDE / Hyprland Lua: single Super+L path → videolock (skip loginctl hop)
local home = os.getenv("HOME") or ("/home/" .. (os.getenv("USER") or "user"))

hl.env("LOCKSCREEN", "videolock")
hl.env("HYDE_LOCKSCREEN", "videolock")
hl.env("HYPRLAND_LOCKSCREEN", "videolock")

-- locked=true ≈ bindl: usable while session is locked
hl.bind(
  "SUPER + L",
  hl.dsp.exec_cmd(home .. "/.local/bin/videolock.sh"),
  { description = "Video lock", locked = true }
)

-- Layout toggle on the LOCK screen (critical for us,ru password entry).
-- Prefer this over a non-locked bind; XKB grp:alt_shift_toggle also works.
hl.bind(
  "SUPER + SPACE",
  hl.dsp.exec_cmd("hyprctl switchxkblayout current next"),
  { description = "Keyboard layout", locked = true }
)

-- Optional: warm decoder on session start
-- hl.on("hyprland.start", function()
--   hl.exec_cmd(home .. "/.local/bin/videolock-warm-video")
-- end)
