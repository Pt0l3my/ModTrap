"""ModTrap's own downloads folder (MT50): the archives of mods ModTrap fetched or took over, each with where it came
from, kept so that no file is downloaded twice.

A folder of archives and one index beside them, `downloads.json`. A record names the file, its size, its source (the
host, the mod's and the file's number, the version, the page), how it came here, and the mod of the modlist it was
got for. A file that lies in MO2's own downloads folder is only referred to: it is MO2's, and stays where it is.

Nothing here reads an archive's contents, and nothing is deleted: a record whose file is gone is told as such.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
import time
from pathlib import Path

from . import logbook, paths

log = logbook.get("downloads")

INDEX = "downloads.json"
PREF = "downloads-folder.json"            # where the folder is, when the owner named another one
MAGIC = ((b"PK\x03\x04", ".zip"), (b"PK\x05\x06", ".zip"), (b"7z\xbc\xaf\x27\x1c", ".7z"), (b"Rar!\x1a\x07", ".rar"))    # an archive's first bytes
ARCHIVE = re.compile(r"\.(zip|7z|rar)$", re.IGNORECASE)
_lock = threading.RLock()


class Bad(Exception):
    """Something the owner can put right; the text is for them."""


def folder() -> Path:
    """ModTrap's downloads folder: the one the owner named, else `downloads` in ModTrap's own folder."""
    try:
        with open(paths.home() / PREF, "rb") as f:
            named = str(json.loads(f.read(64 * 1024).decode("utf-8")).get("folder") or "")
    except (OSError, ValueError, AttributeError):
        named = ""
    return Path(named) if named else paths.home() / "downloads"


def set_folder(path: str) -> Path:
    """Names another folder for ModTrap's downloads, or with "" goes back to its own. The files already downloaded
    are not moved: the folder named before keeps them, and its index."""
    path = (path or "").strip().strip('"')
    if path:
        p = Path(path)
        if not p.is_absolute():
            raise Bad("give the folder's full path")
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise Bad("that folder could not be made: %s" % logbook.why(e)) from None
    paths.write_atomic(paths.home() / PREF, json.dumps({"folder": path}).encode("utf-8"))
    log.info("ModTrap's downloads folder is %s", "the one the owner named" if path else "its own again")
    return folder()


def kind(path: Path) -> str:
    """The ending an archive's first bytes call for (".zip", ".7z", ".rar"), or "" where it is no archive."""
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return ""
    return next((ext for sig, ext in MAGIC if head.startswith(sig)), "")


def load() -> list[dict]:
    try:
        with open(folder() / INDEX, "rb") as f:
            got = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
        return [r for r in got if isinstance(r, dict) and r.get("id")] if isinstance(got, list) else []
    except (OSError, ValueError):
        return []


def _save(records: list[dict]) -> None:
    paths.write_atomic(folder() / INDEX, (json.dumps(records, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def path_of(rec: dict) -> Path:
    """Where a record's file lies: in ModTrap's folder, or where it was referred to."""
    return Path(rec["path"]) if rec.get("path") else folder() / rec.get("file", "")


def there(rec: dict) -> bool:
    try:
        st = path_of(rec).stat()
    except OSError:
        return False
    return not rec.get("size") or st.st_size == rec["size"]


def _same_source(rec: dict, meta: dict) -> bool:
    if meta.get("host") == "nexus" and meta.get("mod_id") and meta.get("file_id"):
        return rec.get("host") == "nexus" and rec.get("game") == meta.get("game") and rec.get("mod_id") == meta["mod_id"] and rec.get("file_id") == meta["file_id"]
    return bool(meta.get("url")) and rec.get("url") == meta.get("url") and rec.get("version") == meta.get("version") and bool(meta.get("version"))


def find(meta: dict) -> dict | None:
    """A file already here for this source: the same mod's same file at Nexus, or the same address and version; else
    one of exactly the size the site gives for the file. Only a record whose file is still there counts."""
    with _lock:
        records = load()
    for rec in records:
        if _same_source(rec, meta) and there(rec):
            return rec
    if meta.get("size"):
        for rec in records:
            if rec.get("size") == meta["size"] and there(rec) and (not meta.get("mod_id") or not rec.get("mod_id") or rec.get("mod_id") == meta["mod_id"]):
                return rec
    return None


def _free_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name).strip(" .")[:180] or "download"
    stem, ext = (name[:-len(m.group(0))], m.group(0)) if (m := ARCHIVE.search(name)) else (name, "")
    out, n = name, 2
    while (folder() / out).exists() or out.lower() == INDEX:
        out, n = "%s (%d)%s" % (stem, n, ext), n + 1
    return out


def _record(meta: dict, how: str) -> dict:
    keep = {k: meta[k] for k in ("host", "game", "mod_id", "file_id", "version", "label", "url", "page", "for_mod", "modlist") if meta.get(k)}
    return {"id": secrets.token_hex(4), "how": how, "when": int(time.time()), **keep}


def take(src: Path, name: str, meta: dict, how: str, move: bool) -> dict:
    """Takes an archive into ModTrap's folder, by moving or by copying it, and records it. Where a file of the same
    source is already here, that one is used and `src` is left where it is: nothing is kept twice."""
    with _lock:
        size = src.stat().st_size
        had = find(dict(meta, size=size))
        if had is not None and path_of(had) != src:
            return had
        ext = kind(src)
        if not ARCHIVE.search(name) and ext:
            name += ext
        dest_name = _free_name(name)
        dest = folder() / dest_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            if move:
                shutil.move(str(src), str(dest))
            else:
                shutil.copyfile(src, dest)
            if dest.stat().st_size != size:
                raise OSError("the file in ModTrap's folder is not whole")
        except OSError as e:
            raise Bad("the download could not be taken into ModTrap's downloads folder: %s" % logbook.why(e)) from None
        rec = dict(_record(meta, how), file=dest_name, size=size)
        records = load()
        records.append(rec)
        _save(records)
        log.info("a download is kept in ModTrap's folder: “%s”, %s bytes (%s)", dest_name, format(size, ","), how)
        return rec


def refer(path: Path, meta: dict, how: str) -> dict:
    """Records a file that stays where it is (MO2's own downloads folder): used from there, never moved or copied."""
    with _lock:
        records = load()
        for rec in records:
            if rec.get("path") == str(path):
                return rec
        rec = dict(_record(meta, how), path=str(path), size=path.stat().st_size)
        records.append(rec)
        _save(records)
        return rec


def note(rec_id: str, **fields) -> None:
    """Adds to a record what became of the file: the mod it was installed as."""
    with _lock:
        records = load()
        for rec in records:
            if rec["id"] == rec_id:
                rec.update({k: v for k, v in fields.items() if v is not None})
                _save(records)
                return


def rows(modlist: str = "", where_mo2: Path | None = None) -> list[dict]:
    """The downloads for the page, newest first: no path of a file outside ModTrap's folder is given, only which
    folder it lies in."""
    out = []
    for rec in sorted(load(), key=lambda r: -int(r.get("when") or 0)):
        p = path_of(rec)
        inside = not rec.get("path")
        out.append({"id": rec["id"], "file": rec.get("file") or p.name, "size": rec.get("size") or 0, "there": there(rec),
                    "where": "ModTrap's downloads folder" if inside else "MO2's downloads folder" if where_mo2 is not None and p.parent == where_mo2 else "another folder",
                    "host": rec.get("host", ""), "game": rec.get("game", ""), "mod_id": rec.get("mod_id") or 0, "file_id": rec.get("file_id") or 0,
                    "version": rec.get("version", ""), "label": rec.get("label", ""), "url": rec.get("url", ""), "page": rec.get("page", ""),
                    "how": rec.get("how", ""), "when": rec.get("when") or 0, "for_mod": rec.get("for_mod", ""), "installed_as": rec.get("installed_as", ""),
                    "this_modlist": not modlist or rec.get("modlist", "") in ("", modlist)})
    return out


__all__ = ["Bad", "find", "folder", "kind", "load", "note", "path_of", "refer", "rows", "set_folder", "take", "there"]
