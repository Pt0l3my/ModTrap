import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from modtrap import __main__ as cli
from tests import _fixtures as fx


class ScanTests(unittest.TestCase):
    def run_scan(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["scan", *args])
        return code, out.getvalue()

    def test_scan_prints_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            root = fx.small_list(Path(d) / "Example List")
            before = sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in root.rglob("*"))
            code, text = self.run_scan(str(root), "--mod", "Bramble", "--plugin", "generated.esp")
            after = sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in root.rglob("*"))
        self.assertEqual(code, 0)
        self.assertEqual(before, after)
        self.assertIn("Health check: clean", text)
        self.assertIn("4 plugin(s) in 4 other mod(s) depend on it", text)
        self.assertIn("in mod 'Patch Collection' (priority 7): 1 other plugin(s) of this mod do not depend on it", text)
        self.assertIn("in mod 'Tool Output' (priority 8): made by a tool: Invented Patcher", text)
        self.assertIn("in mod 'Lantern' (priority 3): every plugin of this mod depends on it", text)
        self.assertIn("masters (3): Skyrim.esm, Bramble.esp, Quill.esp", text)

    def test_not_an_instance(self):
        with tempfile.TemporaryDirectory() as d:
            code, text = self.run_scan(d)
        self.assertEqual(code, 2)
        self.assertIn("cannot read this folder", text)


if __name__ == "__main__":
    unittest.main()
