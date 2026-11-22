"""UI strings (en/ru)."""
from __future__ import annotations

import locale
import os

STRINGS = {
    "en": {
        "hint": "type password · Enter to unlock",
        "bad_password": "wrong password",
        "wait": "wait {n} s",
        "pam_missing": "python-pam missing — lock cancelled",
        "caps": "CAPS",
        "sleep": "sleep",
        "reboot": "reboot",
        "shutdown": "power",
        "charging": "chg",
        "battery": "bat {n}%",
        "net_off": "net off",
        "wifi": "wifi",
        "eth": "eth",
    },
    "ru": {
        "hint": "ввод пароля · Enter — войти",
        "bad_password": "неверный пароль",
        "wait": "подождите {n} с",
        "pam_missing": "Нет модуля pam — блокировка отменена",
        "caps": "CAPS",
        "sleep": "сон",
        "reboot": "перезагрузка",
        "shutdown": "выкл",
        "charging": "зар",
        "battery": "бат {n}%",
        "net_off": "нет сети",
        "wifi": "wifi",
        "eth": "eth",
    },
}


def ui_lang() -> str:
    forced = os.environ.get("VIDEOLOCK_LANG", "").lower().strip()
    if forced in STRINGS:
        return forced
    try:
        loc = locale.getlocale()[0] or ""
    except Exception:
        loc = ""
    if loc.lower().startswith("ru"):
        return "ru"
    return "en"


def _(key: str, **kwargs) -> str:
    lang = ui_lang()
    text = STRINGS.get(lang, STRINGS["en"]).get(key) or STRINGS["en"][key]
    return text.format(**kwargs) if kwargs else text
