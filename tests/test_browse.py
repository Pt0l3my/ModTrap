import os
import tempfile
import unittest
from pathlib import Path

from modtrap import browse
from tests import _fixtures as fx


class BrowseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = fx.small_list(self.base / "Lists" / "Example List")
        (self.base / "Lists" / "Not A List").mkdir()
        (self.base / "Lists" / "$RECYCLE.BIN").mkdir()
        fx.write(self.base / "Lists" / "a file.txt", "not listed")

    def tearDown(self):
        self.tmp.cleanup()

    def test_folders_only_and_modlists_marked(self):
        d = browse.listing(str(self.base / "Lists"))
        self.assertEqual([(f["name"], f["modlist"]) for f in d["folders"]], [("Example List", True), ("Not A List", False)])
        self.assertFalse(d["modlist"])
        self.assertEqual(d["parent"], str(self.base))
        self.assertEqual(d["crumbs"][-1], {"name": "Lists", "path": str(self.base / "Lists")})
        inside = browse.listing(str(self.root))
        self.assertTrue(inside["modlist"])
        self.assertIn("mods", [f["name"] for f in inside["folders"]])

    def test_start_and_refusals(self):
        start = browse.listing("")
        self.assertTrue(start["folders"])
        self.assertIsNone(start["parent"])
        for bad in ("relative/path", "\\\\server\\share", "\\\\?\\C:\\x", str(self.base / "nowhere"), "x" * 2000):
            with self.subTest(bad[:20]):
                with self.assertRaises(browse.Refused):
                    browse.listing(bad)

    def test_links_are_not_shown(self):
        try:
            os.symlink(self.root, self.base / "Lists" / "Linked", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("links cannot be made here")
        self.assertNotIn("Linked", [f["name"] for f in browse.listing(str(self.base / "Lists"))["folders"]])


if __name__ == "__main__":
    unittest.main()
