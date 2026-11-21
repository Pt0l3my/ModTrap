"""Taking in a mod's archive (MT21, DESIGN§16.1): unpacking it into ModTrap's own work folder, and finding in it
the folder that would become the mod. Nothing here touches a modlist.

An archive is someone else's file: every name in it is checked before anything is written (no path that leaves the
target folder, no link), and the unpacked size and file count are capped. A .zip is read with Python itself; .7z
and .rar need the owner's own installed 7-Zip, which ModTrap calls and does not contain (WHY§41).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from . import plugin

MAX_FILES = 400_000
MAX_BYTES = 120 * 1024 ** 3            # unpacked; a mod larger than this is not taken in
SPARE_BYTES = 2 * 1024 ** 3            # left free on the disk after unpacking
SEVEN_ZIP_SECONDS = 3 * 60 * 60
CHUNK = 1024 * 1024
MAGIC = ((b"PK\x03\x04", "zip"), (b"PK\x05\x06", "zip"), (b"7z\xbc\xaf\x27\x1c", "7z"), (b"Rar!\x1a\x07", "rar"))
_BAD_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
_DEVICE = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", re.IGNORECASE)
# Folders the game reads from its Data folder: an archive's folder holding one of these is the mod's own top.
DATA_DIRS = frozenset((
    "meshes", "textures", "scripts", "interface", "skse", "sound", "music", "seq", "strings", "video", "shadersfx",
    "grass", "lodsettings", "dyndolod", "calientetools", "nemesis_engine", "pandora_engine", "mcm", "source",
    "netscriptframework", "dialogueviews", "platform", "terrain", "lightplacer", "pbrnifpatcher", "pbrtexturesets",
    "edit scripts", "fonts", "materials", "particlelights", "shaders"))
DATA_FILES = (".bsa", ".ba2", ".esp", ".esm", ".esl")


class Refused(Exception):
    """The archive is not taken in; the text says why, in words for the owner."""


def kind(path: Path) -> str:
    """What sort of archive the file is, by its first bytes: "zip", "7z", "rar" or ""."""
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return ""
    return next((k for magic, k in MAGIC if head.startswith(magic)), "")


def safe_parts(name: str) -> tuple[str, ...] | None:
    """An archive's entry name as path parts under the target folder, or None when it must not be written:
    an absolute path, a drive, a step upwards, or a name Windows cannot hold."""
    name = name.replace("\\", "/")
    if not name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        return None
    parts = tuple(p for p in name.split("/") if p not in ("", "."))
    if not parts:
        return None
    for p in parts:
        if p == ".." or _BAD_CHARS.search(p) or _DEVICE.match(p) or p != p.rstrip(" .") or len(p) > 240:
            return None
    return parts


def _room(dest: Path, need: int) -> None:
    try:
        free = shutil.disk_usage(dest).free
    except OSError:
        return
    if free < need + SPARE_BYTES:
        raise Refused("There is not enough room on the disk of ModTrap's work folder: the mod unpacks to %s and "
                      "%s is free." % (size_words(need), size_words(free)))


def size_words(n: int) -> str:
    for unit, div in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if n >= div:
            return "%.1f %s" % (n / div, unit)
    return "%d bytes" % n


def _check_listing(entries: list[tuple[str, int]]) -> int:
    if len(entries) > MAX_FILES:
        raise Refused("The archive holds more files than ModTrap takes in (%d)." % len(entries))
    total = sum(max(0, size) for _, size in entries)
    if total > MAX_BYTES:
        raise Refused("The archive unpacks to %s, more than ModTrap takes in." % size_words(total))
    for name, _ in entries:
        if safe_parts(name) is None:
            raise Refused("The archive holds a file whose name would put it outside its own folder, or that Windows "
                          "cannot hold. ModTrap does not unpack it; install it through MO2 if you trust it.")
    return total


# --- zip ------------------------------------------------------------------------------------------------------------

def _unzip(src: Path, dest: Path) -> int:
    try:
        z = zipfile.ZipFile(src)
    except (zipfile.BadZipFile, OSError) as e:
        raise Refused("The .zip could not be read (%s)." % type(e).__name__) from None
    with z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        for i in infos:
            if (i.external_attr >> 16) & 0o170000 == 0o120000:
                raise Refused("The archive holds a link to another place. ModTrap does not unpack it.")
            if i.flag_bits & 0x1:
                raise Refused("The archive is protected by a password. Install it through MO2.")
        total = _check_listing([(i.filename, i.file_size) for i in infos])
        _room(dest, total)
        written = 0
        for i in infos:
            target = dest.joinpath(*safe_parts(i.filename))
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with z.open(i) as r, open(target, "wb") as w:
                    while True:
                        block = r.read(CHUNK)
                        if not block:
                            break
                        written += len(block)
                        if written > total + CHUNK:          # the archive lied about its sizes
                            raise Refused("The archive unpacks to more than it says. ModTrap stopped unpacking it.")
                        w.write(block)
            except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as e:
                raise Refused("A file of the .zip could not be unpacked (%s)." % type(e).__name__) from None
        return len(infos)


# --- 7z and rar, through the owner's own 7-Zip -----------------------------------------------------------------------

def find_7zip() -> Path | None:
    """The owner's installed 7-Zip program, or None. MODTRAP_7ZIP names one outright."""
    named = os.environ.get("MODTRAP_7ZIP")
    if named:
        return Path(named) if Path(named).is_file() else None
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        base = os.environ.get(var)
        if base and (Path(base) / "7-Zip" / "7z.exe").is_file():
            return Path(base) / "7-Zip" / "7z.exe"
    for name in ("7z", "7zz", "7za"):
        hit = shutil.which(name)
        if hit:
            return Path(hit)
    return None


def _run(cmd: list[str], seconds: float) -> subprocess.CompletedProcess:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=seconds, creationflags=flags)


def parse_7z_listing(text: str) -> list[dict]:
    """The entries of `7z l -slt`: blocks of "Key = value" lines, one block an entry, after a line of dashes."""
    _, _, body = text.partition("\n----------")
    out = []
    for block in re.split(r"\r?\n\r?\n", body):
        entry = {}
        for line in block.splitlines():
            key, sep, value = line.partition(" = ")
            if sep:
                entry[key.strip()] = value
        if "Path" in entry:
            out.append(entry)
    return out


def _un7z(exe: Path, src: Path, dest: Path) -> int:
    try:
        got = _run([str(exe), "l", "-slt", "-sccUTF-8", "-p-", "--", str(src)], 600)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Refused("7-Zip could not be started to read the archive (%s)." % type(e).__name__) from None
    if got.returncode not in (0, 1):
        raise Refused("7-Zip could not read the archive. It may be damaged, or protected by a password.")
    entries = parse_7z_listing(got.stdout.decode("utf-8", "replace"))
    files = []
    for e in entries:
        if e.get("Folder") == "+" or e.get("Attributes", "").startswith("D"):
            continue
        if e.get("Symbolic Link") or e.get("Hard Link") or "L" in e.get("Attributes", "").split(" ")[0]:
            raise Refused("The archive holds a link to another place. ModTrap does not unpack it.")
        if e.get("Encrypted") == "+":
            raise Refused("The archive is protected by a password. Install it through MO2.")
        try:
            size = int(e.get("Size") or 0)
        except ValueError:
            size = 0
        files.append((e["Path"], size))
    if not files:
        raise Refused("7-Zip found no file in the archive.")
    total = _check_listing(files)
    _room(dest, total)
    try:
        got = _run([str(exe), "x", "-y", "-bd", "-sccUTF-8", "-p-", "-o" + str(dest), "--", str(src)],
                   SEVEN_ZIP_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Refused("7-Zip did not finish unpacking the archive (%s)." % type(e).__name__) from None
    if got.returncode != 0:
        raise Refused("7-Zip reported a problem while unpacking the archive; nothing of it is used.")
    return len(files)


def _no_links(dest: Path) -> int:
    """After unpacking: nothing under `dest` may be a link, whatever the listing said. Returns the files' count."""
    count = 0
    for base, dirs, files in os.walk(dest):
        for n in dirs + files:
            p = os.path.join(base, n)
            if os.path.islink(p) or (hasattr(os.path, "isjunction") and os.path.isjunction(p)):
                raise Refused("The archive unpacked a link to another place. ModTrap does not use it.")
        count += len(files)
    return count


def unpack(src: Path, dest: Path, seven_zip: Path | None = None) -> dict:
    """Unpacks `src` into the new folder `dest`. On a refusal `dest` is removed again."""
    k = kind(src)
    if not k:
        raise Refused("This is not a .zip, .7z or .rar archive, whatever its name says.")
    dest.mkdir(parents=True, exist_ok=False)
    try:
        if k == "zip":
            _unzip(src, dest)
        else:
            exe = seven_zip or find_7zip()
            if exe is None:
                raise Refused("A .%s archive needs 7-Zip, which ModTrap did not find on this PC. Install 7-Zip (it "
                              "is free) and drop the archive again, or install the mod through MO2." % k)
            _un7z(exe, src, dest)
        return {"kind": k, "files": _no_links(dest)}
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise


# --- which folder of it is the mod ------------------------------------------------------------------------------------

def _listing(folder: Path) -> tuple[list[str], list[str]]:
    dirs, files = [], []
    try:
        with os.scandir(folder) as it:
            for e in it:
                (dirs if e.is_dir(follow_symlinks=False) else files).append(e.name)
    except OSError:
        pass
    return sorted(dirs, key=str.lower), sorted(files, key=str.lower)


def looks_like_data(folder: Path) -> bool:
    dirs, files = _listing(folder)
    return any(d.lower() in DATA_DIRS for d in dirs) or any(f.lower().endswith(DATA_FILES) for f in files)


def has_installer(folder: Path) -> bool:
    dirs, _ = _listing(folder)
    for d in dirs:
        if d.lower() == "fomod":
            _, files = _listing(folder / d)
            if any(f.lower() == "moduleconfig.xml" for f in files):
                return True
    return False


def layout(raw: Path) -> dict:
    """Where the mod is inside an unpacked archive. "root" is the folder that would become the mod's folder;
    "installer" says why ModTrap cannot take it as it is: "fomod" (it comes with an installer that asks which
    parts to install), "options" (several folders to choose from), or "" (it can)."""
    d = raw
    for _ in range(12):
        if has_installer(d):
            return {"root": d, "installer": "fomod", "sure": True}
        if looks_like_data(d):
            return {"root": d, "installer": "", "sure": True}
        dirs, files = _listing(d)
        data = [x for x in dirs if x.lower() == "data"]
        if data and looks_like_data(d / data[0]):
            return {"root": d / data[0], "installer": "", "sure": True}
        if len(dirs) == 1:
            d = d / dirs[0]                       # a wrapping folder (its loose files are a readme or the like)
            continue
        if len([x for x in dirs if looks_like_data(d / x) or has_installer(d / x)]) > 1:
            return {"root": d, "installer": "options", "sure": True, "options": dirs}
        break
    return {"root": d, "installer": "", "sure": False}


def plugins_in(folder: Path) -> tuple[str, ...]:
    _, files = _listing(folder)
    return tuple(f for f in files if plugin.is_plugin_name(f))


__all__ = ["Refused", "kind", "safe_parts", "unpack", "layout", "find_7zip", "parse_7z_listing", "plugins_in",
           "looks_like_data", "size_words"]
