"""GTK CSS for lock panel + corner docks."""
from __future__ import annotations

from .fonts import font_stack, ui_font_stack
from .logutil import log
from .scale import px, ui_scale
from .theme import wallbash_theme


def build_css(scale: float | None = None, theme: dict[str, str] | None = None) -> bytes:
    s = scale if scale is not None else ui_scale()
    display = font_stack()
    ui = ui_font_stack()
    t = theme or wallbash_theme()
    log(f"fonts display={display} ui={ui}")
    return f"""
window {{
  background: {t['bg']};
  font-family: {ui};
}}
label, button, entry, textview {{
  font-family: {ui};
}}
.dim {{ background: rgba(8,12,24,0.22); }}
.panel {{
  background: {t['panel']};
  border: 1px solid {t['border']};
  border-radius: {px(18, s)};
  padding: {px(22, s)} {px(28, s)};
  font-family: {ui};
}}
.clock {{
  color: {t['clock']}; font-size: {px(62, s)}; font-weight: 400;
  font-family: {display};
}}
.date {{ color: {t['date']}; font-size: {px(15, s)}; margin-bottom: {px(10, s)}; font-family: {ui}; }}
.user {{ color: {t['user']}; font-size: {px(14, s)}; margin-bottom: {px(10, s)}; font-family: {display}; }}
.dots {{
  color: {t['dots']}; font-size: {px(24, s)}; letter-spacing: {px(5, s)};
  min-width: {px(280, s)}; min-height: {px(42, s)}; padding: {px(8, s)} {px(14, s)};
  border-radius: {px(12, s)}; background: {t['dots_bg']};
  border: 1px solid {t['dots_border']};
  font-family: {display};
}}
.error {{ color: {t['error']}; font-size: {px(13, s)}; min-height: {px(16, s)}; margin-top: {px(6, s)}; font-family: {ui}; }}
.hint {{ color: {t['hint']}; font-size: {px(12, s)}; margin-top: {px(8, s)}; font-family: {ui}; }}
.status {{
  color: {t['status']}; font-size: {px(12, s)}; margin-top: {px(8, s)}; letter-spacing: {px(2, s)};
  font-family: {display};
}}
.status-warn {{ color: {t['warn']}; }}
.status-caps {{ color: {t['caps']}; }}
.corner-tray {{
  margin: 0 {px(22, s)} {px(22, s)} 0;
}}
.corner-dock {{
  padding: {px(10, s)} {px(12, s)};
  border-radius: {px(14, s)};
  background: {t['panel']};
  border: 1px solid {t['border']};
}}
.info-row, .power-row {{ }}
button.info-chip, .info-chip,
button.power-btn, .power-btn {{
  background: {t['btn_bg']};
  color: {t['btn_fg']};
  border: 1px solid {t['border']};
  border-radius: {px(12, s)};
  padding: {px(6, s)} {px(10, s)};
  font-size: {px(11, s)};
  font-family: {ui};
  min-width: {px(0, s)};
}}
button.info-chip, .info-chip {{ color: {t['status']}; }}
button.info-chip.sys-low, .info-chip.sys-low {{
  color: {t['error']};
  border-color: {t['error']};
}}
button.info-chip:hover, .info-chip:hover,
button.power-btn:hover, .power-btn:hover {{
  border-color: {t['accent']}; color: {t['accent']};
}}
button.power-btn:active, .power-btn:active,
button.info-chip:active, .info-chip:active {{ background: {t['dots_bg']}; }}
button.info-chip image, button.power-btn image {{
  color: inherit;
  -gtk-icon-filter: none;
}}
""".encode()
