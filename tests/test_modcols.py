"""MO2's own columns of the mods' list (MT70, MO04): Conflicts, Installation and Notes, on an invented modlist."""

import os
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, instance, logbook, modcols, model
from tests import _fixtures as fx
from tests.test_modweb import CORE, pf
from tests.test_updates import FakeNet


def invented(root: Path) -> Path:
    fx.make_instance(root, [
        ("+", "Top", {"textures/a.dds": b"t", "textures/only-top.dds": b"t"}),                    # wins over Middle and Bottom: overwrites
        ("+", "Hidden Away", {"textures/a.dds.mohidden": b"h", "meshes.mohidden/x.nif": b"h"}),   # all of it hidden from the game: no state
        ("+", "Middle", {"textures/a.dds": b"m", "textures/b.dds": b"m", "meta.ini": b"[General]\r\ncomments=\"Keep enabled, always\"\r\nnotes=long\r\n"}),   # both
        ("-", "Asleep", {"textures/a.dds": b"z"}),                                                # disabled: not in the game, no state
        ("+", "Covered", {"textures/b.dds": b"c", "Readme.txt": b"about", "fomod/info.xml": b"<fomod/>"}),      # every file loses: redundant
        ("+", "Bottom", {"textures/a.dds": b"b", "textures/c.dds": b"b"}),                       # loses one, keeps one: overwritten
        ("+", "Alone", {"textures/alone.dds": b"x", "readme.txt": b"its own", "meta.ini": b"[General]\r\ncomments=plain\r\n"}),   # shares only papers MO2 leaves out
        ("+", "Notes_separator", {"meta.ini": b"[General]\r\ncomments=Enable all of these\\nwith a controller\r\n"}),
        ("+", "Core", {CORE: pf(())}),
    ], load_order=[CORE])
    return root


class MO2sColumns(unittest.TestCase):
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

    def test_conflicts_as_mo2_tells_them_for_loose_files(self):
        got = modcols.conflicts(self.m)
        self.assertEqual(got["mods"], {"Top": "overwrite", "Middle": "mixed", "Covered": "redundant", "Bottom": "overwritten"})
        self.assertEqual((got["cut"], got["enabled"]), (False, 8))            # the seven enabled mods and Overwrite

    def test_a_mods_list_of_files_is_kept_while_its_folder_looks_the_same_from_above(self):
        cache: dict = {}
        first = modcols.conflicts(self.m, cache)
        again = modcols.conflicts(self.m, cache)
        self.assertEqual((first["listed"], again["listed"], again["mods"]), (8, 0, first["mods"]))
        fx.write(self.root / "mods" / "Alone" / "textures" / "a.dds", b"now it has one too")
        os.utime(self.root / "mods" / "Alone" / "textures", (time.time() + 5, time.time() + 5))
        third = modcols.conflicts(self.m, cache)
        self.assertEqual((third["listed"], third["mods"].get("Alone")), (1, "overwritten"))      # it is the lowest of them: all three above win its new file

    def test_installation_and_notes(self):
        got = modcols.info(self.m.instance)
        self.assertEqual((got["Middle"]["notes"], got["Alone"]["notes"], got["Top"]["notes"]), ("Keep enabled, always", "plain", ""))
        self.assertEqual(got["Notes_separator"]["notes"], "Enable all of these\nwith a controller")
        self.assertTrue(abs(got["Top"]["installed"] - time.time()) < 3600)
        self.assertEqual(modcols.unquote('"a \\"b\\" c\\x2014\\\\d"'), 'a "b" c—\\d')

    def test_the_page_is_told_as_the_answers_come(self):
        a = api.Api()
        a.updating.net = FakeNet({})
        a.updating.by_itself = False
        a.running = lambda image: False
        a.open(str(self.root), wait=True)
        for _ in range(400):
            got = a.get("/api/modcols", {})[1]
            if got["state"] == "done":
                break
            time.sleep(0.02)
        self.assertEqual((got["error"], got["conflicts"]["Middle"], got["info"]["Middle"]["notes"], got["cut"]), ("", "mixed", "Keep enabled, always", False))
        for _ in range(400):
            if a.updating.work["state"] != "going" and a.updating.reading["state"] != "going" and a._listscan["state"] not in ("going", "looking"):
                break
            time.sleep(0.01)


if __name__ == "__main__":
    unittest.main()
