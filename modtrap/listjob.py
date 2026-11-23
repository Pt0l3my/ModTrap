"""A change of MO2's lists made on the Modlist page (MT56): mods enabled or disabled, a mod or a separator moved,
a separator renamed. One small job per change, with the rules of every job that writes: MO2 closed, a copy of each
list in the job's safe folder before it is touched (MT14), the result read back and checked, any failure put back,
the change in the history (MT15), and a way back ("Undo").

What a change does to the plugins is planned by `loadcheck`, by MO2's own rule (MO03); here it is only written.
No mod's file is touched: a separator's folder, which MO2 keeps empty but for its own note, is renamed with its
line, as MO2 itself does (MO03§6).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

from . import history as history_mod
from . import instance, logbook, model, paths, profile, safe
from .instance import fold

log = logbook.get("modlist")
LISTS = ("modlist.txt", "plugins.txt", "loadorder.txt")
MOVABLE = ("mod", "separator")
SEP = "_separator"


class Refused(Exception):
    """The change is not made; the text says why, in words for the page."""


def _bare(name: str) -> str:
    return name[:-len(SEP)] if name.lower().endswith(SEP) else name


def _listed(inst: instance.Instance) -> list[instance.Mod]:
    """MO2's list as modlist.txt has it, lowest priority first: mods, separators and what MO2 does not manage."""
    return sorted((y for y in inst.mods if y.kind in ("mod", "separator", "foreign") and y.listed), key=lambda y: y.priority)


class ListJob:
    def __init__(self, inst: instance.Instance, m: model.Model | None, work: Path, session_dir: Path,
                 closed: Callable[[], bool | None]):
        self.inst, self.model, self.dir = inst, m, work
        self.pdir = inst.profiles_dir / inst.profile
        self.safe = safe.Safe(work / "safe")
        self.history = history_mod.History(session_dir)
        self._closed = closed
        self.record: dict = {}
        try:
            with open(work / "job.json", "rb") as f:
                self.record = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            raise Refused("this change's record cannot be read") from None

    # --- common ------------------------------------------------------------------------------------------------------

    def _save(self) -> None:
        paths.write_atomic(self.dir / "job.json", (json.dumps(self.record, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))

    def _begin(self, op: str, lists: list[Path], **what: object) -> None:
        if self.record:
            raise Refused("this change has already been made")
        if self._closed() is not True:
            raise Refused("MO2 must be closed while ModTrap changes the mod list: an open MO2 would write its own copy back over it. "
                          "Close MO2, then go on.")
        self.dir.mkdir(parents=True, exist_ok=True)
        try:
            for p in lists:
                self.safe.take(p)
        except (safe.Refused, OSError) as e:
            raise Refused(str(e) if isinstance(e, safe.Refused) else logbook.why(e)) from None
        self.record = {"op": op, "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "profile": self.inst.profile, "state": "begun",
                       "undone": "", **what}
        self._save()                                # before the first write: a crash leaves what was begun

    def _write(self, path: Path, fn: Callable[[], object]) -> object:
        self.safe.may_change(path)
        try:
            return fn()
        finally:
            self.safe.wrote(path)

    def _fail(self, e: Exception, undo: Callable[[], None] | None = None) -> None:
        why = logbook.why(e) if isinstance(e, OSError) else str(e)
        log.error("the change of the mod list stopped: %s; putting everything back", why)
        try:
            self.safe.revert(overwrite_foreign=False)
            if undo is not None:
                undo()
        except (safe.Refused, OSError) as e2:
            why += "; and putting back stopped too: %s" % (logbook.why(e2) if isinstance(e2, OSError) else e2)
        self.record["state"] = "failed"
        self.record["undone"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save()
        self.history.add("reverted", why="a change of the mod list stopped part way: %s" % why)
        raise Refused("nothing was changed: %s" % why) from None

    def _now(self) -> tuple[list[tuple[str, str]], list[str], set[str]]:
        """The lists as they are on disk, read from the three files alone (reading the whole modlist again would
        look into every mod's folder): the mod list's lines as (sign, name), highest priority first; the load
        order's names; and the active plugins, folded."""
        def text(n: str) -> str:
            return instance._decode(instance._read_bytes(self.pdir / n))
        try:
            return (instance.parse_modlist(text("modlist.txt")), instance.parse_loadorder(text("loadorder.txt")),
                    {fold(n) for n, a in instance.parse_plugins(text("plugins.txt")) if a})
        except OSError as e:
            raise Refused("the lists could not be read back: %s" % logbook.why(e)) from None

    def _done(self, text: str) -> dict:
        self.record["state"], self.record["text"] = "done", text
        self._save()
        log.info("%s", text)
        return {"job": self.dir.name, "op": self.record["op"], "text": text}

    # --- enable, disable ---------------------------------------------------------------------------------------------

    def set(self, plan: dict) -> dict:
        """Carries out a plan of `loadcheck.plan_set`."""
        on, mods, plugs = bool(plan["on"]), plan["mods"], plan["plugins"]
        if not mods:
            raise Refused("there is nothing to change: the mod is already %s" % ("enabled" if on else "disabled"))
        self._begin("enable" if on else "disable", [self.pdir / n for n in LISTS], mods=mods, plugins=plugs,
                    warnings=[w["text"] for w in plan.get("warnings", [])])
        was = self._now()[0]
        try:
            self._write(self.pdir / "modlist.txt", lambda: profile.set_mods(self.pdir, {x["name"]: on for x in mods}))
            if plugs:
                for n in ("loadorder.txt", "plugins.txt"):
                    self.safe.may_change(self.pdir / n)
                try:
                    if on:
                        # The last place first: each plugin's follower is then where it is to be.
                        profile.place_plugins(self.pdir, [(p["name"], p["before"]) for p in sorted(plugs, key=lambda p: -p["position"])])
                    else:
                        profile.set_plugins(self.pdir, {p["name"]: False for p in plugs})
                finally:
                    for n in ("loadorder.txt", "plugins.txt"):
                        self.safe.wrote(self.pdir / n)
            problems, order = self._check_set(on, mods, plugs, was)
            if problems:
                raise Refused("the lists do not read back as planned: " + "; ".join(problems[:4]))
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            self._fail(e)
        where = {fold(n): i for i, n in enumerate(order)}
        for x in mods:
            mine = [p for p in plugs if p["mod"] == x["name"]]
            self.history.add("mod enabled" if on else "mod disabled", mod=x["name"], priority=x["priority"],
                             why="on the Modlist page", plugins=[{"name": p["name"], "kind": p["kind"], "position": where.get(fold(p["name"]))} for p in mine])
        for p in plugs:
            self.history.add("plugin activated" if on else "plugin deactivated", plugin=p["name"], position=where.get(fold(p["name"])),
                             plugin_kind=p["kind"], mod=p["mod"], **({"before": p["before"]} if on and p["how"] == "placed" else {}))
        names = "“%s”" % mods[0]["name"] + (" and %d more" % (len(mods) - 1) if len(mods) > 1 else "")
        text = "%s %s" % ("Enabled" if on else "Disabled", names)
        if plugs:
            text += ": %d plugin%s %s" % (len(plugs), "" if len(plugs) == 1 else "s", "activated" if on else "deactivated")
        return self._done(text)

    def _check_set(self, on: bool, mods: list[dict], plugs: list[dict], was: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
        """What is not as planned, in words, and the load order as it now is."""
        now, order, active = self._now()
        out = []
        mine = {fold(x["name"]) for x in mods}
        if [n for _s, n in now] != [n for _s, n in was] or any(a != b for a, b in zip(now, was) if fold(a[1]) not in mine):
            out.append("another line of the mod list changed")
        signs = {fold(n): sg for sg, n in now}
        for x in mods:
            if signs.get(fold(x["name"])) != ("+" if on else "-"):
                out.append("“%s” is not %s" % (x["name"], "enabled" if on else "disabled"))
        at = {fold(n): i for i, n in enumerate(order)}
        for p in plugs:
            f = fold(p["name"])
            if on and (f not in at or f not in active):
                out.append("%s is not active" % p["name"])
            elif not on and f in active:
                out.append("%s is still active" % p["name"])
            elif on and p["before"] and (at[f] + 1 >= len(order) or fold(order[at[f] + 1]) != fold(p["before"])):
                out.append("%s is not directly before %s" % (p["name"], p["before"]))
        return out, order

    # --- move ---------------------------------------------------------------------------------------------------------

    def move(self, names: list[str], before: str) -> dict:
        """Moves mods or separators, as one block in the order they have, to directly before the entry `before` as
        MO2 shows its list (one priority lower than it), or with "" to the highest priority. Each keeps its state."""
        listed = _listed(self.inst)
        by = {fold(y.name): y for y in listed}
        block = []
        for n in names:
            y = by.get(fold(n))
            if y is None:
                raise Refused("“%s” is not in the mod list" % _bare(n))
            if y.kind not in MOVABLE:
                raise Refused("“%s” is not managed by MO2 and cannot be moved here" % y.name)
            if y not in block:
                block.append(y)
        if not block:
            raise Refused("there is nothing to move")
        block.sort(key=lambda y: y.priority)
        if before and fold(before) not in by:
            raise Refused("“%s” is not in the mod list" % _bare(before))
        if before and any(fold(before) == fold(y.name) for y in block):
            raise Refused("a mod cannot be placed before itself")
        rest = [y for y in listed if y not in block]
        at = next(i for i, y in enumerate(rest) if fold(y.name) == fold(before)) if before else len(rest)
        if rest[:at] + block + rest[at:] == listed:
            raise Refused("it is there already")
        follower = {y.name: (listed[i + 1].name if i + 1 < len(listed) else "") for i, y in enumerate(listed)}
        self._begin("move", [self.pdir / "modlist.txt"], before=before,
                    mods=[{"name": y.name, "priority": y.priority, "was_before": follower[y.name]} for y in block])
        was = self._now()[0]
        moved = {fold(y.name) for y in block}
        signs = {fold(n): sg for sg, n in was}                  # each line keeps the sign it has (a separator's too)
        try:
            nxt = before
            for y in reversed(block):
                self._write(self.pdir / "modlist.txt", lambda y=y, nxt=nxt: profile.place_mod(self.pdir, y.name, nxt, enabled=signs.get(fold(y.name)) == "+"))
                nxt = y.name
            now = self._now()[0]
            # Read back: every other line where it was, as it was; the block together, in its order, at its place
            # (the file lists the highest priority first, so the block follows `before` there, last one first).
            if [x for x in now if fold(x[1]) not in moved] != [x for x in was if fold(x[1]) not in moved]:
                raise Refused("another line of the mod list changed")
            start = next((i + 1 for i, (_s, n) in enumerate(now) if fold(n) == fold(before)), None) if before else 0
            if start is None or [(sg, fold(n)) for sg, n in now[start:start + len(block)]] != [(signs[fold(y.name)], fold(y.name)) for y in reversed(block)]:
                raise Refused("the list does not read back as planned")
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            self._fail(e)
        new = {y.name: i for i, y in enumerate(rest[:at] + block + rest[at:], start=listed[0].priority)}
        for y in block:
            self.history.add("separator moved" if y.kind == "separator" else "mod moved", mod=_bare(y.name) if y.kind == "separator" else y.name,
                             priority=new[y.name], priority_before=y.priority, **({"before": _bare(before)} if before else {}))
        first = block[0]
        text = "Moved “%s”%s to priority %d" % (_bare(first.name), " and %d more" % (len(block) - 1) if len(block) > 1 else "", new[first.name])
        return self._done(text)

    # --- rename a separator -------------------------------------------------------------------------------------------

    def rename(self, old: str, new: str) -> dict:
        """Renames a separator: its folder in MO2's mods folder and its line in every profile's list (MO03§6)."""
        mod = self.inst.mod(old)
        if mod is None or mod.kind != "separator" or mod.folder is None:
            raise Refused("“%s” is not a separator of MO2's list" % _bare(old))
        if not new.lower().endswith(SEP):
            raise Refused("that is not a separator's name")
        src, dst = mod.folder, self.inst.mods_dir / new
        if src.name == new:
            raise Refused("that is its name already")
        same = fold(src.name) == fold(new)                      # only the letters' case changes
        if not same and (dst.exists() or self.inst.mod(new) is not None):
            raise Refused("MO2 already has a separator called “%s”" % _bare(new))
        profiles = [self.inst.profiles_dir / p for p in self.inst.profiles]
        self._begin("rename", [p / "modlist.txt" for p in profiles], old=src.name, new=new, profiles=list(self.inst.profiles))
        try:
            os.rename(src, dst)
        except OSError as e:
            self._fail(Refused("the separator's folder could not be renamed: %s" % logbook.why(e)))
        back = lambda: os.rename(dst, src)                      # noqa: E731
        try:
            for p in profiles:
                self._write(p / "modlist.txt", lambda p=p: profile.rename_mod(p, src.name, new))
            names = [n for _s, n in self._now()[0]]
            if new not in names or (not same and any(fold(n) == fold(src.name) for n in names)) or not dst.is_dir():
                raise Refused("the list does not read back as planned")
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            self._fail(e, back)
        self.history.add("separator renamed", mod=_bare(new), was=_bare(src.name), now=_bare(new))
        return self._done("Renamed the separator “%s” to “%s”" % (_bare(src.name), _bare(new)))

    # --- undo ---------------------------------------------------------------------------------------------------------

    def undo(self) -> dict:
        rec = self.record
        if not rec or rec.get("state") != "done" or rec.get("undone"):
            raise Refused("there is nothing of this change to undo")
        if self._closed() is not True:
            raise Refused("MO2 must be closed while ModTrap puts the mod list back. Close MO2, then go on.")
        op, how, notes = rec["op"], "whole", []
        try:
            if op == "rename":
                src, dst = self.inst.mods_dir / rec["new"], self.inst.mods_dir / rec["old"]
                if not src.is_dir() or (dst.exists() and fold(rec["old"]) != fold(rec["new"])):
                    raise Refused("the separator is no longer there under the name ModTrap gave it")
                os.rename(src, dst)
            plan = self.safe.check()
            if not plan["foreign"]:
                self.safe.revert(overwrite_foreign=False)
            else:
                # The lists were changed since by something else, a later job or MO2 itself. Putting the old files
                # back would undo that too: only this change's own lines are turned back (DESIGN§11).
                how = "by line"
                notes = self._undo_by_line()
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            raise Refused("the change could not be undone: %s" % (logbook.why(e) if isinstance(e, OSError) else e)) from None
        if how == "whole":
            self.safe.mark_reverted()
        rec["undone"], rec["how"] = time.strftime("%Y-%m-%dT%H:%M:%S"), how
        self._save()
        if op in ("enable", "disable"):
            for x in rec["mods"]:
                self.history.add("mod disabled" if op == "enable" else "mod enabled", mod=x["name"], priority=x["priority"], why="a change on the Modlist page was undone")
            for p in rec["plugins"]:
                self.history.add("plugin deactivated" if op == "enable" else "plugin activated", plugin=p["name"], plugin_kind=p["kind"], mod=p["mod"],
                                 why="a change on the Modlist page was undone")
        self.history.add("reverted", why="the owner undid a change of the mod list: %s" % rec.get("text", op), how=how, notes=notes)
        log.info("undone (%s): %s", how, rec.get("text", op))
        return {"job": self.dir.name, "how": how, "notes": notes, "text": rec.get("text", "")}

    def _undo_by_line(self) -> list[str]:
        rec, op, notes = self.record, self.record["op"], []

        def attempt(what: str, fn: Callable[[], object]) -> None:
            try:
                fn()
            except profile.Refused as e:
                notes.append("%s: %s" % (what, e))

        if op in ("enable", "disable"):
            on = op == "enable"
            for x in rec["mods"]:
                attempt(x["name"], lambda x=x: profile.set_mods(self.pdir, {x["name"]: not on}))
            if on:
                placed = [p["name"] for p in rec["plugins"] if p["how"] == "placed"]
                if placed:
                    attempt("plugins", lambda: profile.remove_plugin_lines(self.pdir, placed))
                for p in rec["plugins"]:
                    if p["how"] != "placed":
                        attempt(p["name"], lambda p=p: profile.set_plugins(self.pdir, {p["name"]: False}))
            else:
                for p in rec["plugins"]:
                    attempt(p["name"], lambda p=p: profile.set_plugins(self.pdir, {p["name"]: True}))
        elif op == "move":
            now = {fold(n): sg for sg, n in self._now()[0]}
            for x in sorted(rec["mods"], key=lambda x: -x["priority"]):         # the highest first: its follower is in place
                sign = now.get(fold(x["name"]))
                if sign is None:
                    notes.append("%s is no longer in the list" % _bare(x["name"]))
                elif x["was_before"] and fold(x["was_before"]) not in now:
                    notes.append("%s stays: %s, which it stood before, is no longer in the list" % (_bare(x["name"]), _bare(x["was_before"])))
                else:
                    attempt(x["name"], lambda x=x, sign=sign: profile.place_mod(self.pdir, x["name"], x["was_before"], enabled=sign == "+"))
        elif op == "rename":
            for p in rec["profiles"]:
                attempt(p, lambda p=p: profile.rename_mod(self.inst.profiles_dir / p, rec["new"], rec["old"]))
        self.safe.mark_reverted()
        return notes

    # --- for the page -------------------------------------------------------------------------------------------------

    @staticmethod
    def summary(work: Path) -> dict | None:
        try:
            with open(work / "job.json", "rb") as f:
                rec = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(rec, dict) or rec.get("state") != "done":
            return None
        return {"job": work.name, "op": rec.get("op", ""), "when": rec.get("when", ""), "text": rec.get("text", ""),
                "undone": rec.get("undone", ""), "profile": rec.get("profile", "")}


__all__ = ["LISTS", "ListJob", "Refused"]
