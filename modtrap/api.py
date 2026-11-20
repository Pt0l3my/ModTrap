"""ModTrap's endpoints (DESIGN§4). Version 0.1 reads only: the instance, its mods, its plugins and what depends on
what. Nothing here writes to an instance; the one thing saved is the chosen folder, in ModTrap's own settings."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import threading
from pathlib import Path
from typing import Callable

from . import NAME, VERSION, dryrun, instance, locate, logbook, model, paths, plugin, sessions, steps
from .server import Bad

log = logbook.get("app")


class HeaderCache:
    """Plugin headers by path, size and time: a rescan re-reads only the plugins that changed."""

    def __init__(self) -> None:
        self._seen: dict[str, tuple[int, int, object]] = {}
        self.read_count = 0
        self.touched: set[str] = set()

    def load(self, path: Path) -> None:
        """Headers kept from an earlier run of ModTrap: a start then re-reads only the plugins that changed."""
        try:
            with open(path, "rb") as f:
                data = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
            for key, (size, mtime, ok, flags, author, description, masters) in data.items():
                got: object = (plugin.Header(flags, author, description, tuple(masters)) if ok
                               else plugin.Unreadable(str(description)))
                self._seen.setdefault(key, (int(size), int(mtime), got))
        except (OSError, ValueError, TypeError):
            return

    def save(self, path: Path) -> None:
        out = {}
        for key in self.touched:
            size, mtime, got = self._seen[key]
            if isinstance(got, plugin.Header):
                out[key] = [size, mtime, True, got.flags, got.author, got.description, list(got.masters)]
            else:
                out[key] = [size, mtime, False, 0, "", str(got), []]
        paths.write_atomic(path, json.dumps(out, ensure_ascii=False).encode("utf-8"))

    def read(self, path: Path) -> plugin.Header:
        try:
            st = path.stat()
        except OSError as e:
            raise plugin.Unreadable("the file could not be opened (%s)" % type(e).__name__) from None
        key = str(path)
        self.touched.add(key)
        hit = self._seen.get(key)
        if hit and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
            got = hit[2]
        else:
            self.read_count += 1
            try:
                got = plugin.read(path)
            except plugin.Unreadable as e:
                got = e
            self._seen[key] = (st.st_size, st.st_mtime_ns, got)
        if isinstance(got, plugin.Unreadable):
            raise got
        return got  # type: ignore[return-value]


class Api:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache = HeaderCache()
        self.status = "none"            # none, reading, ready, error
        self.message = ""
        self.folder = ""
        self.profile = ""
        self.model: model.Model | None = None
        self._run = 0
        self._lists: dict[str, tuple[object, dict]] = {}
        self._deep: dict[tuple, dict | None] = {}     # steps.look_deeper by (reading, mods); None while going
        self.job: dryrun.Job | None = None
        self.launcher = dryrun.launch          # replaced in tests
        self.running = dryrun.image_running
        self.poll = 1.0
        self.store = sessions.Store()
        self.session: sessions.Session | None = None
        self.log_epoch = 0                     # goes up when the log is replaced: the page then reads it afresh
        self.on_quit: Callable[[], None] | None = None

    # --- sessions (MT20, WHY§33) -----------------------------------------------------------------------------------

    def _log_file(self, s: sessions.Session) -> Path:
        return self.store.dir(s.id) / "log.json"

    def save_log(self) -> None:
        """The session's log, written to its folder (the lines are already masked)."""
        s = self.session
        if s is None:
            return
        try:
            paths.write_atomic(self._log_file(s), json.dumps(logbook.dump(), ensure_ascii=False).encode("utf-8"))
        except OSError as e:
            log.warn("the session's log could not be saved: %s", logbook.why(e))

    def _enter(self, s: sessions.Session) -> None:
        """Makes `s` the session in use: the last one's log is saved, this one's log and last job come back."""
        prev = self.session
        if prev is not None and prev.id == s.id:
            self.session = s
            return
        self.save_log()
        lines: list = []
        try:
            with open(self._log_file(s), "rb") as f:
                lines = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
        except (OSError, ValueError):
            pass
        logbook.load(lines if isinstance(lines, list) else [])
        self.log_epoch += 1
        self.session = s
        self.job = None
        if s.last_job:
            d = self.store.dir(s.id) / "jobs" / s.last_job
            if d.is_dir():
                self.job = dryrun.PastJob(d)
        settings = paths.load_settings()
        settings["session"] = s.id
        try:
            paths.save_settings(settings)
        except OSError:
            pass

    def restore(self) -> bool:
        """At start: the session ModTrap was closed in, with its modlist read again. False when there is none."""
        sid = paths.load_settings().get("session")
        if not isinstance(sid, str) or not sid:
            return False
        try:
            s = self.store.get(sid)
        except sessions.Refused:
            return False
        self.open(s.folder, s.profile or None, session=s)
        return True

    def _session_or_bad(self, sid: object) -> sessions.Session:
        if sid is None and self.session is not None:
            return self.session
        if not isinstance(sid, str):
            raise Bad("no session was named")
        try:
            return self.store.get(sid)
        except sessions.Refused as e:
            raise Bad(str(e)) from None

    def session_switch(self, body: dict) -> dict:
        s = self._session_or_bad(body.get("id"))
        if self._busy():
            raise Bad("a dry run is going; switch sessions when it has ended")
        cur = self.session
        if cur is not None and cur.key == s.key and self.status == "ready" and (s.profile or self.profile) == self.profile:
            self._enter(s)                      # the same modlist is already read
            log.info("switched to session '%s'", s.name)
        else:
            self.open(s.folder, s.profile or None, session=s)
        return {"status": self.status}

    def session_new(self) -> dict:
        """Another session on the modlist that is open. It waits until the session holding the modlist is finished."""
        cur = self.session
        if cur is None:
            raise Bad("open a modlist first")
        if self._busy():
            raise Bad("a dry run is going; start a new session when it has ended")
        try:
            s = self.store.create(cur.folder, self.profile)
        except sessions.Refused as e:
            raise Bad(str(e)) from None
        self._enter(s)
        log.info("new session '%s' on <modlist>%s", s.name,
                 ": it waits until the session holding this modlist is finished" if s.status == sessions.WAITING else "")
        return {"id": s.id, "status": s.status}

    def session_rename(self, body: dict) -> dict:
        s = self._session_or_bad(body.get("id"))
        name = body.get("name")
        if not isinstance(name, str):
            raise Bad("a session needs a name", "name")
        try:
            s = self.store.rename(s.id, name)
        except sessions.Refused as e:
            raise Bad(str(e), "name") from None
        if self.session is not None and self.session.id == s.id:
            self.session = s
        return {"id": s.id, "name": s.name}

    def session_finish(self, body: dict) -> dict:
        """Finishing a session frees its modlist for the session that waits for it. First the check that it is
        safe: nothing of this session may still be going. (When ModTrap can demaster, every step of the session's
        jobs must also be done and the modlist's health check clean: DESIGN§14.)"""
        s = self._session_or_bad(body.get("id"))
        mine = self.session is not None and self.session.id == s.id
        if mine and self._busy():
            raise Bad("this session's dry run is still going: let it end, or stop it, before finishing the session")
        try:
            done, nxt = self.store.finish(s.id)
        except sessions.Refused as e:
            raise Bad(str(e)) from None
        log.info("session '%s' is finished: nothing of it was still going", done.name)
        if nxt is not None:
            log.info("session '%s' now holds the modlist and is unlocked", nxt.name)
        if mine:
            self.session = done
            if nxt is not None:
                self._enter(nxt)
        elif self.session is not None and nxt is not None and self.session.id == nxt.id:
            self.session = nxt
        self.save_log()
        return {"finished": done.id, "unlocked": nxt.id if nxt else None}

    def session_ui(self, body: dict) -> dict:
        ui = body.get("ui")
        if self.session is None or not isinstance(ui, dict):
            raise Bad("there is no session to remember that for")
        try:
            self.store.set_ui(self.session.id, ui)
        except sessions.Refused as e:
            raise Bad(str(e)) from None
        self.session.ui = ui
        self.save_log()                 # kept up to date as the owner works, in case the window is simply closed
        return {"saved": True}

    def quit(self, body: dict) -> tuple[dict, Callable[[], None] | None]:
        if self._busy() and body.get("force") is not True:
            raise Bad("a dry run is going. Quitting now leaves xEdit open for you to close (it changes nothing), and "
                      "the dry run's outcome is not kept.")
        if self._busy() and self.job is not None:
            self.job.stop()
        log.info("ModTrap is closing; the session is saved")
        self.save_log()
        return {"quit": True}, self.on_quit

    def _locked(self) -> str:
        """Why the session in use may not start a job, or "" when it may."""
        s = self.session
        if s is None:
            return ""
        if s.status == sessions.FINISHED:
            return "this session is finished: it can be looked at, but work goes on in a new session"
        if s.status == sessions.WAITING:
            holder = self.store.holder(s.folder)
            return ("this session is waiting: session “%s” still holds this modlist. Finish that one first; two "
                    "sessions working on one modlist would trip over each other" % (holder.name if holder else "another"))
        return ""

    # --- reading an instance, off the request thread ---------------------------------------------------------------

    def open(self, folder: str, profile: str | None = None, wait: bool = False,
             session: sessions.Session | None = None) -> None:
        """Reads the modlist in `folder`. With `session`, into that session; otherwise into the session that holds
        this modlist, or a new one (MT20)."""
        folder = folder.strip().strip('"')
        if not folder:
            raise Bad("give the modlist's folder", "folder")
        if self._busy():
            raise Bad("a dry run is going; open another modlist when it has ended")
        with self._lock:
            self._run += 1
            run = self._run
            self.status, self.message, self.folder, self.profile = "reading", "", folder, profile or ""
        t = threading.Thread(target=self._read, args=(run, folder, profile, session), name="read-instance", daemon=True)
        t.start()
        if wait:
            t.join()

    def _cache_file(self, folder: str) -> Path:
        key = hashlib.sha256(sessions.modlist_key(folder).encode("utf-8")).hexdigest()[:20]
        return paths.home() / "cache" / ("headers-%s.json" % key)

    def _read(self, run: int, folder: str, profile: str | None, session: sessions.Session | None = None) -> None:
        logbook.set_masks({"<modlist>": folder, "<modtrap>": str(paths.home())})
        log.info("reading the modlist in <modlist>")
        try:
            inst = instance.load(Path(folder), profile)
            logbook.set_masks({"<modlist>": folder, "<game>": str(inst.game_dir) if inst.game_dir else None,
                               "<mods>": str(inst.mods_dir), "<modtrap>": str(paths.home())})
            self._cache.touched = set()
            self._cache.load(self._cache_file(folder))
            before = self._cache.read_count
            m = model.build(inst, read=self._cache.read)
        except instance.Unusable as e:
            log.warn("the folder cannot be read: %s", str(e))
            with self._lock:
                if run == self._run:
                    self.status, self.message, self.model = "error", logbook.mask(str(e)), None
            return
        except Exception as e:      # never leave the page waiting on "reading"
            log.error("reading the modlist failed: %s", logbook.why(e))
            with self._lock:
                if run == self._run:
                    self.status, self.message, self.model = "error", "reading failed: " + logbook.why(e), None
            return
        with self._lock:
            if run != self._run:
                return
        try:
            s = session or self.store.open_for(folder, inst.profile)
            new = self.session is None or self.session.id != s.id
            self._enter(s)
            if s.folder != folder or s.profile != inst.profile:
                s.folder, s.profile = folder, inst.profile
                self.store.save(s)
            if new:
                log.info("session '%s' (%s)", s.name, {"active": "it holds this modlist", "waiting": "waiting, locked",
                                                       "finished": "finished"}[s.status])
        except (sessions.Refused, OSError) as e:
            log.error("the session could not be opened: %s", str(e) if isinstance(e, sessions.Refused) else logbook.why(e))
            with self._lock:
                if run == self._run:
                    self.status, self.message, self.model = "error", "the session could not be opened", None
            return
        try:
            self._cache.save(self._cache_file(folder))
        except OSError:
            pass
        real = [x for x in inst.mods if x.kind == "mod"]
        log.info("profile '%s': %d mods (%d enabled), %d plugins, %d header(s) read, %d problem(s)",
                 inst.profile, len(real), sum(x.enabled for x in real), len(m.order),
                 self._cache.read_count - before, len(m.issues))
        for note in inst.notes:
            log.warn("%s", note)
        settings = paths.load_settings()
        recent = [r for r in settings.get("recent", []) if isinstance(r, str) and r != folder]
        settings.update({"folder": folder, "profile": inst.profile, "recent": [folder, *recent][:8]})
        try:
            paths.save_settings(settings)
        except OSError as e:
            log.warn("the chosen folder could not be remembered: %s", logbook.why(e))
        with self._lock:
            if run != self._run:
                return
            self.status, self.message, self.model, self.profile = "ready", "", m, inst.profile

    def locate(self, body: dict) -> dict:
        """A folder dropped on the page (WHY§30): its name and its ModOrganizer.ini. Finds it on disk and opens it."""
        name, data = body.get("name"), body.get("ini")
        if name is not None and (not isinstance(name, str) or not name or len(name) > 255 or "/" in name
                                 or "\\" in name):
            raise Bad("the dropped folder's name is not usable")
        if not isinstance(data, str):
            raise Bad("the dropped folder's ModOrganizer.ini did not arrive")
        try:
            ini = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError):
            raise Bad("the dropped folder's ModOrganizer.ini did not arrive whole") from None
        if not ini or len(ini) > locate.INI_CAP:
            raise Bad("that ModOrganizer.ini is empty or larger than ModTrap reads")
        settings = paths.load_settings()
        recents = [r for r in [settings.get("folder"), *settings.get("recent", [])] if isinstance(r, str) and r]
        folder, how = locate.find(name, ini, recents)
        if folder is None:
            log.warn("a dropped modlist folder was not found on this PC's drives")
            raise Bad("ModTrap could not find that folder on this PC by itself (a browser never tells a page where "
                      "a dropped folder is). Paste the folder's path into the box instead: in Explorer, click the "
                      "address bar and copy it.")
        log.info("the dropped folder was found through %s", how)
        self.open(str(folder))
        return {"status": "reading", "how": how}

    # --- the dry run (DESIGN§6.1, DESIGN§6.2) ------------------------------------------------------------------------

    def _mods(self, body: dict) -> list[str]:
        mods = body.get("mods")
        if not isinstance(mods, list) or not mods or len(mods) > 50 or not all(isinstance(x, str) and x for x in mods):
            raise Bad("tick at least one mod")
        return mods

    def _busy(self) -> bool:
        return self.job is not None and self.job.state not in ("done", "failed", "stopped")

    def dry_plan(self, body: dict) -> dict:
        if self._locked():
            raise Bad(self._locked())
        try:
            return dryrun.plan(self._need(), self._mods(body)).public()
        except dryrun.Refused as e:
            raise Bad(str(e)) from None

    def dry_start(self, body: dict) -> dict:
        m = self._need()
        with self._lock:
            if self._busy():
                raise Bad("a dry run is already going")
            if self.status != "ready":
                raise Bad("the modlist is being read; try again in a moment")
            if self._locked():
                raise Bad(self._locked())
            s = self.session
            try:
                p = dryrun.plan(m, self._mods(body))
                base = self.store.dir(s.id) / "jobs" if s is not None else None
                job = dryrun.Job(m, p, dryrun.new_job_dir(base), launcher=self.launcher, running=self.running,
                                 poll=self.poll)
            except dryrun.Refused as e:
                raise Bad(str(e)) from None
            job.on_end = self.save_log
            self.job = job
            if s is not None:
                s.last_job = job.id
                self.store.save(s)
        logbook.set_masks({"<modlist>": self.folder, "<game>": str(m.instance.game_dir) if m.instance.game_dir else None,
                           "<mods>": str(m.instance.mods_dir), "<job>": str(job.dir), "<modtrap>": str(paths.home())})
        job.start()
        return job.public()

    def steps(self, body: dict) -> dict:
        """The steps for the ticked mods (DESIGN§14). The part that reads folders takes seconds on a large list:
        it runs once, off the request, and the answer says while it is still going."""
        m = self._need()
        mods = body.get("mods")
        if not isinstance(mods, list) or len(mods) > 50 or not all(isinstance(x, str) and x for x in mods):
            raise Bad("the ticked mods did not arrive")
        key = (id(m), tuple(sorted(mods)))
        with self._lock:
            started = key in self._deep
            if not started and mods:
                self._deep = {k: v for k, v in self._deep.items() if k[0] == id(m)}     # an older reading's are dropped
                self._deep[key] = None
        if not started and mods:
            def work() -> None:
                try:
                    found = steps.look_deeper(m, mods)
                except Exception as e:
                    log.warn("looking into the ticked mods' folders failed: %s", logbook.why(e))
                    found = {}
                with self._lock:
                    self._deep[key] = found
            threading.Thread(target=work, name="steps-deep", daemon=True).start()
        deep = self._deep.get(key)
        job = self.job.public() if self.job else None
        out = steps.compile_steps(m, mods, job, deep)
        out["looking"] = bool(mods) and deep is None
        return out

    def job_state(self) -> dict:
        return {"job": self.job.public() if self.job else None}

    # --- answers ---------------------------------------------------------------------------------------------------

    def _need(self) -> model.Model:
        m = self.model
        if m is None:
            raise Bad("no modlist is open")
        return m

    def state(self) -> dict:
        with self._lock:
            out = {"name": NAME, "version": VERSION, "status": self.status, "message": self.message,
                   "folder": self.folder, "profile": self.profile}
            m = self.model
        settings = paths.load_settings()
        out["recent"] = [r for r in settings.get("recent", []) if isinstance(r, str) and r][:8]
        out["log_epoch"] = self.log_epoch
        every = self.store.all()
        live = [x for x in every if x.status != sessions.FINISHED]
        done = [x for x in every if x.status == sessions.FINISHED][-10:]
        out["sessions"] = [x.brief() for x in live + done[::-1]]
        s = self.session
        if s is not None:
            cur = next((x for x in every if x.id == s.id), s)           # as it is on disk now
            self.session = cur
            out["session"] = dict(cur.brief(), locked=self._locked(), ui=cur.ui)
        else:
            out["session"] = None
        if m is not None and out["status"] == "ready":
            inst = m.instance
            real = [x for x in inst.mods if x.kind == "mod"]
            rows = list(m.plugins.values())
            out.update({
                "game": inst.game_name, "profiles": list(inst.profiles),
                "mods": len(real), "mods_enabled": sum(x.enabled for x in real),
                "separators": sum(x.kind == "separator" for x in inst.mods),
                "plugins": sum(r.position is not None for r in rows), "plugins_active": sum(r.active for r in rows),
                "unreadable": sum(bool(r.unreadable) and r.source is not None for r in rows),
                "tools": self._tools(inst),
                "notes": [logbook.mask(n) for n in inst.notes],
                "issues": [{"plugin": i.plugin, "master": i.master, "what": i.what} for i in m.issues[:500]],
                "issue_count": len(m.issues),
            })
        return out

    def _tools(self, inst: instance.Instance) -> list[dict]:
        """The executables set up in MO2 (DESIGN§13): title, program file, the mod its new files go to, and
        which one ModTrap would start as xEdit."""
        try:
            chosen = dryrun.find_xedit(inst)[0]
        except dryrun.Refused:
            chosen = ""
        return [{"title": e.title, "file": Path(e.binary.replace("\\", "/")).name,
                 "output_mod": inst.output_mods.get(e.title, ""), "xedit": e.title == chosen}
                for e in inst.executables]

    def mods(self) -> dict:
        m = self._need()
        hit = self._lists.get("mods")
        if hit and hit[0] is m:
            return hit[1]
        rows = []
        for mod in reversed(m.instance.mods):               # highest priority first, as MO2 lists them
            if mod.kind in ("game", "overwrite") and not mod.plugins:
                continue
            won = m.provided_by(mod)
            rows.append({"name": mod.name, "priority": mod.priority, "enabled": mod.enabled, "kind": mod.kind,
                         "listed": mod.listed, "plugins": [r.name for r in won],
                         "files": len(mod.plugins), "dependants": len(m.dependants_of_mod(mod)) if won else 0})
        out = {"mods": rows}
        self._lists["mods"] = (m, out)                  # the lists are worked out once for each reading
        return out

    def plugins(self) -> dict:
        m = self._need()
        rows = []
        for f in m.order:
            r = m.plugins[f]
            rows.append({"name": r.name, "position": r.position, "active": r.active, "kind": r.kind,
                         "mod": r.source or "", "mod_priority": r.source_priority, "primary": r.primary,
                         "masters": len(r.masters), "dependants": len(r.dependants),
                         "missing": r.missing_masters, "inactive": r.inactive_masters,
                         "unreadable": r.unreadable, "also_in": list(r.also_in)})
        return {"plugins": rows}

    def plugin(self, name: str) -> dict:
        r = self._need().row(name)
        if r is None:
            raise Bad("no plugin of that name in this profile")
        return {"name": r.name, "position": r.position, "active": r.active, "kind": r.kind, "mod": r.source or "",
                "mod_priority": r.source_priority, "author": r.author, "description": r.description[:2000],
                "masters": list(r.masters), "dependants": list(r.dependants), "missing": r.missing_masters,
                "inactive": r.inactive_masters, "unreadable": r.unreadable, "also_in": list(r.also_in)}

    def mod(self, name: str) -> dict:
        m = self._need()
        mod = m.instance.mod(name)
        if mod is None:
            raise Bad("no mod of that name in this profile")

        def brief(r: model.PluginRow) -> dict:
            return {"name": r.name, "position": r.position, "kind": r.kind, "active": r.active,
                    "masters": len(r.masters)}

        return {"name": mod.name, "priority": mod.priority, "enabled": mod.enabled, "kind": mod.kind,
                "plugins": [dict(brief(r), master_names=list(r.masters)) for r in m.provided_by(mod)],
                "groups": [{"mod": g.mod.name, "priority": g.mod.priority, "enabled": g.mod.enabled,
                            "reading": g.reading, "others": g.others, "made_by": list(g.made_by),
                            "leftover": list(g.leftover), "evidence": list(g.evidence), "proposal": g.proposal,
                            "plugins": [brief(r) for r in g.dependants]}
                           for g in model.groups(m, mod)]}

    # --- the server's two entry points -----------------------------------------------------------------------------

    def get(self, path: str, query: dict[str, str]) -> tuple[int, object]:
        if path == "/api/state":
            return 200, self.state()
        if path == "/api/mods":
            return 200, self.mods()
        if path == "/api/plugins":
            return 200, self.plugins()
        if path == "/api/plugin":
            return 200, self.plugin(query.get("name", ""))
        if path == "/api/mod":
            return 200, self.mod(query.get("name", ""))
        if path == "/api/job":
            return 200, self.job_state()
        if path == "/api/log":
            try:
                after = int(query.get("after", "0"))
            except ValueError:
                after = 0
            lines, newest = logbook.lines_after(after)
            return 200, {"lines": lines, "newest": newest}
        return 404, {"error": "not found"}

    def post(self, path: str, body: dict) -> tuple[int, object, Callable[[], None] | None]:
        if path == "/api/open":
            folder, profile = body.get("folder"), body.get("profile")
            if not isinstance(folder, str) or len(folder) > 1000:
                raise Bad("give the modlist's folder", "folder")
            if profile is not None and (not isinstance(profile, str) or len(profile) > 200):
                raise Bad("the profile's name is not usable", "profile")
            same = self.session is not None and sessions.modlist_key(folder.strip().strip('"') or ".") == self.session.key
            self.open(folder, profile or None, session=self.session if same else None)
            return 200, {"status": "reading"}, None
        if path == "/api/locate":
            return 200, self.locate(body), None
        if path == "/api/dryrun/plan":
            return 200, self.dry_plan(body), None
        if path == "/api/dryrun/start":
            return 200, self.dry_start(body), None
        if path == "/api/steps":
            return 200, self.steps(body), None
        if path == "/api/job/stop":
            if self.job is None:
                raise Bad("no dry run is going")
            self.job.stop()
            return 200, self.job_state(), None
        if path == "/api/session/switch":
            return 200, self.session_switch(body), None
        if path == "/api/session/new":
            return 200, self.session_new(), None
        if path == "/api/session/rename":
            return 200, self.session_rename(body), None
        if path == "/api/session/finish":
            return 200, self.session_finish(body), None
        if path == "/api/session/ui":
            return 200, self.session_ui(body), None
        if path == "/api/quit":
            answer, after = self.quit(body)
            return 200, answer, after
        if path == "/api/rescan":
            if not self.folder:
                raise Bad("no modlist is open")
            if self._busy():
                raise Bad("a dry run is going; rescan when it has ended")
            self.open(self.folder, self.profile or None, session=self.session)
            return 200, {"status": "reading"}, None
        return 404, {"error": "not found"}, None
