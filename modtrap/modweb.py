"""One mod and the mods it has to do with (MT62, DESIGN§23): for the pop-up that shows a mod in the middle of its web.

Reading only. Two passes, because the second takes seconds on a large list:

- `near`: what the plugins' headers say. The mods this mod needs (its plugins name theirs as masters), the mods that
  need it, which of those look like patches made for it, and which are a tool's output.
- `far`: what the files and the records say. The mods whose files this mod overwrites and the mods that overwrite
  its files (by kind of file, with examples), and the plugins that change the same records as this mod's plugins:
  where neither plugin knows the other (neither is the other's master), that is a conflict, unless a third plugin
  that has both as masters is there to settle it, or the later of the two was made by a tool from the load order
  as a whole (a tool's output, or ModTrap's demastered copy of one): that one is meant to have the last word (MT73).
  And ModTrap's demastered copy of a plugin stands for that plugin, with the same records at the same place: what
  it shares with a plugin that was there when the copy was made is the modlist's own, as before, and no conflict
  of the demaster's (MT74).

Every link is {"mod", "kind", "weight", "text", "lines", ...}. Kinds: "needs", "needed", "patch", "output",
"overwrites", "overwritten", "conflict", "settled", "wins", "loses" (the last two: records of a common master that a
mod it needs or is needed by also changes, which is how a patch works, and no conflict; or records a tool-made
plugin changes after the other, which is what the tool made it for; or records ModTrap's demastered copy shares
with a plugin as the plugin it stands for did: such a link says so in `made`, a sentence for the page).
"""

from __future__ import annotations

import os
import re

from . import adding, loadcheck, model
from .instance import GAME, OVERWRITE, Mod, fold

PATCH_WORDS = re.compile(r"(patch|patches|compat|compatib|fix(es)?\b|tweak|addon|add-on|consistency)", re.IGNORECASE)
MOD_PREFIX = "ModTrap - "      # the mod ModTrap makes for a demaster (as `demaster.MOD_PREFIX`)
LINES = 12                     # detail lines kept for one link
KINDS = ("needs", "needed", "patch", "output", "overwrites", "overwritten", "conflict", "settled", "wins", "loses")


def _name(mod_name: str) -> str:
    return "the game's own files" if mod_name == GAME else "Overwrite" if mod_name == OVERWRITE else mod_name


def _base(m: model.Model, mod: Mod) -> dict:
    return {"name": mod.name, "shown": _name(mod.name), "priority": mod.priority, "enabled": mod.enabled, "kind": mod.kind,
            "plugins": [{"name": r.name, "kind": r.kind, "active": r.active, "position": r.position} for r in m.provided_by(mod)],
            "files_held": len(mod.plugins)}


def _link(m: model.Model, other: str, kind: str, weight: int, text: str, lines: list[str], **more) -> dict:
    o = m.instance.mod(other)
    return {"mod": other, "shown": _name(other), "priority": o.priority if o is not None else None, "enabled": bool(o is not None and o.enabled),
            "kind": kind, "weight": weight, "text": text, "lines": lines[:LINES], "more": max(0, len(lines) - LINES), **more}


def near(m: model.Model, mod: Mod) -> dict:
    """What the plugins' headers say of this mod and the others."""
    links: list[dict] = []
    own = m.provided_by(mod)
    own_f = {fold(r.name) for r in own}
    # The mods it needs: whose plugins its plugins name as masters.
    needs: dict[str, list[str]] = {}
    lacks: list[str] = []
    for r in own:
        for master in r.masters:
            mr = m.plugins.get(fold(master))
            if mr is None or mr.source is None:
                lacks.append("%s needs %s, which no enabled mod has" % (r.name, master))
            elif mr.source != mod.name:
                needs.setdefault(mr.source, []).append("%s needs %s%s" % (r.name, mr.name, "" if mr.active else " (not active)"))
                if r.active and not mr.active:
                    lacks.append("%s needs %s, which is not active" % (r.name, mr.name))
    for other, lines in needs.items():
        links.append(_link(m, other, "needs", len(lines), "%d of its plugins' masters" % len(lines) if len(lines) != 1 else "1 master of its plugins", lines))
    # The mods that need it, by what they look like.
    for g in model.groups(m, mod):
        lines = ["%s needs %s" % (d.name, ", ".join(x for x in d.masters if fold(x) in own_f)) for d in g.dependants]
        n = len(g.dependants)
        if g.reading == "output":
            links.append(_link(m, g.mod.name, "output", n, "made by %s: %d plugin%s that hold%s it" % (", ".join(g.made_by) or "a tool", n, "" if n == 1 else "s", "s" if n == 1 else ""),
                               lines, tools=list(g.made_by), proposal=g.proposal))
            continue
        # A patch made for it: everything in that mod depends on this one, and the mod or its plugins say "patch"
        # (or the like) by name. What else such a mod needs, beyond what this mod needs itself, is what the patch
        # stands between. A mod that needs this one without the name is told as needing it: its masters alone do
        # not tell a patch from a mod built on two others.
        third = set()
        for d in g.dependants:
            for x in d.masters:
                xr = m.plugins.get(fold(x))
                if xr is not None and xr.source not in (None, GAME, mod.name, g.mod.name) and xr.source not in needs:
                    third.add(xr.source)
        between = sorted(third, key=fold)
        also = ": between it and %s" % ", ".join(_name(x) for x in between[:2]) + (" and more" if len(between) > 2 else "") if between else ""
        whole = g.reading in ("whole mod", "most of the mod")
        named = bool(PATCH_WORDS.search(g.mod.name) or any(PATCH_WORDS.search(d.name) for d in g.dependants))
        if whole and named:
            links.append(_link(m, g.mod.name, "patch", n, "a patch for it" + also, lines, between=between[:8], whole=g.reading == "whole mod"))
        else:
            links.append(_link(m, g.mod.name, "needed", n, "%d of its plugins need%s it" % (n, "s" if n == 1 else "") + ("" if whole else " (it has %d more that do not)" % g.others)
                               + (", and %s" % ", ".join(_name(x) for x in between[:2]) if between else ""), lines, between=between[:8], whole=whole))
    base = _base(m, mod)
    if mod.name.startswith(MOD_PREFIX):
        base["copies"] = sorted({x for r in own if (x := copy_of(m, r))}, key=fold)[:8]          # the mods whose plugins its copies stand for
        base["modtrap"] = True
    return {"mod": base, "links": links, "lacks": lacks[:LINES], "lacking": len(lacks), "needs": len(needs), "deep": False, "cut": False}


TOOL_WORD = ("Such a plugin gathers what the plugins before it change and is meant to have the last word on the records it holds, "
             "whether or not it names them as masters.")


def made_to_win(m: model.Model, r: model.PluginRow, memo: dict) -> str:
    """Why this plugin's change over a plugin it does not know is no conflict, in a sentence for the page, or ""
    (MT73). A tool made it from the load order as a whole, to have the last word on the records it holds."""
    f = fold(r.name)
    if f not in memo.setdefault("made", {}):
        why = ""
        held = copy_of(m, r)
        if held is not None:                        # ModTrap's copy: a tool's work where the plugin it stands for is
            o = m.instance.mod(held) if held else None
            if (o is not None and adding.is_output_mod(m, o, memo)) or adding.generated(m, r, memo):
                why = "No conflict: %s is ModTrap's demastered copy of a plugin a tool made from the load order as a whole. %s" % (r.name, TOOL_WORD)
        elif adding.generated(m, r, memo):
            why = "No conflict: a tool made %s from the load order as a whole. %s" % (r.name, TOOL_WORD)
        memo["made"][f] = why
    return memo["made"][f]


def copy_of(m: model.Model, r: model.PluginRow) -> str | None:
    """For ModTrap's demastered copy of a plugin: the mod that holds the plugin it stands for ("" when no enabled
    mod has it any more). None for any other plugin."""
    if not r.source or not r.source.startswith(MOD_PREFIX):
        return None
    return r.also_in[-1] if r.also_in else ""


def _newer(m: model.Model, copy: model.PluginRow, other: model.PluginRow) -> bool:
    """Did the other plugin's mod come into MO2 after the copy was made? Then the plugin the copy stands for never
    stood beside it, and what the two share is new. By the copy's file time and the mod folder's making (as
    MO2's Installation column, MO04§3); where a time cannot be read, it is taken as there before."""
    try:
        made = os.stat(copy.path).st_mtime
        o = m.instance.mod(other.source) if other.source else None
        if o is None or o.folder is None or o.kind != "mod":
            return False
        st = os.stat(o.folder)
        born = getattr(st, "st_birthtime", None) or (st.st_ctime if os.name == "nt" else st.st_mtime)
        return born > made
    except (OSError, TypeError):
        return False


def as_before(m: model.Model, mine: model.PluginRow, theirs: model.PluginRow) -> str:
    """Why what these two plugins share is not the demaster's doing, in a sentence for the page, or "" (MT74)."""
    for copy, other in ((mine, theirs), (theirs, mine)):
        held = copy_of(m, copy)
        if held is None or _newer(m, copy, other):
            continue
        return ("Not the demaster's doing: %s is ModTrap's demastered copy of the plugin %s, with the same records at the same place in the load order. "
                "What the two plugins change in common they changed before the demaster too, in the same order: that is the modlist's own arrangement, "
                "and the copy alters nothing in it." % (copy.name, "in “%s”" % _name(held) if held else "of that name"))
    return ""


def far(m: model.Model, mod: Mod, files_seconds: float = loadcheck.FILES_SECONDS, records_seconds: float = loadcheck.SCAN_SECONDS) -> dict:
    """What the files and the records say: who overwrites whom, and where two plugins change the same records."""
    links: list[dict] = []
    f = loadcheck.files(m, mod, files_seconds)

    def file_lines(e: dict) -> list[str]:
        kinds = ", ".join("%d %s" % (n, k) for k, n in sorted(e["kinds"].items(), key=lambda kv: -kv[1]))
        return [kinds] + ["e.g. " + x for x in e["examples"]]

    for e in f["wins"]:
        links.append(_link(m, e["mod"], "overwrites", e["files"], "%d file%s of it overwritten" % (e["files"], "" if e["files"] == 1 else "s"), file_lines(e),
                           kinds=e["kinds"], notable=e["notable"], output=e.get("output", "")))
    for e in f["loses"]:
        links.append(_link(m, e["mod"], "overwritten", e["files"], "overwrites %d file%s of this mod" % (e["files"], "" if e["files"] == 1 else "s"), file_lines(e),
                           kinds=e["kinds"], notable=e["notable"], output=e.get("output", "")))
    cut = bool(f["cut"])
    if mod.enabled and mod.kind in ("mod", "overwrite"):
        scan = loadcheck.overrides(m, mod, records_seconds)
        cut = cut or bool(scan["cut"])
        by: dict[tuple[str, str], dict] = {}
        memo: dict = {}
        for p in scan["plugins"]:
            mine = m.plugins.get(fold(p["name"]))
            for side, kind_known, kind_unknown in (("overwrites", "wins", "conflict"), ("overwritten_by", "loses", "conflict")):
                for x in p[side]:
                    theirs = m.plugins.get(fold(x["plugin"]))
                    if mine is None or theirs is None or not x["mod"] or x["mod"] == mod.name:
                        continue
                    # Do the two plugins know each other? One that has the other as a master was made with it in
                    # view: its changes over the other's are what a patch is. Two that do not are a conflict,
                    # unless a third plugin has both as masters and so can settle it.
                    known = any(fold(y) == fold(mine.name) for y in theirs.masters) or any(fold(y) == fold(theirs.name) for y in mine.masters)
                    both = sorted(set(mine.dependants) & set(theirs.dependants), key=fold)
                    active_both = [z for z in both if (zr := m.plugins.get(fold(z))) is not None and zr.active]
                    wins = side == "overwrites"
                    # A plugin a tool made from the whole load order is meant to have the last word: what it
                    # changes after a plugin it does not name is its work, not a conflict (MT73). The other way
                    # round stays one: a plugin that loads after a tool's output and does not know it undoes it.
                    # ModTrap's demastered copy stands for the plugin it was made from: what it shares with a
                    # plugin that was there then is as it was before the demaster (MT74).
                    before = "" if known else as_before(m, mine, theirs)
                    made = "" if known or before else made_to_win(m, mine if wins else theirs, memo)
                    kind = kind_known if known or before or made else ("settled" if active_both else kind_unknown)
                    entry = by.setdefault((x["mod"], kind), {"records": 0, "lines": [], "settled_by": set(), "wins": 0, "loses": 0, "made": 0, "before": 0, "why": ""})
                    entry["records"] += x["records"]
                    if before or made:
                        entry["before" if before else "made"] += x["records"]
                        entry["why"] = entry["why"] or before or made
                    entry["wins" if wins else "loses"] += x["records"]
                    kinds = ", ".join("%s %d" % (k, n) for k, n in x["kinds"].items())
                    entry["lines"].append("%s %s %s in %d record%s (%s)" % (mine.name, "wins over" if wins else "loses to", theirs.name, x["records"], "" if x["records"] == 1 else "s", kinds))
                    entry["settled_by"].update(active_both)
        for (other, kind), e in by.items():
            if kind == "conflict":
                text = "%d record%s both change, neither knowing the other" % (e["records"], "" if e["records"] == 1 else "s")
            elif kind == "settled":
                text = "%d record%s both change; %s has both as masters" % (e["records"], "" if e["records"] == 1 else "s", sorted(e["settled_by"], key=fold)[0])
            elif kind == "wins":
                text = "this mod's change wins in %d record%s" % (e["records"], "" if e["records"] == 1 else "s")
            else:
                text = "its change wins over this mod's in %d record%s" % (e["records"], "" if e["records"] == 1 else "s")
            if e["before"]:
                text += ": as before the demaster" if e["before"] == e["records"] else " (%d of them as before the demaster)" % e["before"]
            elif e["made"]:
                text += ": made by a tool to have the last word" if e["made"] == e["records"] else " (%d of them by a tool's output, made to have the last word)" % e["made"]
            links.append(_link(m, other, kind, e["records"], text, e["lines"], wins=e["wins"], loses=e["loses"], settled_by=sorted(e["settled_by"], key=fold)[:6],
                               made=e["why"]))
    return {"links": links, "files": f["files"], "deep": True, "cut": cut}


def web(m: model.Model, mod: Mod, deep: bool) -> dict:
    """The whole answer for the pop-up: the mod, and every link of the pass asked for. `deep` adds `far`."""
    out = near(m, mod)
    if deep:
        got = far(m, mod)
        out["links"] += got["links"]
        out.update(deep=True, cut=got["cut"], files=got["files"])
    counts: dict[str, int] = {}
    for x in out["links"]:
        counts[x["kind"]] = counts.get(x["kind"], 0) + 1
    out["counts"] = counts
    out["links"].sort(key=lambda x: (KINDS.index(x["kind"]), -x["weight"], fold(x["mod"])))
    return out


__all__ = ["KINDS", "far", "near", "web"]
