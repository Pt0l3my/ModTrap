"""MO2's list of programs its virtual file system leaves alone, and adding a compiler to it (MT32, WHY§94).

MO2 hooks every program a tool starts, so that it too sees the modlist's files. MO2's own settings hold a list of
programs that are not hooked (MO01§11): browsers and the like by default. A compiler that a tool starts to build
its own code reads nothing of the modlist, and on some PCs it crashes when hooked (TL01§22). Naming it in that list
is MO2's own answer to a program that does not take the hooking.

One value of one section of `ModOrganizer.ini` is changed, and only when a tool's own log has shown the crash.
MO2 must be closed (it writes its settings when it closes); a copy of the file as it was is kept first; every other
byte of the file stays as it is.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from . import paths
from .instance import ini_value

INI = "ModOrganizer.ini"
SECTION = "Settings"
KEY = "executable_blacklist"
# What MO2 takes the list to be while the settings file does not name one (MO01§11): kept when ModTrap writes the key.
DEFAULT = ("Chrome.exe", "Firefox.exe", "TSVNCache.exe", "TGitCache.exe", "Steam.exe", "GameOverlayUI.exe",
           "Discord.exe", "GalaxyClient.exe", "Spotify.exe", "Brave.exe")
INI_MAX = 32 * 1024 * 1024
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ +\-]{0,80}\.(exe|dll)", re.IGNORECASE)


def _lines(raw: bytes) -> list[str]:
    return raw.decode("latin-1").splitlines(keepends=True)        # one byte, one character: nothing is re-coded


def _find(lines: list[str]) -> tuple[int | None, int | None, int | None]:
    """(the line of the section's header, the line of the key in it, the line after the section's last line)."""
    head = key = end = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            if head is not None and end is None:
                end = i
            if s[1:-1].strip().lower() == SECTION.lower() and head is None:
                head = i
            continue
        if head is not None and end is None and key is None and re.match(r"\s*%s\s*=" % re.escape(KEY), line, re.IGNORECASE):
            key = i
    if head is not None and end is None:
        end = len(lines)
    return head, key, end


def listed(root: Path) -> tuple[list[str], bool] | None:
    """The programs MO2 leaves alone, and whether the settings file names the list itself (else MO2's own
    default holds). None when the file cannot be read."""
    f = root / INI
    try:
        if f.stat().st_size > INI_MAX:
            return None
        lines = _lines(f.read_bytes())
    except OSError:
        return None
    _head, key, _end = _find(lines)
    if key is None:
        return list(DEFAULT), False
    value = ini_value(lines[key].split("=", 1)[1])
    return [x.strip() for x in value.split(";") if x.strip()], True


def missing(root: Path, programs: list[str]) -> list[str]:
    """Those of `programs` that MO2's list does not name yet."""
    got = listed(root)
    if got is None:
        return []
    have = {x.casefold() for x in got[0]}
    return [p for p in programs if _NAME.fullmatch(p) and p.casefold() not in have]


def add(root: Path, programs: list[str], keep_in: Path) -> dict:
    """Adds programs to MO2's list. {"added", "kept", "listed"}; raises OSError or ValueError, with nothing changed,
    when the file cannot be read or written. The caller has made sure MO2 is closed."""
    f = root / INI
    raw = f.read_bytes()
    if len(raw) > INI_MAX:
        raise ValueError("MO2's settings file is larger than ModTrap reads")
    lines = _lines(raw)
    head, key, end = _find(lines)
    current = [x.strip() for x in ini_value(lines[key].split("=", 1)[1]).split(";") if x.strip()] if key is not None else list(DEFAULT)
    have = {x.casefold() for x in current}
    new = [p for p in programs if _NAME.fullmatch(p) and p.casefold() not in have]
    if not new:
        return {"added": [], "kept": "", "listed": current}
    value = ";".join(current + new)
    if any(c in value for c in '"\\\r\n'):
        raise ValueError("the list holds a name ModTrap does not write")
    newline = "\r\n" if raw.count(b"\r\n") else "\n"
    text = '%s="%s"' % (KEY, value)
    if head is None or end is None:                                  # no such section yet: it is added at the end
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += newline
        lines += ["[%s]" % SECTION + newline, text + newline]
    elif key is not None:
        ending = lines[key][len(lines[key].rstrip("\r\n")):]
        lines[key] = text + (ending or newline)
    else:
        at = end
        while at > head + 1 and not lines[at - 1].strip():          # before the blank lines that close the section
            at -= 1
        if at > 0 and not lines[at - 1].endswith(("\n", "\r")):
            lines[at - 1] += newline
        lines.insert(at, text + newline)
    keep_in.mkdir(parents=True, exist_ok=True)
    kept = keep_in / ("%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), INI))
    n = 2
    while kept.exists():
        kept, n = keep_in / ("%s-%d-%s" % (time.strftime("%Y%m%d-%H%M%S"), n, INI)), n + 1
    shutil.copyfile(f, kept)
    if kept.read_bytes() != raw:
        raise OSError("MO2's settings file changed while ModTrap read it")
    paths.write_atomic(f, "".join(lines).encode("latin-1"))
    return {"added": new, "kept": kept.name, "listed": current + new}


__all__ = ["DEFAULT", "INI", "add", "listed", "missing"]
