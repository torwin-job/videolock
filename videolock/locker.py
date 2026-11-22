"""Session lock UI + PAM authenticate + background frames/video."""
from __future__ import annotations

import os
import pwd
import signal
import time
import traceback
from datetime import datetime

from .gi_bootstrap import Gdk, GLib, Gtk, SessionLock, pam
from .hyprland import (
    active_keymap_raw,
    caps_lock_on,
    reset_keyboard_layout,
    short_layout,
)
from .i18n import _
from .logutil import log
from .paths import FRAME_DIR, POSTER, VIDEO
from .security import wipe_bytearray
from .systeminfo import (
    battery_icon_name,
    battery_info,
    network_icon_name,
    network_info,
    power_action,
)
from .widgets import make_icon_chip


class VideoLock:
    def __init__(self, app: Gtk.Application):
        self.app = app
        self.user = pwd.getpwuid(os.getuid()).pw_name
        self._pw = bytearray()
        self._fail_count = 0
        self._unlock_blocked_until = 0.0
        self._clock_pairs: list[tuple[Gtk.Label, Gtk.Label]] = []
        self._dot_labels: list[Gtk.Label] = []
        self._err_labels: list[Gtk.Label] = []
        self._monitors_done: set[str] = set()
        self._windows: list[Gtk.Window] = []
        self._bg_stack: list[Gtk.Stack] = []
        self._media = None
        self._frame_textures: list = []
        self._frame_i = 0
        self._using_frames = False
        self._shutting_down = False
        self._status_labels: list[Gtk.Label] = []
        # (bat_btn, bat_icon, bat_lab, net_btn, net_icon, net_lab) per monitor
        self._sys_chips: list[
            tuple[Gtk.Button, Gtk.Image, Gtk.Label, Gtk.Button, Gtk.Image, Gtk.Label]
        ] = []
        self._layout_code = "?"
        self._caps = False

        self.lock = SessionLock.Instance.new()
        self.lock.connect("locked", lambda *_: log("locked"))
        self.lock.connect("unlocked", self._on_unlocked)
        self.lock.connect("failed", self._on_failed)
        self.lock.connect("monitor", self._on_monitor)

        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)

    def _on_signal(self, signum, _frame):
        log(f"signal {signum} — graceful unlock")
        GLib.idle_add(self._graceful_unlock)

    def _graceful_unlock(self):
        if self._shutting_down:
            return False
        try:
            if self.lock.is_locked():
                self.lock.unlock()
            else:
                self._shutdown()
        except Exception as e:
            log(f"graceful unlock: {e}")
            self._shutdown()
        return False

    def _on_unlocked(self, *_):
        log("unlocked")
        self._shutdown()

    def _on_failed(self, *_):
        log("failed")
        self._shutdown()

    def _shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        self._wipe_password()
        if self._media is not None:
            try:
                self._media.pause()
            except Exception:
                pass
            self._media = None
        try:
            self.app.release()
        except Exception:
            pass
        self.app.quit()

    def start(self) -> None:
        if pam is None:
            log("FATAL: python pam module missing — refusing to lock")
            try:
                from subprocess import Popen
                Popen(
                    ["notify-send", "-u", "critical", "videolock", _("pam_missing")],
                    start_new_session=True,
                )
            except Exception:
                pass
            self.app.quit()
            return
        if not SessionLock.is_supported():
            log("unsupported: ext-session-lock-v1")
            self._shutdown()
            return
        self.app.hold()
        # Critical: unlock passwords are almost always ASCII — reset to primary layout
        reset_keyboard_layout()
        self._layout_code = short_layout(active_keymap_raw())
        self._caps = caps_lock_on(False)
        self._refresh_status_labels()
        log(
            f"lock() video={VIDEO} frames={FRAME_DIR} poster={POSTER} "
            f"gst={os.environ.get('VIDEOLOCK_GST', '0')} layout={self._layout_code}"
        )
        ok = self.lock.lock()
        log(f"lock -> {ok!r} locked={self.lock.is_locked()}")
        if not ok and not self.lock.is_locked():
            GLib.timeout_add(200, self._retry_lock, 1)
        GLib.timeout_add_seconds(1, self._tick_clock)
        GLib.timeout_add(400, self._tick_status)
        GLib.timeout_add_seconds(5, self._tick_sys)
        self._refresh_sys_labels()

    def _retry_lock(self, attempt: int):
        if self.lock.is_locked():
            return False
        ok = self.lock.lock()
        if ok or self.lock.is_locked():
            return False
        if attempt >= 5:
            self._shutdown()
            return False
        GLib.timeout_add(200, self._retry_lock, attempt + 1)
        return False

    def _tick_clock(self):
        now = datetime.now()
        t, d = now.strftime("%H:%M"), now.strftime("%A, %d %B")
        for c, dt in self._clock_pairs:
            c.set_label(t)
            dt.set_label(d)
        return True

    def _status_text(self) -> str:
        parts = [self._layout_code or "?"]
        if self._caps:
            parts.append(_("caps"))
        return " · ".join(parts)

    def _refresh_status_labels(self) -> None:
        text = self._status_text()
        for lab in self._status_labels:
            lab.set_label(text)
            if self._caps:
                lab.add_css_class("status-caps")
                lab.remove_css_class("status-warn")
            elif (self._layout_code or "").upper() not in ("US", "EN", "?"):
                lab.add_css_class("status-warn")
                lab.remove_css_class("status-caps")
            else:
                lab.remove_css_class("status-warn")
                lab.remove_css_class("status-caps")

    def _poll_status(self) -> None:
        raw = active_keymap_raw()
        if raw:
            self._layout_code = short_layout(raw)
        self._caps = caps_lock_on(self._caps)
        self._refresh_status_labels()

    def _poll_status_once(self):
        if not self._shutting_down:
            self._poll_status()
        return False

    def _tick_status(self):
        if self._shutting_down:
            return False
        self._poll_status()
        return True

    def _refresh_sys_labels(self) -> None:
        cap, st = battery_info()
        kind, net_label = network_info()
        if cap is None:
            bat_text = "—"
        else:
            bat_text = f"{cap}%"
            if st.lower() in ("charging", "full"):
                bat_text = f"{bat_text} · {_('charging')}"
        bat_icon = battery_icon_name(cap, st)
        net_icon = network_icon_name(kind)
        low = cap is not None and cap <= 20
        for bat_btn, bat_img, bat_lab, net_btn, net_img, net_lab in self._sys_chips:
            bat_lab.set_label(bat_text)
            net_lab.set_label(net_label)
            bat_img.set_from_icon_name(bat_icon)
            net_img.set_from_icon_name(net_icon)
            if low:
                bat_btn.add_css_class("sys-low")
            else:
                bat_btn.remove_css_class("sys-low")
            if kind == "off":
                net_btn.add_css_class("sys-low")
            else:
                net_btn.remove_css_class("sys-low")

    def _tick_sys(self):
        if self._shutting_down:
            return False
        self._refresh_sys_labels()
        return True

    def _update_dots(self):
        dots = "●" * len(self._pw) if self._pw else " "
        for lab in self._dot_labels:
            lab.set_label(dots)

    def _wipe_password(self):
        wipe_bytearray(self._pw)

    def _clear_password(self):
        self._wipe_password()
        self._update_dots()

    def _authenticate(self) -> bool:
        if pam is None:
            return False
        secret = self._pw.decode("utf-8", errors="surrogateescape")
        try:
            return bool(pam.pam().authenticate(self.user, secret))
        except Exception as e:
            log(f"pam error: {type(e).__name__}")
            return False
        finally:
            secret = "\0" * len(secret)
            del secret
            self._wipe_password()

    def _set_errors(self, text: str):
        for err in self._err_labels:
            err.set_label(text)

    def _try_unlock(self):
        now = time.monotonic()
        if now < self._unlock_blocked_until:
            left = int(self._unlock_blocked_until - now) + 1
            self._set_errors(_("wait", n=left))
            return

        if self._authenticate():
            self._fail_count = 0
            self.lock.unlock()
            return

        self._fail_count += 1
        delay = min(8.0, 0.5 * (2 ** min(self._fail_count - 1, 4)))
        self._unlock_blocked_until = time.monotonic() + delay
        self._set_errors(_("bad_password"))
        self._clear_password()
        GLib.timeout_add(int(delay * 1000), self._clear_backoff_message)

    def _clear_backoff_message(self):
        if time.monotonic() >= self._unlock_blocked_until:
            self._set_errors("")
        return False

    def _on_key(self, _ctrl, keyval: int, _keycode: int, state: Gdk.ModifierType) -> bool:
        # Track caps from modifiers; Caps_Lock toggles after this event → idle refresh
        self._caps = bool(state & Gdk.ModifierType.LOCK_MASK) or caps_lock_on(
            bool(state & Gdk.ModifierType.LOCK_MASK)
        )
        if keyval == Gdk.KEY_Caps_Lock:
            GLib.timeout_add(50, self._poll_status_once)
            return True
        if keyval in (
            Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, Gdk.KEY_Control_L, Gdk.KEY_Control_R,
            Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R,
            Gdk.KEY_Super_L, Gdk.KEY_Super_R, Gdk.KEY_Num_Lock,
        ):
            # Alt/Shift may switch XKB group — refresh layout shortly
            if keyval in (Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Shift_L, Gdk.KEY_Shift_R):
                GLib.timeout_add(80, self._poll_status_once)
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._try_unlock()
            return True
        if keyval == Gdk.KEY_Escape:
            return True
        if time.monotonic() < self._unlock_blocked_until:
            self._refresh_status_labels()
            return True
        if keyval == Gdk.KEY_BackSpace:
            if self._pw:
                self._pw.pop()
                self._update_dots()
                self._set_errors("")
            return True
        if keyval == Gdk.KEY_u and (state & Gdk.ModifierType.CONTROL_MASK):
            self._clear_password()
            return True
        ch = Gdk.keyval_to_unicode(keyval)
        if ch and ch >= 32:
            if len(self._pw) < 256:
                self._pw.extend(chr(ch).encode("utf-8"))
            self._update_dots()
            self._set_errors("")
            # Typing often follows layout toggle — keep indicator fresh
            GLib.timeout_add(50, self._poll_status_once)
            return True
        self._refresh_status_labels()
        return True

    def _start_gst_video(self, stack: Gtk.Stack, video_page: Gtk.Widget):
        if not VIDEO.is_file():
            log("no video file")
            self._start_frame_fallback(stack, video_page)
            return
        try:
            v = Gtk.Video.new_for_filename(str(VIDEO))
            for setter, arg in (
                ("set_autoplay", True),
                ("set_loop", True),
                ("set_controls", False),
                ("set_muted", True),
            ):
                try:
                    getattr(v, setter)(arg)
                except Exception:
                    pass
            v.set_hexpand(True)
            v.set_vexpand(True)
            try:
                stack.remove(video_page)
            except Exception:
                pass
            stack.add_named(v, "video")
            stack.set_visible_child_name("video")
            self._media = v
            log("Gtk.Video started")
            try:
                mf = v.get_media_stream()
                if mf is not None:
                    mf.set_loop(True)
                    try:
                        mf.set_muted(True)
                    except Exception:
                        pass
                    mf.play()
            except Exception as e:
                log(f"stream poke: {type(e).__name__}")

            def watchdog():
                try:
                    mf = v.get_media_stream()
                    ok = mf is not None and mf.get_playing()
                except Exception:
                    ok = False
                if ok:
                    log("watchdog: Gtk.Video ok")
                    return False
                log("watchdog: fallback to frames")
                pic = Gtk.Picture()
                if hasattr(pic, "set_content_fit"):
                    pic.set_content_fit(Gtk.ContentFit.COVER)
                pic.set_hexpand(True)
                pic.set_vexpand(True)
                try:
                    stack.remove(v)
                except Exception:
                    pass
                stack.add_named(pic, "video")
                self._start_frame_fallback(stack, pic)
                return False

            GLib.timeout_add(1500, watchdog)
        except Exception as e:
            log(f"Gtk.Video fail: {type(e).__name__}")
            self._start_frame_fallback(stack, video_page)

    def _load_frame_textures(self):
        if self._frame_textures:
            return
        paths = sorted(FRAME_DIR.glob("f-*.jpg")) if FRAME_DIR.is_dir() else []
        safe: list[Path] = []
        try:
            root = FRAME_DIR.resolve()
        except Exception:
            root = FRAME_DIR
        for fp in paths:
            try:
                rp = fp.resolve()
                if root in rp.parents or rp.parent == root:
                    safe.append(fp)
            except Exception:
                continue
        paths = safe
        if len(paths) > 24:
            step = max(1, len(paths) // 24)
            paths = paths[::step][:24]
        for fp in paths:
            try:
                self._frame_textures.append(Gdk.Texture.new_from_filename(str(fp)))
            except Exception as e:
                log(f"tex skip: {type(e).__name__}")
        log(f"textures={len(self._frame_textures)}")

    def _start_frame_fallback(self, stack: Gtk.Stack, video_page: Gtk.Picture):
        if self._using_frames:
            return
        self._using_frames = True
        if self._media is not None:
            try:
                self._media.pause()
            except Exception:
                pass
            self._media = None
        self._load_frame_textures()
        if not self._frame_textures:
            log("no frames; keep poster/solid")
            return
        video_page.set_paintable(self._frame_textures[0])
        stack.set_visible_child_name("video")

        def tick():
            if not self._using_frames or not self._frame_textures:
                return False
            self._frame_i = (self._frame_i + 1) % len(self._frame_textures)
            tex = self._frame_textures[self._frame_i]
            for st in self._bg_stack:
                child = st.get_child_by_name("video")
                if child is not None:
                    try:
                        child.set_paintable(tex)
                    except Exception:
                        pass
            return True

        GLib.timeout_add(125, tick)
        log("frame animation running")

    def _on_monitor(self, _lock, monitor: Gdk.Monitor):
        try:
            try:
                mid = monitor.get_connector() or monitor.get_description() or "mon"
            except Exception:
                mid = "mon"
            if mid in self._monitors_done:
                return
            self._monitors_done.add(mid)
            log(f"monitor {mid}")

            win = Gtk.Window()
            win.set_decorated(False)
            win.set_can_focus(True)
            win.set_focusable(True)

            overlay = Gtk.Overlay()
            win.set_child(overlay)

            stack = Gtk.Stack()
            stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            stack.set_transition_duration(200)
            stack.set_hexpand(True)
            stack.set_vexpand(True)

            poster = Gtk.Picture()
            if POSTER.is_file():
                poster.set_filename(str(POSTER))
            if hasattr(poster, "set_content_fit"):
                poster.set_content_fit(Gtk.ContentFit.COVER)
            poster.set_hexpand(True)
            poster.set_vexpand(True)

            video_page = Gtk.Picture()
            if hasattr(video_page, "set_content_fit"):
                video_page.set_content_fit(Gtk.ContentFit.COVER)
            video_page.set_hexpand(True)
            video_page.set_vexpand(True)

            stack.add_named(poster, "poster")
            stack.add_named(video_page, "video")
            stack.set_visible_child_name("poster")
            self._bg_stack.append(stack)

            dim = Gtk.Box()
            dim.add_css_class("dim")
            dim.set_hexpand(True)
            dim.set_vexpand(True)

            overlay.set_child(stack)
            overlay.add_overlay(dim)

            panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            panel.add_css_class("panel")
            panel.set_halign(Gtk.Align.CENTER)
            panel.set_valign(Gtk.Align.CENTER)

            clock = Gtk.Label(label=datetime.now().strftime("%H:%M"))
            clock.add_css_class("clock")
            date = Gtk.Label(label=datetime.now().strftime("%A, %d %B"))
            date.add_css_class("date")
            user = Gtk.Label(label=self.user)
            user.add_css_class("user")
            dots = Gtk.Label(label=" ")
            dots.add_css_class("dots")
            dots.set_xalign(0.0)
            err = Gtk.Label(label="")
            err.add_css_class("error")
            hint = Gtk.Label(label=_("hint"))
            hint.add_css_class("hint")
            status = Gtk.Label(label=self._status_text())
            status.add_css_class("status")

            for w in (clock, date, user, dots, err, hint, status):
                panel.append(w)
            overlay.add_overlay(panel)

            # Two sibling docks bottom-right: [bat|wifi] then [sleep|reboot|power].
            tray = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            tray.add_css_class("corner-tray")
            tray.set_halign(Gtk.Align.END)
            tray.set_valign(Gtk.Align.END)

            status_dock = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            status_dock.add_css_class("corner-dock")
            status_dock.add_css_class("info-row")
            cap0, st0 = battery_info()
            kind0, net0 = network_info()
            bat_text0 = f"{cap0}%" if cap0 is not None else "—"
            bat_btn, bat_img, bat_lab = make_icon_chip(
                battery_icon_name(cap0, st0), bat_text0, "info-chip"
            )
            net_btn, net_img, net_lab = make_icon_chip(
                network_icon_name(kind0), net0, "info-chip"
            )
            status_dock.append(bat_btn)
            status_dock.append(net_btn)

            power_dock = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            power_dock.add_css_class("corner-dock")
            power_dock.add_css_class("power-row")
            for action, label_key, icon_name in (
                ("sleep", "sleep", "system-suspend-symbolic"),
                ("reboot", "reboot", "system-reboot-symbolic"),
                ("shutdown", "shutdown", "system-shutdown-symbolic"),
            ):
                btn, _ic, _lb = make_icon_chip(icon_name, _(label_key), "power-btn")
                btn.connect(
                    "clicked",
                    lambda _b, act=action: power_action(act),
                )
                power_dock.append(btn)

            tray.append(status_dock)
            tray.append(power_dock)
            overlay.add_overlay(tray)

            self._clock_pairs.append((clock, date))
            self._dot_labels.append(dots)
            self._err_labels.append(err)
            self._status_labels.append(status)
            self._sys_chips.append((bat_btn, bat_img, bat_lab, net_btn, net_img, net_lab))
            self._windows.append(win)
            self._refresh_status_labels()
            self._refresh_sys_labels()

            key = Gtk.EventControllerKey()
            key.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            key.connect("key-pressed", self._on_key)
            win.add_controller(key)

            self.lock.assign_window_to_monitor(win, monitor)
            win.present()
            log("surface ok")

            def _boot():
                if os.environ.get("VIDEOLOCK_GST", "0") == "1":
                    self._start_gst_video(stack, video_page)
                else:
                    self._start_frame_fallback(stack, video_page)
                return False

            GLib.idle_add(_boot)
        except Exception:
            log(traceback.format_exc())

