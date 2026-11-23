"""Taking in a mod's archive (MT21, DESIGN§16.1): unpacking it into ModTrap's own work folder, and finding in it
the folder that would become the mod. Nothing here touches a modlist.

An archive is someone else's file: every name in it is checked before anything is written (no path that leaves the
target folder, no link), and the unpacked size and file count are capped. A .zip is read with Python itself, and a
.7z with ModTrap's own reader (`sevenz_read.py`, WHY§123), each file's checksum checked. A .rar, and a .7z packed in
a way that reader does not read, go through a program of the owner's PC, which ModTrap calls and does not contain
(WHY§41): the owner's installed 7-Zip where there is one, else the unpacker Windows itself comes with (`tar.exe`).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from . import plugin, sevenz_read

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


# --- 7z, with ModTrap's own reader (WHY§123) ---------------------------------------------------------------------------

class _Other(Exception):
    """ModTrap's own reader does not read this archive; the text says why. Another unpacker is tried."""


def _unseven(src: Path, dest: Path) -> int:
    try:
        a = sevenz_read.Archive(src)
    except sevenz_read.Locked:
        raise Refused("The archive is protected by a password. Install it through MO2.") from None
    except (sevenz_read.Unsupported, sevenz_read.Bad) as e:
        raise _Other(str(e)) from None
    except OSError as e:
        raise Refused("The .7z could not be read (%s)." % type(e).__name__) from None
    with a:
        try:
            a.check()
        except sevenz_read.Locked:
            raise Refused("The archive is protected by a password. Install it through MO2.") from None
        except (sevenz_read.Unsupported, sevenz_read.Bad) as e:
            raise _Other(str(e)) from None
        if any(x.link for x in a.entries):
            raise Refused("The archive holds a link to another place. ModTrap does not unpack it.")
        files = [x for x in a.entries if not x.is_dir]
        if not files:
            raise Refused("There is no file in the archive.")
        total = _check_listing([(x.name, x.size) for x in files])
        _room(dest, total)
        try:
            for x, blocks in a.extract():
                target = dest.joinpath(*safe_parts(x.name))
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "wb") as w:
                    for block in blocks:
                        w.write(block)
        except sevenz_read.Locked:
            raise Refused("The archive is protected by a password. Install it through MO2.") from None
        except (sevenz_read.Unsupported, sevenz_read.Bad) as e:
            raise _Other(str(e)) from None
        except OSError as e:
            raise Refused("A file of the .7z could not be written (%s)." % type(e).__name__) from None
    return len(files)


# --- 7z and rar, through the owner's own 7-Zip -----------------------------------------------------------------------

def _registry_7zip() -> list[Path]:
    """Where 7-Zip's own installer says it is, for one installed outside Program Files."""
    out: list[Path] = []
    if sys.platform != "win32":
        return out
    try:
        import winreg
    except ImportError:
        return out
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for value in ("Path64", "Path"):
            try:
                with winreg.OpenKey(hive, r"Software\7-Zip") as key:
                    folder, _kind = winreg.QueryValueEx(key, value)
            except OSError:
                continue
            if isinstance(folder, str) and folder:
                out.append(Path(folder) / "7z.exe")
    return out


def find_7zip() -> Path | None:
    """The owner's installed 7-Zip program, or None. MODTRAP_7ZIP names one outright."""
    named = os.environ.get("MODTRAP_7ZIP")
    if named:
        return Path(named) if Path(named).is_file() else None
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        base = os.environ.get(var)
        if base and (Path(base) / "7-Zip" / "7z.exe").is_file():
            return Path(base) / "7-Zip" / "7z.exe"
    for exe in _registry_7zip():
        if exe.is_file():
            return exe
    for name in ("7z", "7zz", "7za", "NanaZipC"):
        hit = shutil.which(name)
        if hit:
            return Path(hit)
    return None


# --- 7z and rar, through the unpacker Windows comes with (WHY§123) ----------------------------------------------------
# Windows' own `tar.exe` is bsdtar, the libarchive program. From Windows 11 23H2 it reads .7z and .rar; the one of
# Windows 10 lacks the LZMA part and cannot. It is asked what it is before it is used.

def find_tar() -> tuple[Path, str] | None:
    """The system's bsdtar and what it says of itself, or None. MODTRAP_TAR names one outright."""
    named = os.environ.get("MODTRAP_TAR")
    cands: list[Path] = []
    if named:
        cands.append(Path(named))
    elif sys.platform == "win32":
        root = os.environ.get("SystemRoot") or r"C:\Windows"
        cands += [Path(root) / "Sysnative" / "tar.exe", Path(root) / "System32" / "tar.exe"]
    else:
        hit = shutil.which("bsdtar")
        if hit:
            cands.append(Path(hit))
    for exe in cands:
        if not exe.is_file():
            continue
        try:
            got = _run([str(exe), "--version"], 20)
        except (OSError, subprocess.TimeoutExpired):
            continue
        said = got.stdout.decode("utf-8", "replace").strip()
        if got.returncode == 0 and said.lower().startswith("bsdtar"):
            return exe, said
    return None


_TAR_LINE = re.compile(r"^(\S+)\s+\d+\s+\S+\s+\S+\s+(\d+)\s")


def parse_tar_listing(text: str) -> list[tuple[str, int]]:
    """The entries of `tar -tvf`, each (kind, size): the kind is the first letter of the entry's mode ("-" a file,
    "d" a folder, "l" and "h" links); a line that does not read as an entry counts as a file of unknown size."""
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _TAR_LINE.match(line)
        out.append((m.group(1)[0], int(m.group(2))) if m else ("-", 0))
    return out


def _untar(exe: Path, said: str, src: Path, dest: Path, k: str) -> int:
    who = "Windows' own unpacker" if sys.platform == "win32" else "the system's unpacker"
    if k == "7z" and "liblzma" not in said.lower():
        raise Refused("A .7z archive needs 7-Zip here: %s on this PC is an older one that cannot read .7z (Windows 11 "
                      "from 23H2 can). Install 7-Zip (it is free) and drop the archive again, or install the mod "
                      "through MO2." % who)
    try:
        names = _run([str(exe), "-tf", str(src)], 600)
        long = _run([str(exe), "-tvf", str(src)], 600)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Refused("%s could not be started to read the archive (%s)." % (who[0].upper() + who[1:], type(e).__name__)) from None
    if names.returncode != 0 or long.returncode != 0:
        raise Refused("%s could not read the archive. It may be damaged, protected by a password, or packed in a way only "
                      "7-Zip reads: install 7-Zip (it is free) and drop the archive again." % (who[0].upper() + who[1:]))
    listed = [n for n in names.stdout.decode("utf-8", "replace").splitlines() if n.strip()]
    kinds = parse_tar_listing(long.stdout.decode("utf-8", "replace"))
    if any(kd in ("l", "h") for kd, _size in kinds):
        raise Refused("The archive holds a link to another place. ModTrap does not unpack it.")
    files = [(n, size) for n, (kd, size) in zip(listed, kinds + [("-", 0)] * len(listed)) if kd != "d" and not n.endswith("/")]
    if not files:
        raise Refused("%s found no file in the archive." % (who[0].upper() + who[1:]))
    total = _check_listing(files)
    _room(dest, total)
    try:
        got = _run([str(exe), "-xf", str(src), "-C", str(dest)], SEVEN_ZIP_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Refused("%s did not finish unpacking the archive (%s)." % (who[0].upper() + who[1:], type(e).__name__)) from None
    if got.returncode != 0:
        told = got.stderr.decode("utf-8", "replace")
        if "encrypt" in told.lower():
            raise Refused("The archive is protected by a password. Install it through MO2.")
        raise Refused("%s reported a problem while unpacking the archive; nothing of it is used. 7-Zip may read it: "
                      "install 7-Zip (it is free) and drop the archive again." % (who[0].upper() + who[1:]))
    # What was written is measured too: the listing's sizes are only what the archive says of itself.
    written = 0
    for base, _dirs, fnames in os.walk(dest):
        for n in fnames:
            try:
                written += os.path.getsize(os.path.join(base, n))
            except OSError:
                pass
    if written > MAX_BYTES:
        raise Refused("The archive unpacks to %s, more than ModTrap takes in." % size_words(written))
    return len(files)


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
        attrs = e.get("Attributes", "").split(" ")
        # A link shows as its own field, as an L among Windows' attribute letters, or as a mode that starts with l.
        if e.get("Symbolic Link") or e.get("Hard Link") or "L" in attrs[0] or any(a.startswith("l") for a in attrs[1:]):
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


def unpack(src: Path, dest: Path, seven_zip: Path | None = None, tar: tuple[Path, str] | None = None) -> dict:
    """Unpacks `src` into the new folder `dest`. On a refusal `dest` is removed again. A .7z or .rar goes through
    the owner's 7-Zip where there is one, else through the unpacker Windows comes with; the answer's "by" says
    which."""
    k = kind(src)
    if not k:
        raise Refused("This is not a .zip, .7z or .rar archive, whatever its name says.")
    dest.mkdir(parents=True, exist_ok=False)
    try:
        by, own = "ModTrap itself", ""
        if k == "7z":
            try:
                _unseven(src, dest)
            except _Other as e:
                own = str(e)                                # another unpacker is tried; nothing of this try is kept
                shutil.rmtree(dest, ignore_errors=True)
                dest.mkdir(parents=True, exist_ok=False)
        if k == "zip":
            _unzip(src, dest)
        elif k == "rar" or own:
            exe = seven_zip or find_7zip()
            other = None if exe is not None else (tar or find_tar())
            if exe is not None:
                _un7z(exe, src, dest)
                by = "7-Zip"
            elif other is not None:
                _untar(other[0], other[1], src, dest, k)
                by = "Windows' own unpacker" if sys.platform == "win32" else "the system's unpacker"
            elif own:
                raise Refused("ModTrap's own reader does not unpack this .7z (%s), and neither 7-Zip nor the unpacker Windows 11 "
                              "comes with was found on this PC to do it. Install 7-Zip (it is free) and drop the archive again, "
                              "or install the mod through MO2." % own)
            else:
                raise Refused("A .%s archive needs 7-Zip, or the unpacker Windows 11 comes with, and ModTrap found neither "
                              "on this PC. Install 7-Zip (it is free) and drop the archive again, or install the mod "
                              "through MO2." % k)
        return {"kind": k, "files": _no_links(dest), "by": by}
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


__all__ = ["Refused", "kind", "safe_parts", "unpack", "layout", "find_7zip", "find_tar", "parse_7z_listing", "parse_tar_listing", "plugins_in",
           "looks_like_data", "size_words"]
