"""CLI entry: --check / --recover / run Gtk application."""
from __future__ import annotations

import argparse
import os
import traceback
from datetime import datetime

from . import __version__
from .logutil import log
from .paths import CACHE_DIR, DATA_DIR, FRAME_DIR, LOG, POSTER, VIDEO
from .recover import recover_session
from .security import acquire_singleton


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="videolock",
        description="Wayland session lock for Hyprland (GTK4 + PAM).",
    )
    p.add_argument("-V", "--version", action="version", version=f"videolock {__version__}")
    p.add_argument(
        "--check",
        action="store_true",
        help="verify dependencies and asset paths, then exit",
    )
    p.add_argument(
        "--recover",
        action="store_true",
        help="recover from crashed lock: stop hung locker + clear crash overlay",
    )
    return p.parse_args(argv)


def check() -> int:
    from .gi_bootstrap import SessionLock, pam
    from .scale import ui_scale

    ok = True
    scale = ui_scale()
    print(f"videolock {__version__}")
    print(f"  cache:  {CACHE_DIR}")
    print(f"  data:   {DATA_DIR}")
    print(f"  scale:  {scale:.2f} (override VIDEOLOCK_SCALE)")
    print(f"  poster: {POSTER}  [{'ok' if POSTER.is_file() else 'missing'}]")
    print(f"  video:  {VIDEO}  [{'ok' if VIDEO.is_file() else 'missing'}]")
    nframes = len(list(FRAME_DIR.glob("f-*.jpg"))) if FRAME_DIR.is_dir() else 0
    print(f"  frames: {FRAME_DIR}  [{nframes} jpg]")
    if pam is None:
        print("  pam:    MISSING (python-pam / python3-pam)")
        ok = False
    else:
        print("  pam:    ok")
    if not SessionLock.is_supported():
        print("  lock:   ext-session-lock-v1 NOT supported on this compositor")
        ok = False
    else:
        print("  lock:   supported")
    return 0 if ok else 1


def _run_app() -> int:
    from .gi_bootstrap import Gdk, Gio, Gtk
    from .locker import VideoLock
    from .scale import ui_scale
    from .style import build_css
    from .theme import wallbash_theme

    if not acquire_singleton():
        log("already running — exit")
        return 0

    try:
        fd = os.open(str(LOG), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(f"start {datetime.now().isoformat()} v{__version__}\n")
    except Exception:
        pass

    app = Gtk.Application(
        application_id="org.videolock.VideoLock",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )

    def on_activate(app: Gtk.Application):
        app.hold()
        scale = ui_scale()
        theme = wallbash_theme()
        log(f"ui scale={scale:.2f} accent={theme.get('accent')}")
        css = Gtk.CssProvider()
        css.load_from_data(build_css(scale, theme))
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        app._videolock = VideoLock(app)  # noqa: SLF001 — keep GC ref
        app._videolock.start()

    app.connect("activate", on_activate)
    return app.run([]) or 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.recover:
        return recover_session()
    if args.check:
        return check()
    return _run_app()


def run() -> None:
    try:
        raise SystemExit(main())
    except Exception:
        log(traceback.format_exc())
        raise
