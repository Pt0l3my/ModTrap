"""The update check as the page sees it (MT37, WHY§101): the rows, the Wabbajack file's place, the key, the scan.

`sources.py` reads where each mod came from, `updates.py` asks the two services; this keeps the two together for
one open modlist: what is remembered between launches, the scan as a piece of work that goes on beside everything
else, and the account given to the page. It changes nothing in the modlist.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

from . import logbook, paths, secret, sources, updates

log = logbook.get("updates")

KEY = "nexus"
PLACES = "update-lists.json"         # which Wabbajack file belongs to which modlist
PREFS = "update-prefs.json"          # the folder the owner's browser saves downloads to, if not the usual one
WAIT_SECONDS = 45 * 60               # how long ModTrap waits for a download the owner started in the browser
LOOK_EVERY = 2.0                     # seconds between two looks into the watched folders
NEXUS_NAME = re.compile(r"-(\d+)-.*-(\d{9,11})\.(?:zip|7z|rar)$", re.IGNORECASE)   # a Nexus download's name: mod's number … time of upload
PARTIAL = (".crdownload", ".part", ".partial", ".tmp", ".download", ".unfinished", ".opdownload")
LIST_MAX = 2 * 1024 * 1024 * 1024    # the bytes of a dropped list, at most
DROP_FILES = 20_000                  # meta files taken in one drop, at most
ROWS_MAX = 20_000


class Bad(Exception):
    pass


class Updating:
    def __init__(self, version: str = "", net: updates.Net | None = None):
        self.net = net or updates.Net(version)
        self._lock = threading.Lock()
        self._rows: tuple | None = None           # (the model the rows were made for, the list's reading, the rows)
        self._lists: dict[str, dict] = {}         # a Wabbajack file's path -> its reading
        self.work = {"state": "idle", "text": "", "started": 0.0, "error": ""}
        self.reading = {"state": "idle", "text": "", "error": ""}
        self._stop = threading.Event()
        self.store = updates.load()
        self.launched = False
        self.waiting: dict[str, dict] = {}         # a mod's name -> the download ModTrap waits for (MT42)
        self._sizes: dict[str, int] = {}           # a candidate file -> its size at the last look: taken once it stands
        self._looked = 0.0
        self.premium: bool | None = None           # whether the key's account is a paying one, once Nexus has said
        self.fetching: dict[str, dict] = {}        # a mod's name -> how the fetching of its newer file stands
        self.mark_reader = None                    # reads a download's mark of the browser; a test's stand-in

    # --- the Wabbajack file of a modlist ---------------------------------------------------------------------------
    def _places(self) -> dict:
        try:
            with open(paths.home() / PLACES, "rb") as f:
                got = json.loads(f.read().decode("utf-8"))
            return got if isinstance(got, dict) else {}
        except (OSError, ValueError):
            return {}

    def _place(self, modlist_key: str) -> dict:
        """Where the modlist's Wabbajack list is: {"path"} for a file named by its path, {"memo", "file"} for one that
        was dropped on the page (its reading is kept, the file is not), {} for none."""
        got = self._places().get(modlist_key)
        return {"path": got} if isinstance(got, str) and got else got if isinstance(got, dict) else {}

    def _set_place(self, modlist_key: str, place: dict | None) -> None:
        places = self._places()
        if place:
            places[modlist_key] = place
        else:
            places.pop(modlist_key, None)
        paths.write_atomic(paths.home() / PLACES, json.dumps(places).encode("utf-8"))
        with self._lock:
            self._rows = None
            self.reading = dict(self.reading, error="")

    def set_list(self, modlist_key: str, path: str) -> dict:
        """Names the modlist's own Wabbajack file by its path, or forgets it with an empty path. The file is only read."""
        path = path.strip().strip('"')
        if not path:
            self._set_place(modlist_key, None)
            return {"kept": False}
        p = Path(path)
        if not p.is_file():
            raise Bad("there is no file at that path")
        if p.suffix.lower() != ".wabbajack":
            raise Bad("that is not a Wabbajack file: its name ends in .wabbajack")
        self._set_place(modlist_key, {"path": str(p)})
        self._read_list(str(p), lambda progress: sources.wabbajack(p, progress))
        return {"kept": True}

    def take_list(self, modlist_key: str, name: str, size: int, date: int, method: int, length: int, stream) -> dict:
        """The list of a Wabbajack file dropped on the page: the page cuts the list out of the file and sends its
        bytes alone (WHY§103), so that a file of some gigabytes is not copied. They are written to ModTrap's own
        folder as they arrive, read from there, and deleted; only the reading is kept."""
        name = Path(name.replace("\\", "/")).name[:200] or "a dropped list"
        if length <= 0 or length > LIST_MAX:
            raise Bad("the list did not arrive, or is larger than ModTrap takes")
        with self._lock:
            if self.reading["state"] == "going":
                raise Bad("a Wabbajack list is being read already")
            self.reading = {"state": "going", "text": "taking in the Wabbajack list", "error": ""}
        memo = sources.memo_name(name, size, date)
        tmp = paths.home() / "wabbajack" / ("incoming-%d.bin" % threading.get_ident())
        try:
            tmp.parent.mkdir(parents=True, exist_ok=True)
            left = length
            with open(tmp, "wb") as f:
                while left > 0:
                    piece = stream.read(min(left, 1024 * 1024))
                    if not piece:
                        raise Bad("the list did not arrive whole")
                    f.write(piece)
                    left -= len(piece)
        except (OSError, Bad) as e:
            tmp.unlink(missing_ok=True)
            with self._lock:
                self.reading = {"state": "idle", "text": "", "error": ""}
            raise Bad(str(e) if isinstance(e, Bad) else "the list could not be taken in: %s" % logbook.why(e)) from None

        def read(progress):
            try:
                started = time.monotonic()
                got = sources.read_list_bytes(tmp, method, progress)
                sources.said(got, time.monotonic() - started)
                sources.memo_write(memo, got)
                self._set_place(modlist_key, {"memo": memo, "file": name})
                return got
            finally:
                tmp.unlink(missing_ok=True)

        with self._lock:
            self.reading = {"state": "idle", "text": "", "error": ""}
            self._lists.pop("memo:" + memo, None)           # the same file dropped again is read again
        self._read_list("memo:" + memo, read)
        return {"taken": True, "file": name}

    def _read_list(self, key: str, read) -> None:
        with self._lock:
            if self.reading["state"] == "going" or key in self._lists:
                return
            self.reading = {"state": "going", "text": "reading the Wabbajack list", "error": ""}

        def run():
            try:
                got = read(lambda n: self.reading.update(text="reading the Wabbajack list: %s entries" % format(n, ",")))
                with self._lock:
                    self._lists[key] = got
                    self._rows = None
                    self.reading = {"state": "idle", "text": "", "error": ""}
            except (ValueError, OSError) as e:
                why = str(e) if isinstance(e, ValueError) else logbook.why(e)
                log.warn("the Wabbajack list could not be read: %s", why)
                with self._lock:
                    self.reading = {"state": "idle", "text": "", "error": "The Wabbajack file could not be read: %s." % why}
            except Exception as e:
                log.error("reading the Wabbajack list failed: %s", logbook.why(e))
                with self._lock:
                    self.reading = {"state": "idle", "text": "", "error": "Reading the Wabbajack file failed (%s)." % logbook.why(e)}

        threading.Thread(target=run, name="wabbajack", daemon=True).start()

    def _list(self, modlist_key: str) -> tuple[dict | None, dict]:
        """The modlist's Wabbajack list as far as it is read, and its place."""
        place = self._place(modlist_key)
        if place.get("path"):
            key = place["path"]
            if key not in self._lists and self.reading["state"] != "going" and not self.reading["error"]:
                p = Path(key)
                self._read_list(key, lambda progress: sources.wabbajack(p, progress))
        elif place.get("memo"):
            key = "memo:" + place["memo"]
            if key not in self._lists:
                got = sources.memo_read(place["memo"])
                if got is not None:
                    self._lists[key] = got
        else:
            return None, place
        return self._lists.get(key), place

    # --- what the owner gives by hand (WHY§103) -----------------------------------------------------------------------
    def set_link(self, modlist_key: str, mod: str, url: str) -> dict:
        """The owner's own source link for a mod, or none with an empty address. Kept in ModTrap's folder; the mod's
        own files are not touched."""
        given = sources.given_load()
        mine = given["links"].setdefault(modlist_key, {})
        url = (url or "").strip()
        if not url:
            mine.pop(sources.fold(mod), None)
            kind = ""
        else:
            try:
                kind = sources.parse_link(url)["host"]
            except ValueError as e:
                raise Bad(str(e)) from None
            mine[sources.fold(mod)] = url
        sources.given_save(given)
        with self._lock:
            self._rows = None
        log.info("a source link for “%s” is %s", mod, "kept (%s)" % {"nexus": "a mod's page at Nexus", "github": "a GitHub repository", "url": "a web address"}[kind] if url else "forgotten")
        return {"kept": bool(url), "kind": kind}

    def set_favourite(self, modlist_key: str, mod: str, on: bool) -> dict:
        """The owner's own mark on a mod (MT46): a favourite, to find it again by a filter. Kept in ModTrap's folder
        for that modlist; nothing of the mod is touched."""
        given = sources.given_load()
        mine = set(given["favourites"].get(modlist_key, []))
        (mine.add if on else mine.discard)(sources.fold(mod))
        given["favourites"][modlist_key] = sorted(mine)
        sources.given_save(given)
        return {"favourite": bool(on), "count": len(mine)}

    def take_metas(self, modlist_key: str, files: list) -> dict:
        """Meta files dropped on the page: a download's `<archive>.meta` says where that archive came from, for every
        mod installed from it; a mod's `meta.ini`, dropped with its folder, says so for the mod of that name."""
        given = sources.given_load()
        mods = given["mods"].setdefault(modlist_key, {})
        out = {"archives": 0, "mods": 0, "passed": []}
        for f in files[:DROP_FILES]:
            if not isinstance(f, dict) or not isinstance(f.get("name"), str) or not isinstance(f.get("text"), str):
                continue
            name, folder = f["name"][:300], str(f.get("folder") or "")[:300]
            ini = sources._ini_text(f["text"][:sources.META_BYTES].encode("utf-8"))
            if name.lower().endswith(".meta"):
                got = sources.download_meta_of(ini)
                if got.get("mod_id") or got.get("url"):
                    given["archives"][sources.fold(name[:-5])] = got
                    out["archives"] += 1
                else:
                    out["passed"].append("%s: it names no source" % name)
            elif name.lower() == "meta.ini":
                if not folder:
                    out["passed"].append("meta.ini: alone it does not say which mod it is of; drop the mod's folder, or right-click the mod and add a source link")
                    continue
                got = sources.mod_meta_of(ini)
                if got.get("mod_id") or got.get("url"):
                    mods[sources.fold(folder)] = {k: got[k] for k in ("mod_id", "game", "url", "files", "archive", "version")}
                    out["mods"] += 1
                else:
                    out["passed"].append("%s/meta.ini: it names no source" % folder)
            else:
                out["passed"].append("%s: not a meta file" % name)
        out["passed"] = out["passed"][:40]
        if out["archives"] or out["mods"]:
            sources.given_save(given)
            with self._lock:
                self._rows = None
        log.info("meta files given by hand: %d of downloads, %d of mods, %d passed over", out["archives"], out["mods"], len(out["passed"]))
        return out

    def _given(self, modlist_key: str) -> dict:
        g = sources.given_load()
        return {"links": g["links"].get(modlist_key, {}), "archives": g["archives"], "mods": g["mods"].get(modlist_key, {})}

    # --- the rows ----------------------------------------------------------------------------------------------------
    def rows(self, model, modlist_key: str, added: set[str]) -> tuple[list[dict], dict | None]:
        wj, _place = self._list(modlist_key)
        with self._lock:
            hit = self._rows
            if hit is not None and hit[0] is model and hit[1] is wj and hit[3] == added:
                return hit[2], wj
        rows = sources.gather(model.instance, wj, added, self._given(modlist_key))
        with self._lock:
            self._rows = (model, wj, rows, set(added))
        return rows, wj

    def account(self, model, modlist_key: str, added: set[str], stage=None) -> dict:
        """Everything the Updates tab shows. `stage` takes an archive that lies in a watched folder to Add mods."""
        rows, wj = self.rows(model, modlist_key, added)
        if stage is not None and self.waiting:
            try:
                self.look(model, stage)
            except Exception as e:
                log.warn("looking for a download failed: %s", logbook.why(e))
        out_rows = []
        counts = {"update": 0, "maybe": 0, "current": 0, "not asked": 0, "none": 0, "gone": 0}
        origins = {"list": 0, "added": 0, "modtrap": 0, "": 0}
        hosts: dict[str, int] = {}
        key_kept = secret.kept(KEY)
        for r in rows[:ROWS_MAX]:
            v = updates.verdict(r, self.store)
            counts[v["state"]] = counts.get(v["state"], 0) + 1
            origins[r["origin"]] = origins.get(r["origin"], 0) + 1
            hosts[r["host"] or "not known"] = hosts.get(r["host"] or "not known", 0) + 1
            out_rows.append({"mod": r["mod"], "enabled": r["enabled"], "host": r["host"], "id": r["mod_id"] or r["repo"], "version": r["version"],
                             "archive": r["archive"], "origin": r["origin"], "by": r["by"], "given": r.get("given", ""), "state": v["state"], "text": v["text"],
                             "newest": v["newest"], "file": v["file"], "when": v["when"], "asked": v["asked"], "page": updates.page_of(r),
                             "get": updates.get_of(r, v) or (updates.page_of(r) if r["host"] in ("loverslab", "url") else ""), "fetches": "fetch" in updates.how_to_get(r, v, self.store, key_kept, self.premium)
                             if v["state"] == "update" else False, "priority": r.get("priority", 0), "comments": r.get("comments", ""), "notes": r.get("notes", "")})
        place = self._place(modlist_key)
        given = sources.given_load()
        favs = set(given["favourites"].get(modlist_key, []))
        for r in out_rows:
            r["fav"] = sources.fold(r["mod"]) in favs
        counts["fav"] = sum(1 for r in out_rows if r["fav"])
        return {"rows": out_rows, "counts": counts, "origins": origins, "hosts": hosts, "key": secret.kept(KEY),
                "given": {"links": len(given["links"].get(modlist_key, {})), "archives": len(given["archives"]), "mods": len(given["mods"].get(modlist_key, {}))},
                "list": {"named": bool(place), "file": Path(place["path"]).name if place.get("path") else place.get("file", ""), "name": wj["name"] if wj else "",
                         "version": wj["version"] if wj else "", "counts": wj["counts"] if wj else None,
                         "reading": self.reading["state"] == "going", "text": self.reading["text"], "error": self.reading["error"]},
                "scan": dict(self.work), "last": self.store.get("last") or None,
                "premium": self.premium, "fetching": {k: dict(v) for k, v in self.fetching.items()}, "key_page": updates.KEY_PAGE,
                "watch": {"folder": str(self.downloads_folder()), "there": self.downloads_folder().is_dir(),
                          "waiting": {m: {"minutes": max(0, int((WAIT_SECONDS - (time.time() - w["since"])) // 60)), "name": w["name"]}
                                      for m, w in self.waiting.items()}}}

    # --- waiting for a download the owner starts in the browser (MT42) ---------------------------------------------------
    def downloads_folder(self) -> Path:
        """Where the owner's browser saves downloads: the folder they named, else Windows' own Downloads folder."""
        try:
            with open(paths.home() / PREFS, "rb") as f:
                named = str(json.loads(f.read().decode("utf-8")).get("downloads") or "")
        except (OSError, ValueError, AttributeError):
            named = ""
        if named:
            return Path(named)
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                class GUID(ctypes.Structure):
                    _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

                fid = GUID(0x374DE290, 0x123F, 0x4565, (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
                got = ctypes.c_wchar_p()
                shell32, ole32 = ctypes.WinDLL("shell32"), ctypes.WinDLL("ole32")
                shell32.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
                ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
                if shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(got)) == 0 and got.value:
                    path = Path(got.value)
                    ole32.CoTaskMemFree(got)
                    return path
            except Exception:
                pass
        return Path(os.path.expanduser("~")) / "Downloads"

    def set_downloads_folder(self, path: str) -> dict:
        path = (path or "").strip().strip('"')
        if path and not Path(path).is_dir():
            raise Bad("there is no folder at that path")
        paths.write_atomic(paths.home() / PREFS, json.dumps({"downloads": path}).encode("utf-8"))
        log.info("the folder watched for the browser's downloads is %s", "the one the owner named" if path else "Windows' own Downloads folder again")
        return {"folder": str(self.downloads_folder())}

    def stop_waiting(self, mod: str) -> dict:
        self.waiting.pop(mod, None)
        return {}

    def _expect(self, row: dict, v: dict) -> None:
        self.waiting[row["mod"]] = {"since": time.time(), "host": row["host"], "mod_id": row.get("mod_id") or 0, "file_id": v.get("file_id") or 0,
                                    "name": v.get("file_name") or "", "label": v.get("file") or "", "time": v.get("time") or 0,
                                    "game": row.get("game") or "", "archive": row.get("archive") or "", "version": v.get("newest") or "",
                                    "installed": list(row.get("files") or []), "url": row.get("url") or ""}

    def look(self, model, stage) -> None:
        """Looks into MO2's downloads folder and the browser's for an archive a waiting mod's download has brought, and
        hands it to Add mods through `stage(path, name, mod, version)`, read where it lies. A file counts once it is
        whole: not under a name browsers and MO2 give an unfinished download, and of the same size at two looks.
        It never deletes or moves a file of the owner's."""
        now = time.time()
        if not self.waiting or now - self._looked < LOOK_EVERY:
            return
        self._looked = now
        for mod in [m for m, w in self.waiting.items() if now - w["since"] > WAIT_SECONDS]:
            self.waiting.pop(mod, None)
            self.fetching[mod] = {"state": "failed", "error": "no download for it showed up in %d minutes; ModTrap has stopped waiting" % (WAIT_SECONDS // 60), "open": ""}
        if not self.waiting:
            return
        first = min(w["since"] for w in self.waiting.values())
        shape = lambda name: re.sub(r"[\d._\- ()]+", "", name.lower())
        plain = lambda name: re.sub(r" \(\d+\)(?=\.\w+$)", "", name).lower()        # a browser's "name (1).zip"
        sizes: dict[str, int] = {}
        found: list[tuple[str, Path, str]] = []                                      # (mod, file, where)
        for where, folder in (("MO2's downloads folder", model.instance.downloads_dir), ("your browser's Downloads folder", self.downloads_folder())):
            if folder is None:
                continue
            try:
                with os.scandir(folder) as it:
                    entries = [e for e in it if e.is_file() and updates.ARCHIVE.search(e.name) and not e.name.lower().endswith(PARTIAL)]
            except OSError:
                continue
            for e in entries:
                try:
                    st = e.stat()
                except OSError:
                    continue
                if st.st_mtime < first - 5 or st.st_size <= 0:
                    continue
                sizes[e.path] = st.st_size
                if self._sizes.get(e.path) != st.st_size:
                    continue                                    # seen first now, or still growing: next look
                try:
                    with open(e.path, "rb") as f:
                        f.read(1)
                except OSError:
                    continue                                    # still held by what is writing it
                mine = None
                meta = sources.download_meta(Path(folder), e.name) if where.startswith("MO2") else {}
                mark = sources.web_mark(Path(e.path), self.mark_reader) if not where.startswith("MO2") else {}
                marked = [sources.NEXUS_PAGE.match(u) for u in (mark.get("page", ""), mark.get("url", "")) if u]
                marked = next((m for m in marked if m), None)
                named = NEXUS_NAME.search(plain(e.name))             # "…-<mod's number>-<version>-<time of upload>.7z"
                for mod, w in self.waiting.items():
                    if st.st_mtime < w["since"] - 5:
                        continue
                    if meta.get("mod_id") and w["mod_id"]:
                        # MO2's own record beside the archive: the mod's and the file's number.
                        if meta["mod_id"] == w["mod_id"] and (meta.get("file_id") == w["file_id"] if w["file_id"] else meta.get("file_id") not in w["installed"]):
                            mine = mod
                            break
                        continue
                    if marked is not None and w["mod_id"]:
                        # The browser's mark on the file: the page it was downloaded from is this mod's (WHY§110).
                        if int(marked.group(2)) == w["mod_id"] and marked.group(1).lower() == w["game"]:
                            mine = mod
                            break
                        continue
                    if w["name"] and plain(e.name) == w["name"].lower():
                        mine = mod
                        break
                    if named is not None and w["mod_id"] and int(named.group(1)) == w["mod_id"] and \
                            (int(named.group(2)) == w["time"] if w["time"] else int(named.group(2)) != updates.archive_time(w["archive"])):
                        mine = mod                                   # the mod's number and the upload's time, in the name
                        break
                if mine is None and named is None and marked is None:
                    # Nothing certain to go by (a name that carries a mod's number and a time, or a mark of a mod's
                    # page, has said whose file it is, and it is not a waited one's). A new archive is taken for the
                    # one mod waited for where its name begins as the file's name on its page does, or as the
                    # installed archive's, or where the site gives no name at all; never while several are waited for.
                    letters = lambda t: re.sub(r"[^a-z]+", "", t.lower())
                    alike = [mod for mod, w in self.waiting.items() if st.st_mtime >= w["since"] - 5 and w["archive"] and shape(w["archive"]) == shape(plain(e.name))]
                    if len(alike) == 1:
                        mine = alike[0]
                    elif len(self.waiting) == 1:
                        mod, w = next(iter(self.waiting.items()))
                        lead = letters(e.name)
                        starts = [letters(x)[:12] for x in (w.get("label") or "", re.sub(r"-\d+.*$", "", w["archive"])) if len(letters(x)) >= 4]
                        if st.st_mtime >= w["since"] - 5 and (not w["name"] and not w["mod_id"] or any(lead.startswith(x) for x in starts)):
                            mine = mod
                if mine is not None and mine not in [m for m, _p, _w in found]:
                    found.append((mine, Path(e.path), where))
        self._sizes = sizes
        for mod, path, where in found:
            w = self.waiting.pop(mod)
            try:
                # The new mod's own record gets what is known of the file: its numbers at Nexus, or the address the
                # browser says it came from, else the older version's address (WHY§109).
                dl = sources.download_meta(path.parent, path.name) if where.startswith("MO2") else {}
                meta = {"mod_id": w["mod_id"], "file_id": w["file_id"] or (dl.get("file_id", 0) if dl.get("mod_id") == w["mod_id"] else 0),
                        "version": w["version"] or dl.get("version", "")} if w["mod_id"] else \
                       {"version": w["version"], "url": sources.source_of_mark(sources.web_mark(path, self.mark_reader)) or w.get("url") or ""}
                rec = stage(path, path.name, mod, w["version"], meta)
                self.fetching[mod] = {"state": "done", "staged": rec["id"], "name": rec["name"]}
                log.info("the download for “%s” is in %s: taken to Add mods as its newer version", mod, where)
            except Exception as e:
                why = str(e) if e.__class__.__name__ == "Bad" else logbook.why(e)
                self.fetching[mod] = {"state": "failed", "error": why, "open": ""}
                log.warn("the download for “%s” was found and could not be taken in: %s", mod, why)

    # --- fetching a newer file (MT40) -----------------------------------------------------------------------------------
    def _account(self) -> None:
        """Asks Nexus once what kind of account the key is of: a program may start a download only for a paying one."""
        key = secret.read(KEY)
        if not key or self.premium is not None:
            return
        got = updates.nexus_account(key, self.net)
        if got["ok"]:
            self.premium = got["premium"]
            log.info("Nexus says the key's account is %s", "a Premium one: ModTrap can fetch files itself" if got["premium"]
                     else "not a Premium one: a download goes through Nexus's page and MO2")
        else:
            log.warn("the kind of the key's account could not be asked: %s", got["why"])

    def get(self, model, modlist_key: str, added: set[str], mod: str, folder: Path, stage, only_open: bool = False) -> dict:
        """The update button for one mod. Where ModTrap can fetch the newer file itself (a Nexus key of a paying
        account; a GitHub release), it does, beside everything else, and hands the file to Add mods through `stage`;
        the answer is {"going": True}. Otherwise the answer names the page to open and why: {"open", "why"}."""
        rows, _wj = self.rows(model, modlist_key, added)
        row = next((r for r in rows if r["mod"] == mod), None)
        if row is None:
            raise Bad("that is not a mod of this modlist")
        v = updates.verdict(row, self.store)
        key = secret.read(KEY)
        if row["host"] == "nexus" and key and self.premium is None:
            self._account()
        how = updates.how_to_get(row, v, self.store, bool(key), self.premium)
        if "open" in how or only_open:
            page = how.get("open") or how.get("page") or ""
            why = how.get("why") or "ModTrap adds mods only when it is started with its switch for changes, so the file is not fetched"
            if not page:
                raise Bad("no page is known for this mod: add a source link first")
            log.info("the newer file of “%s” is not fetched: %s; its page is opened instead", mod, why)
            if not only_open:
                self._expect(row, v)                       # what the owner downloads there is taken from the watched folders
            return {"open": page, "why": why, "watching": not only_open}
        with self._lock:
            if self.fetching.get(mod, {}).get("state") == "going":
                return {"going": True}
            self.fetching[mod] = {"state": "going", "text": "asking for the file", "pct": 0}

        def run():
            def progress(done: int, total: int) -> None:
                self.fetching[mod].update(text="fetching %s" % how.get("name", "the file"), pct=int(100 * done / total) if total else 0,
                                          mb=round(done / (1024 * 1024), 1))
            try:
                got = updates.fetch(how, row, key, self.net, folder, progress)
                if "open" in got:
                    self.premium = False
                    self._expect(row, v)
                    self.fetching[mod] = {"state": "open", "open": got["open"], "why": got["why"]}
                    return
                rec = stage(got["path"], got["name"], mod, got["version"],
                            {"mod_id": row.get("mod_id") or 0, "file_id": how.get("file_id") or 0, "version": got["version"],
                             "url": how.get("url") or ""} if row["host"] == "nexus" else {"version": got["version"], "url": how.get("url") or row.get("url") or ""})
                self.fetching[mod] = {"state": "done", "staged": rec["id"], "name": rec["name"]}
            except updates.Refused as e:
                log.warn("the newer file of “%s” was not fetched: %s", mod, e)
                self.fetching[mod] = {"state": "failed", "error": str(e), "open": how.get("page", "")}
            except Exception as e:
                why = str(e) if e.__class__.__name__ == "Bad" else logbook.why(e)
                log.error("fetching the newer file of “%s” failed: %s", mod, why)
                self.fetching[mod] = {"state": "failed", "error": why, "open": how.get("page", "")}

        threading.Thread(target=run, name="fetch", daemon=True).start()
        return {"going": True}

    def seen(self, mod: str) -> None:
        """The page has shown how a fetching ended: it is not told again."""
        if self.fetching.get(mod, {}).get("state") != "going":
            self.fetching.pop(mod, None)

    # --- the key -----------------------------------------------------------------------------------------------------
    def set_key(self, text: str | None) -> dict:
        self.premium = None
        if not text:
            secret.forget(KEY)
            log.info("the Nexus key is forgotten")
            return {"key": False}
        text = text.strip()
        if len(text) < 20 or len(text) > 400 or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in text):
            raise Bad("that does not look like a key from Nexus: it is one long line of letters and digits")
        try:
            secret.keep(KEY, text)
        except (OSError, ValueError) as e:
            raise Bad("the key could not be kept: %s" % logbook.why(e)) from None
        log.info("a Nexus key is kept on this PC (never shown, never written to the log or a session file)")
        return {"key": True}

    # --- the scan ----------------------------------------------------------------------------------------------------
    def start(self, model, modlist_key: str, added: set[str], why: str = "asked for", only: set[str] | None = None) -> dict:
        """A scan, beside everything else. `only`: these mods alone, asked about now whatever is kept."""
        with self._lock:
            if self.work["state"] == "going":
                if only:
                    raise Bad("a scan is going: ask again when it has finished")
                return dict(self.work)
            self.work = {"state": "going", "text": "getting ready", "started": time.time(), "error": ""}
            self._stop.clear()
        rows, _wj = self.rows(model, modlist_key, added)
        if only:
            rows, why = [r for r in rows if r["mod"] in only], "about %d mod(s) by name" % len(only)
        key = secret.read(KEY)
        log.info("scan for updates (%s): %d mod(s), %d with a number at Nexus, %d from a GitHub repository%s", why, len(rows),
                 sum(1 for r in rows if r["host"] == "nexus"), sum(1 for r in rows if r["host"] == "github"),
                 "" if key else "; no Nexus key is kept")

        def run():
            try:
                if key and not only:
                    self._account()
                updates.scan(rows, key, self.net, self.store, progress=lambda t: self.work.update(text=t), stopped=self._stop.is_set,
                             force=bool(only))
                with self._lock:
                    self.work = {"state": "idle", "text": "", "started": 0.0, "error": ""}
            except Exception as e:
                log.error("the scan for updates failed: %s", logbook.why(e))
                with self._lock:
                    self.work = {"state": "idle", "text": "", "started": 0.0, "error": "The scan failed (%s). The log says more." % logbook.why(e)}

        threading.Thread(target=run, name="updates", daemon=True).start()
        return dict(self.work)

    def stop(self) -> dict:
        self._stop.set()
        return dict(self.work)

    def at_launch(self, model, modlist_key: str, added: set[str], wanted: bool) -> None:
        """Once for each start of ModTrap, when the first modlist is read: a scan, if the owner's setting asks for
        one and there is a mod that can be asked about (one from Nexus or from GitHub)."""
        if self.launched:
            return
        self.launched = True
        if not wanted:
            return
        try:
            rows, _wj = self.rows(model, modlist_key, added)
            if any(r["host"] in ("nexus", "github") for r in rows):          # Nexus needs no key (MT44)
                self.start(model, modlist_key, added, "at launch")
        except Exception as e:
            log.warn("the scan for updates at launch could not be started: %s", logbook.why(e))


__all__ = ["Bad", "Updating"]
