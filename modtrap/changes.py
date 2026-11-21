"""The endpoints that change a modlist (DESIGN§8, DESIGN§16.8). Loaded only when ModTrap is started with
`--allow-changes`: without it this module is never imported and the page's "Add it" stays switched off (WHY§44).

What is here: the plan for adding the mods on the Add mods tab, carrying it out, and Revert. Each goes through
addjob, which keeps the rules: MO2 closed, the lists in the safe folder first, the result checked, any failure put
back, everything in the history.
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path

import json

from . import addjob, demaster, dryrun, history, logbook, paths, safe
from .server import Bad

log = logbook.get("add")
PATHS = ("/api/add/plan", "/api/add/run", "/api/add/revert",
         "/api/demaster/plan", "/api/demaster/start", "/api/demaster/install", "/api/demaster/revert")


class Changes:
    PATHS = PATHS

    def __init__(self, api) -> None:
        self.api = api
        self._lock = threading.Lock()
        self.dm: demaster.Demaster | None = None        # the demaster in hand, if any
        self.dm_state = ""                              # working, verified, installed, failed
        self.dm_message = ""
        self.dm_check: dict | None = None
        self._dm_thread: threading.Thread | None = None

    def busy(self) -> bool:
        return self.dm_state == "working"

    def closed(self) -> bool | None:
        """Is MO2 closed? None when it cannot be told; then nothing is changed."""
        r = self.api.running(dryrun.MO2_EXE)
        return None if r is None else not r

    def _jobs_dir(self) -> Path:
        s = self.api.session
        if s is None:
            raise Bad("there is no session to keep the job in")
        return self.api.store.dir(s.id) / "jobs"

    def jobs(self) -> list[dict]:
        """The adds this session carried out, newest first."""
        try:
            folders = sorted((p for p in self._jobs_dir().iterdir() if p.is_dir() and p.name.startswith("add-")),
                             reverse=True)
        except (OSError, Bad):
            return []
        return [x for x in (addjob.AddJob.summary(p) for p in folders) if x is not None]

    def _planned(self, body: dict) -> tuple[object, addjob.Plan]:
        api = self.api
        m = api._need()
        if api._busy():
            raise Bad("something else is going; wait for it to end")
        if api._locked():
            raise Bad(api._locked())
        got = api.add(body)
        if got.get("looking") or got.get("unpacking"):
            raise Bad("ModTrap is still reading the mods; try again in a moment")
        if got.get("failed"):
            raise Bad(got["failed"])
        staged = {r["name"]: {"root": r["root"], "archive": r["archive"], "id": r["id"]}
                  for r in api._staged.values() if r["state"] == "ready" and r["id"] in body.get("staged", [])}
        try:
            return m, addjob.plan(m, got, staged)
        except addjob.Refused as e:
            raise Bad(str(e)) from None

    def plan(self, body: dict) -> dict:
        _m, p = self._planned(body)
        out = p.public()
        out["mo2_closed"] = self.closed()
        out["nothing"] = not p.plugins and all(x["enabled"] for x in p.mods)
        return out

    def run(self, body: dict) -> dict:
        api = self.api
        with self._lock:
            m, p = self._planned(body)
            base = self._jobs_dir()
            work = base / ("add-" + time.strftime("%Y%m%d-%H%M%S"))
            n = 2
            while work.exists():
                work, n = base / ("add-%s-%d" % (time.strftime("%Y%m%d-%H%M%S"), n)), n + 1
            job = addjob.AddJob(m.instance, m, p, work, api.store.dir(api.session.id), self.closed)
            log.info("adding %d mod(s) and %d plugin(s)", len(p.mods), len(p.plugins))
            try:
                done = job.run()
            except addjob.Refused as e:
                log.error("%s", e)
                raise Bad(str(e)) from None
            names = {x["name"] for x in p.mods if x["staged"]}
            for rec in api._staged.values():
                if rec["name"] in names and rec["state"] == "ready":
                    rec["state"] = "installed"
                    api._save_staged(rec)
            for x in done["mods"]:
                log.info("  %s: enabled at priority %s", x["name"], x["priority"])
            for x in done["plugins"]:
                log.info("  %s: active at position %s", x["name"], x["position"])
        api.open(api.folder, api.profile or None, session=api.session)          # read the modlist as it now is
        return {"job": work.name, "done": done}

    def revert(self, body: dict) -> dict:
        api = self.api
        name = body.get("job")
        if not isinstance(name, str) or not re.fullmatch(r"add-[0-9]{8}-[0-9]{6}(-[0-9]+)?", name):
            raise Bad("that is not one of this session's adds")
        with self._lock:
            m = api._need()
            if api._busy():
                raise Bad("something else is going; wait for it to end")
            work = self._jobs_dir() / name
            try:
                job = addjob.AddJob.reopen(m.instance, m, work, api.store.dir(api.session.id), self.closed)
                got = job.revert()
            except addjob.Refused as e:
                raise Bad(str(e)) from None
            names = {x["name"] for x in job.plan.mods if x["staged"]}
            restored = []
            for rec in api._staged.values():
                if rec["name"] in names and rec["state"] == "installed" and rec.get("root") and Path(rec["root"]).is_dir():
                    rec["state"] = "ready"
                    api._save_staged(rec)
                    restored.append({"id": rec["id"], "name": rec["name"]})
            log.info("the add %s was put back%s", name, (" (left in place: %s)" % ", ".join(got["left"])) if got["left"] else "")
        api.open(api.folder, api.profile or None, session=api.session)
        return {"job": name, "left": got["left"], "restored": restored}

    # --- the demaster (DESIGN§6.3 to §6.5, WHY§39, WHY§46) -----------------------------------------------------------

    def _dry(self) -> tuple[object, dryrun.Job]:
        api = self.api
        m = api._need()
        job = api.job
        if not isinstance(job, dryrun.Job) or job.state != "done" or job.model is not m:
            raise Bad("a finished dry run of the modlist as it is now is needed first: run the dry run (again)")
        return m, job

    def _dm_plan(self) -> tuple[object, dryrun.Job, demaster.Plan]:
        m, job = self._dry()
        try:
            return m, job, demaster.plan(m, job.public())
        except demaster.Refused as e:
            raise Bad(str(e)) from None

    @staticmethod
    def _plan_public(pl: demaster.Plan) -> dict:
        return {"mods": pl.trapped_mods, "trapped": pl.trapped, "mod_name": pl.mod_name,
                "demaster": [{"plugin": k, "actions": len(v)} for k, v in pl.demaster.items()],
                "switch_off": pl.switch_off, "needs_you": pl.needs_you, "notes": pl.notes, "blocked": pl.blocked}

    def demaster_plan(self, body: dict) -> dict:
        _m, _job, pl = self._dm_plan()
        return self._plan_public(pl)

    def demaster_start(self, body: dict) -> dict:
        api = self.api
        with self._lock:
            if api._busy():
                raise Bad("something else is going; wait for it to end")
            if api._locked():
                raise Bad(api._locked())
            if self.dm is not None and self.dm_state == "verified":
                raise Bad("a demaster is waiting to be put in place; finish that one first")
            m, job, pl = self._dm_plan()
            base = self._jobs_dir()
            work = base / ("demaster-" + time.strftime("%Y%m%d-%H%M%S"))
            n = 2
            while work.exists():
                work, n = base / ("demaster-%s-%d" % (time.strftime("%Y%m%d-%H%M%S"), n)), n + 1
            work.mkdir(parents=True)
            dm = demaster.Demaster(m, job.plan, pl, work, api.store.dir(api.session.id), launcher=api.launcher,
                                   running=api.running, closed=self.closed, poll=api.poll)
            self.dm, self.dm_state, self.dm_message, self.dm_check = dm, "working", "", None

        def work_it() -> None:
            try:
                dm.make_safe()
                dm.run_xedit()
                good = dm.verify()
                self.dm_state = "verified"
                log.info("the demaster's new plugins are verified: %s", ", ".join(good) or "none")
            except (demaster.Refused, safe.Refused) as e:
                self.dm_state, self.dm_message = "failed", logbook.mask(str(e))
                log.error("the demaster stopped: %s. Nothing in the modlist was changed.", e)
            except Exception as e:
                self.dm_state, self.dm_message = "failed", "an error inside ModTrap: " + logbook.why(e)
                log.error("the demaster stopped: %s", logbook.why(e))
            api.save_log()
        self._dm_thread = threading.Thread(target=work_it, name="demaster", daemon=True)
        self._dm_thread.start()
        return self.demaster_public()

    def demaster_install(self, body: dict) -> dict:
        api = self.api
        with self._lock:
            dm = self.dm
            if dm is None or self.dm_state != "verified":
                raise Bad("there is no verified demaster to put in place")
            try:
                done = dm.install()
                self.dm_check = dm.check()
            except demaster.Refused as e:
                if dm.stage == "reverted":
                    self.dm_state, self.dm_message = "failed", logbook.mask(str(e))
                raise Bad(str(e)) from None
            self.dm_state = "installed"
            paths.write_atomic(dm.dir / "plan.json", (json.dumps(dict(self._plan_public(dm.plan), when=time.strftime(
                "%Y-%m-%dT%H:%M:%S"), written=dm.written), indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
            log.info("the demaster is in place: %d plugin(s) in “%s”, %d mod(s) disabled, %d patch(es) deactivated",
                     len(done["plugins"]), done["mod"], len(done["disabled"]), len(done["deactivated"]))
        api.open(api.folder, api.profile or None, session=api.session)
        return self.demaster_public()

    def demaster_jobs(self) -> list[dict]:
        """The demasters this session put in place, newest first."""
        try:
            folders = sorted((p for p in self._jobs_dir().iterdir() if p.is_dir() and p.name.startswith("demaster-")),
                             reverse=True)
        except (OSError, Bad):
            return []
        out = []
        for d in folders:
            try:
                with open(d / "plan.json", "rb") as f:
                    data = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
                with open(d / "installed.json", "rb") as f:
                    done = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
            except (OSError, ValueError):
                continue
            try:
                reverted = bool(safe.Safe(d / "safe").reverted)
            except safe.Refused:
                reverted = False
            out.append({"job": d.name, "when": data.get("when", ""), "mods": data.get("mods", []),
                        "mod_name": done.get("mod", ""), "plugins": done.get("plugins", []),
                        "disabled": done.get("disabled", []), "deactivated": done.get("deactivated", []),
                        "state": "reverted" if reverted else "installed"})
        return out

    def demaster_revert(self, body: dict) -> dict:
        api = self.api
        name = body.get("job")
        if not isinstance(name, str) or not re.fullmatch(r"demaster-[0-9]{8}-[0-9]{6}(-[0-9]+)?", name):
            raise Bad("that is not one of this session's demasters")
        with self._lock:
            api._need()
            if api._busy():
                raise Bad("something else is going; wait for it to end")
            if self.closed() is not True:
                raise Bad("MO2 must be closed while ModTrap puts the mod list back. Close MO2, then go on.")
            work = self._jobs_dir() / name
            if not (work / "installed.json").is_file():
                raise Bad("that demaster was never put in place")
            try:
                what = safe.Safe(work / "safe").revert(body.get("overwrite") is True)
            except safe.Refused as e:
                raise Bad(str(e)) from None
            history.History(api.store.dir(api.session.id)).add(
                "reverted", why="the owner asked", job=name, restored=[Path(p).name for p in what["restore"]],
                removed=[Path(p).name for p in what["remove"]])
            if self.dm is not None and self.dm.dir.name == name:
                self.dm, self.dm_state, self.dm_check = None, "", None
            log.info("the demaster %s was put back: %d file(s) restored, %d of ModTrap's removed", name,
                     len(what["restore"]), len(what["remove"]))
        api.open(api.folder, api.profile or None, session=api.session)
        return {"job": name, "restored": len(what["restore"]), "removed": len(what["remove"])}

    def demaster_public(self) -> dict:
        dm = self.dm
        out: dict = {"state": self.dm_state, "message": self.dm_message, "jobs": self.demaster_jobs()}
        if dm is not None:
            out.update({"job": dm.dir.name, "plan": self._plan_public(dm.plan), "written": list(dm.written),
                        "check": self.dm_check})
            if self.dm_state == "verified":
                out["mo2_closed"] = self.closed()
        return out

    def post(self, path: str, body: dict) -> dict:
        if path == "/api/demaster/plan":
            return self.demaster_plan(body)
        if path == "/api/demaster/start":
            return self.demaster_start(body)
        if path == "/api/demaster/install":
            return self.demaster_install(body)
        if path == "/api/demaster/revert":
            return self.demaster_revert(body)
        if path == "/api/add/plan":
            return self.plan(body)
        if path == "/api/add/run":
            return self.run(body)
        return self.revert(body)
