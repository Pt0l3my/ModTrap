"""The endpoints that change a modlist (DESIGN§8, DESIGN§16.8). Loaded only when ModTrap is started with
`--allow-changes`: without it this module is never imported and the page's "Add it" stays switched off (WHY§44).

What is here: the probe (DESIGN§9), which must pass before the rest works; adding the mods on the Add mods tab,
and taking them out again; and the demaster with its Revert. Each goes through the job modules, which keep the
rules: MO2 closed, the lists in the safe folder first, the result checked, any failure put back, everything in the
history.
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path

import json

from . import addjob, demaster, dryrun, history, logbook, paths, probejob, safe
from .server import Bad

log = logbook.get("add")
PATHS = ("/api/add/plan", "/api/add/run", "/api/add/revert",
         "/api/demaster/plan", "/api/demaster/start", "/api/demaster/install", "/api/demaster/revert",
         "/api/probe/start", "/api/probe/stop", "/api/probe/cleanup")


class Changes:
    PATHS = PATHS

    def __init__(self, api, require_probe: bool = True) -> None:
        self.api = api
        self._lock = threading.Lock()
        self.require_probe = require_probe              # DESIGN§9: no real job before the probe has passed
        self.probe: probejob.Probe | None = None
        self.dm: demaster.Demaster | None = None        # the demaster in hand, if any
        self.dm_state = ""                              # working, verified, installed, failed
        self.dm_message = ""
        self.dm_check: dict | None = None
        self._dm_thread: threading.Thread | None = None

    def busy(self) -> bool:
        return self.dm_state == "working" or (self.probe is not None and self.probe.state == "working")

    # --- the probe (DESIGN§9, WHY§47) --------------------------------------------------------------------------------

    def gate(self) -> str:
        """Why a real job is not allowed yet, or ""."""
        api = self.api
        if not self.require_probe:
            return ""
        if api.session is None or api.model is None:
            return "no modlist is open"
        return probejob.passed(api.store.dir(api.session.id), api.model.instance)

    def probe_start(self, body: dict) -> dict:
        api = self.api
        with self._lock:
            m = api._need()
            if api._busy():
                raise Bad("something else is going; wait for it to end")
            if api.status != "ready":
                raise Bad("the modlist is being read; try again in a moment")
            if api._locked():
                raise Bad(api._locked())
            if self.closed() is not True:
                raise Bad("close MO2 first: the probe begins by writing its test mods into MO2's lists" if self.closed() is False
                          else "ModTrap cannot tell whether MO2 is open on this PC, so the probe cannot run here")
            base = self._jobs_dir()
            work = base / ("probe-" + time.strftime("%Y%m%d-%H%M%S"))
            n = 2
            while work.exists():
                work, n = base / ("probe-%s-%d" % (time.strftime("%Y%m%d-%H%M%S"), n)), n + 1
            work.mkdir(parents=True)
            pr = probejob.Probe(m, work, api.store.dir(api.session.id), launcher=api.launcher, running=api.running,
                                closed=self.closed, poll=api.poll, read=api._cache.read, closer=api.closer,
                                presser=api.presser)

            def ended() -> None:
                api.save_log()
                api.open(api.folder, api.profile or None, session=api.session)
            pr.on_end = ended
            self.probe = pr
        log.info("the probe starts: invented test plugins only; everything it changes it puts back")
        pr.start()
        return self.probe_public()

    def probe_stop(self, body: dict) -> dict:
        if self.probe is None:
            raise Bad("no probe is going")
        self.probe.stop()
        return self.probe_public()

    def probe_cleanup(self, body: dict) -> dict:
        api = self.api
        if self.probe is None or self.probe.state == "working":
            raise Bad("there is nothing of a probe to remove from here; the test mods can be removed in MO2")
        if self.closed() is not True:
            raise Bad("MO2 must be closed while ModTrap removes its test mods")
        left = self.probe.clean_up_again()
        api.open(api.folder, api.profile or None, session=api.session)
        return {"left": left}

    def probe_public(self) -> dict:
        api = self.api
        out: dict = {"needed": self.require_probe, "reason": self.gate() if api.model is not None else "",
                     "state": "", "steps": [], "when": ""}
        if self.probe is not None:
            out.update(self.probe.public())
            return out
        if api.session is not None:
            try:
                with open(api.store.dir(api.session.id) / "probe.json", "rb") as f:
                    data = json.loads(f.read(4 * 1024 * 1024).decode("utf-8"))
                out.update(data.get("result", {}))
                out["when"] = data.get("when", "")
            except (OSError, ValueError, AttributeError):
                pass
        return out

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
            if self.gate():
                raise Bad(self.gate())
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
        return {"job": name, "left": got["left"], "how": got.get("how", "whole"), "restored": restored}

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
                "switch_off": pl.switch_off, "disable_mods": pl.disable_mods, "needs_you": pl.needs_you, "notes": pl.notes, "blocked": pl.blocked}

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
            if self.gate():
                raise Bad(self.gate())
            m, job, pl = self._dm_plan()
            base = self._jobs_dir()
            work = base / ("demaster-" + time.strftime("%Y%m%d-%H%M%S"))
            n = 2
            while work.exists():
                work, n = base / ("demaster-%s-%d" % (time.strftime("%Y%m%d-%H%M%S"), n)), n + 1
            work.mkdir(parents=True)
            dm = demaster.Demaster(m, job.plan, pl, work, api.store.dir(api.session.id), launcher=api.launcher,
                                   running=api.running, closed=self.closed, poll=api.poll, closer=api.closer,
                                   presser=api.presser)
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
            the_safe = safe.Safe(work / "safe")
            try:
                what = the_safe.revert(False)
            except safe.Refused:
                # The lists changed since (MO2 has run): take back ModTrap's own changes line by line instead.
                try:
                    with open(work / "installed.json", "rb") as f:
                        done = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
                    m = api._need()
                    what = demaster.undo_by_line(m.instance.profiles_dir / m.instance.profile, the_safe, done)
                except (OSError, ValueError) as e:
                    raise Bad("this demaster's record cannot be read: %s" % logbook.why(e)) from None
            history.History(api.store.dir(api.session.id)).add(
                "reverted", why="the owner asked", job=name, restored=[Path(p).name for p in what["restore"]],
                removed=[Path(p).name for p in what["remove"]])
            if self.dm is not None and self.dm.dir.name == name:
                self.dm, self.dm_state, self.dm_check = None, "", None
            log.info("the demaster %s was put back: %d file(s) restored, %d of ModTrap's removed", name,
                     len(what["restore"]), len(what["remove"]))
        api.open(api.folder, api.profile or None, session=api.session)
        return {"job": name, "restored": len(what["restore"]), "removed": len(what["remove"]),
                "how": what.get("how", "whole"), "left": [Path(p).name for p in what.get("left", [])]}

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
        if path == "/api/probe/start":
            return self.probe_start(body)
        if path == "/api/probe/stop":
            return self.probe_stop(body)
        if path == "/api/probe/cleanup":
            return self.probe_cleanup(body)
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
