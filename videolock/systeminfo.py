"""Battery, network, power actions."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .i18n import _
from .logutil import log


def battery_info() -> tuple[int | None, str]:
    base = Path("/sys/class/power_supply")
    if not base.is_dir():
        return None, ""
    for bat in sorted(base.glob("BAT*")):
        try:
            cap = int((bat / "capacity").read_text().strip())
            st = (bat / "status").read_text().strip()
            return cap, st
        except Exception:
            continue
    return None, ""


def network_info() -> tuple[str, str]:
    """Return (kind, label) where kind is wifi | eth | off."""
    try:
        r = subprocess.run(
            ["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        if r.returncode != 0:
            return "off", _("net_off")
        wifi = eth = None
        for line in (r.stdout or "").splitlines():
            parts = line.split(":")
            if len(parts) < 2:
                continue
            typ, state = parts[0], parts[1]
            conn = parts[2] if len(parts) > 2 else ""
            if typ == "wifi" and state.startswith("connected"):
                wifi = conn or _("wifi")
            elif typ == "ethernet" and state.startswith("connected"):
                eth = conn or _("eth")
        if wifi:
            return "wifi", wifi[:16]
        if eth:
            return "eth", eth[:16]
    except Exception:
        pass
    return "off", _("net_off")


def battery_icon_name(cap: int | None, status: str) -> str:
    if cap is None:
        return "battery-missing-symbolic"
    charging = status.lower() in ("charging",)
    step = max(0, min(10, round(cap / 10))) * 10
    if charging:
        return f"battery-level-{step}-charging-symbolic"
    return f"battery-level-{step}-symbolic"


def network_icon_name(kind: str) -> str:
    if kind == "wifi":
        return "network-wireless-signal-excellent-symbolic"
    if kind == "eth":
        return "network-wired-symbolic"
    return "network-wireless-offline-symbolic"


def power_action(action: str) -> None:
    """Suspend / reboot / poweroff via systemctl."""
    log(f"power action: {action}")
    cmd = {
        "sleep": ["systemctl", "suspend"],
        "reboot": ["systemctl", "reboot"],
        "shutdown": ["systemctl", "poweroff"],
    }.get(action)
    if not cmd:
        return
    try:
        subprocess.Popen(cmd, start_new_session=True)
    except Exception as e:
        log(f"power action failed: {type(e).__name__}")
