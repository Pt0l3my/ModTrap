"""The update check as the page sees it (MT37, WHY§101): the rows, the Wabbajack file's place, the key, the scan.

`sources.py` reads where each mod came from, `updates.py` asks the two services; this keeps the two together for
one open modlist: what is remembered between launches, the scan as a piece of work that goes on beside everything
else, and the account given to the page. It changes nothing in the modlist.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from . import logbook, paths, secret, sources, updates

log = logbook.get("updates")

KEY = "nexus"
PLACES = "update-lists.json"         # which Wabbajack file belongs to which modlist
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

    def account(self, model, modlist_key: str, added: set[str]) -> dict:
        """Everything the Updates tab shows."""
        rows, wj = self.rows(model, modlist_key, added)
        out_rows = []
        counts = {"update": 0, "maybe": 0, "current": 0, "not asked": 0, "none": 0, "gone": 0}
        origins = {"list": 0, "added": 0, "modtrap": 0, "": 0}
        hosts: dict[str, int] = {}
        for r in rows[:ROWS_MAX]:
            v = updates.verdict(r, self.store)
            counts[v["state"]] = counts.get(v["state"], 0) + 1
            origins[r["origin"]] = origins.get(r["origin"], 0) + 1
            hosts[r["host"] or "not known"] = hosts.get(r["host"] or "not known", 0) + 1
            out_rows.append({"mod": r["mod"], "enabled": r["enabled"], "host": r["host"], "id": r["mod_id"] or r["repo"], "version": r["version"],
                             "archive": r["archive"], "origin": r["origin"], "by": r["by"], "given": r.get("given", ""), "state": v["state"], "text": v["text"],
                             "newest": v["newest"], "file": v["file"], "when": v["when"], "asked": v["asked"], "page": updates.page_of(r),
                             "get": updates.get_of(r, v), "priority": r.get("priority", 0), "comments": r.get("comments", ""), "notes": r.get("notes", "")})
        place = self._place(modlist_key)
        given = sources.given_load()
        return {"rows": out_rows, "counts": counts, "origins": origins, "hosts": hosts, "key": secret.kept(KEY),
                "given": {"links": len(given["links"].get(modlist_key, {})), "archives": len(given["archives"]), "mods": len(given["mods"].get(modlist_key, {}))},
                "list": {"named": bool(place), "file": Path(place["path"]).name if place.get("path") else place.get("file", ""), "name": wj["name"] if wj else "",
                         "version": wj["version"] if wj else "", "counts": wj["counts"] if wj else None,
                         "reading": self.reading["state"] == "going", "text": self.reading["text"], "error": self.reading["error"]},
                "scan": dict(self.work), "last": self.store.get("last") or None}

    # --- the key -----------------------------------------------------------------------------------------------------
    def set_key(self, text: str | None) -> dict:
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
        one and there is something that can be asked (a key for Nexus, or a mod from GitHub)."""
        if self.launched:
            return
        self.launched = True
        if not wanted:
            return
        try:
            rows, _wj = self.rows(model, modlist_key, added)
            if secret.kept(KEY) or any(r["host"] == "github" for r in rows):
                self.start(model, modlist_key, added, "at launch")
        except Exception as e:
            log.warn("the scan for updates at launch could not be started: %s", logbook.why(e))


__all__ = ["Bad", "Updating"]
