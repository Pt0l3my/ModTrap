"""What a mod does at its place, weighed (MT65, DESIGN§25).

The scanner of DESIGN§21 says which files a mod shares with which mods. This says what that comes to: which of the
overwrites change nothing, which are what a patch or a retexture is for, and which are the usual ways a modlist
breaks when a mod is added. It also looks at the mod's own files for the formats of the older game.

Reading only, bounded in time. A file is opened to compare it with the file it overwrites, or for the first bytes
that say what format it is in; nothing of it is kept. Every finding is {"key", "level", "title", "text", "items",
"more"}; levels: "bad" (likely a fault), "warn" (worth a look), "info", "good" (looked at, and fine).

What the checks rest on is in TL01§33 (the formats' marks) and WHY§130 (what is, and is not, read from them).
"""

from __future__ import annotations

import os
import re
import struct
import time
from pathlib import Path

from . import adding, logbook, model, pex, plugin, steps
from .instance import Mod, fold

log = logbook.get("evaluate")
SECONDS = 15.0
ITEMS = 40                      # lines kept for one finding
COMPARE_ONE = 64 * 1024 * 1024  # a larger file is not compared byte for byte
SCRIPTS = 600                   # compiled scripts of one mod read at most, for what calls a script extender plugin
COMPARE_ALL = 768 * 1024 * 1024
HEADERS = 600                   # files of one kind whose first bytes are read
PLUGIN_BYTES = 300 * 1024 * 1024

PAPERS = re.compile(r"^[^/]+\.(txt|md|pdf|rtf|docx?|html?|jpe?g|png|gif|bmp|webp|url|7z|zip|rar)$|^(fomod|docs?|readmes?|screenshots?|images)/"
                    r"|(^|/)(readme|license|licence|changelog|credits|permissions)[^/]*$", re.IGNORECASE)
SKELETON = re.compile(r"(^|/)skeleton[^/]*\.(nif|hkx)$", re.IGNORECASE)
SUFFIX = re.compile(r"_(n|msn|s|sk|g|m|em|e|p|b|bl|d|h|hl|rmaos|o|f)\.dds$", re.IGNORECASE)
DATA_FOLDERS = {"meshes", "textures", "scripts", "interface", "sound", "music", "skse", "seq", "strings", "video", "shadersfx", "lodsettings", "grass",
                "dyndolod", "calientetools", "netscriptframework", "nemesis_engine", "pandora_engine", "mcm", "source", "platform", "materials",
                "shaders", "facegen", "dialogueviews", "distantlod", "root", "edit scripts", "tools", "docs", "fomod", "lightplacer", "particlelights",
                "pbrnifpatcher", "pbrtexturesets", "terrain", "skyproc patchers", "bashtags", "ini", "cameras", "asi", "dllplugins", "sexlab"}
DELETED = 0x20
REFERENCES = {"REFR", "ACHR", "PGRE", "PHZD", "PMIS", "PARW", "PBAR", "PBEA", "PCON", "PFLA"}


def game_version(game_dir: Path | None) -> tuple[int, int, int] | None:
    """The game's own version, from its program file's version mark; None where it cannot be read."""
    if game_dir is None:
        return None
    for name in ("SkyrimSE.exe", "SkyrimVR.exe"):
        try:
            data = (Path(game_dir) / name).read_bytes()
        except OSError:
            continue
        at = data.find(b"\xbd\x04\xef\xfe")                    # the fixed version block every Windows program carries
        if at < 0 or at + 16 > len(data):
            return None
        ms, ls = struct.unpack_from("<II", data, at + 8)
        return ms >> 16, ms & 0xFFFF, ls >> 16
    return None


def _head(path: Path, n: int) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def _same(a: Path, b: Path, budget: list[int]) -> bool | None:
    """Are the two files the same, byte for byte? None where that was not looked at (too large, or not readable)."""
    try:
        sa, sb = a.stat().st_size, b.stat().st_size
        if sa != sb:
            return False
        if sa > COMPARE_ONE or budget[0] < sa:
            return None
        budget[0] -= sa
        with open(a, "rb") as fa, open(b, "rb") as fb:
            while True:
                x, y = fa.read(1 << 20), fb.read(1 << 20)
                if x != y:
                    return False
                if not x:
                    return True
    except OSError:
        return None


def _dds_size(path: Path) -> tuple[int, int] | None:
    h = _head(path, 20)
    if len(h) < 20 or h[:4] != b"DDS ":
        return None
    height, width = struct.unpack_from("<II", h, 12)
    return width, height


def _finding(key: str, level: str, title: str, text: str, items: list[str] | None = None) -> dict:
    items = items or []
    return {"key": key, "level": level, "title": title, "text": text, "items": items[:ITEMS], "more": max(0, len(items) - ITEMS)}


def _n(n: int, one: str, many: str | None = None) -> str:
    return "%s %s" % (format(n, ","), one if n == 1 else (many or one + "s"))


def extender_wrong(game: tuple[int, int, int] | None, data: bytes) -> str:
    """The game version a script extender plugin was built for, where this game's script extender does not load
    it: "1.5" or "1.6". "" where it loads, or cannot be told. A plugin that carries both ways of naming itself
    loads in either game."""
    newer, older = b"SKSEPlugin_Version\0" in data, b"SKSEPlugin_Query\0" in data
    if game is None:
        return ""
    if game >= (1, 6, 0) and older and not newer:
        return "1.5"
    if game < (1, 6, 0) and newer and not older:
        return "1.6"
    return ""


def _read_script(path: Path) -> dict | None:
    try:
        if path.stat().st_size > pex.BYTES:
            return None
        return pex.read(path.read_bytes())
    except OSError:
        return None


def plugin_use(dll: bytes, scripts: list[tuple[str, Path, Path, str]]) -> dict | None:
    """Whether the scripts beside a script extender plugin still call it (WHY§146). `scripts`: the mod's own
    compiled scripts, each as (its file in lower case, the mod's own copy, the copy the game loads, the mod that
    copy is from or "" for the mod's own).

    A plugin gives scripts functions that a script only declares ("native"). Such a script is the plugin's where
    the plugin's bytes hold the script's name and the name of one of those functions. A script calls the plugin
    where it calls such a function by the script's name. Returns {"scripts": the scripts that declare its
    functions, "own": the mod's own scripts that call them, "now": the ones that still do as the game loads them,
    "by": the mods whose copies took the calls out, "taken_over": the
    declaring script itself is replaced by one that declares none of them}; None where the scripts do not say what the plugin is for."""
    low = dll.lower()

    def held(name: str) -> bool:
        return bool(name) and re.search(rb"(?<![a-z0-9_])" + re.escape(name.lower().encode("utf-8", "replace")) + rb"\x00", low) is not None

    own = {f: _read_script(mine) for f, mine, _now, _by in scripts}
    faces: dict[str, set[str]] = {}                       # a script's name -> the plugin's functions it declares
    for f, got in own.items():
        if got and got["natives"] and held(got["name"]):
            named = {n for n in got["natives"] if held(n)}
            if named:
                faces[got["name"].lower()] = set(got["natives"])
    if not faces:
        return None
    now: dict[str, dict | None] = {}
    for f, mine, loaded, by in scripts:
        now[f] = own[f] if not by else _read_script(loaded)
    # A script that declared the plugin's functions may itself be replaced by one that does the work in Papyrus.
    still = {name: set() for name in faces}
    for f, got in now.items():
        was = own.get(f)
        if was and was["name"].lower() in faces:
            still[was["name"].lower()] = set(faces[was["name"].lower()]) if got is None else set(got["natives"]) & faces[was["name"].lower()]

    def calls(got: dict | None, table: dict[str, set[str]]) -> bool:
        if got is None:
            return False
        me = got["name"].lower()
        return any((s, fn) in got["calls"] or (fn in got["methods"] and s in got["names"]) for s, fns in table.items() if s != me for fn in fns)

    callers = sorted(f for f, got in own.items() if calls(got, faces))
    out = {"scripts": sorted(faces), "own": [_script(f) for f in callers], "now": [], "by": []}
    by_mod = {f: by for f, _mine, _now, by in scripts}
    for f in callers:
        # A copy that cannot be read is taken as calling still: nothing is called fixed on a guess.
        if now[f] is None or calls(now[f], still):
            out["now"].append(_script(f))
        elif by_mod[f] and by_mod[f] not in out["by"]:
            out["by"].append(by_mod[f])
    out["taken_over"] = not any(still.values())
    if out["taken_over"]:
        out["by"] = sorted({by_mod[f] for f, got in own.items() if got and got["name"].lower() in faces and by_mod[f]})
    return out


def _script(file: str) -> str:
    return file.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def _some(names: list[str], n: int = 6) -> str:
    return ", ".join(names[:n]) + (" and %d more" % (len(names) - n) if len(names) > n else "")


def use_told(use: dict) -> str:
    """One line of what `plugin_use` found, for a finding."""
    by = " and ".join("“%s”" % b for b in use["by"]) or "a mod above"
    if use["now"]:
        return "still called by %s: %s" % (_n(len(use["now"]), "script"), _some(use["now"]))
    if use["taken_over"]:
        return "its functions were declared in %s, which %s replaces with a script that does the work itself" % (_some(use["scripts"]), by)
    if len(use["own"]) == 1:
        return "the script that called it (%s) is replaced by %s, and does not call it now" % (use["own"][0], by)
    return "the %d scripts that called it (%s) are replaced by %s, and none calls it now" % (len(use["own"]), _some(use["own"]), by)


def own_files(inst, mod_name: str, folder: Path, mine: list[str], stop: float, won=None) -> tuple[list[dict], bool]:
    """The mod's own files, looked at for what they are: formats of the older game, a script extender plugin built
    for another version of the game, deleted records, and files that lie where the game does not look.
    `won(files)`: of these files of the mod, the ones a mod above replaces, as {file in lower case: (the copy the
    game loads, that mod's name)}; without it every file is taken as the one the game loads."""
    out: list[dict] = []
    cut = False
    low = [(f, f.lower()) for f in mine]

    # Where the files lie.
    tops = {f.split("/", 1)[0] for f, lf in low if "/" in f}
    at_root = [f for f, lf in low if "/" not in f]
    known = [t for t in tops if t.lower() in DATA_FOLDERS]
    loads = known or any(plugin.is_plugin_name(f.lower()) or f.lower().endswith((".bsa", ".esl")) for f in at_root)
    if mine and not loads:
        inner = sorted(t for t in tops if (folder / t / "meshes").is_dir() or (folder / t / "textures").is_dir() or (folder / t / "skse").is_dir()
                       or any(plugin.is_plugin_name(e.lower()) for e in _names(folder / t)))
        if inner:
            out.append(_finding("misplaced", "bad", "Its files lie one folder too deep",
                                "The game looks for meshes, textures, plugins and the like directly in a mod's folder. Here they are inside “%s”, so the game loads "
                                "none of them. The archive was packed with a folder around its content: install it anew with that folder as its top." % inner[0], inner))
        else:
            out.append(_finding("unknown-layout", "info", "None of its folders is one the game loads from",
                                "It has no plugin, no archive, and no folder of a kind ModTrap knows the game or its tools to read. It may be a tool, or papers.", sorted(tops)[:ITEMS]))

    # Archives of the older game.
    for f, lf in low:
        if "/" in f or not lf.endswith((".bsa", ".ba2")):
            continue
        h = _head(folder / f, 8)
        if lf.endswith(".ba2") or h[:4] == b"BTDX":
            out.append(_finding("archive-format", "bad", "An archive of another game", "%s is an archive in Fallout 4's format: Skyrim does not read it." % f, [f]))
        elif h[:4] == b"BSA\0" and len(h) >= 8:
            ver = struct.unpack_from("<I", h, 4)[0]
            if ver < 105:
                out.append(_finding("archive-format", "bad", "An archive in the older game's format",
                                    "%s was packed for the older Skyrim (archive version %d; Special Edition's is 105). Special Edition does not load such an archive, and "
                                    "can stop at its start because of it. The mod needs its Special Edition version, or the archive unpacked and packed anew." % (f, ver), [f]))

    # Plugins: the older game's form, and deleted records.
    for f, lf in low:
        if "/" in f or not plugin.is_plugin_name(lf):
            continue
        if time.monotonic() > stop:
            cut = True
            break
        h = _head(folder / f, 24)
        if len(h) == 24 and h[:4] == b"TES4":
            form = struct.unpack_from("<H", h, 20)[0]
            if form < 44:
                out.append(_finding("plugin-form", "info", "A plugin saved in the older game's form",
                                    "%s has form version %d (Special Edition saves 44). Most such plugins work as they are; a few kinds of record are read wrongly. "
                                    "Opening it in the Special Edition Creation Kit and saving it sets it right." % (f, form), [f]))
        try:
            if (folder / f).stat().st_size > PLUGIN_BYTES:
                continue
            recs = plugin.Records(folder / f)
        except (OSError, plugin.Unreadable, ValueError, struct.error):
            continue
        gone: dict[str, int] = {}
        try:
            for (_k, _form), (_pos, _length, flags, kind) in recs.index.items():
                if flags & DELETED and (kind in REFERENCES or kind == "NAVM"):
                    gone[kind] = gone.get(kind, 0) + 1
        finally:
            recs.close()
        if gone.get("NAVM"):
            out.append(_finding("deleted-navmesh", "bad", "A deleted navmesh",
                                "%s deletes %s. Another plugin that still points at a deleted navmesh crashes the game when the place loads. The mod's author has to "
                                "restore it; xEdit shows which." % (f, _n(gone["NAVM"], "navmesh", "navmeshes")), [f]))
        refs = sum(n for k, n in gone.items() if k != "NAVM")
        if refs:
            out.append(_finding("deleted-references", "warn", "Deleted references",
                                "%s deletes %s outright. A mod that points at one of them crashes the game. xEdit's cleaning (“undelete and disable references”) "
                                "puts them back, disabled, which is safe." % (f, _n(refs, "placed object")), [f]))

    # Animations and meshes in the older game's format (their first bytes say so).
    old_hkx, old_nif, looked = [], [], 0
    for f, lf in low:
        if not lf.endswith((".hkx", ".nif")):
            continue
        if looked >= HEADERS or time.monotonic() > stop:
            cut = True
            break
        looked += 1
        h = _head(folder / f, 64)
        if lf.endswith(".hkx"):
            if len(h) >= 17 and h[:8] == b"\x57\xe0\xe0\x57\x10\xc0\xc0\x10" and h[16] == 4:
                old_hkx.append(f)
        elif h.startswith(b"Gamebryo File Format"):
            end = h.find(b"\n")
            if 0 < end and end + 18 <= len(h):
                user, _blocks, stream = struct.unpack_from("<III", h, end + 6)
                if user == 12 and stream == 83:
                    old_nif.append(f)
    if old_hkx:
        out.append(_finding("old-animations", "bad", "Animations in the older game's format",
                            "%s of its animation or behaviour files %s in the older Skyrim's 32-bit format. Special Edition cannot play them: the characters "
                            "they belong to stand frozen with their arms out. The mod needs its Special Edition version, or the files converted."
                            % (_n(len(old_hkx), "file"), "is" if len(old_hkx) == 1 else "are"), sorted(old_hkx, key=str.lower)))
    if old_nif:
        out.append(_finding("old-meshes", "warn", "Meshes in the older game's format",
                            "%s in the older Skyrim's format. Many show as they should; some show wrongly or crash the game where they load. "
                            "A mesh optimiser converts them." % _n(len(old_nif), "mesh is", "meshes are"), sorted(old_nif, key=str.lower)))

    # Script extender plugins built for another version of the game (WHY§146): only the copy the game loads is
    # judged, and where the scripts say what the plugin is for, whether anything still calls it.
    game = game_version(inst.game_dir)
    dlls = [f for f, lf in low if lf.startswith("skse/plugins/") and lf.endswith(".dll") and lf.count("/") == 2]
    wrong, quiet, replaced = [], [], []
    scripts = [f for f, lf in low if lf.startswith("scripts/") and lf.endswith(".pex") and lf.count("/") == 1][:SCRIPTS]
    above: dict = {}
    for f in dlls if game is not None else []:
        try:
            if (folder / f).stat().st_size > COMPARE_ONE:
                continue
            data = (folder / f).read_bytes()
        except OSError:
            continue
        built = extender_wrong(game, data)
        if not built:
            continue
        if won is not None and not above:
            above = won(dlls + scripts)
        if f.lower() in above:
            replaced.append("%s: built for game version %s, but “%s” above replaces it" % (f, built, above[f.lower()][1]))
            continue
        use = plugin_use(data, [(s.lower(), folder / s, *above.get(s.lower(), (folder / s, ""))) for s in scripts])
        line = "%s: built for game version %s, this game is %d.%d.%d" % (f, built, *game)
        if use is not None and not use["now"] and (use["own"] or use["taken_over"]):
            quiet.append(line + "; " + use_told(use))
        else:
            wrong.append(line + ("; " + use_told(use) if use is not None and use["now"] else ""))
    if wrong:
        out.append(_finding("extender-version", "bad", "A script extender plugin for another version of the game",
                            "The script extender does not load a plugin built for another version of the game, and says so when the game starts; what the mod "
                            "does through it is then missing. The mod's page has the file for this game's version.", wrong))
    if quiet:
        out.append(_finding("extender-unused", "info", "A script extender plugin for another version of the game, which nothing calls now",
                            "The script extender does not load it, but the scripts that called it are replaced: as the game loads this mod's scripts, none of them "
                            "calls the plugin any more. The scripts of other mods were not read.", quiet))
    if replaced:
        out.append(_finding("extender-replaced", "info", "A script extender plugin of this mod is replaced by a mod above",
                            "The game loads the other mod's copy, so this one's does not count.", replaced))
    return out, cut


def _names(folder: Path) -> list[str]:
    try:
        return os.listdir(folder)
    except OSError:
        return []


def shared(m: model.Model, mod: Mod, mine: list[str], stop: float) -> tuple[list[dict], dict, bool]:
    """The files the mod shares with other enabled mods, each weighed: is it the same file, a paper, or one of the
    kinds where the winner matters."""
    findings: list[dict] = []
    cut = False
    trie = adding._trie(mine)
    have = {f.lower() for f in mine}
    budget = [COMPARE_ALL]
    memo: dict = {}
    counts = {"wins": 0, "loses": 0, "same": 0, "papers": 0, "mods": 0}
    by: dict[tuple[str, bool], list[str]] = {}            # (kind, this mod wins) -> lines
    mixed: list[str] = []
    smaller: list[str] = []
    outputs: list[str] = []
    textures = 0
    for o in m.instance.mods:
        if o.kind not in ("mod", "overwrite") or o.folder is None or not o.enabled or o.name == mod.name or not trie:
            continue
        if time.monotonic() > stop:
            cut = True
            break
        found, c = adding.shared_files(o.folder, trie, stop)
        cut = cut or c
        found = [f for f in found if f.lower() != "meta.ini"]
        if not found:
            continue
        counts["mods"] += 1
        wins = o.priority < mod.priority
        counts["wins" if wins else "loses"] += len(found)
        other = "Overwrite" if o.kind == "overwrite" else o.name
        tool = adding.is_output_mod(m, o, memo) if o.kind == "mod" else ""
        if tool and wins:
            outputs.append("%s of “%s”, which %s made" % (_n(len(found), "file"), other, tool))
        per: dict[str, list[str]] = {}
        for f in found:
            lf = f.lower()
            mine_path, their_path = mod.folder / f, o.folder / f
            if PAPERS.search(lf):
                counts["papers"] += 1
                continue
            same = _same(mine_path, their_path, budget) if time.monotonic() < stop else None
            if same:
                counts["same"] += 1
                continue
            kind = "skeleton" if SKELETON.search(lf) else adding.kind_of(f)
            per.setdefault(kind, []).append(f)
            if kind == "textures" and lf.endswith(".dds") and textures < HEADERS:
                textures += 1
                stem = SUFFIX.sub("", lf)
                is_base = stem == lf
                # A texture set from two mods: the colour from the winner, the surface from the loser, or the other way.
                partner = lf[:-4] + "_n.dds" if is_base else stem + ".dds" if lf.endswith("_n.dds") else ""
                if partner and partner not in have and (o.folder / partner).is_file():
                    mixed.append("%s (%s from this mod, %s from “%s”)" % (f, "colour" if is_base else "surface", "surface" if is_base else "colour", other) if wins
                                 else "%s (%s from “%s”, %s from this mod)" % (f, "colour" if is_base else "surface", other, "surface" if is_base else "colour"))
                a, b = _dds_size(mine_path), _dds_size(their_path)
                if a and b and a != b:
                    win, lose = (a, b) if wins else (b, a)
                    if win[0] * win[1] < lose[0] * lose[1]:
                        smaller.append("%s: %d×%d in place of %d×%d (%s)" % (f, *win, *lose, "this mod's over “%s”" % other if wins else "“%s” over this mod's" % other))
        for kind, files in per.items():
            ex = ", ".join(sorted(files, key=str.lower)[:2]) + (" and %d more" % (len(files) - 2) if len(files) > 2 else "")
            by.setdefault((kind, wins), []).append("“%s”: %s (%s)" % (other, _n(len(files), "file"), ex))
            if kind == "plugin":
                for f in files:
                    try:
                        a, b = plugin.read(mod.folder / f), plugin.read(o.folder / f)
                    except (plugin.Unreadable, OSError):
                        continue
                    if [fold(x) for x in a.masters] != [fold(x) for x in b.masters]:
                        by[(kind, wins)].append("   %s: this mod's has the masters %s; “%s”'s has %s" % (f, ", ".join(a.masters) or "none", other, ", ".join(b.masters) or "none"))
            if kind == "skeleton":
                for f in files:
                    try:
                        a, b = (mod.folder / f).stat().st_size, (o.folder / f).stat().st_size
                    except OSError:
                        continue
                    win, lose = (a, b) if wins else (b, a)
                    if win < lose * 0.85:
                        by[(kind, wins)].append("   %s: the winning file is much smaller (%s bytes against %s): fewer bones, most likely" % (f, format(win, ","), format(lose, ",")))

    # Which mod's file wins is how a modlist works, and no warning (MT76): each kind is told, with what follows from
    # it, as information. The one that breaks the game is a skeleton that wins with fewer bones: that is a warning.
    WORDS = {
        "plugin": ("info", "A plugin of the same name", "the whole plugin is replaced: every plugin that names it as a master gets the winner's instead. So it is where one mod is a "
                   "newer version of the other, or a patch made to replace its plugin, as modlists' authors often make them"),
        "script extender plugin": ("info", "The same script extender plugin twice", "only the winner's is loaded. Two copies mostly mean the same mod twice, in two versions, or a mod and a fix that replaces its plugin"),
        "skeleton": ("info", "A skeleton is replaced", "every animation and every physics mod counts on the bones of the skeleton that wins. One with fewer bones crashes the game when a "
                     "character loads; the skeleton with the most bones should be the last"),
        "scripts": ("info", "Compiled scripts are replaced", "only the winner's script runs. So it is where the winner is a patch for the other or its newer version"),
        "face data": ("info", "Face files are replaced", "the mod that wins a character's face files is to be the one whose plugin wins that character"),
        "archive": ("info", "An archive of the same name", "only one of the two archives is used, whole"),
        "animations": ("info", "Animation or behaviour files are replaced", "the behaviour tool of the modlist builds from the winner's; it has to run again after such a change"),
        "lod": ("info", "Distant-view files are replaced", "what the distant-view tools built before does not hold what the winner brings, until they run again"),
        "menus": ("info", "Menu files are replaced", "the look of a menu, or a mod's settings menu, is the winner's"),
        "settings for a script extender plugin": ("info", "Settings files are replaced", "the settings in force are the winner's: what a preset or a patch is for"),
        "sequence file": ("info", "Sequence files are replaced", "they belong to a plugin of the same name; the winner's goes with the winner's plugin"),
        "meshes": ("info", "Meshes are replaced", "what a replacer is for. The textures that go with a mesh should come from a mod made for that mesh"),
        "textures": ("info", "Textures are replaced", "what a retexture is for"),
    }
    for (kind, wins), lines in sorted(by.items(), key=lambda kv: ({"bad": 0, "warn": 1, "info": 2}[WORDS.get(kv[0][0], ("info",))[0]], not kv[0][1], kv[0][0])):
        level, title, why = WORDS.get(kind, ("info", "Other files are replaced", "files of a kind ModTrap has no rule for"))
        if kind == "skeleton" and any("fewer bones" in ln for ln in lines):
            level = "warn"
        side = "This mod's files are the ones loaded" if wins else "The other mod's files are the ones loaded, not this mod's"
        findings.append(_finding("shared:%s:%s" % (kind, "wins" if wins else "loses"), level, title + (": this mod wins" if wins else ": this mod loses"),
                                 "%s. Why it matters: %s." % (side, why), lines))
    if outputs:
        findings.insert(0, _finding("over-output", "bad", "It overwrites what a tool made",
                                    "At this place the mod wins over files a tool of the modlist built, so the game loads the mod's files and not what the tool made "
                                    "from the whole list. A mod belongs below the tools' outputs; the tool then has to run again.", outputs))
    if mixed:
        findings.append(_finding("mixed-textures", "info", "Texture sets put together from two mods",
                                 "A surface has a colour picture and a surface picture that belong together. Here one of the two comes from this mod and the other from "
                                 "another: where they were not made for each other, the surface shows seams or the wrong shine.", sorted(mixed, key=str.lower)))
    if smaller:
        findings.append(_finding("smaller-textures", "info", "Smaller textures over larger ones",
                                 "The winning picture is smaller than the one it replaces: coarser in the game, lighter on the graphics card.", sorted(smaller, key=str.lower)))
    return findings, counts, cut


def mod(m: model.Model, target: Mod, seconds: float = SECONDS, duplicates: list[dict] | None = None) -> dict:
    """The whole weighing of one mod at the place it has: {"mod", "verdict", "summary", "findings", "counts", "cut"}."""
    stop = time.monotonic() + seconds
    out: dict = {"mod": target.name, "verdict": "clean", "summary": "", "findings": [], "counts": {}, "cut": False, "files": 0}
    if target.folder is None:
        out["summary"] = "This entry has no folder of its own to look through."
        return out
    mine, cut = steps.walk(target.folder)
    mine = [f for f in mine if f.lower() != "meta.ini"]
    out["files"] = len(mine)
    findings: list[dict] = []
    for d in duplicates or []:
        findings.append(_finding("duplicate", "warn" if d.get("enabled") and target.enabled else "info", "The same mod is in the modlist already",
                                 "“%s” (%s%s, priority %d) is the same mod%s. This one is %s. Two copies of a mod overwrite each other file for file; where their plugins "
                                 "have the same name only one is loaded. Keep the newer one."
                                 % (d["mod"], "version %s, " % d["version"] if d.get("version") else "", "enabled" if d.get("enabled") else "disabled", d.get("priority", 0),
                                    " (%s)" % d["how"] if d.get("how") else "", "version %s" % d["mine"] if d.get("mine") else "of no known version"), [d["mod"]]))
    def won(files: list[str]) -> dict:
        """Of these files of the mod, the ones an enabled mod above it has too: the copy the game loads."""
        trie = adding._trie(files)
        best: dict[str, tuple] = {}
        for o in m.instance.mods:
            if o.kind not in ("mod", "overwrite") or o.folder is None or not o.enabled or o.name == target.name or not trie:
                continue
            rank = o.priority if o.kind == "mod" else 1 << 30
            if rank < target.priority:
                continue
            for f in adding.shared_files(o.folder, trie, stop)[0]:
                if f.lower() not in best or rank > best[f.lower()][2]:
                    best[f.lower()] = (o.folder / f, "Overwrite" if o.kind == "overwrite" else o.name, rank)
        return {k: v[:2] for k, v in best.items()}

    own, c1 = own_files(m.instance, target.name, target.folder, mine, stop, won if target.enabled else None)
    findings += own
    counts: dict = {"wins": 0, "loses": 0, "same": 0, "papers": 0, "mods": 0}
    c2 = False
    if target.enabled:
        sh, counts, c2 = shared(m, target, mine, stop)
        findings += sh
    else:
        findings.append(_finding("disabled", "info", "The mod is disabled", "A disabled mod overwrites nothing and is overwritten by nothing. Its own files were looked at all the same."))
    quiet = counts["same"] + counts["papers"]
    if counts["same"]:
        findings.append(_finding("same", "good", "%s the same, byte for byte" % _n(counts["same"], "shared file is", "shared files are"),
                                 "Whichever of the two mods wins such a file, the game loads the same thing: these overwrites change nothing."))
    if counts["papers"]:
        findings.append(_finding("papers", "good", "%s the game never loads" % _n(counts["papers"], "shared file is a paper", "shared files are papers"),
                                 "Read-mes, licences, pictures of the mod's page and installer files that several mods carry under the same name. Overwriting them does nothing."))
    order = {"bad": 0, "warn": 1, "info": 2, "good": 3}
    findings.sort(key=lambda f: order[f["level"]])
    bad, warn = sum(f["level"] == "bad" for f in findings), sum(f["level"] == "warn" for f in findings)
    total = counts["wins"] + counts["loses"]
    out.update(findings=findings, counts=counts, cut=bool(cut or c1 or c2), verdict="problem" if bad else "look" if warn else "clean")
    lead = ("%s likely to cause a fault" % _n(bad, "thing is", "things are") + (", and %s worth a look" % _n(warn, "more is", "more are") if warn else "") if bad
            else "%s worth a look; nothing that is a fault by itself" % _n(warn, "thing is", "things are") if warn
            else "Nothing found that is a fault or needs a look")
    out["summary"] = lead + ". " + ("It shares %s with %s%s." % (_n(total, "file"), _n(counts["mods"], "other mod"),
                                                                "; %s change nothing" % ("all of them" if quiet == total else "%s of them" % format(quiet, ",")) if quiet else "")
                                    if total else "It shares no file with any other enabled mod.")
    return out


__all__ = ["game_version", "mod", "own_files", "shared"]
