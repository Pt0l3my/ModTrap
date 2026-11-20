import base64
import json
import os
import tempfile
import unittest
from pathlib import Path

from modtrap import api, locate, logbook
from modtrap.server import Bad
from tests import _fixtures as fx


class LocateTests(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        os.environ["MODTRAP_HOME"] = str(self.base / "home")
        self.root = fx.small_list(self.base / "Lists" / "Example List")
        self.ini = (self.root / "ModOrganizer.ini").read_bytes()

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_found_through_the_paths_in_the_ini(self):
        folder, how = locate.find("Example List", self.ini, roots=[])
        self.assertEqual(folder, self.root)
        self.assertIn("ModOrganizer.ini", how)
        # The ini file alone, with no folder name, is enough too.
        self.assertEqual(locate.find(None, self.ini, roots=[])[0], self.root)

    def test_a_copy_elsewhere_with_the_same_ini_is_not_taken_for_another_name(self):
        self.assertEqual(locate.find("Other Name", self.ini, roots=[]), (None, ""))

    def test_found_by_search_when_the_ini_names_no_path_inside(self):
        ini = b"[General]\r\ngameName=Skyrim Special Edition\r\nselected_profile=@ByteArray(Default)\r\n"
        (self.root / "ModOrganizer.ini").write_bytes(ini)
        self.assertEqual(locate.find("Example List", ini, roots=[])[0], None)
        folder, how = locate.find("example list", ini, roots=[self.base])
        self.assertEqual(folder, self.root)
        self.assertIn("search", how)

    def test_search_is_bounded_and_checks_the_ini(self):
        ini = b"[General]\r\ngameName=Skyrim Special Edition\r\n"
        deep = self.base / "a" / "b" / "c" / "d" / "Deep List"
        fx.write(deep / "ModOrganizer.ini", ini)
        self.assertEqual(locate.find("Deep List", ini, roots=[self.base])[0], None)        # too deep
        self.assertEqual(locate.find("Deep List", ini, roots=[self.base / "a" / "b"])[0], deep)
        fx.write(self.base / "x" / "Deep List" / "ModOrganizer.ini", ini + b"; another list of the same name\r\n")
        self.assertEqual(locate.find("Deep List", ini, roots=[self.base / "x"])[0], None)   # same name, other ini

    def test_an_ini_changed_since_the_drop_still_finds_the_one_instance_of_that_name_and_game(self):
        dropped = self.ini                                              # what the page read
        (self.root / "ModOrganizer.ini").write_bytes(self.ini + b"[Geometry]\r\nwindow=changed\r\n")   # MO2 wrote since
        folder, how = locate.find("Example List", dropped, roots=[])
        self.assertEqual(folder, self.root)
        self.assertIn("changed", how)
        # Another game's instance of the same name is not taken.
        other = dropped.replace(b"Skyrim Special Edition", b"Some Other Game")
        self.assertEqual(locate.find("Example List", other, roots=[])[0], None)

    def test_links_are_not_followed(self):
        ini = b"[General]\r\ngameName=Skyrim Special Edition\r\n"
        real = self.base / "elsewhere" / "Linked List"
        fx.write(real / "ModOrganizer.ini", ini)
        (self.base / "drive").mkdir()
        try:
            os.symlink(real, self.base / "drive" / "Linked List", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("links cannot be made here")
        self.assertEqual(locate.find("Linked List", ini, roots=[self.base / "drive"])[0], None)

    def test_a_recent_folder_is_tried_first(self):
        ini = b"[General]\r\ngameName=Skyrim Special Edition\r\n"
        (self.root / "ModOrganizer.ini").write_bytes(ini)
        folder, how = locate.find("Example List", ini, recents=[str(self.root)], roots=[])
        self.assertEqual((folder, how), (self.root, "a folder opened before"))

    def test_the_api_opens_what_it_finds_and_refuses_what_it_cannot(self):
        a = api.Api()
        body = {"name": "Example List", "ini": base64.b64encode(self.ini).decode()}
        opened = []
        a.open = lambda folder, profile=None, wait=False: opened.append(folder)   # type: ignore[method-assign]
        self.assertEqual(a.locate(body)["status"], "reading")
        self.assertEqual(opened, [str(self.root)])
        for bad in ({"name": "Example List", "ini": "not base64 !"}, {"name": "a/b", "ini": body["ini"]},
                    {"name": "Example List"}, {"name": "Nowhere", "ini": body["ini"]}):
            with self.subTest(json.dumps(bad)[:40]):
                with self.assertRaises(Bad):
                    a.locate(bad)


if __name__ == "__main__":
    unittest.main()
