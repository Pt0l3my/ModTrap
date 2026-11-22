"""The scanner (WHY§98): every settings file in force in the modlist, the winner of each, read to its end."""

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
        self.assertTrue(kinds["_KID.ini"]["read_by_modtrap"])
        self.assertEqual(kinds["_KID.ini"]["framework"], "Keyword Item Distributor")
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
            self.assertEqual(c["too_large"], ["Quill: SKSE/Plugins/Huge.json"])
            self.assertFalse(census.whole(c))
            m = model.build(instance.load(self.root))
            deep = steps.look_deeper(m, ["Bramble"], {})
            got = steps.compile_steps(m, ["Bramble"], dry_done("Bramble"), deep, False, False)
        finally:
            census.SETTINGS_BYTES = old
        st = next(s for s in got["steps"] if s["key"] == "mentions")
        self.assertEqual(st["who"], "you")
        self.assertIn("Quill: SKSE/Plugins/Huge.json", st["why"])

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
