"""A mod's installer file (MT21, DESIGN§16.1, MO02): the questions it asks, which options are allowed for the
answers so far, and the files the answers install.

Some archives carry `fomod/ModuleConfig.xml`: steps of grouped options, each option naming files or folders of the
archive and where they go, with conditions on earlier answers and on the load order. This module reads that file,
works out what to show for a set of answers, and builds the mod's folder from them, inside ModTrap's own work
folder. It is ModTrap's own code, written from the format as MO2's installer reads it (MO02); no code of MO2's.

The file is someone else's: it is size-capped, refused if it declares entities, and every path it names is checked
to stay inside the archive and inside the folder being built.
"""

from __future__ import annotations

import os
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .unpack import safe_parts

MAX_XML = 8 * 1024 * 1024
MAX_OPTIONS = 5000
GROUP_TYPES = ("SelectAtLeastOne", "SelectAtMostOne", "SelectExactlyOne", "SelectAny", "SelectAll")
OPTION_TYPES = ("Required", "Optional", "Recommended", "NotUsable", "CouldBeUsable")


class Unreadable(Exception):
    """The installer file cannot be used; the text says why."""


@dataclass
class FileEntry:
    source: str
    destination: str
    folder: bool
    priority: int
    seq: int


@dataclass
class Condition:
    """A leaf (kind "file", "flag" or "version") or a group of conditions joined by And or Or."""
    kind: str
    a: str = ""                     # file: the plugin's name; flag: the flag's name
    b: str = ""                     # file: Active, Inactive or Missing; flag: the value
    any: bool = False               # a group: Or
    parts: list["Condition"] = field(default_factory=list)


@dataclass
class Option:
    name: str
    description: str
    files: list[FileEntry]
    flags: dict[str, str]
    default_type: str
    patterns: list[tuple[Condition, str]]


@dataclass
class Group:
    name: str
    type: str
    options: list[Option]


@dataclass
class Step:
    name: str
    visible: Condition | None
    groups: list[Group]


@dataclass
class Installer:
    name: str
    required: list[FileEntry]
    steps: list[Step]
    conditional: list[tuple[Condition, list[FileEntry]]]


# --- reading ----------------------------------------------------------------------------------------------------------

def _names(folder: Path) -> list[os.DirEntry]:
    try:
        with os.scandir(folder) as it:
            return list(it)
    except OSError:
        return []


def find(folder: Path) -> Path | None:
    """`fomod/ModuleConfig.xml` under `folder`, whatever the letters' case."""
    for d in _names(folder):
        if d.is_dir(follow_symlinks=False) and d.name.lower() == "fomod":
            for f in _names(Path(d.path)):
                if f.is_file(follow_symlinks=False) and f.name.lower() == "moduleconfig.xml":
                    return Path(f.path)
    return None


def _parse(data: bytes) -> ET.Element:
    def refuse_rules(text: str) -> None:
        low = text.lower()
        if "<!doctype" in low or "<!entity" in low:
            raise Unreadable("The installer file declares its own document rules, which ModTrap does not read.")

    refuse_rules(data.decode("latin-1").replace("\x00", ""))        # whatever the encoding, also two-byte ones
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        pass
    # MO02§2: a file whose header names the wrong encoding is common; the header is dropped and the text tried
    # as UTF-16, UTF-8 and Latin-1.
    for coding in ("utf-16", "utf-8-sig", "latin-1"):
        try:
            text = data.decode(coding)
        except UnicodeError:
            continue
        refuse_rules(text)
        text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text.lstrip("\ufeff"), count=1)
        try:
            return ET.fromstring(text)
        except ET.ParseError:
            continue
    raise Unreadable("The installer file is not readable XML.")


def _order(items: list, attr: str | None, key: Callable) -> list:
    """MO02§3: Ascending (also when nothing is said) and Descending sort by name; Explicit keeps the file's order."""
    if attr == "Explicit":
        return items
    return sorted(items, key=lambda x: key(x).lower(), reverse=attr == "Descending")


class _Reader:
    def __init__(self) -> None:
        self.seq = 0
        self.options = 0

    def files(self, node: ET.Element | None) -> list[FileEntry]:
        out = []
        for e in (node if node is not None else []):
            if e.tag not in ("file", "folder"):
                continue
            src = e.get("source", "")
            if not src:
                continue                        # MO02§4: an entry with no source installs nothing
            try:
                prio = int(e.get("priority", "0"))
            except ValueError:
                prio = 0
            self.seq += 1
            out.append(FileEntry(src, e.get("destination", src), e.tag == "folder", prio, self.seq))
        return out

    def condition(self, node: ET.Element) -> Condition:
        group = Condition("group", any=node.get("operator") == "Or")
        for e in node:
            if e.tag == "fileDependency":
                group.parts.append(Condition("file", e.get("file", ""), e.get("state", "")))
            elif e.tag == "flagDependency":
                group.parts.append(Condition("flag", e.get("flag", ""), e.get("value", "")))
            elif e.tag in ("gameDependency", "fommDependency", "foseDependency"):
                group.parts.append(Condition("version", e.tag, e.get("version", "")))
            elif e.tag == "dependencies":
                group.parts.append(self.condition(e))
        return group

    def option(self, node: ET.Element) -> Option:
        self.options += 1
        if self.options > MAX_OPTIONS:
            raise Unreadable("The installer has more options than ModTrap shows.")
        desc = (node.findtext("description") or "").strip()
        flags = {f.get("name", ""): (f.text or "").strip() for f in node.findall("conditionFlags/flag") if f.get("name")}
        default, patterns = "Optional", []
        td = node.find("typeDescriptor")
        if td is not None:
            if td.find("type") is not None:
                default = td.find("type").get("name", "Optional")
            dt = td.find("dependencyType")
            if dt is not None:
                if dt.find("defaultType") is not None:
                    default = dt.find("defaultType").get("name", "Optional")
                for p in dt.findall("patterns/pattern"):
                    dep, typ = p.find("dependencies"), p.find("type")
                    if dep is not None and typ is not None and typ.get("name") in OPTION_TYPES:
                        patterns.append((self.condition(dep), typ.get("name")))
        if default not in OPTION_TYPES:
            default = "Optional"
        return Option(node.get("name", "").strip() or "(no name)", desc[:4000], self.files(node.find("files")),
                      flags, default, patterns)

    def step(self, s: ET.Element) -> Step:
        groups = []
        gnode = s.find("optionalFileGroups")
        for g in (gnode.findall("group") if gnode is not None else []):
            pnode = g.find("plugins")
            opts = [self.option(p) for p in (pnode.findall("plugin") if pnode is not None else [])]
            opts = _order(opts, pnode.get("order") if pnode is not None else None, lambda o: o.name)
            gtype = g.get("type", "SelectAny")
            groups.append(Group(g.get("name", "").strip(), gtype if gtype in GROUP_TYPES else "SelectAny", opts))
        groups = _order(groups, gnode.get("order") if gnode is not None else None, lambda x: x.name)
        vis = s.find("visible")
        return Step(s.get("name", "").strip(), self.condition(vis) if vis is not None else None, groups)

    def installer(self, root: ET.Element) -> Installer:
        """Everything is read in the file's own order, which numbers the file entries (MO02§4); steps, groups and
        options are put in their shown order afterwards."""
        required: list[FileEntry] = []
        steps: list[Step] = []
        conditional: list[tuple[Condition, list[FileEntry]]] = []
        for node in root:
            if node.tag == "requiredInstallFiles":
                required += self.files(node)
            elif node.tag == "installSteps":
                steps += _order([self.step(x) for x in node.findall("installStep")], node.get("order"), lambda x: x.name)
            elif node.tag == "conditionalFileInstalls":
                for p in node.findall("patterns/pattern"):
                    dep = p.find("dependencies")
                    if dep is not None:
                        conditional.append((self.condition(dep), self.files(p.find("files"))))
        return Installer((root.findtext("moduleName") or "").strip(), required, steps, conditional)


def read(path: Path) -> Installer:
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_XML + 1)
    except OSError as e:
        raise Unreadable("The installer file could not be opened (%s)." % type(e).__name__) from None
    if len(data) > MAX_XML:
        raise Unreadable("The installer file is larger than ModTrap reads.")
    root = _parse(data)
    if root.tag != "config":
        raise Unreadable("The installer file is not an installer's description.")
    return _Reader().installer(root)


def from_folders(names: list[str]) -> Installer:
    """An archive that holds several folders to choose from and no installer file: one question, any of them."""
    opts = [Option(n, "", [FileEntry(n, "", True, i, i)], {}, "Optional", []) for i, n in enumerate(names)]
    return Installer("", [], [Step("Which parts to install", None, [Group(
        "The archive's folders. A later one in the list wins a file two of them share.", "SelectAny", opts)])], [])


# --- answering ---------------------------------------------------------------------------------------------------------

def _test(c: Condition, flags: dict[str, str], plugin_state: Callable[[str], str]) -> bool:
    if c.kind == "file":
        return plugin_state(c.a) == c.b
    if c.kind == "flag":
        return flags[c.a] == c.b if c.a in flags else c.b == ""       # MO02§5: an unset flag equals only ""
    if c.kind == "version":
        return True                              # ModTrap does not know the game's version: taken as met
    results = [_test(p, flags, plugin_state) for p in c.parts]
    return any(results) if c.any else all(results)


def view(inst: Installer, picks: dict[str, list[int]], plugin_state: Callable[[str], str]) -> dict:
    """The installer as it stands for these answers: the steps that show, each option's standing and whether it is
    chosen. `picks` maps "step.group" to the chosen options' numbers for the groups the owner has answered; other
    groups take what the installer recommends. Steps are worked through in order, each seeing the flags of the
    choices before it (MO02§5)."""
    flags: dict[str, str] = {}
    steps_out = []
    chosen_files: list[FileEntry] = []
    problems: list[str] = []
    for si, step in enumerate(inst.steps):
        if step.visible is not None and not _test(step.visible, flags, plugin_state):
            continue
        groups_out = []
        step_flags: dict[str, str] = {}
        for gi, group in enumerate(step.groups):
            key = "%d.%d" % (si, gi)
            types = []
            for o in group.options:
                t = next((typ for cond, typ in o.patterns if _test(cond, flags, plugin_state)), o.default_type)
                types.append(t)
            n = len(group.options)
            if group.type == "SelectAll":
                sel = list(range(n))
            elif key in picks:
                sel = [i for i in dict.fromkeys(picks[key]) if isinstance(i, int) and 0 <= i < n and types[i] != "NotUsable"]
            else:
                sel = [i for i in range(n) if types[i] in ("Required", "Recommended")]
            single = group.type in ("SelectExactlyOne", "SelectAtMostOne")
            required = [i for i in range(n) if types[i] == "Required"]
            if single:
                sel = (required[:1] or sel[:1])
            else:
                sel = sorted(set(sel) | set(required))
            if not sel and group.type in ("SelectExactlyOne", "SelectAtLeastOne") and n:
                # MO02§6: one must be chosen: the first that is merely optional, else the first that could be
                # used, else the first of all.
                first = next((i for i in range(n) if types[i] == "Optional"), None)
                if first is None:
                    first = next((i for i in range(n) if types[i] == "CouldBeUsable"), 0)
                sel = [first]
            if group.type == "SelectAtLeastOne" and not sel:
                problems.append("“%s” needs at least one choice." % (group.name or step.name))
            forced = set(required) if not single else (set(required[:1]) if required else set())
            groups_out.append({"key": key, "name": group.name, "type": group.type, "single": single,
                               "none_allowed": group.type == "SelectAtMostOne" and not required,
                               "options": [{"n": i, "name": o.name, "description": o.description, "type": types[i],
                                            "chosen": i in sel,
                                            "locked": group.type == "SelectAll" or i in forced or types[i] == "NotUsable"
                                            or (single and bool(required))}
                                           for i, o in enumerate(group.options)]})
            for i in sel:
                chosen_files += group.options[i].files
                step_flags.update(group.options[i].flags)
        flags.update(step_flags)
        steps_out.append({"name": step.name, "groups": groups_out})
    files = list(inst.required)
    for cond, entries in inst.conditional:
        if _test(cond, flags, plugin_state):
            files += entries
    files += chosen_files
    files.sort(key=lambda f: (f.priority, f.seq))          # MO02§4: by priority, then as the file lists them
    return {"name": inst.name, "steps": steps_out, "problems": problems, "files": files}


# --- what an option is for (MT81) ---------------------------------------------------------------------------------------

PLUGIN_NAME = re.compile(r"\.(esp|esm|esl)$", re.IGNORECASE)
MASTERS_OPTIONS = 600                # options whose plugins are read for their masters, at most


def wants(option: Option) -> list[str]:
    """The plugins the installer itself says an option goes with: the ones its conditions ask to be active."""
    out: list[str] = []

    def walk(c: Condition) -> None:
        if c.kind == "file" and c.b == "Active" and c.a and c.a not in out:
            out.append(c.a)
        for part in c.parts:
            walk(part)
    for cond, _typ in option.patterns:
        walk(cond)
    return out


def plugins_of(entries: list[FileEntry], root: Path) -> list[Path]:
    """The plugins these file entries would install, as they lie in the unpacked archive: a file entry that is a
    plugin, and the plugins directly inside a folder entry."""
    out: list[Path] = []
    for f in entries:
        at = _find_ci(root, tuple(x for x in f.source.replace("\\", "/").split("/") if x not in ("", ".")))
        if at is None:
            continue
        if f.folder:
            out += [Path(e.path) for e in _names(at) if PLUGIN_NAME.search(e.name) and e.is_file(follow_symlinks=False)]
        elif PLUGIN_NAME.search(at.name) and at.is_file():
            out.append(at)
    return out


def needs(inst: Installer, root: Path, masters_of: Callable[[Path], list[str]]) -> dict:
    """For each option, by "step.group.option", the plugins it goes with that the installer does not bring itself:
    the ones its conditions name, and the masters of the plugins it installs (read from the unpacked archive).
    The game's own plugins are the caller's to leave out."""
    own = {p.name.lower() for p in plugins_of(list(inst.required) + [f for _c, fs in inst.conditional for f in fs], root)}
    per: dict[str, tuple[list[str], list[Path]]] = {}
    n = 0
    for si, step in enumerate(inst.steps):
        for gi, group in enumerate(step.groups):
            for oi, o in enumerate(group.options):
                n += 1
                mine = plugins_of(o.files, root) if n <= MASTERS_OPTIONS else []
                own |= {p.name.lower() for p in mine}
                per["%d.%d.%d" % (si, gi, oi)] = (wants(o), mine)
    out: dict[str, list[str]] = {}
    memo: dict[Path, list[str]] = {}
    for key, (asked, mine) in per.items():
        names = list(asked)
        for path in mine:
            if path not in memo:
                memo[path] = masters_of(path)
            names += memo[path]
        seen: set[str] = set()
        out[key] = [x for x in names if x.lower() not in own and not (x.lower() in seen or seen.add(x.lower()))]
    return out


# --- what an older version was installed with (MT84) ---------------------------------------------------------------

LANDS_FILES = 60_000                 # files of an installer's options that are followed to where they would land, at most


def chosen(steps: list[dict]) -> list[dict]:
    """The answers of a view, by name: [{"step", "group", "options": the chosen options' names}] for every group
    that showed. Names, not numbers: a newer version's installer may list its options in another order."""
    return [{"step": st["name"], "group": g["name"], "options": [o["name"] for o in g["options"] if o["chosen"]]}
            for st in steps for g in st["groups"]]


def prior_picks(inst: Installer, before: list[dict]) -> dict[str, list[int]]:
    """Answers given to an older version's installer, as picks for this one: for each group of this installer that
    the older answers have too (by its step's and its own name, or by its own name where only one group has it),
    the options of the same names. A group the older installer did not have is left to this one's own suggestion."""
    low = lambda t: " ".join(str(t or "").lower().split())
    out: dict[str, list[int]] = {}
    for si, step in enumerate(inst.steps):
        for gi, group in enumerate(step.groups):
            same = [b for b in before if low(b.get("group")) == low(group.name) and low(b.get("step")) == low(step.name)]
            if not same:
                same = [b for b in before if low(b.get("group")) == low(group.name)]
            if len(same) != 1:
                continue
            names = {low(n) for n in same[0].get("options") or []}
            out["%d.%d" % (si, gi)] = [i for i, o in enumerate(group.options) if low(o.name) in names]
    return out


def lands(entries: list[FileEntry], root: Path, budget: list[int]) -> dict[str, Path] | None:
    """Where these file entries would put which file of the unpacked archive: {the place in the mod, lower case:
    the file}. None where it cannot be followed (an entry outside the archive, or more files than are counted)."""
    out: dict[str, Path] = {}
    for f in entries:
        src_parts = safe_parts(f.source)
        raw_dest = f.destination.replace("\\", "/")
        if src_parts is None:
            return None
        src = _find_ci(root, src_parts)
        if src is None or src.is_symlink() or (f.folder and not src.is_dir()) or (not f.folder and not src.is_file()):
            continue
        if f.folder:
            dparts = safe_parts(raw_dest) if raw_dest.strip("/") else ()
            if dparts is None:
                return None
            for base, _dirs, names in os.walk(src):
                for n in names:
                    full = Path(base) / n
                    budget[0] -= 1
                    if budget[0] < 0:
                        return None
                    if not full.is_symlink():
                        out["/".join((*dparts, *full.relative_to(src).parts)).lower()] = full
        else:
            if raw_dest == "" or raw_dest.endswith("/"):
                raw_dest += src.name
            dparts = safe_parts(raw_dest)
            if dparts is None:
                return None
            budget[0] -= 1
            out["/".join(dparts).lower()] = src
    return out


def _same_bytes(a: Path, b: Path) -> bool:
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        with open(a, "rb") as fa, open(b, "rb") as fb:
            while True:
                x, y = fa.read(1 << 20), fb.read(1 << 20)
                if x != y:
                    return False
                if not x:
                    return True
    except OSError:
        return False


def in_older(inst: Installer, root: Path, older: dict[str, Path]) -> set[str]:
    """The options of this installer whose files are in an older version's folder, by "step.group.option": what that
    version was, as far as its files tell, installed with. `older`: the older mod's files, {place in lower case:
    file}. An option counts where every file it alone would install is there. Where several options of one group
    count and they would put files in the same places, the one whose files are the same, byte for byte, is taken;
    where that does not tell them apart, none is. Options that install nothing of their own say nothing."""
    budget = [LANDS_FILES]
    always = lands(list(inst.required), root, budget)
    if always is None:
        return set()
    out: set[str] = set()
    for si, step in enumerate(inst.steps):
        for gi, group in enumerate(step.groups):
            mine: dict[int, dict[str, Path]] = {}
            for oi, o in enumerate(group.options):
                got = lands(o.files, root, budget)
                if got is None:
                    return out
                own = {d: p for d, p in got.items() if d not in always}
                if own and all(d in older for d in own):
                    mine[oi] = own
            for oi, own in mine.items():
                rivals = [k for k, other in mine.items() if k != oi and set(other) & set(own)]
                if not rivals:
                    out.add("%d.%d.%d" % (si, gi, oi))
                    continue
                exact = lambda k: all(_same_bytes(p, older[d]) for d, p in mine[k].items())
                if exact(oi) and not any(exact(k) for k in rivals):
                    out.add("%d.%d.%d" % (si, gi, oi))
    return out


# --- building the mod's folder -----------------------------------------------------------------------------------------

def _find_ci(base: Path, parts: tuple[str, ...]) -> Path | None:
    """`parts` under `base`, matching each name whatever its letters' case (archives are made on Windows)."""
    cur = base
    for p in parts:
        nxt = cur / p
        if not nxt.exists():
            nxt = next((Path(e.path) for e in _names(cur) if e.name.lower() == p.lower()), None)
            if nxt is None:
                return None
        cur = nxt
    return cur


def build(files: list[FileEntry], root: Path, dest: Path) -> dict:
    """Copies what the answers install from the unpacked archive `root` into the new folder `dest`, in order, a
    later entry replacing an earlier one's file (MO02§4). Returns what was copied and what the installer named
    but the archive does not have."""
    dest.mkdir(parents=True, exist_ok=False)
    copied, missing = 0, []
    try:
        for f in files:
            src_parts = safe_parts(f.source)
            raw_dest = f.destination.replace("\\", "/")
            if src_parts is None:
                raise Unreadable("The installer names a file outside the archive. ModTrap does not follow it.")
            src = _find_ci(root, src_parts)
            if src is None or src.is_symlink() or (f.folder and not src.is_dir()) or (not f.folder and not src.is_file()):
                missing.append(f.source)
                continue
            if f.folder:
                dparts = safe_parts(raw_dest) if raw_dest.strip("/") else ()
                if dparts is None:
                    raise Unreadable("The installer puts a folder outside the mod. ModTrap does not follow it.")
                for base, _dirs, names in os.walk(src):
                    for n in names:
                        full = Path(base) / n
                        if full.is_symlink():
                            continue
                        target = dest.joinpath(*dparts, *full.relative_to(src).parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(full, target)
                        copied += 1
            else:
                if raw_dest == "" or raw_dest.endswith("/"):
                    raw_dest += src.name                  # MO02§4: a destination that names a folder keeps the name
                dparts = safe_parts(raw_dest)
                if dparts is None:
                    raise Unreadable("The installer puts a file outside the mod. ModTrap does not follow it.")
                target = dest.joinpath(*dparts)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, target)
                copied += 1
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return {"copied": copied, "missing": missing}


__all__ = ["Installer", "Unreadable", "build", "chosen", "find", "from_folders", "in_older", "lands", "needs", "prior_picks", "read", "view", "wants"]
