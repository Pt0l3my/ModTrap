"""Reading an MO2 instance, read-only (DESIGN§3): ModOrganizer.ini, the profile's modlist.txt, plugins.txt and
loadorder.txt, the mod folders and the plugins in them. The forms of these files are in MO01§2.

Nothing here writes. Paths in the ini use either slash; both are accepted.
"""

from __future__ import annotations

import os
import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from . import plugin

INI_NAME = "ModOrganizer.ini"
READ_CAP = 32 * 1024 * 1024        # no text file of an instance is read past this
# MO01§2: the game's own plugins for Skyrim SE, always active and never written to plugins.txt; the Creation Club
# ones are added from Skyrim.ccc in the game's folder.
PRIMARY = ("Skyrim.esm", "Update.esm", "Dawnguard.esm", "HearthFires.esm", "Dragonborn.esm")
SEPARATOR_SUFFIX = "_separator"
OVERWRITE = "<overwrite>"          # the pseudo-mod above every mod
GAME = "<game>"                    # the game's own Data folder, below every mod


class Unusable(Exception):
    """The folder is not an instance ModTrap can read; the text says why, in words for the page."""


def fold(name: str) -> str:
    """Names of files and mods compare without case, as Windows does."""
    return name.casefold()


def _read_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        data = f.read(READ_CAP + 1)
    if len(data) > READ_CAP:
        raise Unusable("%s is larger than ModTrap reads" % path.name)
    return data


def _decode(data: bytes) -> str:
    """UTF-8 if it is valid (with or without a mark), else the Windows codepage MO2 wrote plugins.txt in."""
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", "replace")


# --- ModOrganizer.ini -------------------------------------------------------------------------------------------

_ESCAPE = re.compile(r"\\(x[0-9A-Fa-f]{1,4}|.)")
_SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', ";": ";", ",": ","}


def ini_value(raw: str) -> str:
    """One value as Qt's settings files write it: an optional @ByteArray(...) wrapper, optional quotes, and
    backslash escapes (a doubled backslash, \\xNNNN for a character)."""
    v = raw.strip()
    if v.startswith("@ByteArray(") and v.endswith(")"):
        v = v[len("@ByteArray("):-1]
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]

    def sub(m: re.Match) -> str:
        t = m.group(1)
        if t[0] == "x" and len(t) > 1:
            return chr(int(t[1:], 16))
        return _SIMPLE.get(t, t)

    return _ESCAPE.sub(sub, v)


def parse_ini(text: str) -> dict[str, dict[str, str]]:
    """Sections to keys to values. Keys keep their case; a key of an array reads "1\\title"."""
    out: dict[str, dict[str, str]] = {}
    section = out.setdefault("", {})
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ";#":
            continue
        if line[0] == "[" and line[-1] == "]":
            section = out.setdefault(line[1:-1], {})
            continue
        key, sep, value = line.partition("=")
        if sep:
            section[key.strip()] = ini_value(value)
    return out


def _path(text: str, base: Path) -> Path:
    """A path from the ini: %BASE_DIR% filled in, either slash, relative ones under `base`."""
    text = text.replace("%BASE_DIR%", str(base)).replace("\\", "/")
    p = Path(text)
    return p if p.is_absolute() or re.match(r"^[A-Za-z]:/", text) else base / p


@dataclass(frozen=True)
class Executable:
    title: str
    binary: str
    arguments: str
    working_directory: str


def _executables(section: dict[str, str]) -> tuple[Executable, ...]:
    try:
        n = int(section.get("size", "0"))
    except ValueError:
        n = 0
    out = []
    for i in range(1, min(n, 500) + 1):
        title = section.get("%d\\title" % i, "")
        if title:
            out.append(Executable(title, section.get("%d\\binary" % i, ""), section.get("%d\\arguments" % i, ""),
                                  section.get("%d\\workingDirectory" % i, "")))
    return tuple(out)


# --- the profile's lists ----------------------------------------------------------------------------------------

def parse_modlist(text: str) -> list[tuple[str, str]]:
    """(sign, name) for each line of modlist.txt, in the file's order: highest priority first (MO01§2). A line
    with no sign counts as enabled, as MO2 reads it."""
    out = []
    for line in text.split("\n"):
        line = line.strip("\r")
        if not line or line[0] == "#":
            continue
        if line[0] in "+-*":
            sign, name = line[0], line[1:].strip()
        else:
            sign, name = "+", line.strip()
        if name:
            out.append((sign, name))
    return out


def parse_plugins(text: str) -> list[tuple[str, bool]]:
    """(name, active) for each line of plugins.txt, in the file's order (MO01§2)."""
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line[0] == "#":
            continue
        if line[0] == "*":
            if line[1:].strip():
                out.append((line[1:].strip(), True))
        else:
            out.append((line, False))
    return out


def parse_loadorder(text: str) -> list[str]:
    return [ln.strip() for ln in text.split("\n") if ln.strip() and ln.strip()[0] != "#"]


# --- the instance -----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Mod:
    name: str
    priority: int                  # 0 is the lowest, as MO2 shows it; the game is -1
    enabled: bool
    kind: str                      # "mod", "separator", "foreign" (not managed by MO2), "overwrite", "game"
    folder: Path | None
    plugins: tuple[str, ...]       # plugin files at the top of its folder, as named on disk
    listed: bool = True            # False: a folder modlist.txt does not name


@dataclass
class Instance:
    root: Path
    mods_dir: Path
    profiles_dir: Path
    overwrite_dir: Path
    game_dir: Path | None
    game_name: str
    profile: str
    profiles: tuple[str, ...]
    executables: tuple[Executable, ...]
    mods: list[Mod]                            # lowest priority first; the game first, overwrite last
    load_order: list[tuple[str, bool]]         # (plugin name, active), in load order
    primary: tuple[str, ...]                   # the game's own plugins, always active
    output_mods: dict[str, str] = field(default_factory=dict)   # an executable's title -> the mod its new files go to
    notes: list[str] = field(default_factory=list)   # what was found that the owner should know, in words
    downloads_dir: Path | None = None          # where MO2 keeps downloaded archives (MO01§7)

    def mod(self, name: str) -> Mod | None:
        f = fold(name)
        return next((m for m in self.mods if fold(m.name) == f), None)


def _plugins_in(folder: Path) -> tuple[str, ...]:
    try:
        names = [e.name for e in os.scandir(folder) if plugin.is_plugin_name(e.name) and e.is_file()]
    except OSError:
        return ()
    return tuple(sorted(names, key=fold))


def _subfolders(folder: Path) -> list[str]:
    try:
        return sorted((e.name for e in os.scandir(folder) if e.is_dir()), key=fold)
    except OSError:
        return []


def load(root: Path | str, profile: str | None = None) -> Instance:
    """The instance in `root` (the folder holding ModOrganizer.ini), with `profile` or the one MO2 last used."""
    root = Path(root)
    ini_path = root / INI_NAME
    if not ini_path.is_file():
        raise Unusable("no %s in this folder: pick the modlist's folder, the one MO2 itself is in" % INI_NAME)
    try:
        ini = parse_ini(_decode(_read_bytes(ini_path)))
    except OSError as e:
        raise Unusable("%s could not be read (%s)" % (INI_NAME, type(e).__name__)) from None
    general, settings = ini.get("General", {}), ini.get("Settings", {})
    notes: list[str] = []

    base = _path(settings["base_directory"], root) if settings.get("base_directory") else root
    mods_dir = _path(settings.get("mod_directory", "") or "mods", base)
    profiles_dir = _path(settings.get("profiles_directory", "") or "profiles", base)
    overwrite_dir = _path(settings.get("overwrite_directory", "") or "overwrite", base)
    downloads_dir = _path(settings.get("download_directory", "") or "downloads", base)
    game_dir = _path(general["gamePath"], root) if general.get("gamePath") else None
    game_name = general.get("gameName", "")

    profiles = tuple(n for n in _subfolders(profiles_dir) if (profiles_dir / n / "modlist.txt").is_file())
    if not profiles:
        raise Unusable("no profile with a modlist.txt was found in the instance's profiles folder")
    wanted = profile or general.get("selected_profile", "")
    chosen = next((p for p in profiles if fold(p) == fold(wanted)), None)
    if chosen is None:
        if profile:
            raise Unusable("the instance has no profile of that name")
        chosen = profiles[0]
        notes.append("MO2's last used profile was not found; showing the profile '%s'" % chosen)
    pdir = profiles_dir / chosen

    # Mods, lowest priority first.
    listed = parse_modlist(_decode(_read_bytes(pdir / "modlist.txt")))
    on_disk = {fold(n): n for n in _subfolders(mods_dir)}
    seen: set[str] = set()
    ordered: list[Mod] = []
    for sign, name in reversed(listed):                      # the file is highest first
        f = fold(name)
        if f in seen:
            notes.append("modlist.txt names '%s' twice; the first is used" % name)
            continue
        seen.add(f)
        if sign == "*":
            ordered.append(Mod(name, 0, True, "foreign", None, ()))
        elif f in on_disk:
            folder = mods_dir / on_disk[f]
            sep = f.endswith(SEPARATOR_SUFFIX)
            ordered.append(Mod(name, 0, sign == "+" and not sep, "separator" if sep else "mod", folder,
                               () if sep else _plugins_in(folder)))
        else:
            notes.append("modlist.txt names '%s', which has no folder in mods; it is left out" % name)
    for f, name in sorted(on_disk.items()):
        if f not in seen:                                    # MO01§2: MO2 adds these above the others
            sep = f.endswith(SEPARATOR_SUFFIX)
            ordered.append(Mod(name, 0, False, "separator" if sep else "mod", mods_dir / name,
                               () if sep else _plugins_in(mods_dir / name), listed=False))
            notes.append("the mod folder '%s' is not in modlist.txt; MO2 will add it at the top, disabled" % name)
    mods = [Mod(m.name, i, m.enabled, m.kind, m.folder, m.plugins, m.listed) for i, m in enumerate(ordered)]

    data_dir = game_dir / "Data" if game_dir else None
    if data_dir is None or not data_dir.is_dir():
        notes.append("the game's Data folder was not found; the game's own plugins are taken as present")
        game_plugins: tuple[str, ...] = ()
    else:
        game_plugins = _plugins_in(data_dir)
    mods.insert(0, Mod(GAME, -1, True, "game", data_dir, game_plugins))
    mods.append(Mod(OVERWRITE, len(mods) - 1, True, "overwrite", overwrite_dir, _plugins_in(overwrite_dir)))

    # The game's own plugins (MO01§2).
    primary = list(PRIMARY)
    ccc = game_dir / "Skyrim.ccc" if game_dir else None
    if ccc is not None and ccc.is_file():
        have = {fold(p) for p in primary}
        for line in _decode(_read_bytes(ccc)).splitlines():
            line = line.strip()
            if line and fold(line) not in have:
                have.add(fold(line))
                primary.append(line)

    # The load order (MO01§2): loadorder.txt has every plugin in order, plugins.txt says which are active; MO2
    # takes the order from the newer of the two.
    lo_path, pl_path = pdir / "loadorder.txt", pdir / "plugins.txt"
    plugins_txt = parse_plugins(_decode(_read_bytes(pl_path))) if pl_path.is_file() else []
    active = {fold(n) for n, a in plugins_txt if a} | {fold(p) for p in primary}
    if lo_path.is_file():
        names = parse_loadorder(_decode(_read_bytes(lo_path)))
        try:
            newer = pl_path.is_file() and pl_path.stat().st_mtime > lo_path.stat().st_mtime
        except OSError:
            newer = False
        if newer:
            in_lo = {fold(n) for n in names}
            a_order = [fold(n) for n, _ in plugins_txt if fold(n) in in_lo]
            in_pl = set(a_order)
            if a_order != [fold(n) for n in names if fold(n) in in_pl]:
                notes.append("plugins.txt is newer than loadorder.txt and orders some plugins differently; "
                             "MO2 will follow plugins.txt at its next start")
    else:
        names = [p for p in primary] + [n for n, _ in plugins_txt]
        notes.append("the profile has no loadorder.txt; the order is taken from plugins.txt")
    order: list[tuple[str, bool]] = []
    seen_p: set[str] = set()
    for n in names:
        if fold(n) not in seen_p:
            seen_p.add(fold(n))
            order.append((n, fold(n) in active))
    for n, a in plugins_txt:                                  # named in plugins.txt only: after the others
        if fold(n) not in seen_p:
            seen_p.add(fold(n))
            order.append((n, a))

    # MO01§2: per executable, the mod that receives the files the program creates (the profile's settings.ini).
    output_mods: dict[str, str] = {}
    st_path = pdir / "settings.ini"
    if st_path.is_file():
        section = parse_ini(_decode(_read_bytes(st_path))).get("custom_overwrites", {})
        for key, value in section.items():
            if value:
                output_mods[urllib.parse.unquote(key)] = value

    return Instance(root=root, mods_dir=mods_dir, profiles_dir=profiles_dir, overwrite_dir=overwrite_dir,
                    game_dir=game_dir, game_name=game_name, profile=chosen, profiles=profiles,
                    executables=_executables(ini.get("customExecutables", {})), mods=mods, load_order=order,
                    primary=tuple(primary), output_mods=output_mods, notes=notes,
                    downloads_dir=downloads_dir)
