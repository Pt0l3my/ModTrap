"""Which tool made a plugin (MT18, DESIGN§13, TL01): the evidence, strongest first, and what follows from it.

The marks and names are data (modtrap/data/tools.json), each with its source. This module only applies them."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "tools.json"
_tools: list[dict] | None = None


@dataclass(frozen=True)
class Evidence:
    tool: str            # the tool's name, or the executable's title in MO2 when the tool is not one ModTrap knows
    kind: str            # "patcher", "generator", "editor" or "tool" (unknown)
    how: str             # in words, for the page
    strong: bool         # weak evidence reads "probably made by"


def load() -> list[dict]:
    global _tools
    if _tools is None:
        with open(DATA, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
        _tools = [t for t in data["tools"] if isinstance(t, dict) and t.get("tool")]
    return _tools


def of_executable(title: str, binary: str = "") -> tuple[str, str]:
    """The tool an executable of MO2's list is, and its kind: (name, kind). Unknown ones keep their title."""
    hay = (title + " " + Path(binary.replace("\\", "/")).name).lower()
    for t in load():
        if any(w in hay for w in t.get("executables", [])):
            return t["tool"], t["kind"]
    return title, "tool"


def identify(plugin_name: str, author: str, mod_name: str, output_mods: dict[str, str],
             binaries: dict[str, str] | None = None) -> list[Evidence]:
    """Every piece of evidence for who made this plugin, strongest first.
    `output_mods` is MO2's own record: an executable's title to the mod its new files go to (MO01§2)."""
    out: list[Evidence] = []
    for title, target in sorted(output_mods.items()):
        if target.casefold() == mod_name.casefold():
            tool, kind = of_executable(title, (binaries or {}).get(title, ""))
            ev = Evidence(tool, kind, "MO2 sends the new files of “%s” to this plugin's mod" % title, True)
            if not any(e.tool == tool for e in out):
                out.append(ev)
    for t in load():
        if any(a.casefold() == author.strip().casefold() for a in t.get("author", [])) and author.strip():
            out.append(Evidence(t["tool"], t["kind"], "its author field reads “%s”" % author.strip(), True))
        elif any(re.search(rx, plugin_name, re.IGNORECASE) for rx in t.get("names", [])):
            out.append(Evidence(t["tool"], t["kind"], "its file name is one this tool gives its output", True))
        elif any(re.search(rx, plugin_name, re.IGNORECASE) for rx in t.get("weak_names", [])):
            out.append(Evidence(t["tool"], t["kind"], "its file name starts like this tool's output", False))
    seen: set[str] = set()
    unique = []
    for e in sorted(out, key=lambda e: not e.strong):
        if e.tool not in seen:
            seen.add(e.tool)
            unique.append(e)
    return unique


def proposal(evidence: list[Evidence]) -> str:
    """What to do with such a plugin when a mod it depends on is taken out. A tool's output is made again by
    running the tool ("run the tool again"; "probably" on weak evidence). The exception is an editor: what was
    written through it came from a script or from hand edits, which ModTrap cannot repeat, so it is demastered.
    A tool ModTrap does not know, but whose output mod MO2 records, counts as a tool, not as an editor."""
    if not evidence:
        return "demaster"
    makers = [e for e in evidence if e.kind != "editor"]
    if not makers:
        return "demaster"
    return "run the tool again" if any(e.strong for e in makers) else "probably run the tool again"
