"""Finding a dropped modlist folder on disk (WHY§30). A browser never tells a page where a dropped folder is, so the
page sends the folder's name and the bytes of its ModOrganizer.ini, and this module finds the folder:

1. the absolute paths inside that ini (MO2's configured executables and the game usually sit inside the instance)
   give candidate folders, as do the folders opened before;
2. failing that, a bounded search of the drives for a folder of that name;
3. a candidate is accepted if its own ModOrganizer.ini is the same file, by sha256; or, when MO2 has rewritten the
   file since the drop, if it is the only candidate of that name that is an instance of the same game.

Read-only: it lists folder names and reads ModOrganizer.ini files, nothing else. The search looks at fixed drives
only, never follows a link or a junction, and never opens a file that a cloud drive would have to download. The
dropped ini is used in memory and never logged or stored.
"""

from __future__ import annotations

import hashlib
import os
import re
import string
import time
from pathlib import Path

from .instance import INI_NAME, READ_CAP, fold, ini_value, parse_ini

INI_CAP = 2 * 1024 * 1024
SEARCH_DEPTH = 3                 # the folder may be this many levels below a drive's root
SEARCH_FOLDERS = 60_000          # folders listed at most, over all drives
SEARCH_SECONDS = 6.0
SKIP = {"windows", "$recycle.bin", "system volume information", "programdata", "$windows.~bt", "$windows.~ws",
        "recovery", "msocache", "perflogs", "proc", "sys", "dev"}
_ABSOLUTE = re.compile(r"^(?:[A-Za-z]:[\\/]|/)")


def ini_paths(text: str) -> list[str]:
    """Every value of the ini that is an absolute path, in order, without repeats."""
    out, seen = [], set()
    for line in text.splitlines():
        _, sep, value = line.partition("=")
        if not sep:
            continue
        v = ini_value(value)
        if _ABSOLUTE.match(v) and v not in seen and "\n" not in v and len(v) < 1000:
            seen.add(v)
            out.append(v)
    return out


def _ancestors(path: str) -> list[Path]:
    p = Path(path.replace("\\", "/"))
    return [p, *p.parents]


# Windows file attributes of a cloud drive's placeholder: opening such a file starts a download.
_OFFLINE, _RECALL_ON_OPEN, _RECALL_ON_DATA_ACCESS = 0x1000, 0x40000, 0x400000


def _local_ini(folder: Path) -> Path | None:
    """The folder's ModOrganizer.ini if it is a plain file held on this PC, of a size ModTrap reads."""
    try:
        ini = folder / INI_NAME
        st = os.stat(ini, follow_symlinks=False)
        attrs = getattr(st, "st_file_attributes", 0)
        if not ini.is_file() or attrs & (_OFFLINE | _RECALL_ON_OPEN | _RECALL_ON_DATA_ACCESS):
            return None
        return ini if 0 < st.st_size <= READ_CAP else None
    except OSError:
        return None


def _same_ini(folder: Path, size: int, digest: str) -> bool:
    ini = _local_ini(folder)
    try:
        if ini is None or ini.stat().st_size != size:
            return False
        with open(ini, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest() == digest
    except OSError:
        return False


def _game_of(ini_text: str) -> str:
    return parse_ini(ini_text).get("General", {}).get("gameName", "")


def _same_instance(folder: Path, game: str) -> bool:
    """The fallback when the ini has changed since the drop: an instance (an ini, and a mods or profiles folder
    beside it) of the same game."""
    ini = _local_ini(folder)
    if ini is None or not ((folder / "mods").is_dir() or (folder / "profiles").is_dir()):
        return False
    try:
        with open(ini, "rb") as f:
            data = f.read(READ_CAP)
    except OSError:
        return False
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("cp1252", "replace")
    return bool(game) and _game_of(text) == game


def drive_roots() -> list[Path]:
    """The fixed drives of this PC: no network drive, no removable one."""
    if os.name != "nt":
        return []
    out = []
    try:
        import ctypes
        kind = ctypes.windll.kernel32.GetDriveTypeW          # 3 is DRIVE_FIXED
    except (ImportError, AttributeError, OSError):
        kind = None
    for c in string.ascii_uppercase:
        root = c + ":\\"
        try:
            if (kind(root) == 3) if kind else os.path.exists(root):
                out.append(Path(root))
        except OSError:
            continue
    return out


def _is_link(entry: os.DirEntry) -> bool:
    try:
        return entry.is_symlink() or bool(getattr(entry, "is_junction", lambda: False)())
    except OSError:
        return True


def _search(name: str, roots: list[Path]) -> list[Path]:
    """Folders called `name`, at most SEARCH_DEPTH levels below a root, breadth first, within the limits."""
    want, found = fold(name), []
    level = [(r, 0) for r in roots]
    listed, stop = 0, time.monotonic() + SEARCH_SECONDS
    while level:
        nxt = []
        for folder, depth in level:
            if listed >= SEARCH_FOLDERS or time.monotonic() > stop:
                return found
            listed += 1
            try:
                with os.scandir(folder) as it:
                    subs = [e.name for e in it if e.is_dir(follow_symlinks=False) and not _is_link(e)]
            except OSError:
                continue
            for sub in subs:
                if fold(sub) == want:
                    found.append(folder / sub)
                elif depth + 1 < SEARCH_DEPTH and fold(sub) not in SKIP:
                    nxt.append((folder / sub, depth + 1))
        level = nxt
    return found


def find(name: str | None, ini: bytes, recents: list[str] | None = None,
         roots: list[Path] | None = None) -> tuple[Path | None, str]:
    """The folder whose ModOrganizer.ini is `ini`, and how it was found ("" when it was not). `name` is the
    dropped folder's name, or None when only the ini file was dropped."""
    size, digest = len(ini), hashlib.sha256(ini).hexdigest()
    try:
        text = ini.decode("utf-8")
    except UnicodeDecodeError:
        text = ini.decode("cp1252", "replace")
    tried: set[str] = set()
    named: list[Path] = []          # candidates of the right name that are not the same file: for the fallback

    def ok(folder: Path) -> bool:
        key = fold(str(folder))
        if key in tried:
            return False
        tried.add(key)
        if name is not None and fold(folder.name) != fold(name):
            return False
        if _same_ini(folder, size, digest):
            return True
        if name is not None:
            named.append(folder)
        return False

    for r in recents or []:
        if ok(Path(r)):
            return Path(r), "a folder opened before"
    for p in ini_paths(text):
        for folder in _ancestors(p):
            if ok(folder):
                return folder, "the paths in its ModOrganizer.ini"
    if name:
        for folder in _search(name, drive_roots() if roots is None else roots):
            if ok(folder):
                return folder, "a search of this PC's fixed drives for a folder of that name"
    # MO2 rewrites its ini, so a drop made while MO2 is open may no longer match byte for byte.
    game = _game_of(text)
    same = [f for f in named if _same_instance(f, game)]
    if len(same) == 1:
        return same[0], "its name and its game (MO2 has changed its ModOrganizer.ini since the drop)"
    return None, ""
