"""Where each mod of the modlist came from (MT37, WHY§101): read from files on this PC only, nothing asked of anyone.

Three records say where a mod came from, and ModTrap reads all three:

- the mod's own `meta.ini`, which MO2 keeps (MO01§12): the mod's number at Nexus, the version installed, the newest
  version MO2 last saw, the archive it was installed from, the files installed by their numbers, a web address;
- the `.meta` file MO2 keeps beside each downloaded archive (MO01§12): the mod's and the file's number, a web
  address;
- the modlist's own Wabbajack file, if the owner names it (TL01§27): every archive of the list with where it is
  downloaded from, and which mod folders the list fills from which archive. It also says which mods are the
  list's own: a mod it does not name was added afterwards.

Nothing here changes a file, and nothing here goes out to the network: that is `updates.py`.
"""

from __future__ import annotations

import json
import os
import re
import time
import zipfile
from pathlib import Path

from . import logbook, paths
MOD_PREFIX = "ModTrap - "               # the name of the mod ModTrap makes for a demaster (as `demaster.MOD_PREFIX`; not
                                     # taken from there: the parts that change a modlist are loaded only with their switch)
from .instance import Instance, fold, parse_ini

log = logbook.get("sources")

META_BYTES = 512 * 1024              # a meta file is read no further than this
WJ_ENTRY = "modlist"                 # the list itself, inside a Wabbajack file (TL01§27)
WJ_CHUNK = 1024 * 1024
WJ_VALUE_MAX = 64 * 1024 * 1024      # one entry of the list larger than this is passed over
GITHUB = re.compile(r"^https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/releases/download/([^/]+)/)?", re.IGNORECASE)
_data: dict | None = None


def data() -> dict:
    """ModTrap's data on sources (`sources.json`): the name of a game at Nexus by MO2's and by Wabbajack's name
    for it, and the states of a file at Nexus."""
    global _data
    if _data is None:
        with open(Path(__file__).with_name("data") / "sources.json", "rb") as f:
            _data = json.loads(f.read().decode("utf-8"))
    return _data


def nexus_game(name: str) -> str:
    """The game's name in Nexus's addresses, for MO2's or Wabbajack's name of it; "" when ModTrap does not know."""
    return str(data()["nexus_games"].get((name or "").strip().lower(), ""))


def _ini(path: Path) -> dict[str, dict[str, str]]:
    try:
        with open(path, "rb") as f:
            raw = f.read(META_BYTES)
    except OSError:
        return {}
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", "replace")
    try:
        got = parse_ini(text)
    except Exception:
        return {}
    return {sec.lower(): {k.lower(): v for k, v in keys.items()} for sec, keys in got.items()}


def _number(text: str) -> int:
    try:
        n = int(str(text).strip())
    except ValueError:
        return 0
    return n if n > 0 else 0


def mod_meta(folder: Path) -> dict:
    """What a mod's `meta.ini` says of where it came from (MO01§12). {"mod_id", "game", "version", "mo2_newest",
    "ignored", "archive", "repository", "url", "last_query", "files": [(mod number, file number)]}."""
    ini = _ini(folder / "meta.ini")
    g = ini.get("general", {})
    files = []
    arr = ini.get("installedfiles", {})
    for i in range(1, _number(arr.get("size", "0")) + 1):
        pair = (_number(arr.get("%d\\modid" % i, "")), _number(arr.get("%d\\fileid" % i, "")))
        if pair[0] and pair[1] and pair not in files:
            files.append(pair)
    url = g.get("url", "") if g.get("hascustomurl", "").lower() == "true" or not _number(g.get("modid", "")) else ""
    return {"mod_id": _number(g.get("modid", "")), "game": g.get("gamename", ""), "version": g.get("version", ""),
            "mo2_newest": g.get("newestversion", ""), "ignored": g.get("ignoredversion", ""),
            "archive": os.path.basename(g.get("installationfile", "").replace("\\", "/")),
            "repository": g.get("repository", ""), "url": url if url.lower().startswith(("http://", "https://")) else "",
            "last_query": g.get("lastnexusquery", ""), "files": files}


def download_meta(downloads: Path | None, archive: str) -> dict:
    """What the `.meta` file beside a downloaded archive says (MO01§12). {"mod_id", "file_id", "game", "version",
    "url"}; empty when there is none."""
    if downloads is None or not archive:
        return {}
    g = _ini(downloads / (archive + ".meta")).get("general", {})
    if not g:
        return {}
    url = next((u for u in g.get("url", "").split(";") if u.lower().startswith(("http://", "https://"))), "")
    return {"mod_id": _number(g.get("modid", "")), "file_id": _number(g.get("fileid", "")), "game": g.get("gamename", ""),
            "version": g.get("version", ""), "url": url}


# --- a Wabbajack file --------------------------------------------------------------------------------------------

def _values(stream, want: set[str]):
    """Walks one large JSON object piece by piece and gives (key, value) for each entry of the arrays named in
    `want` at its top, and (key, value) for its other top entries that are plain texts. The list of a large
    modlist is hundreds of megabytes: it is never held whole."""
    dec = json.JSONDecoder()
    buf = ""
    pos = 0
    done = False

    def more() -> bool:
        nonlocal buf, pos, done
        if done:
            return False
        piece = stream.read(WJ_CHUNK)
        if not piece:
            done = True
            return False
        buf = buf[pos:] + piece
        pos = 0
        return True

    def skip_space() -> bool:
        nonlocal pos
        while True:
            while pos < len(buf) and buf[pos] in " \t\r\n,":
                pos += 1
            if pos < len(buf):
                return True
            if not more():
                return False

    def value():
        """One whole JSON value at `pos`; more of the file is read until it is whole."""
        nonlocal pos
        while True:
            try:
                got, end = dec.raw_decode(buf, pos)
                if end == len(buf) and not done and not buf[pos] in '[{"':
                    raise ValueError("a number or word may go on in the next piece")
                pos = end
                return got
            except ValueError:
                if len(buf) - pos > WJ_VALUE_MAX or not more():
                    raise

    if not skip_space() or buf[pos] != "{":
        raise ValueError("not a list")
    pos += 1
    while skip_space():
        if buf[pos] == "}":
            return
        key = value()
        if not skip_space() or buf[pos] != ":":
            raise ValueError("no value")
        pos += 1
        if not skip_space():
            raise ValueError("cut short")
        if key in want and buf[pos] == "[":
            pos += 1
            while skip_space():
                if buf[pos] == "]":
                    pos += 1
                    break
                yield key, value()
        else:
            got = value()
            if isinstance(got, (str, int, float)):
                yield key, got


def _state(state: dict) -> dict:
    """Where an archive of the list is downloaded from, in ModTrap's own words (TL01§27)."""
    kind = str(state.get("$type", "")).split(",")[0].strip()
    if kind.startswith("NexusDownloader"):
        return {"host": "nexus", "game": nexus_game(str(state.get("GameName", ""))), "mod_id": _number(state.get("ModID", "")),
                "file_id": _number(state.get("FileID", "")), "version": str(state.get("Version") or "")}
    url = str(state.get("Url") or "")
    if url:
        hit = GITHUB.match(url)
        return {"host": "github" if hit else "url", "url": url}
    return {"host": {"GameFileSourceDownloader": "game", "WabbajackCDNDownloader+State": "list's own files",
                     "ManualDownloader": "by hand", "MegaDownloader": "mega", "GoogleDriveDownloader": "google drive",
                     "MediaFireDownloader+State": "mediafire", "ModDBDownloader": "moddb"}.get(kind, kind or "unknown")}


def read_wabbajack(path: Path, progress=None) -> dict:
    """The modlist's own Wabbajack file (TL01§27): {"name", "version", "archives": {archive's hash: {"name", "host",
    ...}}, "by_name": {archive's file name, folded: hash}, "mods": {mod folder, folded: [archive hashes, most used
    first]}, "counts": {...}}. Raises ValueError with a reason in words when the file is not one."""
    try:
        zf = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        raise ValueError("it could not be opened as a Wabbajack file (%s)" % logbook.why(e)) from None
    with zf:
        if WJ_ENTRY not in zf.namelist():
            raise ValueError("it holds no list (an entry called “%s”)" % WJ_ENTRY)
        archives: dict[str, dict] = {}
        by_name: dict[str, str] = {}
        uses: dict[str, dict[str, int]] = {}
        top: dict[str, object] = {}
        n_dir = 0
        hosts: dict[str, int] = {}
        with zf.open(WJ_ENTRY) as raw:
            import io
            stream = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
            try:
                for key, v in _values(stream, {"Archives", "Directives"}):
                    if key == "Archives" and isinstance(v, dict):
                        h = str(v.get("Hash", ""))
                        st = _state(v.get("State") or {}) if isinstance(v.get("State"), dict) else {"host": "unknown"}
                        st["name"] = str(v.get("Name", ""))
                        archives[h] = st
                        by_name[fold(st["name"])] = h
                        hosts[st["host"]] = hosts.get(st["host"], 0) + 1
                    elif key == "Directives" and isinstance(v, dict):
                        n_dir += 1
                        to = str(v.get("To", "")).replace("/", "\\")
                        parts = to.split("\\")
                        if len(parts) >= 3 and parts[0].lower() == "mods":
                            mod = uses.setdefault(fold(parts[1]), {})
                            ahp = v.get("ArchiveHashPath")
                            h = str(ahp[0]) if isinstance(ahp, list) and ahp else ""
                            mod[h] = mod.get(h, 0) + 1
                        if progress is not None and n_dir % 100_000 == 0:
                            progress(n_dir)
                    elif key in ("Name", "Version", "WabbajackVersion", "GameType"):
                        top[key] = v
            except (ValueError, RecursionError) as e:
                raise ValueError("its list could not be read to the end (%s)" % logbook.why(e)) from None
    mods = {m: [h for h, _n in sorted(hs.items(), key=lambda kv: -kv[1]) if h in archives] for m, hs in uses.items()}
    return {"name": str(top.get("Name", "")), "version": str(top.get("Version", "")), "game": str(top.get("GameType", "")),
            "archives": archives, "by_name": by_name, "mods": mods,
            "counts": {"archives": len(archives), "directives": n_dir, "mods": len(mods), "hosts": hosts}}


def wabbajack(path: Path, progress=None) -> dict:
    """`read_wabbajack`, remembered in ModTrap's own folder by the file's size and date: a large list takes a
    while to read, and does not change."""
    st = path.stat()
    memo = paths.home() / "wabbajack" / ("%s-%d-%d.json" % (re.sub(r"[^A-Za-z0-9_.-]", "_", path.name)[:80], st.st_size, st.st_mtime_ns))
    try:
        with open(memo, "rb") as f:
            got = json.loads(f.read().decode("utf-8"))
        if got.get("format") == "modtrap-wabbajack/1":
            return got["list"]
    except (OSError, ValueError, KeyError):
        pass
    started = time.monotonic()
    got = read_wabbajack(path, progress)
    c = got["counts"]
    log.info("the Wabbajack file “%s” (%s) was read in %.1f s: %s archive(s) (%s), %s entr(ies) of what goes where, %s mod folder(s)",
             got["name"], got["version"], time.monotonic() - started, format(c["archives"], ","),
             ", ".join("%s from %s" % (format(n, ","), host) for host, n in sorted(c["hosts"].items(), key=lambda kv: -kv[1])),
             format(c["directives"], ","), format(c["mods"], ","))
    try:
        paths.write_atomic(memo, json.dumps({"format": "modtrap-wabbajack/1", "list": got}).encode("utf-8"))
    except OSError as e:
        log.warn("the reading of the Wabbajack file could not be kept for next time: %s", logbook.why(e))
    return got


# --- all of it, for each mod -----------------------------------------------------------------------------------

def gather(inst: Instance, wj: dict | None = None, added_by_modtrap: set[str] | None = None) -> list[dict]:
    """One row for each mod of the modlist: where it came from, by every record there is. {"mod", "enabled",
    "host": "nexus", "github", "url" or "", "game", "mod_id", "files": [file numbers at Nexus known to be installed],
    "archive", "version", "mo2_newest", "url", "repo": "owner/name", "tag", "origin": "list", "modtrap", "added" or ""
    (not known: no Wabbajack file was named), "by": which record said so}."""
    added = {fold(n) for n in (added_by_modtrap or set())}
    rows = []
    for m in inst.mods:
        if m.kind != "mod" or m.folder is None:
            continue
        meta = mod_meta(m.folder)
        dl = download_meta(inst.downloads_dir, meta["archive"])
        row = {"mod": m.name, "enabled": m.enabled, "host": "", "game": "", "mod_id": 0, "files": [], "archive": meta["archive"],
               "version": meta["version"], "mo2_newest": meta["mo2_newest"], "url": "", "repo": "", "tag": "", "by": []}
        from_list: list[dict] = []
        if wj is not None:
            hashes = list(wj["mods"].get(fold(m.name), []))
            if meta["archive"] and fold(meta["archive"]) in wj["by_name"]:
                h = wj["by_name"][fold(meta["archive"])]
                hashes = [h] + [x for x in hashes if x != h]          # the archive MO2 names for the mod comes first
            from_list = [wj["archives"][h] for h in hashes if h in wj["archives"]]
            in_list = fold(m.name) in wj["mods"]
            row["origin"] = "modtrap" if fold(m.name) in added or m.name.startswith(MOD_PREFIX) else "list" if in_list else "added"
        else:
            row["origin"] = "modtrap" if fold(m.name) in added or m.name.startswith(MOD_PREFIX) else ""
        # Nexus: the mod's number by MO2's own records first, then by the list's file.
        game = nexus_game(meta["game"]) or nexus_game(dl.get("game", ""))
        mod_id = meta["mod_id"] or dl.get("mod_id", 0)
        if mod_id and game:
            row.update(host="nexus", game=game, mod_id=mod_id)
            row["by"].append("meta.ini" if meta["mod_id"] else "the download's meta file")
            ids = [f for mid, f in meta["files"] if mid == mod_id]
            if dl.get("mod_id") == mod_id and dl.get("file_id") and dl["file_id"] not in ids:
                ids.append(dl["file_id"])
            for a in from_list:
                if a["host"] == "nexus" and a.get("mod_id") == mod_id and a.get("game") == game and a.get("file_id") and a["file_id"] not in ids:
                    ids.append(a["file_id"])
                    if "the Wabbajack file" not in row["by"]:
                        row["by"].append("the Wabbajack file")
            row["files"] = ids
        else:
            first = next((a for a in from_list if a["host"] == "nexus" and a.get("mod_id") and a.get("game")), None)
            if first is not None:
                row.update(host="nexus", game=first["game"], mod_id=first["mod_id"], by=["the Wabbajack file"],
                           files=[a["file_id"] for a in from_list if a["host"] == "nexus" and a.get("mod_id") == first["mod_id"] and a.get("file_id")])
                row["version"] = row["version"] or first.get("version", "")
        if not row["host"]:
            url = meta["url"] or dl.get("url", "") or next((a.get("url", "") for a in from_list if a.get("url")), "")
            if url:
                hit = GITHUB.match(url)
                row.update(host="github" if hit else "url", url=url)
                row["by"].append("meta.ini" if meta["url"] else "the download's meta file" if dl.get("url") else "the Wabbajack file")
                if hit:
                    row["repo"] = "%s/%s" % (hit.group(1), re.sub(r"\.git$", "", hit.group(2)))
                    row["tag"] = hit.group(3) or ""
            elif from_list:
                row["host"] = from_list[0]["host"] if from_list[0]["host"] not in ("nexus", "github", "url") else ""
                row["by"].append("the Wabbajack file")
        rows.append(row)
    return rows


__all__ = ["data", "download_meta", "gather", "mod_meta", "nexus_game", "read_wabbajack", "wabbajack"]
