"""The scanner (WHY§98): every settings file in force in the modlist, the winner of each, read to its end."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from modtrap import census, instance, logbook, model, steps
from tests import _fixtures as fx
from tests.test_steps import dry_done


class NamesInText(unittest.TestCase):
    def test_the_longest_known_name_that_ends_there_is_the_one_meant(self):
        known = ["Bramble.esp", "Skyrim.esm", "The Long Name of a Plugin - Patch.esp", "Patch.esp", "a.esl"]
        text = (b"Keyword = 0x801~BRAMBLE.ESP|x\r\n; from Skyrim.esm\r\nItem = 0x5~The Long Name of a Plugin - Patch.esp\r\n"
                b"other = Unknown.esp, a.esl\r\n")
        self.assertEqual(census.names_in(text, known),
                         {"bramble.esp", "skyrim.esm", "the long name of a plugin - patch.esp", "a.esl"})
        self.assertEqual(census.names_in(b"nothing here.esp", known), frozenset())

    def test_a_name_with_letters_beyond_a_to_z_is_found_in_either_writing(self):
        known = ["Brömble.esp"]
        self.assertEqual(census.names_in("x = Brömble.esp".encode("utf-8"), known), {"brömble.esp"})
        self.assertEqual(census.names_in("x = Brömble.esp".encode("cp1252"), known), {"brömble.esp"})
        self.assertEqual(census.names_in("x = brömble.ESP".encode("utf-8"), known), {"brömble.esp"})

    def test_a_file_is_read_to_its_end_and_a_name_across_two_pieces_is_whole(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "big.json"
            names = census.Names(["Bramble.esp", "Quill.esp"])
            for pad in (census.CHUNK - 4, census.CHUNK * 2 + 17):          # the name lies across the end of a piece
                p.write_bytes(b" " * pad + b"Bramble.esp" + b" " * 100)
                self.assertEqual(census.names_in_file(p, names), {"bramble.esp"}, pad)
            p.write_bytes(b" " * (census.CHUNK * 3) + b"\"Quill.esp\"")      # far beyond what was once the limit
            self.assertEqual(census.names_in_file(p, names), {"quill.esp"})


class TheScan(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        self.mods = self.root / "mods"
        census._memo.clear()

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def scan(self):
        inst = instance.load(self.root)
        return census.scan(inst, census.known_plugins(inst))

    def of(self, c, rel):
        return [(e["mod"], sorted(e["names"])) for e in c["entries"] if e["rel"].lower() == rel.lower()]

    def test_only_the_winning_copy_of_a_file_counts(self):
        """Two enabled mods carry a file of the same path: the game sees the one of the higher priority. A line
        about the plugin in the hidden one is not in force, and one in the winner is."""
        inst = instance.load(self.root)
        by_priority = {m.name: m.priority for m in inst.mods}
        low, high = sorted(("Quill", "Lantern"), key=by_priority.get)
        fx.write(self.mods / low / "SKSE/Plugins/Shared_DISTR.ini", "Keyword = 0x801~Bramble.esp|x\n")
        fx.write(self.mods / high / "skse/plugins/shared_distr.ini", "Keyword = 0x801~Quill.esp|x\n")
        c = self.scan()
        self.assertEqual(self.of(c, "SKSE/Plugins/Shared_DISTR.ini"), [(high, ["quill.esp"])])
        self.assertEqual(c["hidden"], 1)
        # Overwrite is loaded last, and wins over both.
        fx.write(instance.load(self.root).overwrite_dir / "SKSE/Plugins/Shared_DISTR.ini", "Keyword = 0x801~Lantern.esp|x\n")
        self.assertEqual(self.of(self.scan(), "SKSE/Plugins/Shared_DISTR.ini"), [("Overwrite", ["lantern.esp"])])

    def test_a_disabled_mod_is_not_in_force_and_every_place_is_looked_through(self):
        fx.write(self.mods / "Old Lantern" / "Old_KID.ini", "Keyword = x|Armor|Bramble.esp\n")           # disabled
        fx.write(self.mods / "Quill" / "Quill_KID.ini", "Keyword = x|Armor|Bramble.esp\n")               # top folder
        fx.write(self.mods / "Quill" / "FLM" / "anything.ini", "FormList = 0x1~Skyrim.esm|0x2~Bramble.esp\n")
        fx.write(self.mods / "Quill" / "SKSE/Plugins/Deep/Deeper/data.json", '{"form": "Bramble.esp|0x801"}')
        fx.write(self.mods / "Quill" / "SKSE/Plugins/po3_KeywordItemDistributor.dll", b"invented")
        fx.write(self.mods / "Quill" / "SKSE/Plugins/InventedFramework.dll", b"invented")
        fx.write(self.mods / "Quill" / "meshes/quill/notes.txt", "Bramble.esp")                           # not a place looked through
        c = self.scan()
        found = sorted(e["rel"] for e in c["entries"] if "bramble.esp" in e["names"])
        self.assertEqual(found, ["FLM/anything.ini", "Quill_KID.ini", "SKSE/Plugins/Deep/Deeper/data.json"])
        self.assertTrue(census.whole(c))
        self.assertEqual(c["read"], c["files"])
        kinds = {k["kind"]: k for k in c["kinds"]}
        self.assertTrue(kinds["…_KID.ini"]["read_by_modtrap"])
        self.assertEqual(kinds["…_KID.ini"]["framework"], "Keyword Item Distributor")
        fw = {f["dll"]: f for f in c["frameworks"]}
        self.assertEqual((fw["po3_KeywordItemDistributor.dll"]["framework"], fw["po3_KeywordItemDistributor.dll"]["mod"]),
                         ("Keyword Item Distributor", "Quill"))
        self.assertFalse(fw["InventedFramework.dll"]["read_by_modtrap"])
        pub = census.public(c)
        self.assertNotIn("entries", pub)
        self.assertTrue(pub["whole"])

    def test_a_file_is_read_once_and_again_only_when_it_changed(self):
        f = fx.write(self.mods / "Quill" / "Quill_KID.ini", "Keyword = x|Armor|Bramble.esp\n")
        first = self.scan()
        self.assertEqual(first["fresh"], first["read"])
        again = self.scan()
        self.assertEqual((again["fresh"], again["read"]), (0, first["read"]))
        f.write_bytes(b"Keyword = x|Armor|Lantern.esp, and more\n")
        third = self.scan()
        self.assertEqual(third["fresh"], 1)
        self.assertEqual(self.of(third, "Quill_KID.ini"), [("Quill", ["lantern.esp"])])

    def test_what_could_not_be_read_is_named_and_the_step_says_so(self):
        """A file past the size of any settings file is not read, and is named: the look is then not whole, and
        the step is the owner's, with the file's name."""
        old = census.SETTINGS_BYTES
        census.SETTINGS_BYTES = 64
        try:
            fx.write(self.mods / "Quill" / "SKSE/Plugins/Huge.json", b" " * 100)
            c = self.scan()
            self.assertEqual(c["too_large"], ["Quill: SKSE/Plugins/Huge.json (0 MB)"])
            self.assertFalse(census.whole(c))
            m = model.build(instance.load(self.root))
            deep = steps.look_deeper(m, ["Bramble"], {})
            got = steps.compile_steps(m, ["Bramble"], dry_done("Bramble"), deep, False, False)
        finally:
            census.SETTINGS_BYTES = old
        st = next(s for s in got["steps"] if s["key"] == "mentions")
        self.assertEqual(st["who"], "you")
        self.assertIn("Quill: SKSE/Plugins/Huge.json", st["why"])

    ANIM = "meshes/actors/character/animations"

    def test_the_folders_of_animation_replacers_are_found_wherever_they_lie_under_meshes(self):
        """TL01§26: the replacer walks all of meshes for folders of its two names. Its condition files are settings
        files in force like any other; a folder named after a plugin, in the older layout, is a mention too."""
        q = self.mods / "Quill"
        fx.write(q / self.ANIM / "OpenAnimationReplacer/Invented Pack/Sub One/config.json",
                 '{\n "conditions": [\n  {"condition": "IsEquipped", "Form": {"pluginName": "Bramble.esp", "formID": "801"}}\n ]\n}\n')
        fx.write(q / self.ANIM / "OpenAnimationReplacer/Invented Pack/Sub One/wave.hkx", b"invented")
        fx.write(q / "meshes/actors/invented/deep/down/DynamicAnimationReplacer/_CustomConditions/100/_conditions.txt",
                 'IsEquippedRight("Bramble.esp" | 0x801) AND\nNOT IsWorn("Lantern.esp" | 0x5)\n')
        fx.write(q / self.ANIM / "DynamicAnimationReplacer/Bramble.esp/00000801/wave.hkx", b"invented")
        fx.write(q / "meshes/quill/config.json", '{"pluginName": "Bramble.esp"}')                 # not in such a folder
        fx.write(q / "SKSE/Plugins/OpenAnimationReplacer.dll", b"invented")
        c = self.scan()
        found = sorted((e["rel"], e["folder"]) for e in c["entries"] if "bramble.esp" in e["names"])
        self.assertEqual(found, [
            ("meshes/actors/character/animations/DynamicAnimationReplacer/Bramble.esp", True),
            ("meshes/actors/character/animations/OpenAnimationReplacer/Invented Pack/Sub One/config.json", False),
            ("meshes/actors/invented/deep/down/DynamicAnimationReplacer/_CustomConditions/100/_conditions.txt", False)])
        self.assertEqual(c["tree_folders"], 3)
        self.assertEqual(c["by_place"]["animation replacers' folders"], 2)
        self.assertTrue(census.whole(c))
        kind = next(k for k in c["kinds"] if k["framework"] == "Open Animation Replacer")
        self.assertEqual((kind["files"], kind["read_by_modtrap"]), (2, True))
        # The steps: every such line is a condition about a thing of the mod's; the replacer settles it itself.
        m = model.build(instance.load(self.root))
        deep = steps.look_deeper(m, ["Bramble"], {})
        by_file = {x["file"].rsplit("/", 1)[-1] or x["file"]: x for x in deep["mentions"]}
        self.assertEqual([ln["where"] for ln in by_file["config.json"]["lines"]], ["condition"])
        self.assertEqual([(ln["n"], ln["where"]) for ln in by_file["_conditions.txt"]["lines"]], [(1, "condition")])
        folder = next(x for x in deep["mentions"] if x["file"].endswith("Bramble.esp/"))
        self.assertEqual((folder["lines"][0]["n"], folder["lines"][0]["where"], folder["unread"]), (0, "only with", 0))
        got = steps.compile_steps(m, ["Bramble"], dry_done("Bramble"), deep, False, False)
        st = next(s for s in got["steps"] if s["key"] == "mentions")
        self.assertEqual((st["who"], st["state"]), ("ModTrap", "done"))

    def conditions(self, name, text, plugins=("Bramble.esp",)):
        f = fx.write(self.mods / "Quill" / self.ANIM / "OpenAnimationReplacer/Pack/Sub" / name, text)
        got = steps.read_mention(f, "Quill", self.ANIM + "/OpenAnimationReplacer/Pack/Sub/" + name, list(plugins), {"openanimationreplacer.dll"})
        return [(ln["n"], ln["where"]) for ln in got["lines"]], got

    def test_the_condition_a_mention_belongs_to_is_read_from_the_files_structure(self):
        """TL01§26: most conditions do not hold once their thing is gone; two can; one of another program's is
        not known. Which it is, is read from the file, also where conditions lie inside one another."""
        form = lambda key: '"%s": {\n    "pluginName": "Bramble.esp",\n    "formID": "801"\n   }' % key
        text = ('{\n "name": "Invented",\n "conditions": [\n  {\n   "condition": "IsEquipped",\n   %s\n  },\n'
                '  {\n   "condition": "OR",\n   "Conditions": [\n    {\n   "condition": "IsInSpecifiedScene",\n   %s\n  },\n'
                '    {\n   "condition": "InventedByAnotherProgram",\n   %s\n  },\n'
                '    {\n   "condition": "IsActorBase", "negated": true,\n   %s\n  }\n   ]\n  }\n ]\n}\n') % (
                    form("Form"), form("Scene"), form("Thing"), form("Actor base"))
        lines, got = self.conditions("config.json", text)
        self.assertEqual([w for _n, w in lines], ["condition", "may hold", "", "condition"])
        self.assertEqual((got["count"], got["unread"], got["kind"]), (4, 2, "Open Animation Replacer"))
        # All on one line: the lines cannot be told apart, so the least settled of them counts for the line.
        lines, got = self.conditions("user.json", json.dumps(json.loads(text)))
        self.assertEqual(lines, [(1, "")])
        lines, got = self.conditions("config.json", json.dumps({"conditions": [{"condition": "IsWorn", "Form": {"pluginName": "bramble.ESP", "formID": "1"}},
                                                                               {"condition": "HasPerk", "Perk": {"pluginName": "Bramble.esp", "formID": "2"}}]}))
        self.assertEqual(lines, [(1, "condition")])
        # Named only in words, or in a file that is not sound: not known, and the owner's.
        lines, got = self.conditions("config.json", '{"name": "for Bramble.esp", "conditions": []}')
        self.assertEqual(lines, [(1, "")])
        lines, got = self.conditions("config.json", '{"conditions": [ {"condition": "IsEquipped", "Form": {"pluginName": "Bramble.esp" ')
        self.assertEqual(lines, [(1, "")])
        # The older text file: one condition to a line, by its name.
        lines, got = self.conditions("_conditions.txt", 'IsEquippedRight("Bramble.esp" | 0x801) AND\nNOT IsWorn("Bramble.esp" | 0x802) OR\n'
                                     'InventedFunction("Bramble.esp" | 0x803) AND\nIsFemale()\n')
        self.assertEqual(lines, [(1, "condition"), (2, "condition"), (3, "")])
        # In the step, what can hold is the owner's, with the line and what to do.
        m = model.build(instance.load(self.root))
        fx.write(self.mods / "Quill" / "SKSE/Plugins/OpenAnimationReplacer.dll", b"invented")
        (self.mods / "Quill" / self.ANIM / "OpenAnimationReplacer/Pack/Sub/_conditions.txt").unlink()
        fx.write(self.mods / "Quill" / self.ANIM / "OpenAnimationReplacer/Pack/Sub/config.json", text)
        (self.mods / "Quill" / self.ANIM / "OpenAnimationReplacer/Pack/Sub/user.json").unlink()
        m = model.build(instance.load(self.root))
        got = steps.compile_steps(m, ["Bramble"], dry_done("Bramble"), steps.look_deeper(m, ["Bramble"], {}), False, False)
        st = next(x for x in got["steps"] if x["key"] == "mentions")
        self.assertEqual(st["who"], "you")
        look = st["items"][0]["look"]
        self.assertEqual(len(look), 2)
        self.assertIn("can hold once the thing is gone", look[0]["means"])
        self.assertIn("animation replacer's own menu", look[0]["todo"])

    def test_without_the_replacer_whose_source_was_read_its_files_are_the_owners_to_judge(self):
        """What ModTrap read is one replacer's handling. Where only another program that uses the same files is
        installed, the file is found all the same, and left to the owner."""
        q = self.mods / "Quill"
        fx.write(q / self.ANIM / "DynamicAnimationReplacer/_CustomConditions/100/_conditions.txt", 'IsEquippedRight("Bramble.esp" | 0x801)\n')
        m = model.build(instance.load(self.root))
        deep = steps.look_deeper(m, ["Bramble"], {})
        self.assertEqual([(x["kind"], x["unread"]) for x in deep["mentions"]], [("", 1)])
        got = steps.compile_steps(m, ["Bramble"], dry_done("Bramble"), deep, False, False)
        self.assertEqual(next(s for s in got["steps"] if s["key"] == "mentions")["who"], "you")

    def test_a_folder_without_folders_is_passed_by_next_time_until_it_changes(self):
        q = self.mods / "Quill"
        for i in range(4):
            fx.write(q / "meshes/quill" / ("set %d" % i) / "leaf.nif", b"invented")
        census._leaf.clear()
        first = self.scan()
        again = self.scan()
        self.assertEqual(first["skipped"], 0)
        self.assertEqual(again["skipped"], 4)
        self.assertLess(again["listed"], first["listed"])
        # A replacer's folder added inside one of them changes that folder, and is found.
        fx.write(q / "meshes/quill/set 2/OpenAnimationReplacer/Pack/Sub/config.json", '{"pluginName": "Bramble.esp"}')
        third = self.scan()
        self.assertEqual(third["tree_folders"], 1)
        self.assertEqual([e["rel"] for e in third["entries"] if "bramble.esp" in e["names"]],
                         ["meshes/quill/set 2/OpenAnimationReplacer/Pack/Sub/config.json"])

    def lines(self, since):
        return [ln["level"] + " " + ln["text"] for ln in logbook.lines_after(since)[0] if ln["source"] == "scanner"]

    def test_the_log_says_what_was_looked_through_and_names_each_failure_with_its_reason(self):
        mark = logbook.lines_after(0)[1]
        census._last_failed = None
        self.scan()
        said = self.lines(mark)
        self.assertTrue(any("the look is whole" in t for t in said), said)
        self.assertTrue(any(t.startswith("info looked through") and "listing took" in t for t in said), said)
        self.assertTrue(any("settings files in force" in t for t in said), said)
        self.assertTrue(any(t.startswith("info read:") for t in said), said)
        # A file that cannot be opened, and a folder that cannot be listed: each on its own line, with the reason.
        real_open, real_scandir = open, os.scandir
        bad_file = fx.write(self.mods / "Quill" / "SKSE/Plugins/Locked.json", "x")
        fx.write(self.mods / "Quill" / "meshes/quill/closed/leaf.nif", b"invented")

        def no_open(path, *a, **k):
            if str(path) == str(bad_file):
                raise PermissionError(13, "Permission denied")
            return real_open(path, *a, **k)

        def no_scandir(path):
            if str(path).replace("\\", "/").endswith("meshes/quill/closed"):
                raise PermissionError(13, "Permission denied")
            return real_scandir(path)

        import builtins
        mark = logbook.lines_after(0)[1]
        builtins.open, os.scandir = no_open, no_scandir
        try:
            c = self.scan()
            again = self.scan()
        finally:
            builtins.open, os.scandir = real_open, real_scandir
        self.assertFalse(census.whole(c))
        self.assertEqual(c["unreadable"], ["Quill: SKSE/Plugins/Locked.json (PermissionError (Permission denied))"])
        self.assertEqual(c["cut_mods"], ["Quill: meshes/quill/closed (PermissionError (Permission denied))"])
        said = self.lines(mark)
        self.assertTrue(any(t.startswith("warn the look is NOT whole: 1 folder(s) could not be listed to the end, 1 file(s) could not be opened") for t in said), said)
        self.assertIn("warn could not be opened: Quill: SKSE/Plugins/Locked.json (PermissionError (Permission denied))", said)
        self.assertIn("warn could not be listed to the end: Quill: meshes/quill/closed (PermissionError (Permission denied))", said)
        # The second look failed in the same way: said, and not written out again.
        self.assertEqual(sum(t.startswith("warn could not be opened") for t in said), 1)
        self.assertTrue(any("the same 2 as at the last look" in t for t in said), said)
        self.assertEqual(again["unreadable"], c["unreadable"])

    def test_a_scanner_that_fails_altogether_is_never_taken_for_nothing_found(self):
        m = model.build(instance.load(self.root))
        real = census.scan

        def broken(*a, **k):
            raise RuntimeError("invented")

        census.scan = broken
        try:
            deep = steps.look_deeper(m, ["Bramble"], {})
        finally:
            census.scan = real
        self.assertEqual(deep["scan"]["failed"], "RuntimeError")
        self.assertFalse(deep["scan"]["whole"])
        got = steps.compile_steps(m, ["Bramble"], dry_done("Bramble"), deep, False, False)
        st = next(s for s in got["steps"] if s["key"] == "mentions")
        self.assertEqual(st["who"], "you")
        self.assertIn("the scanner itself failed (RuntimeError)", st["why"])
        self.assertFalse(got["checked"])

    def test_with_no_file_naming_the_plugin_the_step_states_what_was_looked_through(self):
        m = model.build(instance.load(self.root))
        deep = steps.look_deeper(m, ["Bramble"], {})
        self.assertEqual(deep["mentions"], [])
        got = steps.compile_steps(m, ["Bramble"], dry_done("Bramble"), deep, False, False)
        st = next(s for s in got["steps"] if s["key"] == "mentions")
        self.assertEqual((st["who"], st["state"]), ("ModTrap", "done"))
        self.assertIn("every settings file in force", st["why"])
        self.assertIn("none names the mod's plugin", " ".join(c["text"] for c in got["checks"]))


if __name__ == "__main__":
    unittest.main()
