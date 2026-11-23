"""One mod and the mods it has to do with (MT62, DESIGN§23): for the pop-up that shows a mod in the middle of its web.

Reading only. Two passes, because the second takes seconds on a large list:

- `near`: what the plugins' headers say. The mods this mod needs (its plugins name theirs as masters), the mods that
  need it, which of those look like patches made for it, and which are a tool's output.
- `far`: what the files say. The mods whose files this mod overwrites and the mods that overwrite its files (by
  kind of file, with examples), as MO2's Conflicts column counts them.

Which records two plugins both change is not told (MT76): that one plugin's change wins over another's is how a
modlist works, ModTrap cannot see whether anything is lost by it, and nothing breaks by it.

Every link is {"mod", "kind", "weight", "text", "lines", ...}. Kinds: "needs", "needed", "patch", "output",
"overwrites", "overwritten".
"""

from __future__ import annotations

import re

from . import loadcheck, model
from .instance import GAME, OVERWRITE, Mod, fold

PATCH_WORDS = re.compile(r"(patch|patches|compat|compatib|fix(es)?\b|tweak|addon|add-on|consistency)", re.IGNORECASE)
MOD_PREFIX = "ModTrap - "      # the mod ModTrap makes for a demaster (as `demaster.MOD_PREFIX`)
LINES = 12                     # detail lines kept for one link
KINDS = ("needs", "needed", "patch", "output", "overwrites", "overwritten")


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
    if mod.name.startswith(MOD_PREFIX):             # ModTrap's own mod: the mods whose plugins its demastered copies stand for
        base["copies"] = sorted({r.also_in[-1] for r in own if r.also_in}, key=fold)[:8]
        base["modtrap"] = True
    return {"mod": base, "links": links, "lacks": lacks[:LINES], "lacking": len(lacks), "needs": len(needs), "deep": False, "cut": False}


def far(m: model.Model, mod: Mod, files_seconds: float = loadcheck.FILES_SECONDS) -> dict:
    """What the files say: who overwrites whom."""
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
    return {"links": links, "files": f["files"], "deep": True, "cut": bool(f["cut"])}


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
