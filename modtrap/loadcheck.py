"""What a change on the Modlist page does to the load order, and whether it is safe (MT56): reading only.

Three things, none of which writes:

- `place`: where plugins new to the load order go, by the rule MO2 itself follows when a mod is enabled (MO03§2 to
  §4): a new plugin goes to the end; a master (an .esm, an .esl, or a plugin flagged as a master) stays in the
  masters' block at the top; and no plugin loads before one of its own masters. Written from that rule as read, not
  from MO2's code.
- `plan_set`: what enabling or disabling mods would do: which plugins become active and where, which become
  inactive, and what is not safe about it (a master that is missing or not active, plugins of other mods that
  would lose a master, the game's limit on plugins).
- `overrides`: what a mod's plugins overwrite in the load order as it is: the records of their masters they
  change, the other plugins that change the same records and load before them (whose change they replace) or
  after them (which replace theirs). Read with ModTrap's own reader, record headers only.
"""

from __future__ import annotations

import time
from pathlib import Path

from . import adding, logbook, model, plugin, steps
from .instance import Mod, fold

log = logbook.get("modlist")
FULL_SLOTS = 254               # full plugins the game loads: FE is the light plugins', FF the saved game's
LIGHT_SLOTS = 4096
SCAN_SECONDS = 12.0            # the whole of one scan of what a mod's plugins overwrite
SCAN_FILE_SECONDS = 4.0        # one plugin of it
SHOWN = 12                     # names listed in one finding
FILES_SECONDS = 10.0           # looking for the files a mod shares with the others


class Refused(Exception):
    """This cannot be done; the text says why, in words for the page."""


def _master_name(name: str) -> bool:
    return name.lower().endswith((".esm", ".esl"))


# --- MO2's rule (MO03) --------------------------------------------------------------------------------------------

def place(order: list[tuple[str, bool]], new: list[dict]) -> tuple[list[str], dict[str, str]]:
    """The load order with `new` plugins in it. `order` is the load order as it is: (name, is it a master). Each
    of `new` is {"name", "master": bool, "masters": names, "listed": bool}: one with `listed` is in the order
    already and keeps its place unless a master of its own loads after it. Returns the names in their new order,
    in which only the plugins of `new` have moved, and for each plugin that had to follow a master of its own
    (folded name) that master."""
    names = [n for n, _ in order]
    is_master = {fold(n): m for n, m in order}
    for p in new:
        is_master[fold(p["name"])] = bool(p["master"])
    here = {fold(n) for n in names}
    # 1. A plugin new to the list goes to the end (MO03§2).
    for p in new:
        if fold(p["name"]) not in here:
            names.append(p["name"])
            here.add(fold(p["name"]))
    # 2. A master stays in the masters' block: one that came to lie below it goes to the block's end (MO03§3).
    for p in new:
        if not p["master"] or p.get("listed"):
            continue
        names.remove(p["name"])
        end = next((i for i, n in enumerate(names) if not is_master[fold(n)]), len(names))
        names.insert(end, p["name"])
    # 3. No plugin before a master of its own: it goes right after the last of them (MO03§4). A master's master
    #    that is no master itself cannot be followed into the lower block; the plan says so.
    followed: dict[str, str] = {}
    for _ in range(len(new) + 1):
        moved = False
        for p in new:
            at = {fold(n): i for i, n in enumerate(names)}
            own = at[fold(p["name"])]
            behind = [x for x in p["masters"] if fold(x) in at and at[fold(x)] > own and (not p["master"] or is_master[fold(x)])]
            if behind:
                last = max(behind, key=lambda x: at[fold(x)])
                names.pop(own)
                names.insert(at[fold(last)], p["name"])     # the master moved one place up: this is right after it
                followed[fold(p["name"])] = last
                moved = True
        if not moved:
            break
    return names, followed


def _held_by_disabled(m: model.Model, name: str) -> list[str]:
    f = fold(name)
    return [x.name for x in m.instance.mods if x.kind == "mod" and not x.enabled and any(fold(p) == f for p in x.plugins)]


def _listing(names: list[str]) -> str:
    return ", ".join(names[:SHOWN]) + (" and %d more" % (len(names) - SHOWN) if len(names) > SHOWN else "")


def plan_set(m: model.Model, names: list[str], on: bool, read=plugin.read) -> dict:
    """What enabling (`on`) or disabling the named mods would do, and what is not safe about it. A mod already as
    wanted is passed over. Returns {"on", "mods", "plugins", "notes", "warnings", "ask"}: `plugins` are the ones
    whose line changes, each {"name", "mod", "kind", "how", "before", "position", "why"}; a warning is
    {"level": "bad" or "warn", "text"}; `ask` is true when something is bad enough to ask the owner first."""
    inst = m.instance
    mods: list[Mod] = []
    for name in names:
        mod = inst.mod(name)
        if mod is None:
            raise Refused("“%s” is not in the mod list" % name)
        if mod.kind != "mod":
            raise Refused("“%s” is not a mod MO2 manages: it cannot be enabled or disabled" % name.replace("_separator", ""))
        if not mod.listed:
            raise Refused("“%s” is not in modlist.txt yet: open MO2 once, so that it lists the mod" % name)
        if mod.enabled != on and all(fold(x.name) != fold(mod.name) for x in mods):
            mods.append(mod)
    out: dict = {"on": on, "mods": [{"name": x.name, "priority": x.priority} for x in mods], "plugins": [], "notes": [],
                 "warnings": [], "ask": False}
    if not mods:
        return out
    bad = lambda text: out["warnings"].append({"level": "bad", "text": text})          # noqa: E731
    warn = lambda text: out["warnings"].append({"level": "warn", "text": text})        # noqa: E731
    changing = {fold(x.name) for x in mods}
    if not on:
        gone: dict[str, model.PluginRow] = {}
        for mod in mods:
            for r in m.provided_by(mod):
                others = [n for n in r.also_in if fold(n) not in changing]
                if others:
                    out["notes"].append("%s stays: “%s” has a file of the same name, and MO2 then uses that one." % (r.name, others[-1]))
                    continue
                gone[fold(r.name)] = r
                if r.active and r.position is not None and not r.primary:
                    out["plugins"].append({"name": r.name, "mod": mod.name, "kind": r.kind, "how": "deactivated",
                                           "before": "", "position": r.position, "why": "its mod is disabled"})
        for f, r in gone.items():
            need = [d for d in r.dependants if fold(d) not in gone and (dr := m.row(d)) is not None and dr.active]
            if need:
                bad("%s is a master of %d active plugin%s of other mods, which would then have a missing master: %s."
                    % (r.name, len(need), "" if len(need) == 1 else "s", _listing(need)))
        out["ask"] = any(w["level"] == "bad" for w in out["warnings"])
        return out

    # Enabling. The plugins of these mods that no enabled mod provides yet become active (MO03§5).
    order = [(m.plugins[f].name, _is_master(m.plugins[f])) for f in m.order if m.plugins[f].position is not None]
    in_order = {fold(n) for n, _ in order}
    new: list[dict] = []
    for mod in sorted(mods, key=lambda x: x.priority):
        for p in sorted(mod.plugins, key=fold):
            row = m.row(p)
            if row is not None and row.source is not None and fold(row.source) not in changing:
                # Another enabled mod has a file of this name: MO2 leaves the plugin's state alone (MO03§5).
                if row.source_priority is not None and mod.priority > row.source_priority:
                    out["notes"].append("%s: this mod's file replaces the one of “%s”; the plugin keeps its place and its state." % (p, row.source))
                else:
                    out["notes"].append("%s: “%s” has a file of the same name and the higher priority; MO2 goes on using that one." % (p, row.source))
                continue
            if any(fold(x["name"]) == fold(p) for x in new):
                continue                                    # two of the mods to enable hold it: once
            try:
                h = read(mod.folder / p)
            except plugin.Unreadable as e:
                warn("%s could not be read (%s): it is left as it is, not activated." % (p, e))
                continue
            kind = plugin.kind(p, h)
            new.append({"name": p, "mod": mod.name, "kind": kind, "master": adding.is_master(kind), "masters": h.masters,
                        "listed": fold(p) in in_order, "active": bool(row is not None and row.active)})
    after, followed = place(order, new)
    at = {fold(n): i for i, n in enumerate(after)}
    coming = {fold(p["name"]) for p in new}
    memo: dict = {}
    _pos, made = adding.tail_start(m, memo, False)
    made = [n for n in made if (mr := m.row(n)) is not None and adding.generated(m, mr, memo)]
    for p in new:
        i = at[fold(p["name"])]
        nxt = after[i + 1] if i + 1 < len(after) else ""
        if fold(p["name"]) in followed:
            why = "right after its master %s" % followed[fold(p["name"])]
        elif p["listed"]:
            why = "at the place it had in the load order"
        elif p["master"]:
            why = "at the end of the masters' block"
        else:
            why = "at the end of the load order"
        if not p["active"]:
            out["plugins"].append({"name": p["name"], "mod": p["mod"], "kind": p["kind"], "how": "in place" if p["listed"] else "placed",
                                   "before": nxt, "position": i, "why": why})
        for x in p["masters"]:
            xr = m.row(x)
            if fold(x) in coming:
                if at[fold(x)] > i:
                    warn("%s is flagged as a master but needs %s, which is not: the game loads masters first whatever the list says." % (p["name"], x))
                continue
            if xr is None or xr.source is None:
                held = _held_by_disabled(m, x)
                bad("%s needs %s, which no enabled mod provides%s." % (p["name"], x, (
                    ": the disabled mod “%s” has it" % held[0]) if held else ""))
            elif not xr.active:
                bad("%s needs %s, which is not active." % (p["name"], x))
            elif fold(x) in at and at[fold(x)] > i:
                warn("%s is flagged as a master but needs %s, which is not: the game loads masters first whatever the list says." % (p["name"], x))
        if not p["master"] and not p["listed"] and made and not nxt:
            warn("%s goes last, after what the tools made (%s): by MO2's rule a new plugin goes to the end. Where they change the same records, "
                 "this plugin now wins; run those tools again if the mod should be in their output." % (p["name"], _listing(made[:3])))
    full = sum(1 for r in m.plugins.values() if r.active and r.source is not None and r.position is not None and not adding.is_light(r.kind))
    light = sum(1 for r in m.plugins.values() if r.active and r.source is not None and r.position is not None and adding.is_light(r.kind))
    add_full = sum(1 for x in out["plugins"] if not adding.is_light(x["kind"]))
    add_light = len(out["plugins"]) - add_full
    if add_full and full + add_full > FULL_SLOTS:
        bad("%d full plugins would be active: the game loads %d at most." % (full + add_full, FULL_SLOTS))
    if add_light and light + add_light > LIGHT_SLOTS:
        bad("%d light plugins would be active: the game loads %d at most." % (light + add_light, LIGHT_SLOTS))
    if len(out["plugins"]) > 1:
        out["notes"].append("%d plugins become active together: look at what they overwrite." % len(out["plugins"]))
    out["ask"] = any(w["level"] == "bad" for w in out["warnings"])
    return out


def _is_master(r: model.PluginRow) -> bool:
    return adding.is_master(r.kind) if r.kind else _master_name(r.name)


# --- what a mod's plugins overwrite (the scanner) ------------------------------------------------------------------

def _kinds(keys, index) -> dict[str, int]:
    out: dict[str, int] = {}
    for k in keys:
        kind = index[k][3]
        out[kind] = out.get(kind, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1])[:8])


def overrides(m: model.Model, mod: Mod, seconds: float = SCAN_SECONDS) -> dict:
    """What the plugins this mod provides overwrite, in the load order as it is. Per plugin: its place, whether its
    masters are there and before it, the records of its masters it changes, and the other active plugins that change
    the same records: the ones before it (it overwrites their change) and after it (they overwrite its change)."""
    until = time.monotonic() + seconds
    rows = [m.plugins[f] for f in m.order if m.plugins[f].position is not None]
    listed = len(rows)
    out: dict = {"mod": mod.name, "plugins": [], "cut": False, "looked": 0, "safe": True}
    memo: dict = {}
    _pos, made = adding.tail_start(m, memo, False)
    made_f = {fold(n) for n in made}
    for r in m.provided_by(mod):
        entry: dict = {"name": r.name, "kind": r.kind, "active": r.active, "position": r.position, "of": listed, "problems": [], "notes": [],
                       "records": 0, "own": 0, "masters": [], "overwrites": [], "overwritten_by": [], "cut": False}
        out["plugins"].append(entry)
        if r.unreadable:
            entry["problems"].append("it could not be read: %s" % r.unreadable)
            continue
        if r.position is None or not r.active:
            entry["notes"].append("it is not active: the game does not load it")
        for x in r.masters:
            xr = m.row(x)
            if xr is None or xr.source is None:
                entry["problems"].append("its master %s is missing" % x)
            elif not xr.active:
                entry["problems"].append("its master %s is not active" % x)
            elif r.position is not None and xr.position is not None and xr.position > r.position:
                entry["problems"].append("it loads before its master %s" % x)
        if r.position is not None and not _is_master(r):
            first_normal = next((x.position for x in rows if not _is_master(x)), None)
            if first_normal is not None and r.position < first_normal:
                entry["notes"].append("it stands in the masters' block without being a master")
            late = [x.name for x in rows if fold(x.name) in made_f and x.position < r.position and adding.generated(m, x, memo)]
            if late and not adding.generated(m, r, memo):
                entry["notes"].append("it loads after %s, which a tool made: where they change the same records, this plugin wins" % _listing(late[:3]))
        if r.path is None:
            continue
        try:
            with plugin.Records(r.path, min(SCAN_FILE_SECONDS, max(0.5, until - time.monotonic()))) as mine:
                index, cut = dict(mine.index), mine.cut
                own = mine.own
        except (plugin.Unreadable, OSError) as e:
            entry["problems"].append("its records could not be read: %s" % e)
            continue
        entry["cut"] = cut
        entry["records"] = len(index)
        over = {k for k in index if k[0] != own}
        entry["own"] = len(index) - len(over)
        by_master: dict[str, set] = {}
        for k in over:
            by_master.setdefault(k[0], set()).add(k)
        for name in r.masters:
            keys = by_master.get(name.casefold())
            if keys:
                entry["masters"].append({"name": name, "records": len(keys), "kinds": _kinds(keys, index)})
        if not over or r.position is None:
            continue
        wanted = frozenset(index[k][3] for k in over)
        touched = set(by_master)
        # The plugins that can change the same records: the active ones that share one of those masters. The ones
        # after it first (few, and they win), then the ones before it from the nearest upwards.
        others = [x for x in rows if x is not r and x.active and x.path is not None and x.position is not None
                  and (touched & ({y.casefold() for y in x.masters} | {x.name.casefold()}))]
        others.sort(key=lambda x: (0, x.position) if x.position > r.position else (1, -x.position))
        for x in others:
            if x.name.casefold() in touched and not (touched & {y.casefold() for y in x.masters}):
                continue                                # one of its masters: counted above, as the records it changes
            if time.monotonic() > until:
                entry["cut"] = out["cut"] = True
                break
            try:
                with plugin.Records(x.path, min(SCAN_FILE_SECONDS, max(0.2, until - time.monotonic())), wanted) as there:
                    same = {k for k in over if k in there.index and k[0] != there.own}
            except (plugin.Unreadable, OSError):
                continue
            out["looked"] += 1
            if same:
                entry["overwrites" if x.position < r.position else "overwritten_by"].append(
                    {"plugin": x.name, "mod": x.source or "", "position": x.position, "records": len(same), "kinds": _kinds(same, index)})
        entry["overwrites"].sort(key=lambda e: -e["records"])
        entry["overwritten_by"].sort(key=lambda e: -e["records"])
    out["safe"] = not any(e["problems"] for e in out["plugins"])
    return out


def files(m: model.Model, mod: Mod, seconds: float = FILES_SECONDS) -> dict:
    """The files this mod shares with other enabled mods, at the priority it has: the mods below it, whose files it
    overwrites, and the mods above it, which overwrite its files. Names and counts only; no file is opened."""
    stop = time.monotonic() + seconds
    out: dict = {"files": 0, "wins": [], "loses": [], "cut": False}
    if mod.folder is None:
        return out
    mine, cut = steps.walk(mod.folder)
    mine = [f for f in mine if f.lower() != "meta.ini"]
    out["files"], out["cut"] = len(mine), cut
    trie = adding._trie(mine)
    memo: dict = {}
    for o in m.instance.mods:
        if o.kind not in ("mod", "overwrite") or o.folder is None or not o.enabled or o.name == mod.name or not trie:
            continue
        if time.monotonic() > stop:
            out["cut"] = True
            break
        found, c = adding.shared_files(o.folder, trie, stop)
        out["cut"] = out["cut"] or c
        found = [f for f in found if f.lower() != "meta.ini"]
        if not found:
            continue
        kinds: dict[str, int] = {}
        for f in found:
            k = adding.kind_of(f)
            kinds[k] = kinds.get(k, 0) + 1
        entry = {"mod": o.name, "priority": o.priority, "files": len(found), "kinds": kinds,
                 "examples": sorted(found, key=str.lower)[:adding.EXAMPLES], "notable": [k for k in kinds if k in adding.NOTABLE],
                 "output": adding.is_output_mod(m, o, memo) if o.kind == "mod" else ""}
        (out["wins"] if o.priority < mod.priority else out["loses"]).append(entry)
    out["wins"].sort(key=lambda e: -e["files"])
    out["loses"].sort(key=lambda e: -e["files"])
    return out


__all__ = ["Refused", "files", "overrides", "place", "plan_set"]
