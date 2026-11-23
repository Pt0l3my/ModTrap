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
from . import instance, logbook, model, paths, plugingroups, profile, safe
from .instance import fold

log = logbook.get("modlist")
LISTS = ("modlist.txt", "plugins.txt", "loadorder.txt")
MOVABLE = ("mod", "separator")
SEP = "_separator"
REMOVED = "ModTrap - removed mods"      # beside MO2's mods folder, on the same drive: an uninstalled mod's folder is moved here, whole (MT66)


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

    def _lists(self, *names: str) -> list[Path]:
        """The lists a change may write: those named, and MO2's plugin groups where this MO2 keeps them (MT73)."""
        return [self.pdir / n for n in names] + ([self.pdir / plugingroups.NAME] if plugingroups.present(self.pdir) else [])

    def _group(self, wanted: dict[str, str]) -> None:
        if wanted:
            self._write(self.pdir / plugingroups.NAME, lambda: plugingroups.set_groups(self.pdir, wanted))

    def _group_new(self, placed: list[tuple[str, str]]) -> dict[str, str]:
        """Gives the plugins just placed in the load order, each (name, its mod), their groups by MT73's rule.
        Returns the groups given, by plugin name; nothing where this MO2 keeps none."""
        groups = plugingroups.read(self.pdir)
        if groups is None or not placed:
            return {}
        mods, order, _active = self._now()
        given: dict[str, str] = {}
        for name, mod in placed:
            if groups.get(fold(name)):
                continue                                    # it has one already: it was in this list before
            g = plugingroups.for_new(order, groups, name, plugingroups.separator_of(mods, mod))
            if g:
                given[name], groups[fold(name)] = g, g
        self._group(given)
        return given

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
        self._begin("enable" if on else "disable", self._lists(*LISTS), mods=mods, plugins=plugs,
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
            if on:
                given = self._group_new([(p["name"], p["mod"]) for p in plugs if p["how"] == "placed"])
                for p in plugs:
                    if p["name"] in given:
                        p["group"] = given[p["name"]]
                self._save()
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

    # --- plugins: active or not, and their place (MT58) ---------------------------------------------------------------

    def plugin_set(self, rows: list[dict], on: bool) -> dict:
        """Activates or deactivates plugins, each {"name", "kind", "mod", "listed", "before"}: one the load order
        names keeps its place; one it does not name yet is put where `before` says (MO2's rule, worked out by
        the caller). Only the star changes for the rest."""
        if not rows:
            raise Refused("there is nothing to change: the plugin is already %s" % ("active" if on else "not active"))
        self._begin("plugin on" if on else "plugin off", self._lists("plugins.txt", "loadorder.txt"), plugins=rows)
        try:
            for n in ("loadorder.txt", "plugins.txt"):
                self.safe.may_change(self.pdir / n)
            try:
                for r in rows:
                    named = {fold(n) for n, _a in instance.parse_plugins(instance._decode(instance._read_bytes(self.pdir / "plugins.txt")))}
                    if fold(r["name"]) in named:
                        profile.set_plugins(self.pdir, {r["name"]: on})
                    elif on:
                        profile.place_plugins(self.pdir, [(r["name"], r["before"])])       # not named there yet: placed, with its star
            finally:
                for n in ("loadorder.txt", "plugins.txt"):
                    self.safe.wrote(self.pdir / n)
            _mods, order, active = self._now()
            wrong = [r["name"] for r in rows if (fold(r["name"]) in active) != on or (on and fold(r["name"]) not in {fold(n) for n in order})]
            if wrong:
                raise Refused("the lists do not read back as planned: %s" % ", ".join(wrong[:4]))
            if on:
                given = self._group_new([(r["name"], r["mod"]) for r in rows if not r["listed"]])
                for r in rows:
                    if r["name"] in given:
                        r["group"] = given[r["name"]]
                self._save()
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            self._fail(e)
        where = {fold(n): i for i, n in enumerate(order)}
        for r in rows:
            self.history.add("plugin activated" if on else "plugin deactivated", plugin=r["name"], position=where.get(fold(r["name"])),
                             plugin_kind=r["kind"], mod=r["mod"], why="on the Plugins tab")
        text = "%s %s" % ("Activated" if on else "Deactivated", rows[0]["name"] + (" and %d more" % (len(rows) - 1) if len(rows) > 1 else ""))
        return self._done(text)

    def plugin_move(self, name: str, before: str, was_before: str, kind: str = "", mod: str = "") -> dict:
        """Moves one plugin to directly before `before` in the load order ("" for the end). Its state stays."""
        self._begin("plugin move", self._lists("plugins.txt", "loadorder.txt"), plugin=name, before=before, was_before=was_before,
                    kind=kind, mod=mod)
        was = self._now()
        try:
            for n in ("loadorder.txt", "plugins.txt"):
                self.safe.may_change(self.pdir / n)
            try:
                profile.place_plugins(self.pdir, [(name, before)], activate=False)
            finally:
                for n in ("loadorder.txt", "plugins.txt"):
                    self.safe.wrote(self.pdir / n)
            _mods, order, active = self._now()
            f = fold(name)
            rest_was, rest_now = [n for n in was[1] if fold(n) != f], [n for n in order if fold(n) != f]
            i = next((k for k, n in enumerate(order) if fold(n) == f), None)
            if rest_was != rest_now or i is None or fold(order[i + 1] if i + 1 < len(order) else "") != fold(before) or active != was[2]:
                raise Refused("the lists do not read back as planned")
            groups, moved = plugingroups.read(self.pdir), {}
            if groups is not None:
                g_was, g_now = groups.get(f, ""), plugingroups.after_move(was[1], order, groups, name)
                if g_now != g_was:
                    self._group({name: g_now})
                    if plugingroups.read(self.pdir).get(f, "") != g_now:
                        raise Refused("the plugin's group does not read back as planned")
                    moved = {"group": g_now, "group_was": g_was}
                    self.record.update(moved)
                    self._save()
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            self._fail(e)
        old = next((k for k, n in enumerate(was[1]) if fold(n) == f), None)
        self.history.add("plugin moved", plugin=name, position=i, position_before=old, plugin_kind=kind, mod=mod, **({"before": before} if before else {}), **moved)
        text = "Moved %s to place %d of the load order" % (name, i)
        if moved:
            text += ", into the group “%s”" % moved["group"] if moved["group"] else ", out of the group “%s”" % moved["group_was"]
        return dict(self._done(text), position=i, was=old, **moved)

    def plugin_group(self, rows: list[dict]) -> dict:
        """Gives plugins their groups in MO2's plugin list (MT73), each {"name", "group", "was", "kind", "mod"};
        "" takes a plugin out of its group. Only the profile's groups file changes."""
        rows = [r for r in rows if r["group"] != r["was"]]
        if not rows:
            raise Refused("there is nothing to change: the group is the one the plugin has")
        if not plugingroups.present(self.pdir):
            raise Refused("this MO2 keeps no plugin groups: there is no %s in the profile" % plugingroups.NAME)
        self._begin("plugin group", [self.pdir / plugingroups.NAME], plugins=rows)
        try:
            self._group({r["name"]: r["group"] for r in rows})
            now = plugingroups.read(self.pdir) or {}
            wrong = [r["name"] for r in rows if now.get(fold(r["name"]), "") != r["group"]]
            if wrong:
                raise Refused("the groups do not read back as planned: %s" % ", ".join(wrong[:4]))
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            self._fail(e)
        for r in rows:
            self.history.add("plugin grouped", plugin=r["name"], group=r["group"], group_was=r["was"], plugin_kind=r["kind"], mod=r["mod"],
                             why="on the Plugins tab")
        more = " and %d more" % (len(rows) - 1) if len(rows) > 1 else ""
        same = len({r["group"] for r in rows}) == 1
        text = ("Put %s%s in the group “%s”" % (rows[0]["name"], more, rows[0]["group"]) if same and rows[0]["group"]
                else "Took %s%s out of %s" % (rows[0]["name"], more, "its group" if not more else "their groups") if same
                else "Gave %s%s their groups" % (rows[0]["name"], more))
        return self._done(text)

    # --- rename a separator -------------------------------------------------------------------------------------------

    def rename(self, old: str, new: str) -> dict:
        """Renames a mod or a separator, as MO2 does: its folder in MO2's mods folder and its line in every
        profile's list (MO03§6)."""
        mod = self.inst.mod(old)
        if mod is None or mod.kind not in MOVABLE or mod.folder is None:
            raise Refused("“%s” is not a mod or a separator of MO2's list" % _bare(old))
        word = "separator" if mod.kind == "separator" else "mod"
        if (mod.kind == "separator") != new.lower().endswith(SEP):
            raise Refused("that is not a %s's name" % word)
        if mod.kind == "mod":
            tool = next((t for t, n in self.inst.output_mods.items() if fold(n) == fold(mod.name)), "")
            if tool:
                raise Refused("“%s” is the mod the tool “%s” writes into, and MO2's settings name it. Neither MO2 nor ModTrap changes those with a mod's name: "
                              "renamed, the tool's files would land in Overwrite. Name another mod for the tool in MO2 first." % (mod.name, tool))
        src, dst = mod.folder, self.inst.mods_dir / new
        if src.name == new:
            raise Refused("that is its name already")
        same = fold(src.name) == fold(new)                      # only the letters' case changes
        if not same and (dst.exists() or self.inst.mod(new) is not None):
            raise Refused("MO2 already has a %s called “%s”" % ("separator" if new.lower().endswith(SEP) else "mod", _bare(new)))
        profiles = [self.inst.profiles_dir / p for p in self.inst.profiles]
        self._begin("rename", [p / "modlist.txt" for p in profiles], old=src.name, new=new, profiles=list(self.inst.profiles), kind=word,
                    priority=mod.priority)
        try:
            os.rename(src, dst)
        except OSError as e:
            self._fail(Refused("the %s's folder could not be renamed: %s" % (word, logbook.why(e))))
        back = lambda: os.rename(dst, src)                      # noqa: E731
        try:
            for p in profiles:
                self._write(p / "modlist.txt", lambda p=p: profile.rename_mod(p, src.name, new))
            names = [n for _s, n in self._now()[0]]
            if new not in names or (not same and any(fold(n) == fold(src.name) for n in names)) or not dst.is_dir():
                raise Refused("the list does not read back as planned")
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            self._fail(e, back)
        self.history.add("%s renamed" % word, mod=_bare(new), was=_bare(src.name), now=_bare(new), priority=mod.priority)
        return self._done("Renamed the %s “%s” to “%s”" % (word, _bare(src.name), _bare(new)))

    # --- uninstall: out of MO2, kept by ModTrap (MT66) ----------------------------------------------------------------

    def uninstall(self, names: list[str], original: set[str] | None = None) -> dict:
        """Takes mods out of MO2: each mod's line leaves every profile's mod list, the plugins that only it gave
        leave the load order, and its folder is moved, whole, out of MO2's mods folder into ModTrap's own folder
        beside it. Nothing is deleted: undo moves the folders back and puts the lists back."""
        original = {fold(n) for n in (original or ())}
        mods = []
        for n in names:
            y = self.inst.mod(n)
            if y is None or y.kind != "mod" or y.folder is None or not y.listed:
                raise Refused("“%s” is not a mod of MO2's list that can be taken out here" % n)
            if not y.folder.is_dir():
                raise Refused("the folder of “%s” is not in MO2's mods folder" % n)
            if y not in mods:
                mods.append(y)
        going = {fold(y.name) for y in mods}
        keep = self.inst.mods_dir.parent / REMOVED / self.dir.name
        # The plugins that leave the load order with their mod: those only it gives. One that another enabled mod
        # has too stays in the lists, and is that mod's from now on.
        order = self._now()[1]
        active = self._now()[2]
        others = {fold(p) for o in self.inst.mods if o.kind == "mod" and o.enabled and fold(o.name) not in going for p in o.plugins}
        drop = []
        for y in mods:
            for r in (self.model.provided_by(y) if self.model is not None else []):
                if fold(r.name) not in others:
                    drop.append({"name": r.name, "mod": y.name, "kind": r.kind, "active": fold(r.name) in active, "position": r.position})
        dropping = {fold(d["name"]) for d in drop}
        grouped = plugingroups.read(self.pdir) or {}
        for d in drop:
            if grouped.get(fold(d["name"])):
                d["group"] = grouped[fold(d["name"])]           # its line stays in MO2's groups file; MO2 drops it at its next start (MO05§1)
            at = next((i for i, n in enumerate(order) if fold(n) == fold(d["name"])), None)
            d["was_before"] = next((n for n in order[at + 1:] if fold(n) not in dropping), "") if at is not None else ""
        # Each profile's line of each mod: its sign, and the entry it stood directly before in MO2's list.
        profiles = [p for p in self.inst.profiles]
        lines: dict[str, dict[str, dict]] = {}
        for p in profiles:
            try:
                rows = instance.parse_modlist(instance._decode(instance._read_bytes(self.inst.profiles_dir / p / "modlist.txt")))
            except OSError:
                continue
            for i, (sign, name) in enumerate(rows):
                if fold(name) in going:
                    above = next((n for _s, n in reversed(rows[:i]) if fold(n) not in going), "")
                    lines.setdefault(p, {})[name] = {"sign": sign, "before": above}
        lists = [self.inst.profiles_dir / p / "modlist.txt" for p in lines] + self._lists("plugins.txt", "loadorder.txt")
        self._begin("uninstall", list(dict.fromkeys(lists)), kept=str(Path(REMOVED) / self.dir.name), lines=lines, plugins=drop,
                    mods=[{"name": y.name, "priority": y.priority, "enabled": y.enabled, "original": fold(y.name) in original, "plugins": list(y.plugins)} for y in mods])
        moved: list[tuple[Path, Path]] = []

        def back() -> None:
            for src, dst in reversed(moved):
                os.rename(dst, src)
        try:
            keep.mkdir(parents=True, exist_ok=True)
            for y in mods:
                dst = keep / y.folder.name
                os.rename(y.folder, dst)
                moved.append((y.folder, dst))
        except OSError as e:
            self._fail(Refused("the mod's folder could not be moved out of MO2's mods folder: %s" % logbook.why(e)), back)
        try:
            for p, named in lines.items():
                for name in named:
                    self._write(self.inst.profiles_dir / p / "modlist.txt", lambda p=p, name=name: profile.remove_mod_line(self.inst.profiles_dir / p, name))
            if drop:
                for n in ("loadorder.txt", "plugins.txt"):
                    self.safe.may_change(self.pdir / n)
                try:
                    profile.remove_plugin_lines(self.pdir, [d["name"] for d in drop])
                finally:
                    for n in ("loadorder.txt", "plugins.txt"):
                        self.safe.wrote(self.pdir / n)
            now_mods, now_order, _a = self._now()
            if any(fold(n) in going for _s, n in now_mods) or any(fold(n) in dropping for n in now_order) or any(src.exists() or not dst.is_dir() for src, dst in moved):
                raise Refused("the lists do not read back as planned")
        except (Refused, profile.Refused, safe.Refused, OSError) as e:
            self._fail(e, back)
        for y in mods:
            self.history.add("mod uninstalled", mod=y.name, priority=y.priority, was="enabled" if y.enabled else "disabled",
                             original=fold(y.name) in original, plugins=[{"name": d["name"], "kind": d["kind"], "position": d["position"]} for d in drop if d["mod"] == y.name],
                             why="on the Modlist page; its folder is kept by ModTrap, beside MO2's mods folder")
        text = "Uninstalled “%s”%s" % (mods[0].name, " and %d more" % (len(mods) - 1) if len(mods) > 1 else "")
        if drop:
            text += ": %d plugin%s left the load order" % (len(drop), "" if len(drop) == 1 else "s")
        return self._done(text)

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
                    raise Refused("the %s is no longer there under the name ModTrap gave it" % rec.get("kind", "separator"))
                os.rename(src, dst)
            if op == "uninstall":
                keep = self.inst.mods_dir.parent / rec["kept"]
                pairs = [(keep / x["name"], self.inst.mods_dir / x["name"]) for x in rec["mods"]]
                for src, dst in pairs:
                    if not src.is_dir():
                        raise Refused("the folder of “%s” is no longer where ModTrap kept it" % src.name)
                    if dst.exists():
                        raise Refused("MO2's mods folder has a “%s” again: rename or remove that one first" % dst.name)
                for src, dst in pairs:
                    os.rename(src, dst)
                try:
                    keep.rmdir()                                # empty now; a folder that is not stays
                    keep.parent.rmdir()
                except OSError:
                    pass
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
        if op in ("plugin on", "plugin off"):
            for r in rec["plugins"]:
                self.history.add("plugin deactivated" if op == "plugin on" else "plugin activated", plugin=r["name"], plugin_kind=r["kind"], mod=r["mod"],
                                 why="a change on the Plugins tab was undone")
        if op == "plugin group":
            for r in rec["plugins"]:
                self.history.add("plugin grouped", plugin=r["name"], group=r["was"], group_was=r["group"], plugin_kind=r["kind"], mod=r["mod"],
                                 why="a change of groups was undone")
        if op in ("enable", "disable"):
            for x in rec["mods"]:
                self.history.add("mod disabled" if op == "enable" else "mod enabled", mod=x["name"], priority=x["priority"], why="a change on the Modlist page was undone")
            for p in rec["plugins"]:
                self.history.add("plugin deactivated" if op == "enable" else "plugin activated", plugin=p["name"], plugin_kind=p["kind"], mod=p["mod"],
                                 why="a change on the Modlist page was undone")
        if op == "uninstall":
            for x in rec["mods"]:
                self.history.add("mod put back", mod=x["name"], priority=x["priority"], why="an uninstall was undone: its folder is in MO2's mods folder again")
        if op == "rename":
            self.history.add("%s renamed" % rec.get("kind", "separator"), mod=_bare(rec["old"]), was=_bare(rec["new"]), now=_bare(rec["old"]), why="a rename was undone")
        if op == "move":
            for x in rec.get("mods", []):
                self.history.add("separator moved" if x["name"].lower().endswith(SEP) else "mod moved", mod=_bare(x["name"]), priority=x["priority"],
                                 priority_before=x.get("to"), why="a move was undone")
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

        def ungroup(given: dict[str, str], back: dict[str, str]) -> None:
            """Turns back the groups this change gave: only a line that still says what it wrote."""
            now = plugingroups.read(self.pdir)
            if now is None:
                return
            todo = {n: back.get(n, "") for n, g in given.items() if now.get(fold(n), "") == g and back.get(n, "") != g}
            if todo:
                attempt("the plugins' groups", lambda: plugingroups.set_groups(self.pdir, todo))
            for n, g in given.items():
                if now.get(fold(n), "") != g:
                    notes.append("%s keeps the group it has now: it was changed again since" % n)

        if op in ("enable", "disable"):
            on = op == "enable"
            for x in rec["mods"]:
                attempt(x["name"], lambda x=x: profile.set_mods(self.pdir, {x["name"]: not on}))
            if on:
                placed = [p["name"] for p in rec["plugins"] if p["how"] == "placed"]
                if placed:
                    attempt("plugins", lambda: profile.remove_plugin_lines(self.pdir, placed))
                ungroup({p["name"]: p["group"] for p in rec["plugins"] if p.get("group")}, {})
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
        elif op == "uninstall":
            for p, named in rec["lines"].items():
                pd = self.inst.profiles_dir / p
                try:
                    there = {fold(n) for _s, n in instance.parse_modlist(instance._decode(instance._read_bytes(pd / "modlist.txt")))}
                except OSError:
                    notes.append("the mod list of profile %s could not be read" % p)
                    continue
                for name, was in named.items():
                    before = was["before"] if fold(was["before"]) in there else ""
                    if was["before"] and not before:
                        notes.append("%s goes to the top in profile %s: %s, which it stood before, is no longer in the list" % (name, p, _bare(was["before"])))
                    attempt(name, lambda pd=pd, name=name, before=before, was=was: profile.place_mod(pd, name, before, enabled=was["sign"] == "+"))
            names = {fold(n) for n in self._now()[1]}
            for d in sorted(rec["plugins"], key=lambda d: -(d["position"] or 0)):
                before = d["was_before"] if fold(d["was_before"]) in names else ""
                attempt(d["name"], lambda d=d, before=before: profile.place_plugins(self.pdir, [(d["name"], before)], activate=False))
                if d["active"]:
                    attempt(d["name"], lambda d=d: profile.set_plugins(self.pdir, {d["name"]: True}))
            now = plugingroups.read(self.pdir)
            lost = {d["name"]: d["group"] for d in rec["plugins"] if d.get("group") and now is not None and not now.get(fold(d["name"]))}
            if lost:                                        # MO2 ran since and dropped their lines: they are in their groups again
                attempt("the plugins' groups", lambda: plugingroups.set_groups(self.pdir, lost))
        elif op in ("plugin on", "plugin off"):
            for r in rec["plugins"]:
                attempt(r["name"], lambda r=r: profile.set_plugins(self.pdir, {r["name"]: op == "plugin off"}))
        elif op == "plugin move":
            names = {fold(n) for n in self._now()[1]}
            if rec["was_before"] and fold(rec["was_before"]) not in names:
                notes.append("%s stays: %s, which it stood before, is no longer in the load order" % (rec["plugin"], rec["was_before"]))
            else:
                attempt(rec["plugin"], lambda: profile.place_plugins(self.pdir, [(rec["plugin"], rec["was_before"])], activate=False))
                if "group_was" in rec:
                    ungroup({rec["plugin"]: rec["group"]}, {rec["plugin"]: rec["group_was"]})
        elif op == "plugin group":
            ungroup({r["name"]: r["group"] for r in rec["plugins"]}, {r["name"]: r["was"] for r in rec["plugins"]})
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
                "undone": rec.get("undone", ""), "profile": rec.get("profile", ""), "how": rec.get("how", ""),
                "kept": rec.get("kept", "") if not rec.get("undone") else "",
                "mods": [x.get("name", "") for x in rec.get("mods", []) if isinstance(x, dict)][:50] or ([rec["new"]] if rec.get("op") == "rename" else [])}


__all__ = ["LISTS", "ListJob", "Refused"]
