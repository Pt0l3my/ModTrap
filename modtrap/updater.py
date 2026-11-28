"""The Updater (MT50): one press takes a mod of the modlist to its newer version, from finding the file to the
check of the result, and shows each stage as it goes.

    find      which file is the newer one (asked of the site at the press), and whether it is already on this PC
    download  fetched by ModTrap where the host gives a file to a program; else the owner presses the site's own
              download button on the page ModTrap opened, and ModTrap takes the file when it is whole
    unpack    read where it lies, into the session's work folder
    check     what the newer version needs (a master it names must be there)
    install   right after the older version in MO2's list, the older one disabled, the plugins keeping their places
    verify    the modlist read again: the newer one enabled, the older one disabled, no master missing

It changes a modlist only through the add job (DESIGN§16.8, MT49), which keeps its record and its Revert. A file is
never downloaded twice: ModTrap's own downloads folder, MO2's and the browser's are looked through first.
"""

from __future__ import annotations

import os
import re
import secrets as _secrets
import threading
import time
from pathlib import Path

from . import downloads, logbook, secret, sources, updates, updating

log = logbook.get("updater")

STAGES = (("find", "Find the newer file"), ("download", "Download it"), ("unpack", "Unpack it"),
          ("check", "Check what it needs"), ("install", "Put it in the older version's place"), ("verify", "Check the result"))
UNPACK_SECONDS = 1800          # the most an unpacking may take
ANSWER_SECONDS = 12 * 3600     # the most a run waits for an installer's questions to be answered (MT83)
SETTLE_SECONDS = 900           # the most ModTrap waits for its own reading and scanning, and for MO2 to be closed
KEEP_RUNS = 40                 # how many runs the Updater tool keeps in view


class Bad(Exception):
    """Something the owner can put right; the text is for them."""


class _Stopped(Exception):
    pass


class _Yours(Exception):
    """The run cannot go on by itself: the rest is the owner's, with the text."""


class Updater:
    def __init__(self, api):
        self.api = api
        self.runs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._installing = threading.Lock()          # one add at a time
        self._starting: set[str] = set()             # mods whose update is being begun right now

    # --- what the page is told ------------------------------------------------------------------------------------
    @staticmethod
    def _public(run: dict) -> dict:
        return {k: v for k, v in run.items() if not k.startswith("_")}

    def state(self) -> dict:
        self._reconcile()
        with self._lock:
            runs = sorted(self.runs.values(), key=lambda r: -r["started"])
        return {"runs": [self._public(r) for r in runs], "going": any(r["state"] in ("going", "yours") and not r["handed"] for r in runs),
                "folder": str(downloads.folder())}

    def _run_for(self, mod: str) -> dict | None:
        return next((r for r in self.runs.values() if r["mod"] == mod and r["state"] in ("going", "yours") and not r["handed"]), None)

    # --- the stages' words ------------------------------------------------------------------------------------------
    @staticmethod
    def _stage(run: dict, key: str) -> dict:
        return next(s for s in run["stages"] if s["key"] == key)

    def _set(self, run: dict, key: str, state: str, note: str | None = None) -> None:
        s = self._stage(run, key)
        s["state"] = state
        if note is not None:
            s["note"] = note
        if state in ("done", "skipped", "failed"):
            for t in s["tasks"]:
                if t["state"] == "going":
                    t["state"] = "done" if state != "failed" else "failed"

    def _task(self, run: dict, key: str, text: str, state: str = "done", note: str = "", slot: str = "") -> dict:
        """Adds a task to a stage, or rewrites the one of the same `slot` (a task whose words change as it goes)."""
        s = self._stage(run, key)
        if slot:
            for t in s["tasks"]:
                if t.get("slot") == slot:
                    t.update(text=text, state=state, note=note)
                    return t
        t = {"text": text, "state": state, "note": note, "slot": slot}
        s["tasks"].append(t)
        return t

    def _check(self, run: dict) -> None:
        if run["_stop"]:
            raise _Stopped()

    # --- the press ----------------------------------------------------------------------------------------------------
    def start(self, mod: str, staged: str = "") -> dict:
        """Starts the update of one mod. The answer comes at once and says whether a page of the site is to be opened
        for the owner's press: {"run", "open"}. Everything else goes on by itself and is told by `state`."""
        api = self.api
        m = api._need()
        if api.changes is None or api.session is None:
            raise Bad("ModTrap updates a mod only when it is started with its switch for changes")
        if api._locked():
            raise Bad(api._locked())
        with self._lock:
            had = self._run_for(mod)
            if had is not None:
                return {"run": had["id"], "open": had["open"] if had["waits_page"] else "", "again": True}
            if mod in self._starting:
                # A second press while the first is still finding the file: one update for a mod (WHY§118).
                return {"run": "", "open": "", "again": True}
            self._starting.add(mod)
        try:
            return self._start(m, mod, staged)
        finally:
            with self._lock:
                self._starting.discard(mod)

    def _start(self, m, mod: str, staged: str) -> dict:
        api = self.api
        key, added = api._updates_for()
        rows, _wj = api.updating.rows(m, key, added)
        row = next((r for r in rows if r["mod"] == mod), None)
        if row is None:
            raise Bad("that is not a mod of this modlist")
        run = {"id": _secrets.token_hex(4), "mod": mod, "started": time.time(), "ended": 0.0, "state": "going", "summary": "", "open": "", "why_page": "",
               "version": "", "new": "", "job": "", "staged": "", "handed": False, "asks": False, "download": "",
               "stages": [{"key": k, "title": t, "state": "waiting", "note": "", "tasks": []} for k, t in STAGES],
               "waits_page": False, "needs_open": False, "_stop": False, "_arrived": threading.Event(), "_file": None}
        net = api.updating.net
        store = api.updating.store
        plan: dict = {"row": row, "path": None, "name": "", "rec": None, "how": None, "v": None, "meta": {}}
        if staged:
            # An archive the owner gave ("Manual update"): the file is here already.
            if staged not in api._staged:
                raise Bad("that archive is no longer there")
            run["staged"] = staged
            self._set(run, "find", "skipped", "You gave the file yourself.")
            self._set(run, "download", "skipped")
        else:
            self._set(run, "find", "going")
            key_text = secret.read(updating.KEY)
            if row["host"] == "nexus" and key_text and api.updating.premium is None:
                api.updating._account()
            if row["host"] == "nexus" and not (key_text and api.updating.premium):
                why = updates.ask_files(row, net, store)
                self._task(run, "find", "Nexus was asked about the mod's files now" if not why else "Nexus could not be asked now (%s): what the last scan kept is used" % why,
                           "done" if not why else "skipped")
            v = updates.verdict(row, store)
            how = updates.how_to_get(row, v, store, bool(key_text), api.updating.premium)
            page = how.get("open") or how.get("page") or updates.page_of(row)
            if v["state"] != "update" and not page:
                raise Bad("no newer file is known for this mod, and no page of it: add a source link first")
            run["version"] = v.get("newest") or ""
            meta = {"host": row["host"], "game": row.get("game") or "", "mod_id": row.get("mod_id") or 0, "file_id": v.get("file_id") or 0,
                    "version": v.get("newest") or "", "label": v.get("file") or "", "size": v.get("size") or 0, "code": v.get("code") or "",
                    "url": how.get("url") or row.get("url") or "", "page": page, "for_mod": mod, "modlist": key}
            plan.update(how=how, v=v, meta=meta)
            if v["state"] == "update":
                self._task(run, "find", "the newer file: %s%s" % (v.get("file") or "the mod's newer file", ", version %s" % v["newest"] if v.get("newest") else "")
                           + (", %s" % _mb(meta["size"]) if meta["size"] else ""))
            else:
                self._task(run, "find", "which file is the newer one is not known for certain: the mod's page is opened for you to choose", "skipped")
            here = self._on_this_pc(m, meta) if v["state"] == "update" else None
            if here is not None:
                plan.update(path=here["path"], name=here["name"], rec=here["rec"])
                run["download"] = here["rec"]["id"]
                self._task(run, "find", "it is on this PC already, in %s: it is not downloaded again" % here["where"])
                self._set(run, "find", "done")
                self._set(run, "download", "skipped", "The file is here already.")
            else:
                self._task(run, "find", "it is not on this PC yet")
                self._set(run, "find", "done")
                if "fetch" not in how:
                    # The site gives the file only to the owner's browser: its page is opened, the press is theirs.
                    run["open"], run["why_page"], run["waits_page"] = page, how.get("why") or "", True
        with self._lock:
            self.runs[run["id"]] = run
            for old in sorted(self.runs.values(), key=lambda r: -r["started"])[KEEP_RUNS:]:
                if old["state"] not in ("going", "yours"):
                    self.runs.pop(old["id"], None)
        if run["waits_page"]:
            self._wait_for_page(run, m, plan)
        log.info("update of “%s” begun%s", mod, ": its page is opened for the owner's press on the site's download button" if run["waits_page"] else
                 ": the file is on this PC already" if plan["path"] is not None else ": from an archive the owner gave" if staged else ": ModTrap fetches the file")
        threading.Thread(target=self._go, args=(run, plan), name="update", daemon=True).start()
        return {"run": run["id"], "open": run["open"] if run["waits_page"] else ""}

    def _wait_for_page(self, run: dict, m, plan: dict) -> None:
        up = self.api.updating
        up._ctx = (m, self.arrived)                  # the watch hands what it finds to the run, where the file lies
        up.fetching.pop(run["mod"], None)
        up._expect(plan["row"], plan["v"])
        self._set(run, "download", "yours", "ModTrap cannot press the site's download button: that press is yours. " + (run["why_page"][:1].upper() + run["why_page"][1:] + "." if run["why_page"] else ""))
        self._task(run, "download", "press the download button on the page that opened (“Start download” at Nexus)" if plan["row"]["host"] == "nexus"
                   else "press download on the page that opened", "yours", slot="press")

    def reopen(self, run_id: str) -> dict:
        """The page for the owner's press, again (a tab closed too early)."""
        run = self.runs.get(run_id)
        if run is None or not run["waits_page"] or run["state"] not in ("going", "yours"):
            raise Bad("that update does not wait for a download")
        return {"open": run["open"]}

    def stop(self, run_id: str) -> dict:
        run = self.runs.get(run_id)
        if run is None:
            raise Bad("that update is not known")
        if run["state"] in ("going", "yours") and not run["handed"]:
            run["_stop"] = True
            run["_arrived"].set()
            self.api.updating.stop_waiting(run["mod"])
        return {}

    def revert(self, run_id: str) -> dict:
        """Takes a finished update out again, through the add's own Revert: the older version enabled as it was, the
        newer one taken out. The downloaded file stays."""
        run = self.runs.get(run_id)
        if run is None or run["state"] != "done" or not run["job"]:
            raise Bad("that update is not one that can be taken out again")
        try:
            got = self.api.changes.revert({"job": run["job"]})
        except Exception as e:
            if e.__class__.__name__ == "Bad":
                raise Bad(str(e)) from None
            raise
        run["state"], run["summary"] = "reverted", "Taken out again: “%s”, the older version, is enabled as it was%s." % (
            run["mod"], "; left in place: " + ", ".join(got["left"]) if got.get("left") else "")
        if run["download"]:
            downloads.note(run["download"], installed_as="")
        log.info("update of “%s” taken out again (%s)", run["mod"], run["job"])
        return {"left": got.get("left") or []}

    def clear(self) -> dict:
        """Takes the runs that have ended off the view. Nothing of the modlist is touched."""
        with self._lock:
            gone = [i for i, r in self.runs.items() if r["state"] not in ("going", "yours") or r["handed"]]
            for i in gone:
                self.runs.pop(i, None)
        return {"cleared": len(gone)}

    # --- a file already on this PC (MT50: nothing is downloaded twice) ----------------------------------------------
    def _on_this_pc(self, m, meta: dict) -> dict | None:
        rec = downloads.find(meta)
        if rec is not None:
            return {"path": downloads.path_of(rec), "name": rec.get("file") or downloads.path_of(rec).name, "rec": rec, "where": "ModTrap's downloads folder"}
        if not (meta.get("size") or (meta.get("mod_id") and meta.get("file_id"))):
            return None
        mo2 = m.instance.downloads_dir
        code = re.compile(r"(?<![0-9A-Za-z])%s(?![0-9A-Za-z])" % re.escape(meta["code"])) if meta.get("code") else None
        number = re.compile(r"(?<!\d)%d(?!\d)" % meta["mod_id"]) if meta.get("mod_id") else None
        for where, folder in (("MO2's downloads folder", mo2), ("your browser's Downloads folder", self.api.updating.downloads_folder())):
            if folder is None:
                continue
            try:
                with os.scandir(folder) as it:
                    entries = [e for e in it if e.is_file() and not e.name.lower().endswith(updating.PARTIAL + (".meta",))]
            except OSError:
                continue
            for e in entries:
                try:
                    size = e.stat().st_size                 # as the folder lists it: these files are whole, and thousands
                except OSError:
                    continue
                mine = False
                if where.startswith("MO2"):
                    if not downloads.ARCHIVE.search(e.name):
                        continue
                    if meta.get("size"):
                        mine = size == meta["size"]         # the size the site gives, to the byte: no file is opened for it
                    elif meta.get("mod_id") and meta.get("file_id"):
                        # No size is known: the record MO2 keeps beside each archive is read (slow in a large folder).
                        dl = sources.download_meta(Path(folder), e.name)
                        mine = dl.get("mod_id") == meta["mod_id"] and dl.get("file_id") == meta["file_id"]
                else:
                    mine = bool(meta.get("size")) and size == meta["size"] or \
                        bool(code and number and not meta.get("size") and code.search(e.name) and number.search(e.name))
                if not mine or size <= 0 or not (downloads.kind(Path(e.path)) or downloads.ARCHIVE.search(e.name)):
                    continue
                path = Path(e.path)
                if where.startswith("MO2"):
                    rec = downloads.refer(path, meta, "found in MO2's downloads folder, used from there")
                    return {"path": path, "name": e.name, "rec": rec, "where": where}
                rec = self._keep(path, e.name, meta, "downloaded in your browser before")
                return {"path": downloads.path_of(rec), "name": rec.get("file") or e.name, "rec": rec, "where": where}
        return None

    def _keep(self, path: Path, name: str, meta: dict, how: str) -> dict:
        """A download from the browser's folder is taken into ModTrap's own: moved there, or copied where the owner
        set so. It is the file the site gives for the mod, known to the byte."""
        move = bool(self.api.settings().get("downloads_move", True))
        return downloads.take(path, name, meta, how + (", moved into ModTrap's downloads folder" if move else ", copied into ModTrap's downloads folder"), move)

    # --- the watch's hand-over ----------------------------------------------------------------------------------------
    def arrived(self, path, as_name: str, mod: str, version: str, meta: dict) -> dict:
        """What the watch for a download calls when the file is whole (WHY§112): the run takes it from here."""
        run = self._run_for(mod)
        if run is None:
            # No run waits for it (a watch begun another way): it goes to Install mods as before.
            return self.api.stage_where_it_lies(path, as_name, mod, version, meta)
        run["_file"] = (Path(path), as_name)
        run["_arrived"].set()
        return {"id": "", "name": mod}

    # --- the run ----------------------------------------------------------------------------------------------------
    def _go(self, run: dict, plan: dict) -> None:
        api = self.api
        mod = run["mod"]
        at = "download"
        try:
            row, meta = plan["row"], plan["meta"]
            # --- download ---
            if not run["staged"] and plan["path"] is None:
                if run["waits_page"]:
                    self._await_download(run, plan)
                else:
                    self._fetch(run, plan)
            self._check(run)
            # --- unpack ---
            at = "unpack"
            self._set(run, "unpack", "going")
            if run["staged"]:
                rec = api._staged[run["staged"]]
            else:
                record = {"mod_id": meta["mod_id"], "file_id": meta["file_id"], "version": meta["version"]} if meta.get("mod_id") else \
                         {"version": meta.get("version") or "", "url": meta.get("url") or ""}
                # The same file unpacked before for this mod (an update taken out again) is used as it lies.
                before = next((r for r in api._staged.values() if r.get("updates") == mod and r["state"] == "ready" and r.get("root") and Path(r["root"]).is_dir()
                               and meta.get("file_id") and (r.get("meta") or {}).get("file_id") == meta["file_id"]), None)
                if before is not None:
                    rec = before
                    self._task(run, "unpack", "it was unpacked before, and is used as it lies")
                else:
                    pub = api.stage_where_it_lies(plan["path"], plan["name"], mod, meta.get("version") or "", record)
                    rec = api._staged[pub["id"]]
                run["staged"] = rec["id"]
            self._task(run, "unpack", "unpacking “%s”" % rec["archive"], "going", slot="unpack")
            end = time.time() + UNPACK_SECONDS
            while rec["state"] in ("copying", "unpacking"):
                self._check(run)
                if time.time() > end:
                    raise Bad("unpacking took longer than %d minutes" % (UNPACK_SECONDS // 60))
                time.sleep(0.3)
            if rec["state"] == "failed":
                raise Bad(rec.get("note") or "the archive could not be unpacked")
            self._task(run, "unpack", "unpacked “%s”: %d file(s)" % (rec["archive"], rec.get("files") or 0), slot="unpack")
            if rec["state"] == "installer":
                if not rec.get("installer"):
                    self._set(run, "unpack", "done")
                    raise _Yours("its installer is one ModTrap cannot read: the archive waits on Install mods, which says what can be done")
                # An installer asks which parts to install (MT83): its questions are answered here, on the Updater
                # tool, and the update goes on with the answers. The run waits; nothing else of ModTrap does.
                self._task(run, "unpack", "its installer asks which parts to install: answer its questions below", "yours", slot="answers")
                self._set(run, "unpack", "yours", "Its installer asks which parts to install. Answer its questions below: the update goes on by itself.")
                run["asks"], run["state"], run["summary"] = True, "yours", "Waits for you: its installer asks which parts to install. Answer its questions below."
                end = time.time() + ANSWER_SECONDS
                try:
                    while rec["state"] == "installer":
                        self._check(run)
                        if api._staged.get(rec["id"]) is not rec:
                            raise Bad("the archive was taken off ModTrap's list before its installer was answered")
                        if time.time() > end:
                            raise Bad("its installer's questions were not answered in %d hours" % (ANSWER_SECONDS // 3600))
                        time.sleep(0.3)
                finally:
                    run["asks"] = False
                run["state"], run["summary"] = "going", ""
                self._stage(run, "unpack")["note"] = ""
                for t in self._stage(run, "unpack")["tasks"]:
                    if t.get("slot") == "answers":
                        t.update(text="its installer's questions are answered: the mod is built from the answers (%d file(s))" % (rec.get("files") or 0), state="done")
            if rec["state"] == "failed":
                raise Bad(rec.get("note") or "the mod could not be built from the installer's answers")
            self._set(run, "unpack", "done")
            run["new"] = rec["name"]
            if rec["state"] == "installed":             # answered and installed on Install mods meanwhile: nothing is left to do but look
                self._elsewhere(run, rec)
                return
            # --- check ---
            at = "check"
            self._set(run, "check", "going")
            body = {"mods": [], "staged": [rec["id"]]}
            got = self._analysed(run, body)
            x = next((y for y in got.get("mods", []) if y["name"] == rec["name"]), None)
            if x is None or not x.get("updates"):
                raise Bad("the mod it is a newer version of is no longer in the modlist")
            needs = next((s for s in got.get("steps", []) if s["key"] == "needs"), None)
            if needs is not None and needs["state"] != "done":
                for i in needs["items"][:8]:
                    self._task(run, "check", i["text"], "yours")
                raise _Yours("something the newer version needs is not there yet: get it, then press “Install mod” on Install mods")
            self._task(run, "check", "every master it names is in the modlist and active")
            d = x.get("differs")
            if d:
                self._task(run, "check", "against the older version: %d file(s) new, %d gone, %d of another size, %d the same" % (d["added"], d["gone"], d["changed"], d["same"]))
            told = next((s for s in got.get("steps", []) if s["key"] == "differs"), None)
            if told is not None and told.get("note", "").startswith("Tools of this modlist"):
                self._task(run, "check", told["note"], "skipped", note="for you to know")
            self._set(run, "check", "done")
            # --- install ---
            at = "install"
            self._set(run, "install", "going")
            with self._installing:
                done = self._install(run, body)
            for y in done["done"]["mods"]:
                self._task(run, "install", "“%s”: enabled, at priority %s" % (y["name"], y["priority"]))
                if y.get("replaces"):
                    self._task(run, "install", "“%s”, the older version: disabled, not deleted" % y["replaces"])
            for p in x["plugins"]:
                if p.get("keeps") or p.get("active"):
                    self._task(run, "install", "%s: keeps its place in the load order" % p["name"])
            for p in done["done"]["plugins"]:
                self._task(run, "install", "%s: active at position %s" % (p["name"], p["position"]))
            run["job"] = done["job"]
            # The owner's setting (MT82): the older version is uninstalled too, by the uninstall of MT66.
            removed = done.get("removed") or {}
            for n in removed.get("mods", []):
                self._task(run, "install", "“%s”, the older version: taken out of the modlist too (your setting). Its folder is kept by ModTrap, and “Uninstall” puts it back" % n)
            for k in removed.get("kept", []):
                self._task(run, "install", "“%s”, the older version, stays in the modlist, disabled: %s" % (k["mod"], k["why"]))
            run["removed"] = bool(removed.get("mods"))
            self._set(run, "install", "done")
            if run["download"]:
                downloads.note(run["download"], installed_as=rec["name"])
            # --- verify ---
            at = "verify"
            self._set(run, "verify", "going")
            self._settled(run, "verify")
            m = api.model
            new, old = (m.instance.mod(rec["name"]), m.instance.mod(mod)) if m is not None else (None, None)
            if new is None or not new.enabled:
                raise Bad("after the add, “%s” is not enabled in the modlist as it was read again" % rec["name"])
            self._task(run, "verify", "“%s” is enabled%s" % (rec["name"], "; “%s” is disabled" % mod if old is not None and not old.enabled else ""))
            if old is not None and old.enabled:
                self._task(run, "verify", "“%s”, the older version, is still enabled: disable it in MO2" % mod, "yours")
            mine = {sources.fold(p) for p in new.plugins}
            issues = [i for i in m.issues if sources.fold(i.plugin) in mine]
            if issues:
                for i in issues[:8]:
                    self._task(run, "verify", "%s needs %s, which is %s" % (i.plugin, i.master, "not active" if i.what == "inactive" else "missing"), "failed")
                raise Bad("a master of the newer version is missing or not active: see Health; “Uninstall” puts the older version back")
            self._task(run, "verify", "no master is missing or inactive")
            self._set(run, "verify", "done")
            run["state"] = "done"
            run["summary"] = ("“%s” is updated%s: “%s” is enabled in its place, and the older version is taken out of the modlist (kept by ModTrap; “Uninstall” puts it back)."
                              if run.get("removed") else
                              "“%s” is updated%s: “%s” is enabled right after it, and the older version is disabled, not deleted.") % (
                mod, " to %s" % run["version"] if run["version"] else "", rec["name"])
            log.info("update of “%s” done: “%s” is in place (%s)", mod, rec["name"], run["job"])
        except _Stopped:
            self._set(run, at, "failed", "Stopped.")
            run["state"], run["summary"] = "stopped", "Stopped. Nothing of the modlist was changed." if not run["job"] else "Stopped after the add; “Uninstall” puts the older version back."
            log.info("update of “%s” stopped by the owner", mod)
        except _Yours as e:
            # Handed to Install mods, where the archive now waits with the steps of an update (MT49).
            self._set(run, at, "yours", str(e)[:1].upper() + str(e)[1:] + ".")
            run["state"], run["handed"], run["summary"] = "yours", True, "Waits for you: %s." % e
            log.info("update of “%s” waits for the owner: %s", mod, e)
        except Exception as e:
            why = str(e) if e.__class__.__name__ in ("Bad", "Refused") else logbook.why(e)
            self._set(run, at, "failed", why)
            run["state"], run["summary"] = "failed", "Stopped at “%s”: %s" % (dict(STAGES)[at], why)
            (log.warn if e.__class__.__name__ in ("Bad", "Refused") else log.error)("update of “%s” stopped at “%s”: %s", mod, dict(STAGES)[at], why)
        finally:
            run["ended"] = time.time()
            run["waits_page"] = False
            for s in run["stages"]:
                if s["state"] == "going":
                    s["state"] = "failed"

    def _fetch(self, run: dict, plan: dict) -> None:
        """ModTrap fetches the file itself: Nexus for the key of a paying account, GitHub for a release's file."""
        api = self.api
        row, how, meta = plan["row"], plan["how"], plan["meta"]
        self._set(run, "download", "going")
        t = self._task(run, "download", "asking for the file", "going", slot="fetch")

        def progress(done: int, total: int) -> None:
            t["text"] = "fetching %s: %s%s" % (how.get("name") or "the file", _mb(done), " of %s, %d%%" % (_mb(total), 100 * done // total) if total else "")

        got = updates.fetch(how, row, secret.read(updating.KEY), api.updating.net, api._incoming() / "fetching", progress, lambda: run["_stop"])
        if "open" in got:
            # The host would not give it to a program after all: the page, and the owner's press.
            api.updating.premium = False
            run["open"], run["why_page"], run["waits_page"] = got["open"], got["why"], True
            t.update(text="Nexus did not give the file to ModTrap", state="skipped")
            self._wait_for_page(run, api.model, plan)
            run["needs_open"] = True
            self._await_download(run, plan)
            return
        rec = downloads.take(Path(got["path"]), got["name"], meta, "fetched by ModTrap from %s" % ("Nexus, with your key" if how["fetch"] == "nexus" else "GitHub"), True)
        plan.update(path=downloads.path_of(rec), name=rec.get("file") or got["name"], rec=rec)
        run["download"] = rec["id"]
        t.update(text="fetched “%s”, %s, into ModTrap's downloads folder" % (rec.get("file") or got["name"], _mb(rec.get("size") or 0)), state="done")
        self._set(run, "download", "done")

    def _await_download(self, run: dict, plan: dict) -> None:
        """The owner's press on the site, then the file as it comes in: told from what the watch sees."""
        api = self.api
        mod, meta = run["mod"], plan["meta"]
        while not run["_arrived"].wait(0.5):
            w = api.updating.waiting.get(mod)
            if w is None:
                if run["_arrived"].wait(3.0):               # the watch has it and is handing it over
                    break
                failed = api.updating.fetching.get(mod, {})
                raise Bad(failed.get("error") or "ModTrap has stopped waiting for the download")
            saw = w.get("saw") or ""
            if saw:
                self._stage(run, "download")["state"] = "going"
                self._task(run, "download", "the download button was pressed", slot="press")
                self._task(run, "download", saw, "going", slot="coming")
        self._check(run)
        path, as_name = run["_file"]
        run["waits_page"] = False
        self._task(run, "download", "the download button was pressed", slot="press")
        in_mo2 = api.model is not None and api.model.instance.downloads_dir is not None and path.parent == api.model.instance.downloads_dir
        if in_mo2:
            rec = downloads.refer(path, meta, "downloaded through MO2, used from MO2's downloads folder")
        else:
            rec = self._keep(path, as_name, meta, "downloaded in your browser")
        plan.update(path=downloads.path_of(rec), name=rec.get("file") or as_name, rec=rec)
        run["download"] = rec["id"]
        self._task(run, "download", "the download is whole: “%s”, %s, %s" % (rec.get("file") or as_name, _mb(rec.get("size") or 0),
                                                                              "used from MO2's downloads folder" if in_mo2 else "now in ModTrap's downloads folder"), slot="coming")
        self._set(run, "download", "done", "")

    def _elsewhere(self, run: dict, rec: dict) -> None:
        """An update that was finished on Install mods (MT83): the run takes that in, and ends as done. The install
        is found among the session's adds, so that "Uninstall" here takes it out again like any other update."""
        api = self.api
        job = None
        if api.changes is not None:
            job = next((j for j in api.changes.jobs() if j["state"] == "added" and rec["name"] in j["mods"]), None)
        for key in ("unpack", "check", "install"):
            st = self._stage(run, key)
            if st["state"] != "done":
                st["state"], st["note"] = "done", ""
                for t in st["tasks"]:
                    if t["state"] in ("yours", "going"):
                        t["state"] = "done"
        self._task(run, "install", "installed from Install mods: “%s” is in the modlist" % rec["name"])
        run["new"], run["job"] = rec["name"], job["job"] if job else ""
        m = api.model
        new = m.instance.mod(rec["name"]) if m is not None else None
        old = m.instance.mod(run["mod"]) if m is not None else None
        self._task(run, "verify", "“%s” is %s%s" % (rec["name"], "enabled" if new is not None and new.enabled else "in the modlist, not enabled" if new is not None else "not in the modlist as it was last read",
                                                   "; “%s”, the older version, is %s" % (run["mod"], "still enabled" if old is not None and old.enabled else "disabled" if old is not None else "taken out of the modlist")),
                   "done" if new is not None and new.enabled else "yours")
        self._stage(run, "verify")["state"] = "done" if new is not None and new.enabled else "yours"
        if run["download"]:
            downloads.note(run["download"], installed_as=rec["name"])
        run["state"], run["handed"], run["ended"] = "done", False, time.time()
        run["summary"] = "“%s” is updated%s: “%s” was installed from Install mods." % (run["mod"], " to %s" % run["version"] if run["version"] else "", rec["name"])
        log.info("update of “%s” done: “%s” was installed from Install mods (%s)", run["mod"], rec["name"], run["job"] or "its install was not found among this session's")

    def _reconcile(self) -> None:
        """Runs handed to Install mods (something the newer version needs, an installer ModTrap cannot read) are
        looked at again each time the page asks: one whose archive has been installed there is done (MT83)."""
        for run in list(self.runs.values()):
            if run["state"] != "yours" or not run["handed"] or not run["staged"]:
                continue
            rec = self.api._staged.get(run["staged"])
            if rec is not None and rec["state"] == "installed":
                try:
                    self._elsewhere(run, rec)
                except Exception as e:
                    log.warn("an update finished on Install mods could not be taken in: %s", logbook.why(e))

    def _analysed(self, run: dict, body: dict) -> dict:
        end = time.time() + SETTLE_SECONDS
        while True:
            self._check(run)
            got = self.api.add(body)
            if got.get("failed"):
                raise Bad(got["failed"])
            if not got.get("looking") and not got.get("unpacking"):
                return got
            if time.time() > end:
                raise Bad("reading the newer version took too long")
            time.sleep(0.3)

    def _settled(self, run: dict, key: str) -> None:
        """Waits for ModTrap's own reading and scanning to end, saying what it waits for."""
        api = self.api
        end = time.time() + SETTLE_SECONDS
        while True:
            self._check(run)
            why = api.unsettled() or ("something else is going" if api._busy() else "")
            if not why:
                for t in self._stage(run, key)["tasks"]:
                    if t.get("slot") == "settle":
                        t.update(text="ModTrap has finished its own reading", state="done")
                return
            self._task(run, key, "waiting: " + why, "going", slot="settle")
            if time.time() > end:
                raise Bad("ModTrap was still at work after %d minutes (%s)" % (SETTLE_SECONDS // 60, why))
            time.sleep(0.5)

    def _install(self, run: dict, body: dict) -> dict:
        """The add itself, through the add job. Where MO2 is open, the run waits for the owner to close it."""
        api = self.api
        end = time.time() + SETTLE_SECONDS
        while True:
            self._settled(run, "install")
            closed = api.changes.closed()
            if closed:
                break
            self._stage(run, "install")["state"] = "yours"
            self._task(run, "install", "close MO2: ModTrap changes MO2's lists only while MO2 is closed" if closed is False else
                       "ModTrap cannot tell whether MO2 is closed", "yours", slot="mo2")
            if time.time() > end:
                raise Bad("MO2 was still open after %d minutes" % (SETTLE_SECONDS // 60))
            time.sleep(1.0)
        self._stage(run, "install")["state"] = "going"
        for t in self._stage(run, "install")["tasks"]:
            if t.get("slot") == "mo2":
                t.update(text="MO2 is closed", state="done")
        t = self._task(run, "install", "copying the newer version into MO2's mods folder, and changing MO2's lists", "going", slot="add")
        try:
            done = api.changes.run(body)
        except Exception as e:
            if e.__class__.__name__ == "Bad":
                raise Bad(str(e)) from None
            raise
        t.update(text="the newer version is copied in, and MO2's lists are changed", state="done")
        return done


def _mb(n: int) -> str:
    return "%.1f MB" % (n / (1024 * 1024))


__all__ = ["Updater", "Bad", "STAGES"]
