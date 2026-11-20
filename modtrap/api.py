"""ModTrap's endpoints (DESIGN§4). Version 0.1 reads only: the instance, its mods, its plugins and what depends on
what. Nothing here writes to an instance; the one thing saved is the chosen folder, in ModTrap's own settings."""

from __future__ import annotations

import base64
import binascii
import threading
from pathlib import Path
from typing import Callable

from . import NAME, VERSION, dryrun, instance, locate, logbook, model, paths, plugin
from .server import Bad

log = logbook.get("app")


class HeaderCache:
    """Plugin headers by path, size and time: a rescan re-reads only the plugins that changed."""

    def __init__(self) -> None:
        self._seen: dict[str, tuple[int, int, object]] = {}
        self.read_count = 0

    def read(self, path: Path) -> plugin.Header:
        try:
            st = path.stat()
        except OSError as e:
            raise plugin.Unreadable("the file could not be opened (%s)" % type(e).__name__) from None
        key = str(path)
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
        self.job: dryrun.Job | None = None
        self.launcher = dryrun.launch          # replaced in tests
        self.running = dryrun.image_running
        self.poll = 1.0

    # --- reading an instance, off the request thread ---------------------------------------------------------------

    def open(self, folder: str, profile: str | None = None, wait: bool = False) -> None:
        folder = folder.strip().strip('"')
        if not folder:
            raise Bad("give the modlist's folder", "folder")
        with self._lock:
            self._run += 1
            run = self._run
            self.status, self.message, self.folder, self.profile = "reading", "", folder, profile or ""
        t = threading.Thread(target=self._read, args=(run, folder, profile), name="read-instance", daemon=True)
        t.start()
        if wait:
            t.join()

    def _read(self, run: int, folder: str, profile: str | None) -> None:
        logbook.set_masks({"<modlist>": folder})
        log.info("reading the modlist in <modlist>")
        try:
            inst = instance.load(Path(folder), profile)
            logbook.set_masks({"<modlist>": folder, "<game>": str(inst.game_dir) if inst.game_dir else None,
                               "<mods>": str(inst.mods_dir)})
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
            try:
                p = dryrun.plan(m, self._mods(body))
                job = dryrun.Job(m, p, dryrun.new_job_dir(), launcher=self.launcher, running=self.running,
                                 poll=self.poll)
            except dryrun.Refused as e:
                raise Bad(str(e)) from None
            self.job = job
        logbook.set_masks({"<modlist>": self.folder, "<game>": str(m.instance.game_dir) if m.instance.game_dir else None,
                           "<mods>": str(m.instance.mods_dir), "<job>": str(job.dir)})
        job.start()
        return job.public()

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
                            "leftover": list(g.leftover), "plugins": [brief(r) for r in g.dependants]}
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
            self.open(folder, profile or None)
            return 200, {"status": "reading"}, None
        if path == "/api/locate":
            return 200, self.locate(body), None
        if path == "/api/dryrun/plan":
            return 200, self.dry_plan(body), None
        if path == "/api/dryrun/start":
            return 200, self.dry_start(body), None
        if path == "/api/job/stop":
            if self.job is None:
                raise Bad("no dry run is going")
            self.job.stop()
            return 200, self.job_state(), None
        if path == "/api/rescan":
            if not self.folder:
                raise Bad("no modlist is open")
            if self._busy():
                raise Bad("a dry run is going; rescan when it has ended")
            self.open(self.folder, self.profile or None)
            return 200, {"status": "reading"}, None
        return 404, {"error": "not found"}, None
