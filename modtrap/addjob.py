"""Carrying out the adding of mods (MT21, DESIGN§16.8): putting an unpacked mod into MO2's mods folder, the mod in
its place in the mod list, its plugins in their place in the load order, and the way back.

NOT USED. Nothing the page can call reaches this module (a test checks that): it is built and tested ahead of the
day ModTrap is allowed to change a modlist (WHY§36, WHY§42). What it does when it is used, in order:

  plan      from the analysis (adding.analyse): refused while anything the mods need is missing;
  run       with MO2 closed: the profile's three lists into the safe folder (MT14); each unpacked mod copied into
            MO2's mods folder, never over an existing one; each mod placed and enabled; each plugin placed and
            activated; the modlist read again and checked. Any failure puts everything back;
  revert    the three lists as they were, and ModTrap's own copies of the mods removed if they are still as copied.

Every change goes into the history (MT15), with priorities and positions. No mod is ever deleted but a copy
ModTrap itself made in the same job (MT9).
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import history as history_mod, instance, logbook, model, paths, profile, safe, sources
from .instance import fold

log = logbook.get("add")
LISTS = ("modlist.txt", "plugins.txt", "loadorder.txt")


class Refused(Exception):
    """The job does not go on; the text says why, in words for the page."""


@dataclass
class Plan:
    mods: list[dict] = field(default_factory=list)       # {"name", "before", "staged", "root", "archive", "enabled",
                                                         #  "updates": the mod it is a newer version of, "replaces": that
                                                         #  mod where it is enabled now and is to be disabled (MT40)}
    plugins: list[dict] = field(default_factory=list)    # {"name", "before", "kind", "mod"}
    lists: dict[str, str] = field(default_factory=dict)  # the three lists' checksums when the plan was made

    def public(self) -> dict:
        return {"mods": [{k: v for k, v in x.items() if k != "root"} for x in self.mods], "plugins": self.plugins}


def plan(m: model.Model, report: dict, staged: dict[str, dict] | None = None) -> Plan:
    """What "Add it" would do, from the analysis. `staged` maps an unpacked mod's name to {"root", "archive"}."""
    staged = staged or {}
    needs = next((s for s in report.get("steps", []) if s["key"] == "needs"), None)
    if not report.get("mods"):
        raise Refused("there is nothing to add")
    if needs is None or needs["state"] != "done":
        raise Refused("not everything the mods need is there yet: " + "; ".join(
            i["text"] for i in (needs["items"] if needs else [])[:4]))
    inst = m.instance
    p = Plan()
    before = report["place"]["before"]
    for x in report["mods"]:
        if x.get("staged"):
            src = staged.get(x["name"])
            if src is None or not Path(src["root"]).is_dir():
                raise Refused("the unpacked copy of '%s' is no longer in ModTrap's work folder" % x["name"])
            if (inst.mods_dir / x["name"]).exists() or inst.mod(x["name"]) is not None:
                raise Refused("MO2 already has a mod called '%s'; ModTrap never overwrites one" % x["name"])
            old = x.get("updates") or ""
            if old and inst.mod(old) is None:
                raise Refused("'%s', which '%s' is a newer version of, is no longer in the modlist" % (old, x["name"]))
            p.mods.append({"name": x["name"], "before": x.get("own_before", "") if old else before, "staged": True, "root": str(src["root"]),
                           "archive": src.get("archive", ""), "enabled": False, "meta": src.get("meta") or {}, "updates": old,
                           "replaces": old if old and x.get("updates_enabled") else ""})
        else:
            p.mods.append({"name": x["name"], "before": before, "staged": False, "root": "", "archive": "",
                           "enabled": x["enabled"]})
    # A plugin of a newer version that the load order already names (the older version's) keeps its place and its
    # state there: only what the newer version brings anew is placed.
    listed = {fold(n) for n, _active in inst.load_order}
    todo = [(pl, x["name"]) for x in report["mods"] for pl in x["plugins"]
            if not pl["active"] and not (x.get("updates") and fold(pl["name"]) in listed)]
    for pl, mod_name in sorted(todo, key=lambda t: t[0].get("order", 0)):
        p.plugins.append({"name": pl["name"], "before": pl["proposed"]["before"], "kind": pl["kind"], "mod": mod_name})
    pdir = inst.profiles_dir / inst.profile
    for n in LISTS:
        p.lists[n] = profile.checksum(pdir / n)
    return p


def _tree(folder: Path) -> dict[str, int]:
    """Every file under `folder` with its size, by relative path."""
    out: dict[str, int] = {}
    for base, _dirs, files in os.walk(folder):
        for n in files:
            full = Path(base) / n
            out[full.relative_to(folder).as_posix()] = full.stat().st_size
    return out


class AddJob:
    def __init__(self, inst: instance.Instance, m: model.Model, the_plan: Plan, work: Path, session_dir: Path,
                 closed: Callable[[], bool | None]):
        self.inst, self.model, self.plan, self.dir = inst, m, the_plan, work
        self.pdir = inst.profiles_dir / inst.profile
        self.safe = safe.Safe(work / "safe")
        self.history = history_mod.History(session_dir)
        self._closed = closed
        self.stage = "planned"
        self.copied: list[dict] = []            # {"name", "folder", "files": {rel: size}}
        self.how = "whole"                      # how the last Revert went: the whole files, or "by line"
        self._record = work / "copied.json"
        if self._record.is_file():
            try:
                with open(self._record, "rb") as f:
                    self.copied = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
            except (OSError, ValueError):
                raise Refused("this job's record cannot be read") from None

    # --- run ---------------------------------------------------------------------------------------------------------

    def _copy_in(self, x: dict) -> None:
        src, dst = Path(x["root"]), self.inst.mods_dir / x["name"]
        if dst.exists():
            raise Refused("MO2 already has a mod called '%s'; ModTrap never overwrites one" % x["name"])
        want = _tree(src)
        dst.mkdir(parents=True)
        self.copied.append({"name": x["name"], "folder": str(dst), "files": {}})
        self._save_copied()                     # noted before the first file: a failure must be able to undo it
        for rel in sorted(want):
            if rel.lower() == "meta.ini":
                continue                        # MO2's own file: ModTrap writes it
            target = dst.joinpath(*rel.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src.joinpath(*rel.split("/")), target)
            if target.stat().st_size != want[rel]:
                raise Refused("%s did not copy whole into MO2's mods folder" % rel)
        # The mod's own record: the archive, and where the mod came from when that is known (WHY§109), so that a
        # mod ModTrap added can be asked about for updates like any other.
        paths.write_atomic(dst / "meta.ini", sources.own_record(x["archive"], x.get("meta")).encode("utf-8"))
        self.copied[-1]["files"] = _tree(dst)
        self._save_copied()

    def _save_copied(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        paths.write_atomic(self._record, (json.dumps(self.copied, ensure_ascii=False) + "\n").encode("utf-8"))

    def run(self) -> dict:
        if self.stage != "planned":
            raise Refused("this job has already run")
        if self._closed() is not True:
            raise Refused("MO2 must be closed while ModTrap changes the mod list: an open MO2 would write its own "
                          "copy back over it. Close MO2, then go on.")
        log.info("MO2 is closed (no ModOrganizer.exe is running); changing the lists")
        for n in LISTS:
            if profile.checksum(self.pdir / n) != self.plan.lists.get(n):
                raise Refused("%s changed since this was planned; read the modlist again" % n)
        done: dict = {"mods": [], "plugins": []}
        self.dir.mkdir(parents=True, exist_ok=True)
        paths.write_atomic(self.dir / "plan.json", (json.dumps(
            {"mods": self.plan.mods, "plugins": self.plan.plugins, "lists": self.plan.lists,
             "when": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        try:
            for n in LISTS:
                self.safe.take(self.pdir / n)
            for x in self.plan.mods:
                if x["staged"]:
                    self._copy_in(x)
                if x["enabled"]:
                    continue                    # already in, where the owner has it
                self.safe.may_change(self.pdir / "modlist.txt")
                ch = profile.place_mod(self.pdir, x["name"], x["before"], enabled=True)
                self.safe.wrote(self.pdir / "modlist.txt")
                line = ch.lines[0]
                done["mods"].append({"name": x["name"], "priority": line["priority"]})
                self.history.add("mod added" if x["staged"] else "mod enabled", mod=x["name"],
                                 priority=line["priority"], priority_before=line["was"], before=x["before"],
                                 archive=x["archive"], plugins=[{"name": p["name"], "kind": p["kind"]}
                                                                for p in self.plan.plugins if p["mod"] == x["name"]])
                if x.get("replaces"):
                    # The older version steps aside: disabled, never deleted (MT9); Revert enables it again.
                    self.safe.may_change(self.pdir / "modlist.txt")
                    profile.set_mods(self.pdir, {x["replaces"]: False})
                    self.safe.wrote(self.pdir / "modlist.txt")
                    done["mods"][-1]["replaces"] = x["replaces"]
                    self.history.add("mod disabled", mod=x["replaces"], why="a newer version of it was added: %s" % x["name"])
            if self.plan.plugins:
                for n in ("loadorder.txt", "plugins.txt"):
                    self.safe.may_change(self.pdir / n)
                try:
                    changes = profile.place_plugins(self.pdir, [(p["name"], p["before"]) for p in self.plan.plugins])
                finally:
                    for n in ("loadorder.txt", "plugins.txt"):
                        self.safe.wrote(self.pdir / n)
                where = {ln["plugin"]: ln["position"] for ln in changes[0].lines}
                for p in self.plan.plugins:
                    done["plugins"].append({"name": p["name"], "position": where[p["name"]]})
                    self.history.add("plugin activated", plugin=p["name"], position=where[p["name"]],
                                     plugin_kind=p["kind"], mod=p["mod"], before=p["before"])
            problems = self.check()
            if problems:
                raise Refused("the modlist does not read back as planned: " + "; ".join(problems[:4]))
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            why = logbook.why(e) if isinstance(e, OSError) else str(e)
            log.error("adding stopped: %s; putting everything back", why)
            self.stage = "failed"
            left = self._put_back()
            for x in self.plan.mods:
                if x.get("replaces") and any(d.get("replaces") == x["replaces"] for d in done["mods"]):
                    self.history.add("mod enabled", mod=x["replaces"], why="adding stopped part way")
            self.history.add("reverted", why="adding stopped part way", left=left)
            self.stage = "reverted"
            raise Refused("adding stopped and everything was put back: %s" % why) from None
        self.stage = "added"
        self.history.add("verified", what="mods added", mods=[x["name"] for x in self.plan.mods])
        paths.write_atomic(self.dir / "added.json", (json.dumps(done, indent=1) + "\n").encode("utf-8"))
        return done

    # --- check -------------------------------------------------------------------------------------------------------

    def check(self) -> list[str]:
        """The modlist read again from disk: is every mod enabled where it was to go, every plugin active after its
        masters, and is no problem new? Returns what is wrong, in words; nothing when all is as planned."""
        inst = instance.load(self.inst.root, self.inst.profile)
        m = model.build(inst)
        out: list[str] = []
        for x in self.plan.mods:
            mod = inst.mod(x["name"])
            if mod is None or not mod.enabled:
                out.append("'%s' is not enabled" % x["name"])
                continue
            if x.get("replaces"):
                old = inst.mod(x["replaces"])
                if old is None or old.enabled:
                    out.append("'%s', the older version of '%s', is not disabled" % (x["replaces"], x["name"]))
            if not x["enabled"] and x["before"]:
                nxt = next((y for y in inst.mods if y.priority == mod.priority + 1), None)
                if nxt is None or fold(nxt.name) != fold(x["before"]) and fold(nxt.name) not in {
                        fold(y["name"]) for y in self.plan.mods}:
                    out.append("'%s' is not directly before '%s'" % (x["name"], x["before"]))
        for p in self.plan.plugins:
            r = m.row(p["name"])
            if r is None or not r.active or r.position is None:
                out.append("%s is not active" % p["name"])
                continue
            if fold(r.source or "") != fold(p["mod"]):
                out.append("%s is used from '%s', not from '%s'" % (p["name"], r.source, p["mod"]))
            for name in r.masters:
                mr = m.row(name)
                if mr is not None and mr.position is not None and mr.position > r.position:
                    out.append("%s loads before its master %s" % (p["name"], name))
        was = {(fold(i.plugin), fold(i.master), i.what) for i in self.model.issues}
        for i in m.issues:
            if (fold(i.plugin), fold(i.master), i.what) not in was:
                out.append("%s needs %s, which is %s" % (i.plugin, i.master,
                                                         "not active" if i.what == "inactive" else "missing"))
        return out

    # --- revert ------------------------------------------------------------------------------------------------------

    def _put_back(self) -> list[str]:
        """The lists as they were; ModTrap's own copies of mods removed where they are still exactly as copied.
        Returns the folders left in place because something else changed them since."""
        self.how = "whole"
        if self.safe.items:
            try:
                self.safe.revert(overwrite_foreign=False)
            except safe.Refused:
                # The lists were changed since by something else, as MO2 does whenever it runs. Putting the old
                # files back would undo that too; instead only ModTrap's own lines are taken out (DESIGN§11).
                self._undo_by_line()
                self.how = "by line"
        left: list[str] = []
        for c in self.copied:
            folder = Path(c["folder"])
            if not folder.is_dir():
                continue
            if folder.parent != self.inst.mods_dir:
                left.append(c["name"])
                continue
            now = _tree(folder)
            if c["files"] and now != c["files"]:
                left.append(c["name"])              # changed since: it stays, for the owner to look at
                continue
            shutil.rmtree(folder)
        self.copied = [c for c in self.copied if c["name"] in left]
        self._save_copied()
        return left

    def _undo_by_line(self) -> None:
        mine = {x["name"] for x in self.copied}                      # mods this job copied in: their lines go
        try:
            profile.remove_plugin_lines(self.pdir, [p["name"] for p in self.plan.plugins if p["mod"] in mine])
        except profile.Refused as e:
            log.warn("undoing by line: %s", e)
        back = {p["name"]: False for p in self.plan.plugins if p["mod"] not in mine}
        for name, on in back.items():                                # plugins of mods MO2 had: inactive again
            try:
                profile.set_plugins(self.pdir, {name: on})
            except profile.Refused as e:
                log.warn("undoing by line: %s", e)
        for x in self.plan.mods:
            if x["enabled"]:
                continue                                             # was enabled before: not ModTrap's doing
            try:
                if x["name"] in mine:
                    profile.remove_mod_line(self.pdir, x["name"])
                else:
                    profile.set_mods(self.pdir, {x["name"]: False})  # disabled again; it keeps its new place
            except profile.Refused as e:
                log.warn("undoing by line: %s", e)
            if x.get("replaces"):
                try:
                    profile.set_mods(self.pdir, {x["replaces"]: True})   # the older version, enabled as it was
                except profile.Refused as e:
                    log.warn("undoing by line: %s", e)
        self.safe.mark_reverted()

    def revert(self) -> dict:
        if self.stage not in ("added", "failed"):
            raise Refused("there is nothing of this job to put back")
        if self._closed() is not True:
            raise Refused("MO2 must be closed while ModTrap puts the mod list back. Close MO2, then go on.")
        try:
            left = self._put_back()
        except safe.Refused as e:
            raise Refused(str(e)) from None
        self.stage = "reverted"
        for x in self.plan.mods:
            if x.get("replaces"):
                self.history.add("mod enabled", mod=x["replaces"], why="the newer version was taken out again: %s" % x["name"])
        self.history.add("reverted", why="the owner asked", mods=[x["name"] for x in self.plan.mods], left=left,
                         how=self.how)
        paths.write_atomic(self.dir / "reverted.json", (json.dumps(
            {"when": time.strftime("%Y-%m-%dT%H:%M:%S"), "left": left, "how": self.how}) + "\n").encode("utf-8"))
        return {"left": left, "how": self.how}

    @classmethod
    def reopen(cls, inst: instance.Instance, m: model.Model, work: Path, session_dir: Path,
               closed: Callable[[], bool | None]) -> "AddJob":
        """A job that ran earlier, from its folder: for Revert."""
        try:
            with open(work / "plan.json", "rb") as f:
                data = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
            the_plan = Plan(mods=list(data["mods"]), plugins=list(data["plugins"]), lists=dict(data["lists"]))
        except (OSError, ValueError, KeyError, TypeError):
            raise Refused("this job's record cannot be read") from None
        job = cls(inst, m, the_plan, work, session_dir, closed)
        job.stage = "added" if (work / "added.json").is_file() and not (work / "reverted.json").is_file() else "reverted"
        return job

    @staticmethod
    def summary(work: Path) -> dict | None:
        """What a job's folder says of it, for the page: when, which mods and plugins, and whether it stands."""
        try:
            with open(work / "plan.json", "rb") as f:
                data = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
        except (OSError, ValueError):
            return None
        state = "reverted" if (work / "reverted.json").is_file() else "added" if (work / "added.json").is_file() else "failed"
        return {"job": work.name, "when": data.get("when", ""), "state": state,
                "mods": [x["name"] for x in data.get("mods", [])], "plugins": [x["name"] for x in data.get("plugins", [])],
                # the mods of this job that are newer versions, each with the mod it is a newer version of (MT49)
                "updates": {x["name"]: x["updates"] for x in data.get("mods", []) if x.get("updates")},
                "archives": {x["name"]: x.get("archive", "") for x in data.get("mods", []) if x.get("archive")}}


__all__ = ["AddJob", "Plan", "plan", "Refused"]
