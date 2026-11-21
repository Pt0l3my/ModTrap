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

from . import addjob, dryrun, logbook
from .server import Bad

log = logbook.get("add")
PATHS = ("/api/add/plan", "/api/add/run", "/api/add/revert")


class Changes:
    PATHS = PATHS

    def __init__(self, api) -> None:
        self.api = api
        self._lock = threading.Lock()

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

    def post(self, path: str, body: dict) -> dict:
        if path == "/api/add/plan":
            return self.plan(body)
        if path == "/api/add/run":
            return self.run(body)
        return self.revert(body)
