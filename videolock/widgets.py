"""Small GTK widgets used on the lock surface."""
from __future__ import annotations

from .gi_bootstrap import Gtk


def make_icon_chip(
    icon_name: str, text: str, css: str = "info-chip"
) -> tuple[Gtk.Button, Gtk.Image, Gtk.Label]:
    """Pill button with symbolic icon + label (status chip or power action)."""
    btn = Gtk.Button()
    btn.add_css_class(css)
    btn.set_focusable(False)
    btn.set_can_focus(False)
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    icon = Gtk.Image.new_from_icon_name(icon_name)
    if hasattr(icon, "set_icon_size"):
        icon.set_icon_size(Gtk.IconSize.NORMAL)
    icon.set_pixel_size(16)
    lab = Gtk.Label(label=text)
    lab.set_xalign(0.0)
    row.append(icon)
    row.append(lab)
    btn.set_child(row)
    return btn, icon, lab
