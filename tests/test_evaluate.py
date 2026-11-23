"""A mod weighed at its place, and a modlist looked through for the same mod twice (MT65), on an invented modlist."""

import os
import struct
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, dupes, evaluate, instance, logbook, model, probe
from tests import _fixtures as fx
from tests.test_modweb import CORE, pf
from tests.test_updates import FakeNet, meta

SE_BSA = b"BSA\0" + struct.pack("<I", 105) + b"\0" * 28
LE_BSA = b"BSA\0" + struct.pack("<I", 104) + b"\0" * 28
HKX = b"\x57\xe0\xe0\x57\x10\xc0\xc0\x10" + struct.pack("<II", 0, 8)


def nif(stream: int) -> bytes:
    return b"Gamebryo File Format, Version 20.2.0.7\n" + struct.pack("<IBIII", 0x14020007, 1, 12, 3, stream) + b"\0" * 16


def dds(w: int, h: int) -> bytes:
    return b"DDS " + struct.pack("<IIII", 124, 0, h, w) + b"\0" * 108


def deleting() -> bytes:
    refs = [probe.record(b"REFR", 0xA01, [(b"NAME", struct.pack("<I", 0xA00))], flags=0x20), probe.record(b"REFR", 0xA02, [(b"NAME", struct.pack("<I", 0xA00))])]
    navs = [probe.record(b"NAVM", 0xB01, [(b"NVNM", b"\0" * 8)], flags=0x20)]
    return probe.plugin_file([CORE], [probe.group(b"REFR", refs), probe.group(b"NAVM", navs)], 3, 0x900, "invented")


def exe(a: int, b: int, c: int) -> bytes:
    return b"MZ" + b"\0" * 300 + b"\xbd\x04\xef\xfe" + struct.pack("<III", 0x10000, (a << 16) | b, c << 16) + b"\0" * 40


def invented(root: Path) -> Path:
    fx.make_instance(root, [
        ("+", "Tool Output", {"Generated.esp": pf((CORE,)), "meshes/built/a.nif": nif(100)}),
        ("+", "Newcomer", {
            "Newcomer.esp": deleting(), "Old.bsa": LE_BSA, "readme.txt": b"about the newcomer", "Shared.esp": pf((CORE, "Quill.esp")),
            "meshes/actors/character/skeleton.nif": nif(100) + b"\0" * 10, "meshes/old/le.nif": nif(83), "meshes/actors/anim/idle.hkx": HKX + b"\x04\x01\x00\x01",
            "meshes/built/a.nif": nif(100) + b"mine", "scripts/quillscript.pex": b"newer script", "scripts/same.pex": b"one and the same",
            "textures/set/wall.dds": dds(1024, 1024), "skse/plugins/thing.dll": b"MZ...SKSEPlugin_Query\0...",
            "meta.ini": meta(gameName="SkyrimSE", modid=777, version="2.0", installationFile="Newcomer-777-2-0-1700000000.7z").encode()}),
        ("+", "Quill", {
            "Quill.esp": pf((CORE,)), "Shared.esp": pf((CORE,)), "New.bsa": SE_BSA, "readme.txt": b"about quill", "scripts/quillscript.pex": b"older script",
            "scripts/same.pex": b"one and the same", "meshes/actors/character/skeleton.nif": nif(100) + b"\0" * 400, "meshes/actors/anim/idle.hkx": HKX + b"\x08\x01\x00\x01",
            "textures/set/wall.dds": dds(4096, 4096), "textures/set/wall_n.dds": dds(4096, 4096), "skse/plugins/thing.dll": b"MZ...SKSEPlugin_Version\0...SKSEPlugin_Query\0"}),
        ("+", "Newcomer (2)", {"Other.esp": pf((CORE,)), "meta.ini": meta(gameName="SkyrimSE", modid=777, version="1.0", installationFile="Newcomer-777-1-0-1600000000.7z").encode()}),
        ("+", "Shadowed", {"textures/set/wall.dds": dds(512, 512), "textures/set/wall_n.dds": dds(512, 512)}),
        ("+", "Wrapped", {"Wrapped Mod/meshes/x.nif": nif(100), "Wrapped Mod/Wrapped.esp": pf((CORE,))}),
        ("+", "Core", {CORE: pf(())}),
    ], load_order=[CORE, "Quill.esp", "Shared.esp", "Other.esp", "Newcomer.esp", "Generated.esp"],
        profile_settings="[custom_overwrites]\r\nInvented%20Patcher=Tool Output\r\n")
    fx.write(root / "Game" / "SkyrimSE.exe", exe(1, 6, 1170))
    return root


class AModWeighed(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "Example List")
        self.m = model.build(instance.load(self.root))

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def found(self, name: str) -> dict:
        got = evaluate.mod(self.m, self.m.instance.mod(name))
        return {f["key"]: f for f in got["findings"]} | {"": got}

    def test_the_games_version_is_read_from_its_program(self):
        self.assertEqual(evaluate.game_version(self.m.instance.game_dir), (1, 6, 1170))
        self.assertIsNone(evaluate.game_version(Path(self.tmp.name) / "nowhere"))

    def test_the_mods_own_files_formats_of_the_older_game_and_what_does_not_load(self):
        f = self.found("Newcomer")
        self.assertEqual((f["archive-format"]["level"], f["archive-format"]["items"]), ("bad", ["Old.bsa"]))
        self.assertEqual((f["old-animations"]["level"], f["old-animations"]["items"]), ("bad", ["meshes/actors/anim/idle.hkx"]))
        self.assertEqual((f["old-meshes"]["level"], f["old-meshes"]["items"]), ("warn", ["meshes/old/le.nif"]))
        self.assertEqual(f["extender-version"]["items"], ["skse/plugins/thing.dll: built for game version 1.5, this game is 1.6.1170"])
        self.assertEqual((f["deleted-navmesh"]["level"], f["deleted-references"]["level"]), ("bad", "warn"))
        self.assertIn("deletes 1 placed object outright", f["deleted-references"]["text"])
        self.assertEqual(f[""]["verdict"], "problem")
        quill = self.found("Quill")                                 # the newer formats, and a plugin for both versions: nothing said
        self.assertFalse({"archive-format", "old-animations", "old-meshes", "extender-version"} & set(quill))
        wrapped = self.found("Wrapped")
        self.assertEqual((wrapped["misplaced"]["level"], wrapped["misplaced"]["items"]), ("bad", ["Wrapped Mod"]))

    def test_what_its_overwrites_come_to(self):
        f = self.found("Newcomer")
        got = f[""]
        self.assertEqual((got["counts"]["same"], got["counts"]["papers"]), (1, 1))              # the same script, and a read-me
        self.assertIn("1 shared file is the same, byte for byte", f["same"]["title"])
        self.assertEqual(f["papers"]["level"], "good")
        self.assertEqual(f["shared:scripts:wins"]["level"], "info")              # MT76: which mod's file wins is no warning
        self.assertEqual(f["shared:scripts:wins"]["items"], ["“Quill”: 1 file (scripts/quillscript.pex)"])
        plug = f["shared:plugin:wins"]
        self.assertEqual(plug["level"], "info")
        self.assertIn("   Shared.esp: this mod's has the masters Core.esm, Quill.esp; “Quill”'s has Core.esm", plug["items"])
        self.assertTrue(any("the winning file is much smaller" in x for x in f["shared:skeleton:wins"]["items"]))
        self.assertEqual(f["shared:skeleton:wins"]["level"], "warn")             # the one that crashes the game: fewer bones win
        self.assertEqual((f["shared:script extender plugin:wins"]["level"], f["mixed-textures"]["level"]), ("info", "info"))
        # A colour picture from this mod over a mod that has the surface picture too: a set from two mods, and smaller.
        self.assertTrue(any("textures/set/wall.dds (colour from this mod, surface from “Quill”)" == x for x in f["mixed-textures"]["items"]))
        self.assertTrue(any("1024×1024 in place of 4096×4096" in x for x in f["smaller-textures"]["items"]))
        # And where a tool's output is overwritten, or overwrites.
        self.assertNotIn("over-output", f)                                # the output is above it: as it should be
        self.assertIn("shared:meshes:loses", f)

    def test_the_same_mod_twice_is_told_by_its_page_and_its_files_name(self):
        rows = [{"mod": "Newcomer", "host": "nexus", "mod_id": 777, "game": "skyrimspecialedition", "version": "2.0", "archive": "Newcomer-777-2-0-1700000000.7z", "enabled": True},
                {"mod": "Newcomer (2)", "host": "nexus", "mod_id": 777, "game": "skyrimspecialedition", "version": "1.0", "archive": "Newcomer-777-1-0-1600000000.7z", "enabled": True},
                {"mod": "Quill", "host": "", "mod_id": 0, "game": "", "version": "", "archive": "", "enabled": True}]
        got = dupes.same_as(self.m, rows, "Newcomer-777-3-0-1800000000.7z")
        self.assertEqual([(e["mod"], e["version"], e["mine"], e["newer"], e["how"]) for e in got],
                         [("Newcomer", "2.0", "3.0", 1, "the same file of the same page at Nexus"), ("Newcomer (2)", "1.0", "3.0", 1, "the same file of the same page at Nexus")])
        self.assertEqual(dupes.same_as(self.m, rows, "Newcomer Patch-777-1-0-1800000000.7z"), [])              # another file of the same page: not the same mod
        self.assertEqual([e["how"] for e in dupes.same_as(self.m, rows, "Quill (2).zip")], ["it has the name this file gives its mod"])
        self.assertEqual((dupes.newer("1.10", "1.9"), dupes.newer("2.0", "2.0.0"), dupes.newer("", "1")), (1, 0, 0))
        quick = {f["key"]: f for f in dupes.quick(self.m, rows)}
        # The same title, both enabled, and the higher one does not hold the lower one's file: twice in the game.
        self.assertEqual((sorted(quick), quick["twice"]["level"], quick["twice"]["mods"]), (["twice"], "warn", ["Newcomer (2)", "Newcomer"]))
        self.assertIn("1 of the lower one's 1 files are not in the higher one", quick["twice"]["items"][0])
        # A plugin of the same name in two enabled mods (Newcomer's Shared.esp over Quill's) is what a patch does: no word of it.

    def test_the_whole_list_mods_that_do_nothing_and_old_formats(self):
        seen = []
        got = dupes.deep(self.m, lambda i, n: seen.append((i, n)))
        by = {f["key"]: f for f in got["findings"]}
        self.assertEqual(by["does-nothing"]["mods"], ["Shadowed"])
        self.assertIn("overwritten by “Newcomer” (1), “Quill” (1)", by["does-nothing"]["items"][0])
        self.assertEqual(by["archive-format"]["items"], ["“Newcomer”: Old.bsa"])
        self.assertEqual(by["extender-version"]["items"], ["“Newcomer”: skse/plugins/thing.dll, built for game version 1.5"])
        self.assertEqual((got["mods"], got["cut"], seen[-1]), (7, False, (7, 7)))


class AModsName(unittest.TestCase):
    """MT67: a mod is named by its title and its version."""

    def test_the_title_and_the_version_come_out_of_the_files_name(self):
        from modtrap import adding
        for archive, title, version in (
                ("Example Terrain Skse 4321 1.2 2026-01-02T03-04Z abcDEF123.7z", "Example Terrain Skse", "1.2"),      # as Nexus names a download now
                ("Example Terrain Skse 4321 1.2 2026-01-02T03-04Z abcDEF123 (1).7z", "Example Terrain Skse", "1.2"),
                ("Lantern-4321-2-1-1700000000.zip", "Lantern", "2.1"),                                                # as it did before
                ("Lantern v2.10.3.zip", "Lantern", "2.10.3"), ("Lantern_1_4.rar", "Lantern", "1.4"), ("Lantern (3.0b).7z", "Lantern", "3.0b"),
                ("Lantern.zip", "Lantern", ""), ("Lantern 2.zip", "Lantern 2", ""), ("4.5.zip", "4.5", "")):
            said = adding.from_archive_name(archive)
            self.assertEqual((said["stem"], said["version"]), (title, version), archive)

    def test_the_name_is_the_title_and_the_version_and_an_update_keeps_the_title(self):
        from modtrap import adding
        self.assertEqual(adding.mod_name("Example Terrain Skse", "1.2"), "Example Terrain Skse 1.2")
        self.assertEqual(adding.mod_name("Lantern", "v2.1"), "Lantern 2.1")
        self.assertEqual(adding.mod_name("Lantern 2.1", "2.1"), "Lantern 2.1")                 # not said twice
        self.assertEqual(adding.mod_name("Lantern", ""), "Lantern")
        self.assertEqual(adding.mod_name('Lan<te>rn: "x"', "1/2"), "Lan te rn   x 1 2")
        for name, was, title in (("Lantern 2.1", "2.1", "Lantern"), ("Lantern (2.1)", "2.1", "Lantern"), ("Lantern - v2.1", "", "Lantern"),
                                 ("Lantern (new)", "", "Lantern"), ("Lantern", "2.1", "Lantern"), ("Lantern 2", "", "Lantern 2"), ("Lantern SE", "1.0", "Lantern SE")):
            self.assertEqual(adding.title_of(name, was), title, name)
        self.assertEqual((adding.version_in("Lantern 2.1"), adding.version_in("Lantern")), ("2.1", ""))

    def test_a_file_inside_the_archive_can_say_the_version(self):
        from modtrap import adding
        with tempfile.TemporaryDirectory() as d:
            fx.write(Path(d) / "Fomod" / "Info.xml", "<fomod><Name>Lantern</Name><Version MachineVersion=\"3.1\"> 3.1 </Version></fomod>".encode("utf-16"))
            self.assertEqual(adding.info_version(Path(d)), "3.1")
            self.assertEqual(adding.info_version(Path(d) / "Fomod"), "")


class ObsoleteAndRedundant(unittest.TestCase):
    """MT68: what counts as the same mod, and what is said of it."""

    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        nexus = lambda number, version, archive: meta(gameName="SkyrimSE", modid=number, version=version, installationFile=archive).encode()     # noqa: E731
        root = Path(self.tmp.name) / "Example List"
        fx.make_instance(root, [
            ("+", "Lantern (2.0b)", {"Lantern.esp": pf((CORE,)), "meta.ini": nexus(900, "2.0b", "Lantern-900-2-0b-1800000000.7z")}),
            ("-", "Lantern", {"Lantern.esp": pf((CORE,)), "meta.ini": nexus(900, "1.9", "Lantern-900-1-9-1700000000.7z")}),          # obsolete: disabled, newer one enabled
            ("+", "Moss 2.0", {"textures/m/a.dds": b"2", "textures/m/b.dds": b"2", "textures/m/c.dds": b"2"}),
            ("+", "Moss", {"textures/m/a.dds": b"1", "textures/m/b.dds": b"1", "readme.txt": b"about"}),                               # redundant: wholly inside its newer version
            ("+", "Kit - AIO - Overwrite", {"meshes/kit/over.nif": b"o", "meta.ini": nexus(555, "1.0", "Kit All In One-555-1-0-1700000000.7z")}),
            ("+", "Kit - AIO", {"meshes/kit/base.nif": b"b", "Kit.esp": pf((CORE,)), "meta.ini": nexus(555, "1.0", "Kit All In One-555-1-0-1700000000.7z")}),   # one file, two mods: left alone
            ("+", "Quill - Fixes", {"Quill.esp": pf((CORE,))}),                                                                         # a patch that replaces the plugin: left alone
            ("+", "Quill", {"Quill.esp": pf((CORE,)), "textures/q/a.dds": b"q"}),
            ("+", "Quill AE", {"textures/q/a.dds": b"q"}),                                                                              # another title that holds the same words
            ("-", "Beacon (2)", {"Beacon.esp": pf((CORE,))}),
            ("-", "Beacon", {"Beacon.esp": pf((CORE,))}),                                                                               # both disabled: nothing of them is in the game
            ("+", "Thistle (2)", {"textures/t/new.dds": b"n"}),
            ("+", "Thistle", {"textures/t/old.dds": b"o", "textures/t/new.dds": b"o"}),                                                 # twice in the game
            ("+", "Core", {CORE: pf(())}),
        ], load_order=[CORE, "Quill.esp", "Kit.esp", "Lantern.esp"])
        self.m = model.build(instance.load(root))
        from modtrap import sources
        self.rows = [dict(sources.mod_meta(x.folder), mod=x.name, enabled=x.enabled, host="nexus" if sources.mod_meta(x.folder).get("mod_id") else "")
                     for x in self.m.instance.mods if x.kind == "mod"]

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_titles_are_the_same_only_when_they_are_and_not_when_one_holds_the_other(self):
        same = lambda a, b: dupes.base_title(a) == dupes.base_title(b)          # noqa: E731
        self.assertTrue(same("Lantern", "Lantern (2.0b)") and same("Lantern 1.9", "Lantern v2.0") and same("Moss", "Moss (2)") and same("Moss", "Moss - Copy"))
        self.assertFalse(same("Quill", "Quill AE") or same("Quill", "Quill - Fixes") or same("Kit - AIO", "Kit - AIO - Overwrite") or same("Lantern", "Lantern Patch"))

    def test_three_notes_each_a_list_and_patches_left_alone(self):
        got = {f["key"]: f for f in dupes.quick(self.m, self.rows)}
        self.assertEqual(sorted(got), ["obsolete", "redundant", "twice"])
        self.assertEqual((got["obsolete"]["level"], got["obsolete"]["mods"]), ("info", ["Lantern"]))
        self.assertIn("“Lantern” version 1.9 (disabled, priority", got["obsolete"]["items"][0])
        self.assertIn("its newer version is “Lantern (2.0b)” version 2.0b (enabled", got["obsolete"]["items"][0])
        self.assertEqual((got["redundant"]["level"], got["redundant"]["mods"]), ("info", ["Moss"]))
        self.assertIn("all 2 of its files are in “Moss 2.0”", got["redundant"]["items"][0])           # its read-me is a paper, and does not count
        self.assertEqual((got["twice"]["level"], got["twice"]["mods"]), ("warn", ["Thistle", "Thistle (2)"]))
        named = " ".join(n for f in got.values() for n in f["mods"])
        for left_alone in ("Kit", "Quill", "Beacon"):
            self.assertNotIn(left_alone, named)


class TheScansRoutes(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "Example List")
        self.api = api.Api()
        self.api.updating.net = FakeNet({})
        self.api.updating.by_itself = False
        self.api.running = lambda image: False
        self.api.open(str(self.root), wait=True)

    def tearDown(self):
        for _ in range(400):                              # what was begun when the modlist opened ends before its folder goes
            if self.api.updating.work["state"] != "going" and self.api.updating.reading["state"] != "going" and self.api._listscan["state"] not in ("going", "looking"):
                break
            time.sleep(0.01)
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_doubles_are_looked_for_when_the_modlist_opens_and_the_scan_goes_through_every_mod(self):
        st = self.api.get("/api/state", {})[1]
        self.assertEqual((st["scan"]["deep"], st["scan"]["going"]), (False, False))
        for _ in range(400):
            first = self.api.get("/api/listscan", {})[1]
            if first["state"] != "looking":
                break
            time.sleep(0.02)
        self.assertEqual((first["deep"], [f["key"] for f in first["quick"]]), (None, ["twice"]))
        self.assertEqual((self.api.get("/api/state", {})[1]["scan"]["found"], self.api.get("/api/state", {})[1]["scan"]["bad"]), (1, 0))
        self.api.post("/api/listscan/start", {})
        for _ in range(400):
            got = self.api.get("/api/listscan", {})[1]
            if got["state"] == "idle":
                break
            time.sleep(0.02)
        self.assertEqual((got["error"], got["looked"]["mods"], sorted(f["key"] for f in got["deep"])), ("", 7, ["archive-format", "does-nothing", "extender-version"]))
        self.assertTrue(self.api.get("/api/state", {})[1]["scan"]["deep"])

    def test_a_mod_is_weighed_with_its_double_named(self):
        got = self.api.post("/api/mod/evaluate", {"mod": "Newcomer"})[1]
        dup = next(f for f in got["findings"] if f["key"] == "duplicate")
        self.assertEqual((got["verdict"], dup["level"], dup["items"]), ("problem", "warn", ["Newcomer (2)"]))
        self.assertIn("“Newcomer (2)” (version 1.0, enabled, priority", dup["text"])
        self.assertIn("This one is version 2.0", dup["text"])
        with self.assertRaises(api.Bad):
            self.api.post("/api/mod/evaluate", {"mod": "Nobody"})

    def test_a_file_given_for_a_mod_that_is_there_already_says_so(self):
        rec = self.api._new_staged("Newcomer-777-3-0-1800000000.7z", "upload")
        pub = self.api._staged_public(rec)
        self.assertEqual((pub["name"], pub["version"], [(e["mod"], e["version"], e["newer"]) for e in pub["already"]]),
                         ("Newcomer 3.0", "3.0", [("Newcomer", "2.0", 1), ("Newcomer (2)", "1.0", 1)]))
        self.assertEqual(self.api._staged_public(self.api._new_staged("Lantern-900-1-0-1800000000.7z", "upload"))["already"], [])

    def test_a_mod_is_named_by_title_and_version_and_the_owners_own_name_is_taken(self):
        rec = self.api._new_staged("Lantern 900 1.0 2026-10-11T12-11Z abcdefgh.7z", "upload")
        self.assertEqual((rec["name"], rec["version"], rec["title"]), ("Lantern 1.0", "1.0", "Lantern"))
        up = self.api._new_staged("anything.zip", "fetched", updates="Newcomer", version="v2.5")          # the source's word comes first
        self.assertEqual(up["name"], "Newcomer 2.5")
        late = self.api._new_staged("Beacon.zip", "upload")
        self.api._version_found(late, "4.0", "a file inside it")
        self.assertEqual((late["name"], late["version"]), ("Beacon 4.0", "4.0"))
        got = self.api.post("/api/add/name", {"id": rec["id"], "name": "  My   Lantern "})[1]
        self.assertEqual(got["name"], "My Lantern")
        self.api._version_found(rec, "9.9", "a file inside it")                                         # a name the owner gave stays
        self.assertEqual(rec["name"], "My Lantern")
        for bad in ({"id": rec["id"], "name": "Quill"}, {"id": rec["id"], "name": "a/b"}, {"id": rec["id"], "name": "x_separator"}, {"id": "none", "name": "Fine"},
                    {"updates": "Quill", "name": "Newcomer"}):
            with self.assertRaises(api.Bad):
                self.api.post("/api/add/name", bad)
        self.assertEqual(self.api.post("/api/add/propose", {"updates": "Newcomer"})[1]["name"], "Newcomer (new)")       # no newer version is known of it here
        self.api.post("/api/add/name", {"updates": "Quill", "name": "Quill, the newer one"})
        self.assertEqual(self.api._new_staged("q.zip", "fetched", updates="Quill", version="2.0")["name"], "Quill, the newer one")
        self.assertEqual(self.api._new_staged("q2.zip", "fetched", updates="Quill", version="2.0")["name"], "Quill 2.0")  # asked for once, used once


if __name__ == "__main__":
    unittest.main()
