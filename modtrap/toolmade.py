"""What the modlist's tools made, as far as their own files say it (TL01§14, WHY§74).

Two readings, both of files only, nothing run:

- A tool-made plugin, by the kinds of record it holds: a patcher that only ever writes cells and landscape has
  nothing to say about a mod's characters. Read with ModTrap's own reader (record headers only).
- The patcher framework's own settings file: which patchers make each of its output plugins, whether each is
  switched on, and which plugins it was told to leave out for an output (TL01§14). Its patchers' own settings
  are searched for the name of a plugin.

Names of plugins, patchers and record kinds only; no record's content is kept."""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from pathlib import Path

from . import logbook, model, plugin, tools
from .instance import Instance, fold

log = logbook.get("tools")
SETTINGS_MAX = 16 * 1024 * 1024
PLUGIN_SECONDS = 12.0
ALL_SECONDS = 90.0
SEARCH_SECONDS = 3.0
SEARCH_FILE = 2 * 1024 * 1024
SEARCH_FILES = 600


def kinds_of(path: Path, seconds: float = PLUGIN_SECONDS) -> dict:
    """How many records of each kind a plugin holds: {"records", "kinds": [[kind, count], ...], "cut"}."""
    try:
        with plugin.Records(path, seconds) as r:
            count = Counter(v[3] for v in r.index.values())
            return {"records": len(r.index), "kinds": [[k, n] for k, n in count.most_common()], "cut": r.cut}
    except (plugin.Unreadable, OSError):
        return {"records": 0, "kinds": [], "cut": True}


def _name(x: object) -> str:
    return x if isinstance(x, str) else ""


def synthesis_groups(folders: list[Path]) -> list[dict]:
    """The framework's own account of what it makes (TL01§14): for each group of patchers that is its own output
    plugin, the patchers in order and the plugins left out. [] when its settings file is not there or not read."""
    for folder in folders:
        f = folder / "PipelineSettings.json"
        try:
            if not f.is_file() or f.stat().st_size > SETTINGS_MAX:
                continue
            data = json.loads(f.read_bytes().decode("utf-8-sig"))
        except (OSError, ValueError):
            continue
        out = []
        for prof in (data.get("Profiles") if isinstance(data, dict) else None) or []:
            if not isinstance(prof, dict):
                continue
            groups = prof.get("Groups")
            if not isinstance(groups, list):          # the older layout: one list of patchers, one output
                groups = [{"Name": "Synthesis", "On": True, "Patchers": prof.get("Patchers") or [], "BlacklistedMods": []}]
            for g in groups:
                if not isinstance(g, dict):
                    continue
                patchers = []
                for p in g.get("Patchers") or []:
                    if not isinstance(p, dict):
                        continue
                    repo = _name(p.get("RemoteRepoPath")) or _name(p.get("ProjectSubpath")) or _name(p.get("PathToExecutable"))
                    name = _name(p.get("Nickname")) or repo.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
                    if name:
                        patchers.append({"name": name[:120], "on": p.get("On") is not False})
                out.append({"profile": _name(prof.get("Nickname"))[:120], "group": _name(g.get("Name"))[:120],
                            "on": g.get("On") is not False, "patchers": patchers,
                            "left_out": sorted({_name(x) for x in g.get("BlacklistedMods") or [] if _name(x)}, key=fold)})
        return out
    return []


def group_of(plugin_name: str, groups: list[dict]) -> dict | None:
    """The group whose output this plugin is: the plugin is named after the group."""
    stem = fold(plugin_name.rsplit(".", 1)[0])
    exact = [g for g in groups if fold(g["group"]) == stem]
    if exact:
        return next((g for g in exact if g["on"]), exact[0])
    # an output split in parts carries the group's name and a number
    part = [g for g in groups if g["group"] and stem.startswith(fold(g["group"])) and stem[len(g["group"]):].strip(" _-").isdigit()]
    return part[0] if part else None


def tool_folders(inst: Instance, tool: str) -> list[Path]:
    """Where a tool of MO2's list lives: its program's folder, and the folder MO2 starts it in."""
    out: list[Path] = []
    for e in inst.executables:
        if tools.of_executable(e.title, e.binary)[0] != tool:
            continue
        for raw in (str(Path(e.binary.replace("\\", "/")).parent), e.working_directory.replace("\\", "/")):
            if raw and raw != "." and Path(raw) not in out:
                out.append(Path(raw))
    return out


def named_in_settings(folders: list[Path], plugin_names: list[str]) -> list[dict]:
    """The settings files of a tool's patchers (its Data folder) that name one of these plugins."""
    needles = [(n, n.lower().encode("utf-8")) for n in plugin_names]
    out: list[dict] = []
    until, seen = time.monotonic() + SEARCH_SECONDS, 0
    for folder in folders:
        base = folder / "Data"
        try:
            walk = os.walk(base)
        except OSError:
            continue
        for here, _dirs, files in walk:
            for name in files:
                if not name.lower().endswith((".json", ".txt", ".ini", ".toml", ".yaml", ".yml")):
                    continue
                seen += 1
                if seen > SEARCH_FILES or time.monotonic() > until:
                    return out
                f = Path(here) / name
                try:
                    if f.stat().st_size > SEARCH_FILE:
                        continue
                    data = f.read_bytes().lower()
                except OSError:
                    continue
                hit = [n for n, b in needles if b in data]
                if hit:
                    out.append({"file": f.relative_to(folder).as_posix(), "names": hit})
    return out


def made(m: model.Model) -> dict:
    """Every plugin a tool made in this modlist: the tool, how ModTrap knows, its records by kind, its masters, and
    for the patcher framework the patchers behind it."""
    inst = m.instance
    binaries = {e.title: e.binary for e in inst.executables}
    groups = synthesis_groups(tool_folders(inst, "Synthesis"))
    rows, until = [], time.monotonic() + ALL_SECONDS
    for f in m.order:
        r = m.plugins[f]
        if r.source is None or r.path is None:
            continue
        ev = [e for e in tools.identify(r.name, r.author, r.source, inst.output_mods, binaries) if e.kind != "editor"]
        if not ev:
            continue
        left = until - time.monotonic()
        prof = kinds_of(r.path, min(PLUGIN_SECONDS, left)) if left > 0 else {"records": 0, "kinds": [], "cut": True}
        row = {"plugin": r.name, "mod": r.source, "tool": ev[0].tool, "how": ev[0].how, "strong": ev[0].strong,
               "active": r.active, "masters": len(r.masters), **prof}
        g = group_of(r.name, groups) if ev[0].tool == "Synthesis" else None
        if g is not None:
            row["made_by"] = {"group": g["group"], "patchers": g["patchers"], "left_out": len(g["left_out"])}
        rows.append(row)
    log.info("what the tools made: %d plugin(s) of %d tool(s) read", len(rows), len({x["tool"] for x in rows}))
    return {"plugins": rows, "synthesis_settings": bool(groups)}


__all__ = ["kinds_of", "synthesis_groups", "group_of", "tool_folders", "named_in_settings", "made"]
