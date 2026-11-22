"""Load native libs + GI bindings once (GTK4 / Gdk / SessionLock / PAM)."""
from __future__ import annotations

import os
from ctypes import CDLL

os.environ.setdefault("GTK_IM_MODULE", "none")
os.environ.setdefault("GST_PLUGIN_FEATURE_RANK", "vah264dec:MAX,vaapih264dec:MAX")

for lib in ("libgtk4-layer-shell.so", "libgtk-session-lock.so"):
    try:
        CDLL(lib)
    except OSError:
        pass

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4SessionLock", "1.0")

from gi.repository import Gdk, GLib, Gio, Gtk, Gtk4SessionLock as SessionLock

try:
    import pam
except ImportError:
    pam = None

__all__ = ["Gdk", "GLib", "Gio", "Gtk", "SessionLock", "pam"]
