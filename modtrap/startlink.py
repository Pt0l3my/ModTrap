"""A link that starts ModTrap (MT64, DESIGN§26).

When ModTrap has closed with its tab and the browser brings that tab back, the page ModTrap's worker kept in the
browser shows instead, and asks the browser to open a link of the kind `modtrap:`. Windows starts ModTrap.exe for
such a link, once that kind of link is entered for this Windows account.

What makes this safe:
- the entry names this ModTrap.exe and nothing else, and hands on nothing of the link: whatever a link says after
  `modtrap:`, ModTrap is started the one same way, as a double-click on it does. A link cannot give it a switch,
  a folder or a file;
- any web page can show such a link, and the browser asks before it opens one. All it can ever do is start ModTrap,
  which then waits for its own page and does nothing by itself;
- it is one entry under this account's own part of the registry (no administrator's rights, nothing for other
  accounts), written only by a ModTrap started from its package, and taken out again by the setting.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCHEME = "modtrap"
SWITCH = "--from-page"
KEY = r"Software\Classes\%s" % SCHEME


def command(exe: Path) -> str:
    """What Windows runs for the link. No "%1": nothing of the link reaches the command line."""
    return '"%s" %s' % (exe, SWITCH)


def _reg():
    if sys.platform != "win32":
        return None
    import winreg
    return winreg


def entered(reg=None) -> str:
    """The command entered for the link, or "" where there is none."""
    reg = reg or _reg()
    if reg is None:
        return ""
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, KEY + r"\shell\open\command") as k:
            return str(reg.QueryValueEx(k, "")[0])
    except OSError:
        return ""


def enter(exe: Path, reg=None) -> bool:
    """Enters the link for this account, pointing at `exe`. True when something was written."""
    reg = reg or _reg()
    if reg is None or "%" in str(exe) or '"' in str(exe):
        return False
    want = command(exe)
    if entered(reg) == want:
        return False
    with reg.CreateKey(reg.HKEY_CURRENT_USER, KEY) as k:
        reg.SetValueEx(k, "", 0, reg.REG_SZ, "URL:ModTrap")
        reg.SetValueEx(k, "URL Protocol", 0, reg.REG_SZ, "")
    with reg.CreateKey(reg.HKEY_CURRENT_USER, KEY + r"\shell\open\command") as k:
        reg.SetValueEx(k, "", 0, reg.REG_SZ, want)
    return True


def remove(exe: Path | None = None, reg=None) -> bool:
    """Takes the entry out again; with `exe`, only when it points at that program. True when it was taken out."""
    reg = reg or _reg()
    if reg is None:
        return False
    now = entered(reg)
    if not now or (exe is not None and now != command(exe)):
        return False
    for sub in (r"\shell\open\command", r"\shell\open", r"\shell", ""):
        try:
            reg.DeleteKey(reg.HKEY_CURRENT_USER, KEY + sub)
        except OSError:
            return False
    return True


__all__ = ["SCHEME", "SWITCH", "command", "enter", "entered", "remove"]
