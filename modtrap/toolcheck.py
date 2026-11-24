"""The tool check (MT23, DESIGN§34): what the plugins a tool made hold of the mods that are to leave, compared by
what the fields mean.

ModTrap's own reader compares bytes, which says nothing for a patcher that writes records in a form of its own
(TL01§13). xEdit knows what every field means. So, when the owner asks for it, ModTrap starts the owner's xEdit
through MO2 with a script of its own that only reports (modtrap/xedit/ModTrapTools.pas), as the record check does
(`records`), with the whole active load order loaded. For each record a tool's plugin holds on which a leaving
plugin has the last word, each part of the tool's copy says what the leaving plugin says (the tool has it from the
mod: run it again), or what the next in line says (nothing of the mod is in it), or neither (a value of the tool's
own, which it may have worked out from either).

The mods must still be in the load order: xEdit compares with their records. Nothing is changed; the tools'
plugins are hashed before and after to prove it.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import dryrun, logbook, model, paths, records, tools
from .instance import fold
from .records import Refused

log = logbook.get("toolcheck")
SCRIPT = Path(__file__).resolve().parent / "xedit" / "ModTrapTools.pas"
ROWS = 200                     # records told for one plugin, for the page


@dataclass
class Plan(records.Plan):
    mods: list[str] = field(default_factory=list)       # the mods to take out
    gone: list[str] = field(default_factory=list)       # the leaving plugins: theirs, and the patches made for them
    made: list[str] = field(default_factory=list)       # every plugin a tool made

    def public(self) -> dict:
        return dict(super().public(), mods=self.mods, gone=self.gone)


def tool_made(m: model.Model) -> dict[str, list]:
    """The active plugins a tool made (not an editor), by folded name, with the evidence (TL01§7)."""
    inst = m.instance
    binaries = {e.title: e.binary for e in inst.executables}
    out: dict[str, list] = {}
    for f in m.order:
        r = m.plugins[f]
        if r.source is None or r.path is None:
            continue
        ev = [e for e in tools.identify(r.name, r.author, r.source, inst.output_mods, binaries) if e.kind != "editor"]
        if ev:
            out[f] = ev
    return out


def plan(m: model.Model, mod_names: list[str], touched: dict | None = None) -> Plan:
    """`touched` is what a dry run of these mods told (the plugins whose own changes it looked at: the mods' and
    the patches made for them); without it the leaving plugins are the mods' own."""
    inst = m.instance
    trapped: dict[str, str] = {}
    for name in mod_names:
        mod = inst.mod(name)
        if mod is None or mod.kind != "mod":
            raise Refused("'%s' is not a mod of this profile" % name)
        if not mod.enabled:
            raise Refused("“%s” is disabled. xEdit compares a tool's plugin with the mod's own records, and can read them only "
                          "while the mod is in the load order: this check is for before the demaster is put in place. Now, run "
                          "the tool, or Revert the demaster first." % mod.name)
        for r in m.provided_by(mod):
            if r.active and r.path is not None and not r.primary:
                trapped[fold(r.name)] = r.name
    if not trapped:
        raise Refused("these mods have no active plugin: there is nothing of theirs for a tool's plugin to hold")
    gone = dict(trapped)
    for name in (touched or {}):
        r = m.plugins.get(fold(name)) if name else None
        if r is not None and r.active and r.source is not None:
            gone.setdefault(fold(r.name), r.name)
    made = tool_made(m)
    data = {t["tool"]: t for t in tools.load()}
    look = []
    for f, ev in made.items():
        r = m.plugins[f]
        if not r.active or f in gone or "plugins" not in data.get(ev[0].tool, {}).get("reads", ["plugins"]):
            continue
        if any(fold(x) in trapped for x in r.masters):
            continue                                    # a dependant: the demaster deals with it, the tool makes it anew
        look.append(r.name)
    if not look:
        raise Refused("no plugin of this modlist was made by a tool that reads plugins: there is nothing to check")
    rows = [m.plugins[f] for f in m.order if m.plugins[f].position is not None and m.plugins[f].active
            and m.plugins[f].source is not None]
    missing = sorted({i.plugin for i in m.issues})
    if missing:
        raise Refused("the load order has plugins with missing or inactive masters (%s): xEdit would stop at them. "
                      "See the Health tab." % ", ".join(missing[:4]))
    exe = dryrun.find_xedit_exe(inst)
    order = [r.name for r in rows]
    return Plan(new=[n for n in order if n in set(look)], load=order, mo2=str(inst.root / dryrun.MO2_EXE), profile=inst.profile,
                tool=exe.title, tool_binary=exe.binary, tool_args=exe.arguments, data_dir=dryrun.data_dir_of(inst),
                mods=sorted(mod_names), gone=[n for n in order if fold(n) in gone],
                made=[m.plugins[f].name for f in made])


def stamp(path: Path | None) -> list[int]:
    """What tells that a plugin is still the file that was checked, cheaply: its size and when it was written."""
    try:
        st = os.stat(path) if path is not None else None
    except OSError:
        st = None
    return [st.st_size, st.st_mtime_ns] if st is not None else [-1, -1]


def prepare(m: model.Model, p: Plan, job_dir: Path) -> dict:
    """The job's folder: the script, its job file, the plugin list for xEdit, and a hash of each plugin looked at.
    Writes nothing outside `job_dir`."""
    script_dir = job_dir / "script"
    script_dir.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script_dir / SCRIPT.name)
    lines = ["format=modtrap-job/1", "mode=tools", "out=%s" % (job_dir / "report.tsv"), "progress=%s" % (job_dir / "progress.txt")]
    for key, names in (("tool", p.new), ("gone", p.gone), ("made", p.made)):
        lines.append("%s.count=%d" % (key, len(names)))
        lines += ["%s.%d=%s" % (key, i, n) for i, n in enumerate(names)]
    paths.write_atomic(script_dir / "modtrap-job.txt", ("\r\n".join(lines) + "\r\n").encode("utf-8-sig"))
    primary = {fold(x) for x in m.instance.primary}
    listed = ["*" + n for n in p.load if fold(n) not in primary]
    try:
        text = ("\r\n".join(listed) + "\r\n").encode("mbcs" if os.name == "nt" else "cp1252")
    except UnicodeEncodeError:
        raise Refused("a plugin's name cannot be written in this PC's text encoding, which xEdit's plugin list "
                      "needs") from None
    paths.write_atomic(job_dir / "plugins.txt", text)
    hashes = {n: dryrun._sha256(m.plugins[fold(n)].path) for n in p.new}
    manifest = {"format": "modtrap-toolcheck/1", "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "profile": p.profile,
                "mods": p.mods, "gone": p.gone, "new": p.new, "load": len(p.load), "tool": p.tool, "sha256": hashes,
                "stamp": {n: stamp(m.plugins[fold(n)].path) for n in p.new}}
    paths.write_atomic(job_dir / "manifest.json", (json.dumps(manifest, indent=1) + "\n").encode("utf-8"))
    return manifest


def command(p: Plan, job_dir: Path) -> list[str]:
    return [p.mo2, "-p", p.profile, "run", "-e", "-a", dryrun.arguments(job_dir, SCRIPT.name, p.tool_args, p.data_dir), p.tool]


def _int(s: str) -> int:
    try:
        return int(s or 0)
    except ValueError:
        return 0


def parse_report(text: str) -> dict:
    """What the script found, for each tool's plugin: {"name", "records", "held" (records a leaving plugin holds
    too), "last_else" (of those, a plugin that stays has the last word), "mod" (records with a part that says what
    the leaving plugin says), "own" (a part of the tool's own, none of the mod's), "next", "same", "rows" (the mod
    and own records), "values", "verdict"}. The verdict: "mod" (it holds the mod's value: run the tool again),
    "own" (values of its own where the mod has the last word: it cannot be ruled out that they come from the mod),
    "clear" (nothing of the mod is in it)."""
    files: dict[str, dict] = {}
    out = {"format": "", "xedit": "", "files": [], "missing": [], "held_changed": [], "end": "", "reason": "", "data_path": ""}
    for line in text.split("\n"):
        f = line.rstrip("\r").split("\t")
        kind = f[0]
        if kind == "H" and len(f) >= 4:
            out["format"], out["xedit"] = f[1], f[3]
        elif kind == "P" and len(f) >= 2:
            out["data_path"] = f[1]
        elif kind == "F" and len(f) >= 3:
            files[fold(f[1])] = {"name": f[1], "records": _int(f[2]), "held": 0, "last_else": 0, "mod": 0, "own": 0, "next": 0,
                                 "same": 0, "rows": [], "rows_more": 0, "values": [], "done": False, "verdict": ""}
        elif kind == "K" and len(f) >= 10 and fold(f[1]) in files:
            d = files[fold(f[1])]
            if len(d["rows"]) < ROWS:
                d["rows"].append({"form": f[2], "kind": f[3], "owner": f[4], "by": f[5], "next_by": f[6],
                                  "mod": [x for x in f[7].split(",") if x], "next": [x for x in f[8].split(",") if x],
                                  "own": [x for x in f[9].split(",") if x]})
            else:
                d["rows_more"] += 1
        elif kind == "Y" and len(f) >= 8 and fold(f[1]) in files:
            files[fold(f[1])]["values"].append({"form": f[2], "what": f[3], "part": f[4], "tool": f[5], "mod": f[6], "next": f[7]})
        elif kind == "S" and len(f) >= 8 and fold(f[1]) in files:
            d = files[fold(f[1])]
            d["held"], d["last_else"], d["mod"], d["own"], d["next"], d["same"] = (_int(x) for x in f[2:8])
            d["done"] = True
            d["verdict"] = "mod" if d["mod"] else "own" if d["own"] else "clear"
        elif kind in ("M", "N") and len(f) >= 2:
            out["missing"].append(f[1])
        elif kind == "U" and len(f) >= 2:
            out["held_changed"].append(f[1])
        elif kind == "X" and len(f) >= 2:
            out["end"], out["reason"] = f[1], f[2] if len(f) > 2 else ""
    for d in files.values():
        d["rows"].sort(key=lambda r: (not r["mod"], r["kind"], r["form"]))
    out["files"] = list(files.values())
    return out


class Job(records.Job):
    """One tool check: the record check's run (`records.Job`), with the script that compares the tools' plugins."""

    WHAT = "tool check"
    THREAD = "toolcheck"

    def _prepare(self) -> dict:
        return prepare(self.model, self.plan, self.dir)

    def _command(self) -> list[str]:
        return command(self.plan, self.dir)

    def _parse(self, text: str) -> dict:
        return parse_report(text)

    def _does(self) -> str:
        return "with ModTrap's script that compares the tools' plugins with the leaving mods' records"

    def _told(self) -> None:
        for f in self.result["files"]:
            log.info("  %s: of %d record(s) a leaving plugin holds too, %d where a plugin that stays has the last word; %d with "
                     "the mod's value, %d with a value of the tool's own, %d as the next in line, %d with nothing to tell apart -> %s",
                     f["name"], f["held"], f["last_else"], f["mod"], f["own"], f["next"], f["same"],
                     {"mod": "it holds the mod's value", "own": "cannot be ruled out", "clear": "nothing of the mod in it"}.get(f["verdict"], "not read"))
            for v in f["values"][:12]:
                log.info("    %s %s: this plugin has %s; the mod has %s; the next in line has %s", v["form"], v["part"], v["tool"], v["mod"], v["next"])


def read_result(job_dir: Path) -> dict | None:
    """A finished check's findings by folded plugin name, each with the stamp of the file that was checked;
    None where the folder holds no finished check. {"mods", "when", "job", "files": {plugin: {...}}}"""
    try:
        with open(job_dir / "manifest.json", "rb") as f:
            man = json.loads(f.read(16 * 1024 * 1024).decode("utf-8"))
        with open(job_dir / "result.json", "rb") as f:
            res = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(man, dict) or not isinstance(res, dict) or res.get("end") != "ok":
        return None
    stamps = man.get("stamp", {})
    files = {fold(d["name"]): dict(d, stamp=stamps.get(d["name"], [-1, -1])) for d in res.get("files", []) if isinstance(d, dict) and d.get("done")}
    return {"mods": sorted(man.get("mods", [])), "when": man.get("when", ""), "job": job_dir.name, "gone": man.get("gone", []), "files": files}


__all__ = ["Plan", "Job", "Refused", "plan", "prepare", "command", "parse_report", "read_result", "stamp", "tool_made"]
