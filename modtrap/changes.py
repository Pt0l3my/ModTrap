"""The endpoints that change a modlist (DESIGN§8, DESIGN§16.8). Loaded only when ModTrap is started with
`--allow-changes`: without it this module is never imported and the page's "Add it" stays switched off (WHY§44).

What is here: the probe (DESIGN§9), which must pass before the rest works; adding the mods on the Add mods tab,
and taking them out again; and the demaster with its Revert. Each goes through the job modules, which keep the
rules: MO2 closed, the lists in the safe folder first, the result checked, any failure put back, everything in the
history.
"""

from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path

import json

import shutil

from . import addjob, demaster, dryrun, history, logbook, paths, plugin, probejob, safe
from . import process
from .instance import fold
from .server import Bad

log = logbook.get("add")
TOOL_KEEP_FILES = 5000                 # a tool's output is kept for Revert up to this many files
TOOL_KEEP_BYTES = 1024 * 1024 * 1024   # and this much in all; a larger one is to be made again after a Revert

PATHS = ("/api/add/plan", "/api/add/run", "/api/add/revert",
         "/api/demaster/plan", "/api/demaster/start", "/api/demaster/install", "/api/demaster/revert",
         "/api/demaster/drop", "/api/demaster/retire", "/api/jobs/clear",
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
        self._hashes: dict[tuple, str] = {}             # (path, size, time) -> sha256, for the stale check
        self._gap_memo: tuple = (None, [])              # what a reverted demaster's lists still lack, per state of the lists
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
        self.api.wait_mo2_gone()                # a MO2 of ModTrap's own last run may still be leaving (WHY§67)
        api = self.api
        with self._lock:
            m = api._need()
            if api._busy():
                raise Bad("something else is going; wait for it to end")
            if api.unsettled():
                raise Bad(api.unsettled() + "; try again in a moment")
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
            pr = probejob.Probe(m, work, api.store.dir(api.session.id), launcher=api._launch, running=api.running,
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
        return self.api.mo2_closed()            # this modlist's MO2; another modlist's does not count (WHY§58)

    def _jobs_dir(self) -> Path:
        s = self.api.session
        if s is None:
            raise Bad("there is no session to keep the job in")
        return self.api.store.dir(s.id) / "jobs"

    def _hidden(self) -> set[str]:
        """The finished jobs the owner cleared from the lists (WHY§67). Their folders, and the history of what
        ModTrap changed, stay."""
        try:
            with open(self._jobs_dir() / "hidden.json", "rb") as f:
                data = json.loads(f.read(4 * 1024 * 1024).decode("utf-8"))
            return {x for x in data if isinstance(x, str)}
        except (OSError, ValueError, Bad, TypeError):
            return set()

    def jobs(self) -> list[dict]:
        """The adds this session carried out, newest first."""
        try:
            folders = sorted((p for p in self._jobs_dir().iterdir() if p.is_dir() and p.name.startswith("add-")),
                             reverse=True)
        except (OSError, Bad):
            return []
        hidden = self._hidden()
        return [x for x in (addjob.AddJob.summary(p) for p in folders if p.name not in hidden) if x is not None]

    def jobs_clear(self, body: dict) -> dict:
        """Takes the jobs that no longer stand (reverted, or failed) off the lists. A job that is still in place
        stays: its Revert needs it. Nothing is deleted, and the history of changes is not touched."""
        gone = [j["job"] for j in self.jobs() if j["state"] != "added"] + \
               [j["job"] for j in self.demaster_jobs() if j["state"] != "installed" and not j["unfinished"] and not j["left_behind"]]
        hidden = sorted(self._hidden() | set(gone))
        try:
            paths.write_atomic(self._jobs_dir() / "hidden.json", (json.dumps(hidden, indent=1) + "\n").encode("utf-8"))
        except OSError as e:
            raise Bad("the list could not be cleared: %s" % logbook.why(e)) from None
        return {"cleared": len(gone)}

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
        self.api.wait_mo2_gone()                # a MO2 of ModTrap's own last run may still be leaving (WHY§67)
        api = self.api
        with self._lock:
            if self.gate():
                raise Bad(self.gate())
            if api.unsettled():
                raise Bad(api.unsettled() + "; try again in a moment")
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
        self.api.wait_mo2_gone()                # a MO2 of ModTrap's own last run may still be leaving (WHY§67)
        api = self.api
        name = body.get("job")
        if not isinstance(name, str) or not re.fullmatch(r"add-[0-9]{8}-[0-9]{6}(-[0-9]+)?", name):
            raise Bad("that is not one of this session's adds")
        with self._lock:
            m = api._need()
            if api._busy():
                raise Bad("something else is going; wait for it to end")
            if api.unsettled():
                raise Bad(api.unsettled() + "; try again in a moment")
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
            if api.unsettled():
                raise Bad(api.unsettled() + "; try again in a moment")
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
            dm = demaster.Demaster(m, job.plan, pl, work, api.store.dir(api.session.id), launcher=api._launch,
                                   running=api.running, closed=self.closed, poll=api.poll, closer=api.closer,
                                   presser=api.presser)
            self.dm, self.dm_state, self.dm_message, self.dm_check = dm, "working", "", None

        def work_it() -> None:
            try:
                dm.make_safe()
                dm.run_xedit()
                good = dm.verify()
                if not good and not dm.plan.switch_off and not dm.plan.disable_mods:
                    # Nothing to put in place: say why, and stop here. The modlist is as it was.
                    raise demaster.Refused("nothing could be demastered this time. " + " ".join(dm.plan.notes[:6]))
                self.dm_state = "verified"
                log.info("the demaster's new plugins are verified: %s", ", ".join(good) or "none")
            except (demaster.Refused, safe.Refused) as e:
                self.dm_state, self.dm_message = "failed", logbook.mask(str(e))
                log.error("the demaster stopped: %s. Nothing in the modlist was changed.", e)
                process.BOARD.stop("change", self.dm_message)
            except Exception as e:
                self.dm_state, self.dm_message = "failed", "an error inside ModTrap: " + logbook.why(e)
                log.error("the demaster stopped: %s", logbook.why(e))
                process.BOARD.stop("change", self.dm_message)
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
            if api.unsettled():
                raise Bad(api.unsettled() + "; try again in a moment")
            # The MO2 of the xEdit run may still be leaving; and in the one go, the plan the owner confirmed said
            # MO2 would be closed for this step (WHY§67).
            board = process.BOARD
            board.begin("install", process.INSTALL)
            board.mark("install", "mo2", process.GOING, "waiting for MO2 to close")
            api.wait_mo2_gone(owners_too=body.get("close_mo2") is True)
            try:
                done = dm.install()
                board.mark("install", "reread", process.GOING)
                self.dm_check = dm.check()
            except demaster.Refused as e:
                if dm.stage == "reverted":
                    self.dm_state, self.dm_message = "failed", logbook.mask(str(e))
                else:
                    board.begin("install", process.INSTALL)        # refused before anything was changed: as before
                    board.mark("install", "mo2", process.YOURS, logbook.mask(str(e)))
                raise Bad(str(e)) from None
            ok = bool(self.dm_check and self.dm_check.get("ok"))
            board.mark("install", "reread", process.DONE)
            problems = bool(self.dm_check and self.dm_check.get("new_problems"))
            board.mark("install", "health", process.FAILED if problems else process.DONE,
                       "the check found something: see the Selection tab" if problems else "clean")
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
        hidden = self._hidden()
        seen = False                 # has the newest demaster that was put in place been met yet
        for d in folders:
            if seen and d.name in hidden:
                continue
            try:
                with open(d / "plan.json", "rb") as f:
                    data = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
                with open(d / "installed.json", "rb") as f:
                    done = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
            except (OSError, ValueError):
                continue
            newest, seen = not seen, True
            if d.name in hidden and not newest:
                continue
            try:
                reverted = bool(safe.Safe(d / "safe").reverted)
            except safe.Refused:
                reverted = False
            # Only the newest demaster is looked at: an older one's plugins are a later one's business. A Revert that
            # left plugins out of their places stays on the list, cleared or not, until it is finished (WHY§83).
            unfinished = self._unfinished(d, done) if reverted and newest else []
            left_behind = self._left_behind(d) if reverted and newest else []
            if d.name in hidden and not unfinished and not left_behind:
                continue
            retired = [n for n in done.get("retired", []) if isinstance(n, str)]
            # ModTrap's copies that hide a plugin made anew (WHY§56), and for each whether the copy can go: the new
            # original must stand without the mod (WHY§80).
            remade = [] if reverted else self._remade(d, [n for n in done.get("plugins", []) if n not in retired],
                                                    data.get("trapped", []))
            out.append({"job": d.name, "when": data.get("when", ""), "mods": data.get("mods", []),
                        "mod_name": done.get("mod", ""), "plugins": done.get("plugins", []),
                        "disabled": done.get("disabled", []), "deactivated": done.get("deactivated", []),
                        "state": "reverted" if reverted else "installed", "retired": retired,
                        "stale": [x["plugin"] for x in remade], "remade": remade,
                        "unfinished": unfinished, "left_behind": left_behind})
        return out

    # --- the tools run after a demaster (MT29, WHY§91) ----------------------------------------------------------------

    def _placed(self) -> Path | None:
        """The folder of the demaster that is in place now (the newest one put in place and not reverted)."""
        job = next((j for j in self.demaster_jobs() if j["state"] == "installed"), None)
        return self._jobs_dir() / job["job"] if job is not None else None

    def tool_ran(self, title: str, files: int) -> None:
        """Notes, with the demaster in place, that a tool ModTrap started after it has closed with its output
        written. That note, and nothing the owner says, is what makes the tool's step done. Never raises."""
        try:
            work = self._placed()
            if work is None or files <= 0:
                return
            ran = self._tools_run_of(work)
            ran[title] = {"when": time.strftime("%Y-%m-%dT%H:%M:%S"), "files": int(files)}
            paths.write_atomic(work / "tools-run.json", (json.dumps(ran, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        except Exception as e:
            log.warn("the run of “%s” could not be noted with the demaster: %s", title, logbook.why(e))

    @staticmethod
    def _tools_run_of(work: Path) -> dict:
        try:
            with open(work / "tools-run.json", "rb") as f:
                data = json.loads(f.read(4 * 1024 * 1024).decode("utf-8"))
            return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, dict)} if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def tools_run(self) -> dict:
        """The tools that have had their run since the demaster in place was put in place: {title: {"when", "files"}}.
        Empty when no demaster is in place: a Revert, or a new demaster, starts every tool's step afresh."""
        try:
            work = self._placed()
            return self._tools_run_of(work) if work is not None else {}
        except Exception:
            return {}

    def _remade(self, job_dir: Path, plugins: list[str], trapped: list[str]) -> list[dict]:
        """The demastered plugins whose original a tool has made anew, each with whether ModTrap's copy of it can be
        retired: the original as it is now names no ticked plugin as a master, and every master it names is in the
        load order and active. {"plugin", "ok", "why", "original"}."""
        names = self._stale(job_dir, plugins)
        if not names:
            return []
        try:
            where = {fold(Path(i["path"]).name): Path(i["path"]) for i in safe.Safe(job_dir / "safe").items}
        except safe.Refused:
            where = {}
        m = self.api.model
        tf = {fold(t) for t in trapped}
        out = []
        for name in names:
            orig = where.get(fold(name))
            ok, why = False, "its original could not be found"
            if orig is not None:
                masters = None
                try:
                    masters = plugin.read(orig).masters
                except (plugin.Unreadable, OSError) as e:
                    why = "the new original cannot be read: %s" % logbook.why(e)
                if masters is not None:
                    still = [x for x in masters if fold(x) in tf]
                    absent = [x for x in masters if m is not None and (m.row(x) is None or not m.row(x).active)]
                    if still:
                        why = "the new original still names %s as a master: it was made while the mod was enabled" % ", ".join(still)
                    elif absent:
                        why = "the new original names a master that is missing or not active: %s" % ", ".join(absent[:4])
                    else:
                        ok, why = True, "the new original stands without the mod"
            out.append({"plugin": name, "ok": ok, "why": why, "original": orig.parent.name if orig is not None else ""})
        return out

    def demaster_retire(self, body: dict, quiet: bool = False) -> dict:
        """Takes ModTrap's own demastered copy of a plugin out of ModTrap's mod once a tool has made the plugin anew
        without the mod (WHY§80): the copy has the higher priority and would hide the new one. The copy is moved
        into the job's folder, not deleted; nothing else is touched, and the plugin keeps its place in the load
        order under its new provider."""
        api = self.api
        name = body.get("job")
        wanted = body.get("plugins")
        if not isinstance(name, str) or not re.fullmatch(r"demaster-[0-9]{8}-[0-9]{6}(-[0-9]+)?", name):
            raise Bad("that is not one of this session's demasters")
        api.wait_mo2_gone()
        gone = []
        with self._lock:
            api._need()
            if api._busy() or self.busy():
                raise Bad("something else is going; wait for it to end")
            if not quiet and api.unsettled():
                raise Bad(api.unsettled() + "; try again in a moment")
            if self.closed() is not True:
                raise Bad("MO2 must be closed while ModTrap takes its copy out of its mod. Close MO2, then go on.")
            job = next((j for j in self.demaster_jobs() if j["job"] == name), None)
            if job is None or job["state"] != "installed":
                raise Bad("that demaster is not in place")
            can = [x for x in job["remade"] if x["ok"] and (not isinstance(wanted, list) or x["plugin"] in wanted)]
            if not can:
                if quiet:
                    return {"retired": []}
                raise Bad("no copy of ModTrap's can be retired there: " + ("; ".join(
                    "%s: %s" % (x["plugin"], x["why"]) for x in job["remade"]) or "no original has been made anew"))
            work = self._jobs_dir() / name
            mod_dir = api.model.instance.mods_dir / job["mod_name"]
            hist = history.History(api.store.dir(api.session.id))
            for x in can:
                src, dst = mod_dir / x["plugin"], work / "retired" / x["plugin"]
                try:
                    if not src.is_file():
                        continue
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                    if safe.sha256(dst) != safe.sha256(src):
                        raise OSError("the copy kept in the job's folder is not whole")
                    src.unlink()
                except OSError as e:
                    raise Bad("%s could not be retired: %s. What was retired before it stays so." % (x["plugin"], logbook.why(e))) from None
                gone.append(x["plugin"])
                hist.add("copy retired", plugin=x["plugin"], mod=job["mod_name"], now_in=x["original"],
                         why="a tool made the plugin anew, without the mod")
                log.info("ModTrap's copy of %s is retired from “%s”: the plugin a tool made anew in “%s” now counts",
                         x["plugin"], job["mod_name"], x["original"])
            if gone:
                try:
                    with open(work / "installed.json", "rb") as f:
                        done = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
                    done["retired"] = sorted(set(done.get("retired", [])) | set(gone))
                    paths.write_atomic(work / "installed.json", (json.dumps(done, indent=1) + "\n").encode("utf-8"))
                except (OSError, ValueError) as e:
                    log.warn("the retiring could not be written down: %s", logbook.why(e))
        if gone:
            api.open(api.folder, api.profile or None, session=api.session)
        return {"retired": gone}

    def retire_remade(self) -> None:
        """After a tool's run that ModTrap started: every copy of ModTrap's that the run made needless is retired,
        if the owner's setting says so. Never raises: a tool's run must end cleanly whatever comes of this."""
        try:
            if self.api.settings().get("retire_copies") is False:
                return
            for job in self.demaster_jobs():
                if job["state"] == "installed" and any(x["ok"] for x in job["remade"]):
                    self.demaster_retire({"job": job["job"]}, quiet=True)
        except Bad as e:
            log.warn("ModTrap's copy was not retired by itself: %s", e)
        except Exception as e:
            log.warn("ModTrap's copy was not retired by itself: %s", logbook.why(e))

    def _stale(self, job_dir: Path, plugins: list[str]) -> list[str]:
        """The demastered plugins whose original has changed since. ModTrap's copy lies in ModTrap's own mod, above
        the original; when a tool makes the original again, the copy hides the newer file (WHY§56). The original
        as it was is known from the job's safe folder; a file is hashed again only when its size or time changed."""
        try:
            items = safe.Safe(job_dir / "safe").items
        except safe.Refused:
            return []
        want = {fold(n) for n in plugins}
        out = []
        for item in items:
            p = Path(item["path"])
            if fold(p.name) not in want:
                continue
            try:
                st = p.stat()
            except OSError:
                continue                                    # gone: nothing newer is being hidden
            key = (str(p), st.st_size, st.st_mtime_ns)
            if key not in self._hashes:
                try:
                    self._hashes[key] = safe.sha256(p)
                except OSError:
                    continue
            if self._hashes[key] != item["sha256"]:
                out.append(p.name)
        return out

    def demaster_revert(self, body: dict) -> dict:
        self.api.wait_mo2_gone()                # a MO2 of ModTrap's own last run may still be leaving (WHY§67)
        api = self.api
        name = body.get("job")
        if not isinstance(name, str) or not re.fullmatch(r"demaster-[0-9]{8}-[0-9]{6}(-[0-9]+)?", name):
            raise Bad("that is not one of this session's demasters")
        if body.get("finish") is True:
            with self._lock:
                api._need()
                if api._busy():
                    raise Bad("something else is going; wait for it to end")
                if api.unsettled():
                    raise Bad(api.unsettled() + "; try again in a moment")
                if self.closed() is not True:
                    raise Bad("MO2 must be closed while ModTrap puts the plugins back in the load order. Close MO2, then go on.")
                work = self._jobs_dir() / name
                if not (work / "installed.json").is_file():
                    raise Bad("that demaster was never put in place")
                out = self._revert_finish(name, work, safe.Safe(work / "safe"))
            api.open(api.folder, api.profile or None, session=api.session)
            return out
        with self._lock:
            api._need()
            if api._busy():
                raise Bad("something else is going; wait for it to end")
            if api.unsettled():
                raise Bad(api.unsettled() + "; try again in a moment")
            if self.closed() is not True:
                raise Bad("MO2 must be closed while ModTrap puts the mod list back. Close MO2, then go on.")
            work = self._jobs_dir() / name
            if not (work / "installed.json").is_file():
                raise Bad("that demaster was never put in place")
            the_safe = safe.Safe(work / "safe")
            if the_safe.reverted:
                raise Bad("that demaster has been put back already")
            try:
                what = the_safe.revert(False)
            except safe.Refused:
                # The lists changed since (MO2 has run): take back ModTrap's own changes line by line instead.
                try:
                    with open(work / "installed.json", "rb") as f:
                        done = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
                    m = api._need()
                    what = demaster.undo_by_line(m.instance.profiles_dir / m.instance.profile, the_safe, done, m.instance)
                except (OSError, ValueError) as e:
                    raise Bad("this demaster's record cannot be read: %s" % logbook.why(e)) from None
            # Back to how things stood before the demaster, whatever came after it (WHY§81): a plugin ModTrap
            # demastered that a tool has since made anew gets its original back, and so does a tool's output that
            # ModTrap kept before it started the tool. What is there now is set aside in the job's folder first.
            m = api._need()
            originals = self._originals_back(the_safe, work, m.instance.profiles_dir / m.instance.profile)
            tools_back = self._tools_back(work)
            # A plugin of ModTrap's own mod that a tool has written anew in place (MO2 writes to the file that wins, and
            # ModTrap's copy won): not as ModTrap made it, so Revert left it there. It is set aside, kept, so that
            # ModTrap's mod can go and the original, back in force, is the only one (WHY§95).
            rewritten = 0
            for path in list(what.get("left", [])):
                p = Path(path)
                try:
                    if p.is_file():
                        self._aside(p, work / "set-aside-by-revert" / "modtraps-own-mod")
                        p.unlink()
                        rewritten += 1
                        log.info("%s in ModTrap's own mod had been written anew by a tool: it is set aside in the job's folder", p.name)
                        try:
                            p.parent.rmdir()
                        except OSError:
                            pass
                except OSError as e:
                    log.warn("%s in ModTrap's own mod could not be set aside: %s", p.name, logbook.why(e))
            what["left"] = [x for x in what.get("left", []) if Path(x).exists()]
            what["restore"] = list(what["restore"]) + originals
            history.History(api.store.dir(api.session.id)).add(
                "reverted", why="the owner asked", job=name, restored=[Path(p).name for p in what["restore"]],
                removed=[Path(p).name for p in what["remove"]], tools=tools_back["titles"], not_kept=tools_back["not_kept"],
                placed=list(what.get("placed", [])), notes=[logbook.mask(n) for n in what.get("notes", [])])
            # Whatever the page still shows of a demaster describes the modlist as it was before this Revert: the
            # one that was reverted, or one still waiting to be put in place (WHY§62). It goes.
            if self.dm is not None and (self.dm.dir.name == name or self.dm_state in ("verified", "failed")):
                self._drop("the modlist was put back by Revert")
            log.info("the demaster %s was put back%s: %d file(s) restored, %d of ModTrap's removed%s", name,
                     " line by line, because the lists had changed since" if what.get("how") == "by line" else "",
                     len(what["restore"]), len(what["remove"]),
                     ", %d plugin(s) back at their places in the load order" % len(what["placed"]) if what.get("placed") else "")
        process.BOARD.drop("dry", "change", "install")     # put back: the Process tab shows a demaster still to come
        api.open(api.folder, api.profile or None, session=api.session)
        return {"job": name, "restored": len(what["restore"]), "removed": len(what["remove"]),
                "how": what.get("how", "whole"), "left": [Path(p).name for p in what.get("left", [])],
                "placed": len(what.get("placed", [])), "notes": [logbook.mask(n) for n in what.get("notes", [])],
                "tools": tools_back["titles"], "tools_not_kept": tools_back["not_kept"], "set_aside": tools_back["aside"] + len(originals) + rewritten}

    def _installed(self, work: Path) -> dict:
        try:
            with open(work / "installed.json", "rb") as f:
                done = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
        except (OSError, ValueError) as e:
            raise Bad("this demaster's record cannot be read: %s" % logbook.why(e)) from None
        if not isinstance(done, dict):
            raise Bad("this demaster's record cannot be read")
        return done

    def _unfinished(self, work: Path, done: dict) -> list[str]:
        """For a demaster that was reverted: the plugins it had taken out of the game that are not back at their
        places in the load order (WHY§83). Only said while every mod it had disabled is enabled: a later demaster
        of the same mods has them out again by intent. Never raises."""
        try:
            m = self.api.model
            if m is None:
                return []
            inst = m.instance
            pdir = inst.profiles_dir / inst.profile
            key = (work.name, id(m)) + tuple((pdir / n).stat().st_mtime_ns for n in ("modlist.txt", "plugins.txt", "loadorder.txt"))
            if self._gap_memo[0] == key:
                return self._gap_memo[1]
            mods = [inst.mod(n) for n in done.get("disabled", []) if isinstance(n, str)]
            names: list[str] = []
            if not any(x is None or not x.enabled for x in mods):
                gap = demaster.lists_gap(pdir, safe.Safe(work / "safe"), inst, done)
                names = [] if gap is None else [n for n, _b, _a in gap["place"]] + list(gap["activate"])
            self._gap_memo = (key, names)
            return names
        except Exception:
            return []

    @staticmethod
    def _left_behind(work: Path) -> list[str]:
        """For a demaster that was reverted: the plugins of ModTrap's own mod that are still on disk. A Revert leaves
        one that is no longer as ModTrap made it (a tool wrote it anew in place); from 0.3.25 it sets it aside, and
        one made before that left it, with ModTrap's mod folder around it (WHY§96). Never raises."""
        try:
            return [Path(a["path"]).name for a in safe.Safe(work / "safe").added if Path(a["path"]).is_file()]
        except Exception:
            return []

    def _revert_finish(self, name: str, work: Path, the_safe: safe.Safe) -> dict:
        """A Revert made before ModTrap put plugin lines back (or cut short): the plugins the demaster had taken out
        go back to their places in the load order. Nothing else is touched. Called with the lock held, MO2 closed;
        the caller reads the modlist again."""
        api = self.api
        if not the_safe.reverted:
            raise Bad("that demaster is still in place: Revert it first")
        done = self._installed(work)
        m = api._need()
        pdir = m.instance.profiles_dir / m.instance.profile
        gap = demaster.lists_gap(pdir, the_safe, m.instance, done)
        behind = [Path(a["path"]) for a in the_safe.added if Path(a["path"]).is_file()]
        if gap is None and not behind:
            raise Bad("the safe folder's copies of the plugin lists are not there any more, so ModTrap cannot say "
                      "where the plugins stood")
        gap = gap or {"place": [], "activate": []}
        placed, notes = demaster.lists_back(pdir, gap)
        # What the Revert left of ModTrap's own mod (WHY§96): set aside, kept, and the emptied folder taken away. Only
        # while the mod is not in MO2's list any more: a folder MO2 has listed again is MO2's and the owner's.
        aside = 0
        listed = m.instance.mod(str(done.get("mod", ""))) if done.get("mod") else None
        if behind and listed is not None and listed.listed:
            notes.append("ModTrap's own mod “%s” is in MO2's list again, so ModTrap leaves it alone: remove it in MO2" % done.get("mod"))
        else:
            for p in behind:
                try:
                    self._aside(p, work / "set-aside-by-revert" / "modtraps-own-mod")
                    p.unlink()
                    aside += 1
                    try:
                        p.parent.rmdir()
                    except OSError:
                        pass
                except OSError as e:
                    notes.append("%s could not be set aside: %s" % (p.name, logbook.why(e)))
        history.History(api.store.dir(api.session.id)).add(
            "revert finished", job=name, placed=placed + list(gap["activate"]), notes=[logbook.mask(n) for n in notes],
            left=[p.name for p in behind] if aside else [])
        log.info("the Revert of %s is finished: %d plugin(s) back at their places in the load order, %d left in ModTrap's "
                 "own mod set aside%s", name, len(placed) + len(gap["activate"]), aside, "; " + "; ".join(notes) if notes else "")
        return {"job": name, "placed": len(placed) + len(gap["activate"]), "notes": [logbook.mask(n) for n in notes],
                "how": "finish", "restored": 0, "removed": 0, "left": [], "tools": [], "tools_not_kept": [], "set_aside": aside}

    # --- a strong Revert (WHY§81) ------------------------------------------------------------------------------------

    @staticmethod
    def _aside(path: Path, folder: Path) -> None:
        """Moves a file that is about to be replaced into the job's folder, so that nothing made since is lost."""
        folder.mkdir(parents=True, exist_ok=True)
        dst, n = folder / path.name, 2
        while dst.exists():
            dst, n = folder / ("%s.%d" % (path.name, n)), n + 1
        shutil.copy2(path, dst)

    def _originals_back(self, the_safe: safe.Safe, work: Path, profile_dir: Path) -> list[str]:
        """Every plugin whose original ModTrap copied into the safe folder and that is no longer that original (a
        tool has made it anew, or it is gone) is put back as it was. The profile's lists are not touched here."""
        back = []
        for item in the_safe.items:
            p = Path(item["path"])
            if p.parent == profile_dir:
                continue
            try:
                if p.is_file() and safe.sha256(p) == item["sha256"]:
                    continue
                src = the_safe.files / item["copy"]
                if safe.sha256(src) != item["sha256"]:
                    log.warn("the safe folder's copy of %s is no longer what was taken; it was not put back", p.name)
                    continue
                if p.is_file():
                    self._aside(p, work / "set-aside-by-revert")
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_name(p.name + ".modtrap-revert")
                shutil.copy2(src, tmp)
                os.replace(tmp, p)
                back.append(str(p))
                log.info("%s is put back as it was before the demaster; what a tool made of it since is kept in the job's folder", p.name)
            except OSError as e:
                log.warn("%s could not be put back as it was: %s", p.name, logbook.why(e))
        return back

    def before_tool(self, title: str, made: list[Path], folder: Path | None) -> None:
        """Before ModTrap starts a tool while a demaster is in place: a copy of what the tool is about to write over
        (its output mod's files and the plugins it made) goes into that demaster's folder, once for each tool, so
        that Revert can bring the modlist back to how it stood before the demaster. Too large an output is not
        kept, and Revert then says that the tool is to run again. Never raises."""
        try:
            job = next((j for j in self.demaster_jobs() if j["state"] == "installed"), None)
            if job is None:
                return
            work = self._jobs_dir() / job["job"] / "tool-before" / re.sub(r"[^A-Za-z0-9._-]+", "_", title)[:60]
            if (work / "manifest.json").is_file():
                return                                   # the first copy is the state before the demaster's tools
            files: list[Path] = []
            if folder is not None and folder.is_dir():
                for here, _dirs, names in os.walk(folder):
                    files += [Path(here) / n for n in names]
                    if len(files) > TOOL_KEEP_FILES:
                        break
            files += [x for x in made if x.is_file() and x not in files]
            total = 0
            for f in files:
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
            work.mkdir(parents=True, exist_ok=True)
            record: dict = {"title": title, "folder": str(folder) if folder is not None else "", "files": [],
                            "when": time.strftime("%Y-%m-%dT%H:%M:%S")}
            if len(files) > TOOL_KEEP_FILES or total > TOOL_KEEP_BYTES:
                record["skipped"] = "%d file(s), %d MB: more than ModTrap keeps a copy of" % (len(files), total // (1024 * 1024))
                log.warn("“%s”: its output is too large to keep a copy of (%s). After a Revert, run it again.", title, record["skipped"])
            else:
                for i, f in enumerate(files):
                    copy = "%05d-%s" % (i + 1, f.name)
                    (work / "files").mkdir(exist_ok=True)
                    shutil.copy2(f, work / "files" / copy)
                    record["files"].append({"path": str(f), "copy": copy, "sha256": safe.sha256(f)})
                log.info("“%s”: a copy of its output as it is now (%d file(s)) is kept with the demaster, for Revert", title, len(files))
            paths.write_atomic(work / "manifest.json", (json.dumps(record, indent=1) + "\n").encode("utf-8"))
        except Exception as e:
            log.warn("a copy of “%s”'s output could not be kept for Revert: %s", title, logbook.why(e))

    def _tools_back(self, work: Path) -> dict:
        """Puts back each tool's output that was kept before ModTrap started the tool (`before_tool`): files changed
        since are replaced by the kept ones, files the run added are set aside. What was too large to keep is named."""
        out = {"titles": [], "not_kept": [], "aside": 0}
        base = work / "tool-before"
        try:
            kept = sorted((d for d in base.iterdir() if (d / "manifest.json").is_file()), reverse=True)
        except OSError:
            return out
        for d in kept:
            try:
                with open(d / "manifest.json", "rb") as f:
                    rec = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
            except (OSError, ValueError):
                continue
            title = str(rec.get("title", d.name))
            if rec.get("skipped"):
                out["not_kept"].append(title)
                continue
            aside = work / "set-aside-by-revert" / d.name
            known = set()
            changed = 0
            for item in rec.get("files", []):
                p = Path(item["path"])
                known.add(str(p))
                try:
                    if p.is_file() and safe.sha256(p) == item["sha256"]:
                        continue
                    if p.is_file():
                        self._aside(p, aside)
                        out["aside"] += 1
                    p.parent.mkdir(parents=True, exist_ok=True)
                    tmp = p.with_name(p.name + ".modtrap-revert")
                    shutil.copy2(d / "files" / item["copy"], tmp)
                    os.replace(tmp, p)
                    changed += 1
                except OSError as e:
                    log.warn("%s of “%s” could not be put back: %s", p.name, title, logbook.why(e))
            folder = Path(rec["folder"]) if rec.get("folder") else None
            if folder is not None and folder.is_dir():
                for here, _dirs, names in os.walk(folder):
                    for n in names:
                        p = Path(here) / n
                        if str(p) not in known:               # the run added it: out of the way, kept
                            try:
                                self._aside(p, aside)
                                p.unlink()
                                out["aside"] += 1
                                changed += 1
                            except OSError as e:
                                log.warn("%s of “%s” could not be set aside: %s", n, title, logbook.why(e))
            out["titles"].append(title)
            log.info("“%s”: its output is put back as it was before the demaster (%d file(s) changed back or set aside)", title, changed)
        return out

    def _drop(self, why: str) -> None:
        """Forgets the demaster in hand that was not put in place. Its files stay in its job folder; nothing in
        the modlist was changed by it."""
        if self.dm is not None and self.dm_state == "verified":
            log.info("the demaster that was waiting to be put in place is dropped: %s. Nothing of it was in the "
                     "modlist; run “Demaster Selected” again when you want it.", why)
        self.dm, self.dm_state, self.dm_check, self.dm_message = None, "", None, ""
        process.BOARD.drop("change", "install")           # the Process tab starts these over (WHY§71)

    def demaster_drop(self, body: dict) -> dict:
        with self._lock:
            if self.dm_state == "working":
                raise Bad("the demaster is still running; wait for it to end")
            if self.dm_state in ("verified", "failed"):
                self._drop("you said not now")
        return self.demaster_public()

    def demaster_public(self) -> dict:
        dm = self.dm
        # New plugins that wait to be put in place were made for the modlist as it was read then. Once it has
        # been read again (a Rescan, an add, a Revert, a change in MO2) they are no longer offered (WHY§62).
        if dm is not None and self.dm_state == "verified" and self.api.status == "ready" \
                and self.api.model is not None and dm.model is not self.api.model:
            self._drop("the modlist has been read again since")
            dm = None
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
        if path == "/api/demaster/drop":
            return self.demaster_drop(body)
        if path == "/api/demaster/retire":
            return self.demaster_retire(body)
        if path == "/api/jobs/clear":
            return self.jobs_clear(body)
        if path == "/api/add/plan":
            return self.plan(body)
        if path == "/api/add/run":
            return self.run(body)
        return self.revert(body)
