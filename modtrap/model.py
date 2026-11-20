"""What depends on what (DESIGN§3): for every plugin the instance provides, where it comes from, its masters and
its dependants; for every mod, its plugins and what depends on them; and the health check, which is what MO2's own
missing-master warning reports.

Built from an Instance and the plugin headers alone. Read-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import plugin, tools
from .instance import GAME, Instance, Mod, fold


@dataclass
class PluginRow:
    name: str                       # as named on disk, or as the load order names it when no file provides it
    position: int | None            # place in the load order, 0 first; None: not in the load order
    active: bool
    source: str | None              # the mod that provides it (the winner); None: no file
    source_priority: int | None
    also_in: tuple[str, ...]        # other enabled mods holding a file of the same name (they lose)
    path: Path | None
    kind: str                       # plugin.kind(); "" when unreadable or missing
    masters: tuple[str, ...]
    author: str = ""
    description: str = ""
    unreadable: str = ""            # why the header could not be read, or ""
    primary: bool = False           # one of the game's own plugins
    dependants: list[str] = field(default_factory=list)       # plugins that list this one as a master
    missing_masters: list[str] = field(default_factory=list)  # masters no enabled mod provides
    inactive_masters: list[str] = field(default_factory=list)  # masters that are provided but not active


@dataclass
class Issue:
    plugin: str
    master: str
    what: str                       # "missing": no file; "inactive": not active in the load order


@dataclass
class Model:
    instance: Instance
    plugins: dict[str, PluginRow]   # by folded name
    order: list[str]                # folded names in load order, then those outside it by name
    issues: list[Issue]
    _by_source: dict[str, list[PluginRow]] = field(default_factory=dict, repr=False)

    def row(self, name: str) -> PluginRow | None:
        return self.plugins.get(fold(name))

    def provided_by(self, mod: Mod) -> list[PluginRow]:
        """The mod's plugins that MO2 would use (it wins them), in load order."""
        if not self._by_source:
            for f in self.order:
                r = self.plugins[f]
                if r.source is not None:
                    self._by_source.setdefault(r.source, []).append(r)
        return self._by_source.get(mod.name, [])

    def dependants_of_mod(self, mod: Mod) -> list[PluginRow]:
        """Plugins of other mods that list one of this mod's plugins as a master, in load order."""
        own = {fold(r.name) for r in self.provided_by(mod)}
        out: dict[str, PluginRow] = {}
        for f in own:
            for d in self.plugins[f].dependants:
                if fold(d) not in own:
                    out[fold(d)] = self.plugins[fold(d)]
        return [self.plugins[f] for f in self.order if f in out]


@dataclass
class Group:
    """The dependants of a trapped mod that live in one other mod, and a first reading of what they are
    (DESIGN§5). The dry run through xEdit refines it; this much is known from the headers alone."""
    mod: Mod
    dependants: list[PluginRow]
    others: int                     # the mod's plugins (that it wins) that do not depend on the trapped mod
    made_by: tuple[str, ...]        # the tools that made these plugins, as far as the evidence goes (TL01§7)
    reading: str                    # "output", "whole mod", "most of the mod", "some plugins"
    leftover: tuple[str, ...] = ()  # for "most of the mod": its plugins that do not depend on the trapped mod
    evidence: tuple[dict, ...] = () # per plugin: {"plugin", "tool", "kind", "how", "strong"}
    proposal: str = ""              # for an output: "run the tool again", "probably run the tool again", "demaster"


def groups(model: Model, trapped: Mod) -> list[Group]:
    """The trapped mod's dependants grouped by the mod they live in, in load order of their first plugin."""
    inst = model.instance
    binaries = {e.title: e.binary for e in inst.executables}
    by_mod: dict[str, list[PluginRow]] = {}
    for r in model.dependants_of_mod(trapped):
        by_mod.setdefault(r.source or "", []).append(r)
    out = []
    for name, rows in by_mod.items():
        mod = inst.mod(name)
        if mod is None:
            continue
        others = len(model.provided_by(mod)) - len(rows)
        found = {r.name: tools.identify(r.name, r.author, name, inst.output_mods, binaries) for r in rows}
        every = all(found[r.name] for r in rows)            # each of these plugins has a maker we can name
        made_by = tuple(sorted({e.tool for evs in found.values() for e in evs})) if every else ()
        evidence = tuple({"plugin": pn, "tool": e.tool, "kind": e.kind, "how": e.how, "strong": e.strong}
                         for pn, evs in found.items() for e in evs)
        dep = {fold(r.name) for r in rows}
        rest = [r for r in model.provided_by(mod) if fold(r.name) not in dep]
        # "Most of the mod": more of its plugins depend on the trapped mod than not, and nothing outside the mod
        # needs the ones that do not. Such a mod is probably all about the trapped mod (a patch hub with one patch
        # that needs no master), and disabling it whole is proposed, for the owner to judge (WHY§28).
        mostly = 0 < others < len(rows) and all(
            all(model.plugins[fold(d)].source == mod.name for d in r.dependants) for r in rest)
        if made_by:
            reading = "output"
        elif others == 0:
            reading = "whole mod"
        else:
            reading = "most of the mod" if mostly else "some plugins"
        proposal = tools.proposal([e for evs in found.values() for e in evs]) if made_by else ""
        out.append(Group(mod, rows, others, made_by, reading,
                         tuple(r.name for r in rest) if reading == "most of the mod" else (), evidence, proposal))
    return out


def build(inst: Instance, read=plugin.read) -> Model:
    """The model of an instance. `read` reads one plugin's header (replaced in tests)."""
    # Who provides each plugin: the highest enabled mod holding a file of that name; the game's folder is lowest.
    holders: dict[str, list[Mod]] = {}
    disk_name: dict[tuple[str, str], str] = {}
    for m in inst.mods:                                    # lowest priority first
        if not m.enabled or m.folder is None:
            continue
        for p in m.plugins:
            holders.setdefault(fold(p), []).append(m)
            disk_name[(fold(p), m.name)] = p

    primary = {fold(p) for p in inst.primary}
    position = {fold(n): i for i, (n, _) in enumerate(inst.load_order)}
    active = {fold(n) for n, a in inst.load_order if a}
    listed_name = {fold(n): n for n, _ in inst.load_order}
    no_game_folder = not any(m.kind == "game" and m.folder is not None and m.plugins for m in inst.mods)

    rows: dict[str, PluginRow] = {}
    for f in set(holders) | set(position):
        hs = holders.get(f, [])
        if hs:
            win = hs[-1]
            name = disk_name[(f, win.name)]
            path = win.folder / name
            row = PluginRow(name=name, position=position.get(f), active=f in active or (f in primary),
                            source=win.name, source_priority=win.priority,
                            also_in=tuple(h.name for h in hs[:-1]), path=path, kind="", masters=(),
                            primary=f in primary)
            try:
                h = read(path)
                row.masters, row.author, row.description = h.masters, h.author, h.description
                row.kind = plugin.kind(name, h)
            except plugin.Unreadable as e:
                row.unreadable = str(e)
        else:
            # In the load order with no file. A game plugin is taken as present when the game's folder was not
            # found (the instance's note says so); anything else is a plugin MO2 will drop.
            present = f in primary and no_game_folder
            row = PluginRow(name=listed_name[f], position=position.get(f), active=f in active,
                            source=GAME if present else None, source_priority=-1 if present else None,
                            also_in=(), path=None, kind="", masters=(), primary=f in primary,
                            unreadable="" if present else "no enabled mod holds this file")
        rows[f] = row

    in_order = sorted((f for f in rows if rows[f].position is not None), key=lambda f: rows[f].position)
    outside = sorted(f for f in rows if rows[f].position is None)
    order = in_order + outside

    issues: list[Issue] = []
    for f in order:
        r = rows[f]
        for m in r.masters:
            mf = fold(m)
            target = rows.get(mf)
            if target is not None and target.source is not None:
                target.dependants.append(r.name)
                if r.active and not target.active:
                    r.inactive_masters.append(m)
                    issues.append(Issue(r.name, m, "inactive"))
            else:
                r.missing_masters.append(m)
                if r.active:
                    issues.append(Issue(r.name, m, "missing"))
    return Model(instance=inst, plugins=rows, order=order, issues=issues)
