-- HyDE / Hyprland Lua: single Super+L path → videolock (skip loginctl hop)
local home = os.getenv("HOME") or ("/home/" .. (os.getenv("USER") or "user"))

hl.env("LOCKSCREEN", "videolock")
hl.env("HYDE_LOCKSCREEN", "videolock")
hl.env("HYPRLAND_LOCKSCREEN", "videolock")

hl.bind(
  "SUPER + L",
  hl.dsp.exec_cmd(home .. "/.local/bin/videolock.sh"),
  { description = "Video lock", locked = true }
)

-- Optional: warm decoder on session start
-- hl.on("hyprland.start", function()
--   hl.exec_cmd(home .. "/.local/bin/videolock-warm-video")
-- end)
