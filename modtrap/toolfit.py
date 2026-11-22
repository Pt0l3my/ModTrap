"""The patcher framework's library versions: do the ones its profile is set to fit the program? (MT27, WHY§89)

Synthesis builds each patcher on the owner's PC against two libraries, whose versions its profile names. A program
older than those versions builds for a .NET version they no longer support, and every patcher then fails with the
same error (TL01§18). Which versions fit is not guessed:

- the program's own log says, at its top, which versions of the two libraries the program itself was built with:
  those it can build for;
- the same log says, in its build errors, which library version did not fit;
- the program's settings file says which versions the profile is set to.

Only when all three agree that the profile is still set to a version the last log shows as not fitting does ModTrap
set the profile to the program's own pair, in the settings file, with a copy of that file kept first. Field names
as in Synthesis's source (TL01§19); nothing else in the file is touched.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

from . import logbook, paths, tools, toollog

log = logbook.get("tool")
SETTINGS = "PipelineSettings.json"
SETTINGS_MAX = 16 * 1024 * 1024
TOOL = "Synthesis"
MANUAL, LATEST = "Manual", "Latest"
_HOW = {1: "Latest", 2: "Match", 3: "Manual"}            # the profile's way of choosing a version, when kept as a number

_OWN_M = re.compile(r"\] Mutagen version: (?P<v>\d[\w.\-]*)\s*$")
_OWN_S = re.compile(r"\] Synthesis version: (?P<v>\d[\w.\-]*)\s*$")
_UNFIT = re.compile(r"error NU1202: Package (?P<package>Mutagen\.[\w.]+) (?P<version>\d[\w.\-]*) is not compatible with (?P<target>net[\d.]+)")


def log_facts(text: str) -> dict:
    """From one of the program's logs: the library versions the program was built with ({"mutagen", "synthesis"},
    each "" if not told), and the library versions its build errors name as not fitting."""
    own = {"mutagen": "", "synthesis": ""}
    unfit: dict[str, set[str]] = {"mutagen": set(), "synthesis": set()}
    target = ""
    for line in text.split("\n"):
        line = line.rstrip("\r")[:4000]
        if not own["mutagen"] and (m := _OWN_M.search(line)):
            own["mutagen"] = m.group("v")
        elif not own["synthesis"] and (m := _OWN_S.search(line)):
            own["synthesis"] = m.group("v")
        elif (m := _UNFIT.search(line)):
            which = "synthesis" if m.group("package").lower() == "mutagen.bethesda.synthesis" else "mutagen"
            unfit[which].add(m.group("version"))
            target = m.group("target")
    return {"own": own, "unfit": {k: sorted(v) for k, v in unfit.items()}, "target": target}


def _how(value: object) -> str:
    return _HOW.get(value, "") if isinstance(value, int) and not isinstance(value, bool) else (value if isinstance(value, str) else "")


def _load(folder: Path) -> tuple[dict, bytes] | None:
    f = folder / SETTINGS
    try:
        if not f.is_file() or f.stat().st_size > SETTINGS_MAX:
            return None
        raw = f.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"))
    except (OSError, ValueError):
        return None
    return (data, raw) if isinstance(data, dict) and isinstance(data.get("Profiles"), list) else None


def profiles(folder: Path) -> list[dict]:
    """Each profile of the settings file with how it chooses the two library versions, and which."""
    got = _load(folder)
    out = []
    for p in (got[0]["Profiles"] if got else []):
        if isinstance(p, dict):
            out.append({"profile": str(p.get("Nickname", ""))[:120],
                        "mutagen_how": _how(p.get("MutagenVersioning")), "mutagen": str(p.get("MutagenManualVersion") or ""),
                        "synthesis_how": _how(p.get("SynthesisVersioning")), "synthesis": str(p.get("SynthesisManualVersion") or "")})
    return out


def check(folder: Path) -> list[dict]:
    """The profiles whose library versions the program's newest log shows as not fitting, each with the pair to set:
    [{"profile", "was": {"mutagen", "synthesis"}, "now": {"mutagen", "synthesis"}, "target", "log"}]. [] when
    nothing is to be set, or when a fact is missing (no log, no versions at its top, no such error in it)."""
    spec = toollog.spec_for(TOOL, TOOL.lower() + ".exe")
    if spec is None:
        return []
    path = toollog.newest(folder / str(spec["folder"]), str(spec.get("pattern", "*.log")), 0.0)
    if path is None:
        return []
    try:
        facts = log_facts(toollog.read(path))
    except OSError:
        return []
    own = facts["own"]
    if not own["mutagen"] or not own["synthesis"] or not (facts["unfit"]["mutagen"] or facts["unfit"]["synthesis"]):
        return []
    out = []
    for p in profiles(folder):
        bad_m = (p["mutagen_how"] == MANUAL and p["mutagen"] in facts["unfit"]["mutagen"]) or \
                (p["mutagen_how"] == LATEST and bool(facts["unfit"]["mutagen"]))
        bad_s = (p["synthesis_how"] == MANUAL and p["synthesis"] in facts["unfit"]["synthesis"]) or \
                (p["synthesis_how"] == LATEST and bool(facts["unfit"]["synthesis"]))
        if not (bad_m or bad_s):
            continue
        was = {"mutagen": p["mutagen"] if p["mutagen_how"] == MANUAL else p["mutagen_how"].lower() or "not set",
               "synthesis": p["synthesis"] if p["synthesis_how"] == MANUAL else p["synthesis_how"].lower() or "not set"}
        if was == own:
            continue
        out.append({"profile": p["profile"], "was": was, "now": dict(own), "target": facts["target"], "log": path.name})
    return out


def apply(folder: Path, found: list[dict], keep_in: Path) -> list[dict]:
    """Sets each found profile to the program's own pair of library versions, chosen by hand ("Manual"), in the
    settings file. A copy of the file as it was is in `keep_in` first. Returns what was set, as `found` with
    "kept" added; raises OSError or ValueError when the file cannot be read or written (nothing is changed then)."""
    got = _load(folder)
    if got is None:
        raise ValueError("the settings file cannot be read")
    data, raw = got
    wanted = {f["profile"]: f for f in found}
    done = []
    for p in data["Profiles"]:
        if not isinstance(p, dict) or str(p.get("Nickname", ""))[:120] not in wanted:
            continue
        f = wanted[str(p.get("Nickname", ""))[:120]]
        for key in ("MutagenVersioning", "SynthesisVersioning"):                 # kept as the file keeps it: a word or a number
            p[key] = 3 if isinstance(p.get(key), int) and not isinstance(p.get(key), bool) else MANUAL
        p["MutagenManualVersion"], p["SynthesisManualVersion"] = f["now"]["mutagen"], f["now"]["synthesis"]
        done.append(f)
    if not done:
        return []
    keep_in.mkdir(parents=True, exist_ok=True)
    kept = keep_in / ("%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), SETTINGS))
    n = 2
    while kept.exists():
        kept, n = keep_in / ("%s-%d-%s" % (time.strftime("%Y%m%d-%H%M%S"), n, SETTINGS)), n + 1
    shutil.copyfile(folder / SETTINGS, kept)
    if kept.read_bytes() != raw:
        raise OSError("the settings file changed while ModTrap read it")
    text = json.dumps(data, indent=2, ensure_ascii=False)
    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    end = "\r\n" if b"\r\n" in raw else "\n"
    paths.write_atomic(folder / SETTINGS, bom + text.replace("\n", end).encode("utf-8"))
    return [dict(f, kept=kept.name) for f in done]


def is_tool(title: str, binary: str) -> bool:
    return tools.of_executable(title, binary)[0] == TOOL


def words(f: dict) -> str:
    return ("Synthesis's profile “%s” was set to library versions its last log (%s) shows as not fitting this "
            "Synthesis (Mutagen %s, Synthesis %s; it builds for %s). ModTrap set them to the versions this Synthesis "
            "was built with, as its log states them: Mutagen %s, Synthesis %s" % (
                f["profile"], f["log"], f["was"]["mutagen"], f["was"]["synthesis"], f["target"] or "an older .NET",
                f["now"]["mutagen"], f["now"]["synthesis"]))


__all__ = ["apply", "check", "is_tool", "log_facts", "profiles", "words"]
