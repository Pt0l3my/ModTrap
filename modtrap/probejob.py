"""The probe (DESIGN§9, WHY§47): the whole of ModTrap's work, done once on invented plugins in the owner's own MO2
and xEdit, and undone again, before any real mod is touched.

Loaded only with --allow-changes (through modtrap/changes.py). It uses nothing of its own to change the modlist:
the same add job, dry run, demaster and Revert that real work uses, so that passing here says something about
them. The two test mods hold four tiny plugins written by ModTrap (modtrap/probe.py); nothing of a real mod is
read into them or changed.

Each step answers one thing that could not be shown without the owner's PC:
  write      ModTrap's own mods go into MO2, in place and enabled, their plugins active in order
  dry        xEdit starts through MO2, loads the invented plugins, and the reading script reports what is expected
  kept       after MO2 has run, the mod list and the load order are still as ModTrap wrote them
  apply      the changing script takes out exactly what was listed and writes a sound new plugin
  untouched  xEdit saved nothing over an original
  install    the demastered copy goes in place, the patch is switched off, the mod is disabled, the check is clean
  revert     everything is put back: the lists as before the probe, the test mods gone
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Callable

from . import adding, addjob, demaster, dryrun, instance, logbook, model, paths, plugin, probe
from . import process
from .instance import fold

log = logbook.get("probe")
BAD_MOD = "ModTrap Probe - Bad"
DEP_MOD = "ModTrap Probe - Dependants"
STEPS = (
    ("write", "ModTrap's two test mods go into MO2, in place and enabled"),
    ("dry", "xEdit starts through MO2, loads the invented plugins, and ModTrap's script reads them"),
    ("kept", "MO2 kept the mod list and the load order as ModTrap wrote them"),
    ("apply", "The changing script takes out what the dry run listed and writes a new plugin"),
    ("untouched", "xEdit saved nothing over an original"),
    ("install", "The demastered copy goes in place, the patch is switched off, the test mod is disabled"),
    ("revert", "Revert puts everything back, and the test mods are gone"),
)
CLOSE_WAIT = 30 * 60
CLEAN_WAIT = 90                 # seconds the clean-up after a failed probe waits for MO2 to close


class Failed(Exception):
    def __init__(self, step: str, why: str):
        super().__init__(why)
        self.step = step


def _lists(root: Path, profile: str) -> dict:
    """The mod list and both plugin lists as they read from disk now. Both plugin lists are compared: MO2 takes
    the order from the newer one (MO01§2), so either may be the one that counts."""
    inst = instance.load(root, profile)
    pdir = inst.profiles_dir / inst.profile

    def text(name: str) -> str:
        try:
            return instance._decode(instance._read_bytes(pdir / name))
        except OSError:
            return ""
    return {"mods": [(x.name, x.enabled) for x in inst.mods if x.kind in ("mod", "separator", "foreign")],
            "plugins": [(fold(n), a) for n, a in instance.parse_plugins(text("plugins.txt"))],
            "loadorder": [fold(n) for n in instance.parse_loadorder(text("loadorder.txt"))]}


class Probe:
    def __init__(self, m: model.Model, work: Path, session_dir: Path, *, launcher: Callable, running: Callable,
                 closed: Callable[[], bool | None], poll: float = 1.0, read=plugin.read,
                 closer: Callable[[str, bool], None] = dryrun.close_program,
                 presser: Callable[[str], bool] = dryrun.winauto.press_module_selection_ok):
        self.model, self.dir, self.session_dir = m, work, session_dir
        self.inst = m.instance
        self._launcher, self._running, self._closed, self._poll, self._read = launcher, running, closed, poll, read
        self._closer, self._presser = closer, presser
        self.state = "new"              # new, working, passed, failed
        self.now = ""
        self.results: dict[str, dict] = {}
        self.xedit = ""
        self.left_behind: list[str] = []
        self.message = ""
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.on_end: Callable[[], None] | None = None
        self._aj: addjob.AddJob | None = None
        self._dm: demaster.Demaster | None = None

    # --- for the page ------------------------------------------------------------------------------------------------

    def public(self) -> dict:
        return {"state": self.state, "now": self.now, "message": self.message, "xedit": self.xedit,
                "left_behind": self.left_behind,
                "steps": [{"key": k, "title": t, **self.results.get(k, {"result": "going" if self.now == k else ""})}
                          for k, t in STEPS]}

    def start(self) -> None:
        self.state = "working"
        self._thread = threading.Thread(target=self._run, name="probe", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    # --- the run -----------------------------------------------------------------------------------------------------

    def _ok(self, key: str, detail: str = "") -> None:
        self.results[key] = {"result": "passed", "detail": detail}
        log.info("probe: passed: %s%s", dict(STEPS)[key], (" (%s)" % detail) if detail else "")

    def _wait_closed(self, step: str) -> None:
        """MO2 must be closed for a write to its lists. After xEdit has run through MO2, MO2 closes by itself
        unless the owner had it open; then the probe waits for the owner to close it."""
        started = time.time()
        said = False
        while True:
            c = self._closed()
            if c is True:
                self.message = ""
                return
            if c is None:
                raise Failed(step, "ModTrap cannot tell whether MO2 is open on this PC, so it will not change its lists")
            if not said and time.time() - started > 5:
                said = True
                self.message = ("MO2 is still open. If it shows a message, press OK there; when MO2 has closed, the "
                                "probe goes on by itself.")
                log.warn("probe: waiting for MO2 to be closed")
            if self._stop.wait(max(self._poll, 0.05)) or time.time() - started > CLOSE_WAIT:
                raise Failed(step, "MO2 stayed open, so the probe stopped")

    def _run(self) -> None:
        before = None
        try:
            before = _lists(self.inst.root, self.inst.profile)
            self._do(before)
            self.state = "passed"
            log.info("probe: every step passed (xEdit %s)", self.xedit or "version not reported")
        except Failed as e:
            self.results[e.step] = {"result": "failed", "detail": logbook.mask(str(e))}
            self.state = "failed"
            log.error("probe: FAILED at “%s”: %s", dict(STEPS).get(e.step, e.step), e)
        except Exception as e:
            self.results[self.now or "write"] = {"result": "failed", "detail": "an error inside ModTrap: " + logbook.why(e)}
            self.state = "failed"
            log.error("probe: stopped by an error inside ModTrap: %s", logbook.why(e))
        if self.state == "failed":
            self._clean_up(before)
        self.now = ""
        try:
            paths.write_atomic(self.session_dir / "probe.json", (json.dumps(
                {"when": time.strftime("%Y-%m-%dT%H:%M:%S"), "ok": self.state == "passed", "xedit": self.xedit,
                 "scripts": scripts_mark(),
                 "tool": self._tool_binary(), "result": self.public()}, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        except (OSError, TypeError, ValueError) as e:
            log.warn("the probe's outcome could not be kept: %s", logbook.why(e))
        if self.on_end:
            try:
                self.on_end()
            except Exception as e:
                log.warn("after the probe: %s", logbook.why(e))

    def _tool_binary(self) -> str:
        try:
            return dryrun.find_xedit(self.inst)[1]
        except dryrun.Refused:
            return ""

    def _clean_up(self, before: dict | None) -> None:
        """After a failure: put back whatever the probe changed, if MO2 is closed. What cannot be put back is
        named; the test mods are harmless and say so in their plugins' descriptions."""
        try:
            end = time.time() + CLEAN_WAIT              # MO2 takes a moment to go once xEdit has closed
            while self._closed() is False and time.time() < end and not self._stop.is_set():
                time.sleep(max(self._poll, 0.05))
            if self._closed() is not True:
                raise addjob.Refused("MO2 is still open" if self._closed() is False else
                                     "it cannot be told on this PC whether MO2 is open")
            log.info("probe: MO2 is closed; putting back what the probe changed")
            if self._dm is not None and self._dm.stage == "installed":
                self._dm.revert()
            if self._aj is not None and self._aj.stage == "added":
                self._aj.revert()
        except Exception as e:
            log.warn("probe: could not put everything back by itself: %s", e if isinstance(e, (addjob.Refused, demaster.Refused)) else logbook.why(e))
        self.left_behind = [n for n in (BAD_MOD, DEP_MOD, self._dm.plan.mod_name if self._dm is not None else "")
                            if n and (self.inst.mods_dir / n).is_dir()]
        if self.left_behind:
            log.warn("probe: still in MO2's mods folder: %s. They are invented and safe to remove.", ", ".join(self.left_behind))

    def clean_up_again(self) -> list[str]:
        """Asked for from the page, once MO2 is closed: removes what a failed probe left."""
        self._clean_up(None)
        return self.left_behind

    def _do(self, before: dict) -> None:
        inst, m = self.inst, self.model
        # --- write ------------------------------------------------------------------------------------------------
        self.now = "write"
        for n in (BAD_MOD, DEP_MOD):
            if inst.mod(n) is not None or (inst.mods_dir / n).exists():
                raise Failed("write", "a mod called “%s” is already in MO2, left by an earlier probe: remove it in MO2 "
                             "(it is invented and safe to remove), then run the probe again" % n)
        self._wait_closed("write")
        files = probe.probe_set()
        probe.check_headers(files)
        staged = self.dir / "staged"
        # Base stays when Bad's mod is disabled, so it lives with the dependants.
        for mod_name, names in ((BAD_MOD, (probe.BAD,)), (DEP_MOD, (probe.BASE, probe.OVERRIDE, probe.PATCH))):
            (staged / mod_name).mkdir(parents=True, exist_ok=True)
            for n in names:
                (staged / mod_name / n).write_bytes(files[n])
        extra = [adding.staged_mod(BAD_MOD, staged / BAD_MOD), adding.staged_mod(DEP_MOD, staged / DEP_MOD)]
        rep = adding.analyse(m, [], read=self._read, staged=extra, seconds=5.0)
        try:
            pl = addjob.plan(m, rep, {n: {"root": str(staged / n), "archive": ""} for n in (BAD_MOD, DEP_MOD)})
            self._aj = addjob.AddJob(inst, m, pl, self.dir / "add", self.session_dir, self._closed)
            done = self._aj.run()
        except addjob.Refused as e:
            raise Failed("write", str(e)) from None
        written = _lists(inst.root, inst.profile)
        self._ok("write", "%d mods, %d plugins" % (len(done["mods"]), len(done["plugins"])))

        # --- dry --------------------------------------------------------------------------------------------------
        self.now = "dry"
        m2 = model.build(instance.load(inst.root, inst.profile), read=self._read)
        try:
            dp = dryrun.plan(m2, [BAD_MOD])
        except dryrun.Refused as e:
            raise Failed("dry", str(e)) from None
        job = dryrun.Job(m2, dp, self.dir / "dry", launcher=self._launcher, running=self._running, poll=self._poll,
                         closer=self._closer, presser=self._presser)
        job.board = process.Board()          # the probe has its own box on the Process tab: its steps (WHY§70)
        (self.dir / "dry").mkdir(parents=True, exist_ok=True)
        job.start()
        while job.state not in ("done", "failed", "stopped"):
            if self._stop.wait(max(self._poll, 0.05)):
                job.stop()
        job.join(30)
        if job.state != "done":
            raise Failed("dry", job.message or "the dry run did not finish")
        self.xedit = str(job.result.get("xedit", ""))
        got = {f["name"]: f for f in job.result["files"]}
        wrong = []
        for name, want in probe.EXPECTED.items():
            f = got.get(name)
            if f is None:
                wrong.append("%s was not read" % name)
                continue
            for key in ("records", "own", "entries", "parts", "needs_you", "reading"):
                if f[key] != want[key]:
                    extra_words = ""
                    if key in ("entries", "parts", "needs_you", "reading"):
                        arrays = sorted({e["array"] or e["path"] for r in f["items"] for e in r["elements"]})
                        extra_words = "; xEdit names the list %s" % ", ".join("“%s”" % a for a in arrays) if arrays else ""
                    wrong.append("%s: %s is %r, expected %r%s" % (name, key, f[key], want[key], extra_words))
        if wrong:
            raise Failed("dry", "xEdit read the invented plugins, but not as expected: " + "; ".join(wrong[:4]))
        self._ok("dry", "xEdit version %s" % self.xedit if self.xedit else "")

        # --- kept -------------------------------------------------------------------------------------------------
        self.now = "kept"
        self._wait_closed("kept")
        after_mo2 = _lists(inst.root, inst.profile)
        diffs = []
        if after_mo2["mods"] != written["mods"]:
            moved = [n for (n, e), (n2, e2) in zip(after_mo2["mods"], written["mods"]) if (n, e) != (n2, e2)]
            diffs.append("the mod list differs (first at “%s”)" % (moved[0] if moved else "its length"))
        if after_mo2["plugins"] != written["plugins"]:
            moved = [n for (n, a), (n2, a2) in zip(after_mo2["plugins"], written["plugins"]) if (n, a) != (n2, a2)]
            diffs.append("the load order differs in plugins.txt (first at %s)" % (moved[0] if moved else "its length"))
        if after_mo2["loadorder"] != written["loadorder"]:
            moved = [n for n, n2 in zip(after_mo2["loadorder"], written["loadorder"]) if n != n2]
            diffs.append("the load order differs in loadorder.txt (first at %s)" % (moved[0] if moved else "its length"))
        if diffs:
            raise Failed("kept", "after MO2 had run, " + " and ".join(diffs) + ". ModTrap must not write these lists "
                         "on this PC until that is understood.")
        self._ok("kept")

        # --- apply, untouched -------------------------------------------------------------------------------------
        self.now = "apply"
        try:
            dpl = demaster.plan(m2, job.public())
        except demaster.Refused as e:
            raise Failed("apply", str(e)) from None
        if sorted(dpl.demaster) != [probe.OVERRIDE] or dpl.switch_off != [probe.PATCH] or dpl.needs_you:
            raise Failed("apply", "the plan from the dry run is not the expected one")
        self._dm = demaster.Demaster(m2, dp, dpl, self.dir / "demaster", self.session_dir, launcher=self._launcher,
                                     running=self._running, closed=self._closed, poll=self._poll, closer=self._closer,
                                     presser=self._presser)
        self._dm.board = process.Board()
        (self.dir / "demaster").mkdir(parents=True, exist_ok=True)
        try:
            self._dm.make_safe()
            self._dm.run_xedit()
            good = self._dm.verify()
        except demaster.Refused as e:
            step = "untouched" if "not the file it was" in str(e) else "apply"
            raise Failed(step, str(e)) from None
        if good != [probe.OVERRIDE]:
            raise Failed("apply", "the new plugin did not pass ModTrap's checks: " + "; ".join(dpl.notes[:3]))
        new = self._read(self._dm.out / probe.OVERRIDE)
        if list(new.masters) != probe.EXPECTED[probe.OVERRIDE]["masters_after"]:
            raise Failed("apply", "the new plugin's masters are %s, expected only %s" % (
                ", ".join(new.masters) or "none", probe.BASE))
        try:
            data = (self._dm.out / probe.OVERRIDE).read_bytes()
        except OSError as e:
            raise Failed("apply", "the new plugin could not be read: %s" % logbook.why(e)) from None
        if probe.PARENT_BACK not in data or probe.PARENT_BAD in data:
            raise Failed("apply", "the part carried on from the test mod was not put back as %s has it" % probe.BASE)
        self._ok("apply", "the new %s no longer names the test mod, and the part it carried on is as %s has it" % (
            probe.OVERRIDE, probe.BASE))
        self._ok("untouched")

        # --- install ----------------------------------------------------------------------------------------------
        self.now = "install"
        self._wait_closed("install")
        try:
            self._dm.install()
            chk = self._dm.check()
        except demaster.Refused as e:
            raise Failed("install", str(e)) from None
        if not chk["ok"]:
            raise Failed("install", "the health check after installing is not clean: %s" % (
                "; ".join("%s needs %s" % (a, b) for a, b, _ in chk["new_problems"][:3]) or "the test mod is still enabled"))
        self._ok("install")

        # --- revert -----------------------------------------------------------------------------------------------
        self.now = "revert"
        try:
            self._dm.revert()
            got_back = self._aj.revert()
        except (demaster.Refused, addjob.Refused) as e:
            raise Failed("revert", str(e)) from None
        left = [n for n in (BAD_MOD, DEP_MOD, dpl.mod_name) if (inst.mods_dir / n).exists()] + got_back["left"]
        if left:
            raise Failed("revert", "still there after Revert: %s" % ", ".join(sorted(set(left))))
        if _lists(inst.root, inst.profile) != before:
            raise Failed("revert", "the mod list or the load order is not what it was before the probe")
        self._ok("revert")


def scripts_mark() -> str:
    """A mark of ModTrap's own xEdit scripts as they are now. The probe proves these scripts on the owner's xEdit,
    so a pass counts only for the scripts it ran (WHY§53)."""
    h = hashlib.sha256()
    for f in sorted((Path(__file__).parent / "xedit").glob("*.pas")):
        h.update(f.name.encode("utf-8") + b"\0" + f.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()[:16]


def passed(session_dir: Path, inst: instance.Instance) -> str:
    """Why real work is not allowed yet, or "" when the probe has passed for this modlist with this xEdit and
    these scripts."""
    try:
        with open(session_dir / "probe.json", "rb") as f:
            data = json.loads(f.read(4 * 1024 * 1024).decode("utf-8"))
    except (OSError, ValueError):
        return "the probe has not been run on this modlist yet: run it on the Tools tab first"
    if not isinstance(data, dict) or data.get("ok") is not True:
        return "the probe did not pass on this modlist: see the Tools tab"
    try:
        tool = dryrun.find_xedit(inst)[1]
    except dryrun.Refused:
        tool = ""
    if data.get("tool") != tool:
        return "the xEdit set up in MO2 is not the one the probe passed with: run the probe again"
    if data.get("scripts") != scripts_mark():
        return "ModTrap's xEdit scripts have changed since the probe passed: run the probe again (Tools tab)"
    return ""


__all__ = ["Probe", "passed", "BAD_MOD", "DEP_MOD", "STEPS"]
