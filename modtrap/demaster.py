"""The demaster itself (DESIGN§6.3 to DESIGN§6.5): from a finished dry run to a modlist in which the ticked mods are
disabled and nothing misses a master, and back again with Revert.

BEHIND A SWITCH THAT IS OFF. The page reaches this module only through modtrap/changes.py, which is loaded only
when ModTrap is started with --allow-changes (WHY§39, WHY§46). It is built and tested against a stand-in for
xEdit; before the switch is used for real, ModTrap's read-only script must have run on a real modlist, and this
module's own script (ModTrapApply.pas) on the probe's invented plugins.

The order, and what each step may touch:
  1. plan       from the dry run's result: what to take out of each dependant, which patches to switch off
  2. safe       copies of every dependant and of the profile's three lists (MT14)
  3. xEdit      changes the dependants in memory, writes finished plugins into the job's own folder
  4. verify     each new plugin, with ModTrap's own reader; every original must be unchanged
  5. install    MO2 closed: a ModTrap mod with the new plugins on top of the list, the ticked mods disabled, the
                patch-only plugins deactivated; each change into the history
  6. check      the modlist read again: no active plugin may miss a master
  7. revert     at any time after 5: everything back as it was
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import dryrun, history, instance, logbook, model, paths, plugin, profile, safe
from .instance import fold

SCRIPT = Path(__file__).resolve().parent / "xedit" / "ModTrapApply.pas"
MOD_PREFIX = "ModTrap - "
log = logbook.get("demaster")


class Refused(Exception):
    """The demaster cannot go on; the text says why, in words for the page."""


@dataclass
class Plan:
    trapped_mods: list[str]
    trapped: list[str]                               # trapped plugins
    demaster: dict[str, list[str]]                   # dependant -> actions for the script, in order
    switch_off: list[str]                            # patch-only plugins: deactivated, not demastered
    needs_you: list[str]                             # dependants ModTrap will not touch
    mod_name: str                                    # ModTrap's own mod for the new plugins
    notes: list[str] = field(default_factory=list)
    disable_mods: list[str] = field(default_factory=list)    # patch mods made for the trapped mods: disabled whole

    @property
    def blocked(self) -> bool:
        """With a dependant left that still needs a ticked plugin, the mods cannot be disabled."""
        return bool(self.needs_you)


def actions_for(file_result: dict) -> list[str]:
    """What the script is to do in one dependant, from the dry run's reading of it (MT4): take out entries of
    lists, put back or take out parts it only carries on from the mod, and take out its copies of the trapped
    plugins' own records. Entries go first, the later ones first, so that taking one out does not move the next;
    parts are named, not counted, so they come after; whole records last."""
    records, entries, parts = [], {}, {}
    for rec in file_result["items"]:
        if rec["would"] == "record":
            records.append("%s|R" % rec["form"])
        elif rec["would"] in ("entry", "part"):
            for e in rec["elements"]:
                if e["would"] == "entry":
                    if not e.get("route"):
                        raise Refused("the dry run did not say where an entry of %s is" % rec["form"])
                    entries[(rec["form"], tuple(e["route"]))] = e["entry"]
                elif e["would"] == "part" and e.get("action") in ("put back", "take out") and e.get("from"):
                    if "|" in e["part"] or "|" in e["from"]:
                        raise Refused("a name in %s cannot be passed to the script" % rec["form"])
                    parts[(rec["form"], e["part"])] = "%s|%s|%s|%s" % (
                        rec["form"], "P" if e["action"] == "put back" else "X", e["part"], e["from"])
                else:
                    raise Refused("the dry run did not say what to do about a part of %s" % rec["form"])
        else:
            raise Refused("a record that needs the owner is not something ModTrap takes out")
    ordered = sorted(entries.items(), key=lambda kv: (kv[0][0], tuple(-i for i in kv[0][1])))
    return (["%s|E|%s|%s" % (form, "/".join(str(i) for i in route), name) for (form, route), name in ordered]
            + list(parts.values()) + records)


def plan(m: model.Model, dry: dict, mod_name: str = "") -> Plan:
    """The plan from a dry run's public state (`dryrun.Job.public()`)."""
    if dry.get("state") != "done" or not dry.get("result") or dry.get("unchanged") is not True:
        raise Refused("a finished dry run is needed first")
    p, result = dry["plan"], dry["result"]
    out = Plan(trapped_mods=list(p["trapped_mods"]), trapped=list(p["trapped"]), demaster={}, switch_off=[],
               needs_you=[], mod_name=mod_name or MOD_PREFIX + " + ".join(p["trapped_mods"])[:80])
    seen = {fold(f["name"]) for f in result["files"]}
    for name in p["dependants"]:
        if fold(name) not in seen:
            out.needs_you.append(name)
            out.notes.append("%s was not read by the dry run" % name)
    for f in result["files"]:
        r = m.row(f["name"])
        if r is None or r.path is None:
            raise Refused("%s is no longer in the modlist; run the dry run again" % f["name"])
        if f["reading"] == "patch only":
            out.switch_off.append(r.name)
        elif f["reading"] == "can be demastered":
            out.demaster[r.name] = actions_for(f)
        else:
            out.needs_you.append(r.name)
    # A mod that is all, or nearly all, patches for the trapped mods is disabled whole, as a person would, so that
    # its loose files go with its plugins (DESIGN§5, WHY§28, WHY§52). A patch among others in a collection is only
    # deactivated.
    off = {fold(n) for n in out.switch_off}
    for name in out.trapped_mods:
        trapped_mod = m.instance.mod(name)
        for g in model.groups(m, trapped_mod) if trapped_mod else []:
            if g.reading in ("whole mod", "most of the mod") and all(fold(r.name) in off for r in g.dependants) \
                    and g.mod.enabled and g.mod.name not in out.disable_mods and g.mod.name not in out.trapped_mods:
                out.disable_mods.append(g.mod.name)
                if g.leftover:
                    out.notes.append("%s is disabled whole; it also holds %s, which does not need the mod" % (
                        g.mod.name, ", ".join(g.leftover)))
    if not out.demaster and not out.switch_off:
        raise Refused("the dry run found nothing ModTrap can do by itself")
    return out


class Demaster:
    """One demaster job. Each step is a method, called in order by the caller; each refuses if the one before it
    has not been done. `closed` answers whether MO2 is closed (True), open (False) or cannot be told (None)."""

    def __init__(self, m: model.Model, dry_plan: dryrun.Plan, pl: Plan, job_dir: Path, session_dir: Path, *,
                 launcher: Callable = dryrun.launch, running: Callable = dryrun.image_running,
                 closed: Callable[[], bool | None] | None = None, poll: float = 1.0,
                 closer: Callable[[str, bool], None] = dryrun.close_program,
                 presser: Callable[[str], bool] = dryrun.winauto.press_module_selection_ok):
        self.model, self.dry_plan, self.plan, self.dir = m, dry_plan, pl, job_dir
        self.inst = m.instance
        self.pdir = self.inst.profiles_dir / self.inst.profile
        self.safe = safe.Safe(job_dir / "safe")
        self.history = history.History(session_dir)
        self.out = job_dir / "out"
        self._launcher, self._running, self._poll, self._closer = launcher, running, poll, closer
        self._presser = presser
        self._closed = closed or (lambda: None if running(dryrun.MO2_EXE) is None else not running(dryrun.MO2_EXE))
        self.report: dict = {}
        self.written: list[str] = []
        self.stage = "new"            # new, safe, changed, verified, installed, reverted

    # --- 2. safe ---------------------------------------------------------------------------------------------------

    def make_safe(self) -> None:
        for name in list(self.plan.demaster) + self.plan.switch_off:
            self.safe.take(self.model.row(name).path)
        for fname in ("modlist.txt", "plugins.txt", "loadorder.txt"):
            if (self.pdir / fname).is_file():
                self.safe.take(self.pdir / fname)
        self.stage = "safe"
        log.info("the safe folder holds %d file(s)", len(self.safe.items))

    # --- 3. xEdit --------------------------------------------------------------------------------------------------

    def prepare(self) -> list[str]:
        if self.stage != "safe":
            raise Refused("the safe folder comes first")
        script_dir = self.dir / "script"
        script_dir.mkdir(parents=True, exist_ok=True)
        self.out.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCRIPT, script_dir / SCRIPT.name)
        deps = list(self.plan.demaster)
        lines = ["format=modtrap-job/1", "mode=apply", "out=%s" % (self.dir / "report.tsv"),
                 "progress=%s" % (self.dir / "progress.txt"), "outdir=%s" % (str(self.out) + "\\" if "\\" in str(self.out)
                                                                             else str(self.out) + "/"),
                 "trap.count=%d" % len(self.plan.trapped)]
        lines += ["trap.%d=%s" % (i, n) for i, n in enumerate(self.plan.trapped)]
        lines += ["dep.count=%d" % len(deps)]
        for i, name in enumerate(deps):
            acts = self.plan.demaster[name]
            lines += ["dep.%d=%s" % (i, name), "do.%d.count=%d" % (i, len(acts))]
            lines += ["do.%d.%d=%s" % (i, k, a) for k, a in enumerate(acts)]
        paths.write_atomic(script_dir / "modtrap-job.txt", ("\r\n".join(lines) + "\r\n").encode("utf-8-sig"))
        primary = {fold(x) for x in self.inst.primary}
        listed = ["*" + n for n in self.dry_plan.load if fold(n) not in primary]
        paths.write_atomic(self.dir / "plugins.txt", ("\r\n".join(listed) + "\r\n").encode("cp1252", "replace"))
        return dryrun.command(self.dry_plan, self.dir, SCRIPT.name)

    def run_xedit(self, time_limit: float = dryrun.TIME_LIMIT) -> None:
        cmd = self.prepare()
        image = Path(self.dry_plan.tool_binary.replace("\\", "/")).name
        if self._running(image):
            raise Refused("%s is already running: close it first" % image)
        log.info("starting xEdit through MO2 with ModTrap's script: %d dependant(s) to change, in memory only",
                 len(self.plan.demaster))
        mo2_was_running = self._running(dryrun.MO2_EXE)
        proc = self._launcher(cmd, str(Path(self.dry_plan.mo2).parent))
        started, seen, report = time.time(), 0, self.dir / "report.tsv"
        ok = dryrun.OkPresser(image, self._presser)
        while True:
            time.sleep(self._poll)
            if seen == 0:
                ok.look()
            lines = dryrun._lines(self.dir / "progress.txt")
            for ln in lines[seen:]:
                log.info("xEdit: %s", ln)
            seen = len(lines)
            if dryrun._ended(report):
                break
            if proc.poll() is not None and self._running(image) is False and time.time() - started > dryrun.GONE_GRACE:
                raise Refused("xEdit closed before the script finished; nothing was installed")
            if time.time() - started > time_limit:
                raise Refused("xEdit took too long; nothing was installed")
        self.report = parse_report(dryrun._read(report))
        # The script has written its new files and taken the "changed" marks off. xEdit stays open after a script
        # (XE01§11): it is asked to close, and ended if it does not, so that it cannot save anything (WHY§4).
        dryrun.close_xedit(image, self._running, self._closer, self._poll, changed=True,
                           mo2_was_running=mo2_was_running)
        self.stage = "changed"

    # --- 4. verify -------------------------------------------------------------------------------------------------

    def verify(self) -> list[str]:
        """The new plugins that pass every check, by name. One that fails is not installed, and its dependant
        counts as still needing the owner."""
        if self.stage != "changed":
            raise Refused("xEdit has not run")
        if self.report.get("end") != "ok":
            raise Refused("the script reported a failure: %s" % (self.report.get("reason") or "no reason given"))
        for item in self.safe.items:                               # no original may have changed (DESIGN§8)
            p = Path(item["path"])
            if not p.is_file() or safe.sha256(p) != item["sha256"]:
                raise Refused("%s is not the file it was before xEdit ran. Nothing was installed; its original is in "
                              "the safe folder." % p.name)
        tf = {fold(t) for t in self.plan.trapped}
        good = []
        for name in self.plan.demaster:
            why = ""
            info = self.report["files"].get(fold(name), {})
            new = self.out / name
            if name not in self.report["written"] or not new.is_file():
                why = info.get("kept") or "the script did not write it"
            else:
                try:
                    h = plugin.read(new)
                except plugin.Unreadable as e:
                    why = "the new file cannot be read: %s" % e
                else:
                    still = [x for x in h.masters if fold(x) in tf]
                    gone = [x for x in h.masters if (r := self.model.row(x)) is None or r.source is None or not r.active]
                    before = self.model.row(name)
                    added = [x for x in h.masters if fold(x) not in {fold(y) for y in before.masters}]
                    if still:
                        why = "it still lists %s as a master" % ", ".join(still)
                    elif gone:
                        why = "it lists a master that is missing or not active: %s" % ", ".join(gone)
                    elif added:
                        why = "it lists a master it did not have before: %s" % ", ".join(added)
                    elif info.get("remaining", 0) != 0:
                        why = "xEdit still found %d record(s) needing a trapped plugin" % info["remaining"]
            if why:
                log.warn("%s is not installed: %s", name, why)
                self.plan.needs_you.append(name)
                self.plan.notes.append("%s: %s" % (name, why))
            else:
                good.append(name)
        self.written = good
        self.stage = "verified"
        return good

    # --- 5. install ------------------------------------------------------------------------------------------------

    def install(self) -> dict:
        if self.stage != "verified":
            raise Refused("the new plugins have not been verified")
        if self._closed() is not True:
            raise Refused("MO2 must be closed while ModTrap changes the mod list: an open MO2 would write its own "
                          "copy back over it. Close MO2, then go on.")
        mod_dir = self.inst.mods_dir / self.plan.mod_name
        if mod_dir.exists():
            raise Refused("a mod called '%s' already exists; ModTrap never overwrites one" % self.plan.mod_name)
        done: dict = {"mod": self.plan.mod_name, "plugins": [], "disabled": [], "deactivated": []}
        try:
            if self.written:
                mod_dir.mkdir()
                for name in self.written:
                    shutil.copyfile(self.out / name, mod_dir / name)
                    if safe.sha256(mod_dir / name) != safe.sha256(self.out / name):
                        raise Refused("%s did not copy whole into ModTrap's mod" % name)
                    self.safe.created(mod_dir / name)
                    r = self.model.row(name)
                    done["plugins"].append(name)
                    self.history.add("plugin demastered", plugin=name, position=r.position, plugin_kind=r.kind,
                                     mod=r.source, mod_priority=r.source_priority, now_in=self.plan.mod_name,
                                     masters_before=list(r.masters), masters_after=list(plugin.read(mod_dir / name).masters))
                self.safe.may_change(self.pdir / "modlist.txt")
                ch = profile.add_mod_on_top(self.pdir, self.plan.mod_name)
                self.safe.wrote(self.pdir / "modlist.txt")       # noted at once: a later failure must be able to undo it
                self.history.add("mod added", mod=self.plan.mod_name, priority=ch.lines[0]["priority"],
                                 plugins=[{"name": n} for n in self.written])
            off = [x for x in self.plan.switch_off]
            if off:
                self.safe.may_change(self.pdir / "plugins.txt")
                profile.set_plugins(self.pdir, {n: False for n in off})
                self.safe.wrote(self.pdir / "plugins.txt")
                for n in off:
                    r = self.model.row(n)
                    done["deactivated"].append(n)
                    self.history.add("plugin deactivated", plugin=n, position=r.position, plugin_kind=r.kind,
                                     mod=r.source, mod_priority=r.source_priority, why="a patch made only for the mod")
            if self.plan.disable_mods:
                self.safe.may_change(self.pdir / "modlist.txt")
                profile.set_mods(self.pdir, {n: False for n in self.plan.disable_mods})
                self.safe.wrote(self.pdir / "modlist.txt")
                for n in self.plan.disable_mods:
                    mod = self.inst.mod(n)
                    done["disabled"].append(n)
                    self.history.add("mod disabled", mod=n, priority=mod.priority, why="patches made only for the mod",
                                     plugins=[{"name": r.name, "position": r.position, "kind": r.kind}
                                              for r in self.model.provided_by(mod)])
            if not self.plan.blocked:
                self.safe.may_change(self.pdir / "modlist.txt")
                profile.set_mods(self.pdir, {n: False for n in self.plan.trapped_mods})
                self.safe.wrote(self.pdir / "modlist.txt")
                for n in self.plan.trapped_mods:
                    mod = self.inst.mod(n)
                    done["disabled"].append(n)
                    self.history.add("mod disabled", mod=n, priority=mod.priority, plugins=[
                        {"name": r.name, "position": r.position, "kind": r.kind} for r in self.model.provided_by(mod)])
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            log.error("installing stopped: %s; putting everything back", e if not isinstance(e, OSError) else logbook.why(e))
            self.safe.revert(overwrite_foreign=False)
            self.history.add("reverted", why="installing stopped part way")
            self.stage = "reverted"
            raise Refused("installing stopped and everything was put back: %s" % (
                e if not isinstance(e, OSError) else logbook.why(e))) from None
        self.stage = "installed"
        paths.write_atomic(self.dir / "installed.json", (json.dumps(done, indent=1) + "\n").encode("utf-8"))
        return done

    # --- 6. check --------------------------------------------------------------------------------------------------

    def check(self) -> dict:
        """The modlist read again from disk: what the health check says now, and whether any problem has to do
        with the ticked plugins."""
        m = model.build(instance.load(self.inst.root, self.inst.profile))
        tf = {fold(t) for t in self.plan.trapped}
        ours = [i for i in m.issues if fold(i.master) in tf or fold(i.plugin) in {fold(n) for n in self.written}]
        before = {(fold(i.plugin), fold(i.master)) for i in self.model.issues}
        new = [i for i in m.issues if (fold(i.plugin), fold(i.master)) not in before]
        ok = not ours and not new and (self.plan.blocked or all(not m.instance.mod(n).enabled for n in self.plan.trapped_mods))
        self.history.add("verified", ok=ok, problems=[[i.plugin, i.master, i.what] for i in new],
                         still_needs_you=list(self.plan.needs_you))
        return {"ok": ok, "new_problems": [[i.plugin, i.master, i.what] for i in new],
                "needs_you": list(self.plan.needs_you), "disabled": not self.plan.blocked}

    # --- 7. revert -------------------------------------------------------------------------------------------------

    def revert(self, overwrite_foreign: bool = False) -> dict:
        if self._closed() is not True:
            raise Refused("MO2 must be closed while ModTrap puts the mod list back")
        try:
            what = self.safe.revert(overwrite_foreign)
        except safe.Refused:
            try:
                with open(self.dir / "installed.json", "rb") as f:
                    done = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
            except (OSError, ValueError):
                raise Refused("the lists changed since, and this job's record cannot be read") from None
            what = undo_by_line(self.pdir, self.safe, done)
        self.history.add("reverted", restored=[Path(p).name for p in what["restore"]],
                         removed=[Path(p).name for p in what["remove"]])
        self.stage = "reverted"
        return what


def undo_by_line(profile_dir: Path, the_safe: safe.Safe, done: dict) -> dict:
    """Revert for a demaster whose lists were changed since by something else, as MO2 does whenever it runs
    (DESIGN§11): instead of putting the old files back, which would undo that too, only ModTrap's own changes are
    taken back: the mods it disabled are enabled, the plugins it deactivated are activated, its own mod's line is
    taken out of the list, and the plugins it wrote are removed if they are still as written. `done` is what the
    install recorded."""
    notes = []
    for name in done.get("disabled", []):
        try:
            profile.set_mods(profile_dir, {name: True})
        except profile.Refused as e:
            notes.append(str(e))
    for name in done.get("deactivated", []):
        try:
            profile.set_plugins(profile_dir, {name: True})
        except profile.Refused as e:
            notes.append(str(e))
    if done.get("mod"):
        try:
            profile.remove_mod_line(profile_dir, done["mod"])
        except profile.Refused as e:
            notes.append(str(e))
    left = the_safe.remove_added()
    the_safe.mark_reverted()
    return {"restore": [], "remove": [a["path"] for a in the_safe.added if a["path"] not in left], "left": left,
            "notes": notes, "how": "by line"}


def parse_report(text: str) -> dict:
    out: dict = {"format": "", "end": "", "reason": "", "files": {}, "written": [], "not_loaded": []}
    for line in text.split("\n"):
        f = line.rstrip("\r").split("\t")
        if f[0] == "H" and len(f) >= 2:
            out["format"] = f[1]
        elif f[0] == "A" and len(f) >= 5:
            d = out["files"].setdefault(fold(f[1]), {"actions": 0, "refused": []})
            d["actions"] += 1
            if f[4] != "ok":
                d["refused"].append("%s %s: %s" % (f[2], f[3], f[5] if len(f) > 5 else ""))
        elif f[0] == "C" and len(f) >= 5:
            d = out["files"].setdefault(fold(f[1]), {"actions": 0, "refused": []})
            d["masters"], d["remaining"], d["records"] = [x for x in f[2].split(",") if x], int(f[3] or 0), int(f[4] or 0)
        elif f[0] == "W" and len(f) >= 2:
            out["written"].append(f[1])
        elif f[0] == "K" and len(f) >= 3:
            out["files"].setdefault(fold(f[1]), {"actions": 0, "refused": []})["kept"] = f[2]
        elif f[0] == "M" and len(f) >= 2:
            out["not_loaded"].append(f[1])
        elif f[0] == "X" and len(f) >= 2:
            out["end"], out["reason"] = f[1], f[2] if len(f) > 2 else ""
    return out
