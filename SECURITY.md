# Security Policy

## What this protects

`videolock` implements a **Wayland session lock** (`ext-session-lock-v1`).
It blanks/obscures the graphical session until PAM accepts the current user's password.

It does **not**:
- encrypt the disk
- stop another TTY / SSH login
- protect against a compromised kernel or physical DMA attacks

## Reporting

Please open a private security advisory / email the maintainer. Do not file public issues with exploit PoCs against production lockers.

## Design expectations

| Topic | Behavior |
|-------|----------|
| Password storage | In-process `bytearray`, wiped after each PAM attempt |
| Logging | `~/.cache/videolock/` mode `0700` / log `0600`; never logs secrets |
| Missing PAM | Refuses to take the session lock (fail-open for availability, fail-closed for auth UX) |
| Unlock helper | Signals the locker PID from the lockfile; prefers `SessionLock.unlock()` over `pkill -f` |
| Rate limit | Exponential backoff after failed PAM (0.5–8 s) |
| Assets | Frame paths resolved under configured frame dir (symlink escape limited) |

## Hardening tips for deployers

1. Keep `python-pam` installed — without it the locker will not arm.
2. Prefer JPEG frames under session-lock (default) over experimental `VIDEOLOCK_GST=1`.
3. One Super+L path only (direct bind **or** `loginctl lock-session` → hypridle, not both firing duplicate UI).
4. Do not run the locker as root.
