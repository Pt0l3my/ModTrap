import struct
import tempfile
import unittest
from pathlib import Path

from modtrap import plugin


class HeaderTests(unittest.TestCase):
    def test_round_trip(self):
        data = plugin.build(("Skyrim.esm", "Bramble.esp"), flags=plugin.FLAG_ESL, author="someone invented",
                            description="an invented plugin")
        h = plugin.parse(data)
        self.assertEqual(h.masters, ("Skyrim.esm", "Bramble.esp"))
        self.assertEqual((h.author, h.description), ("someone invented", "an invented plugin"))
        self.assertTrue(h.esl_flag)
        self.assertFalse(h.esm_flag)
        self.assertEqual(h.fields[:2], ("HEDR", "CNAM"))

    def test_no_masters(self):
        self.assertEqual(plugin.parse(plugin.build()).masters, ())

    def test_reads_the_header_only(self):
        # Whatever follows the header record is never looked at.
        data = plugin.build(("Skyrim.esm",)) + b"GRUP" + b"\xff" * 64
        self.assertEqual(plugin.parse(data).masters, ("Skyrim.esm",))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Invented.esp"
            p.write_bytes(data)
            self.assertEqual(plugin.read(p).masters, ("Skyrim.esm",))

    def test_large_field_with_size_prefix(self):
        big = b"\x00" * 70000
        body = b"HEDR" + struct.pack("<H", 12) + b"\x00" * 12
        body += b"XXXX" + struct.pack("<HI", 4, len(big)) + b"ONAM" + struct.pack("<H", 0) + big
        body += b"MAST" + struct.pack("<H", 11) + b"Skyrim.esm\x00" + b"DATA" + struct.pack("<H", 8) + b"\x00" * 8
        data = b"TES4" + struct.pack("<IIIIHH", len(body), 0, 0, 0, 44, 0) + body
        self.assertEqual(plugin.parse(data).masters, ("Skyrim.esm",))

    def test_name_in_windows_1252(self):
        name = "Caf\xe9.esp".encode("cp1252") + b"\x00"
        body = b"MAST" + struct.pack("<H", len(name)) + name
        data = b"TES4" + struct.pack("<IIIIHH", len(body), 0, 0, 0, 44, 0) + body
        self.assertEqual(plugin.parse(data).masters, ("Caf\xe9.esp",))

    def test_refusals(self):
        good = plugin.build(("Skyrim.esm",))
        cases = {
            "short": good[:10],
            "not a plugin": b"GRUP" + good[4:],
            "cut": good[:-3],
            "huge": b"TES4" + struct.pack("<I", plugin.HEADER_CAP + 1) + b"\x00" * 16,
            "field past the header": b"TES4" + struct.pack("<IIIIHH", 8, 0, 0, 0, 44, 0) + b"MAST" +
                                     struct.pack("<H", 500) + b"ab",
            "empty master": b"TES4" + struct.pack("<IIIIHH", 7, 0, 0, 0, 44, 0) + b"MAST" +
                            struct.pack("<H", 1) + b"\x00",
        }
        for label, data in cases.items():
            with self.subTest(label):
                with self.assertRaises(plugin.Unreadable):
                    plugin.parse(data)

    def test_missing_file(self):
        with self.assertRaises(plugin.Unreadable):
            plugin.read(Path("/nonexistent/Invented.esp"))

    def test_kind(self):
        esl = plugin.parse(plugin.build(flags=plugin.FLAG_ESL))
        esm = plugin.parse(plugin.build(flags=plugin.FLAG_ESM))
        plain = plugin.parse(plugin.build())
        self.assertEqual(plugin.kind("A.esp", plain), "esp")
        self.assertEqual(plugin.kind("A.esp", esl), "esp+esl")
        self.assertEqual(plugin.kind("A.esp", esm), "esp+esm")
        self.assertEqual(plugin.kind("A.ESM", plain), "esm")
        self.assertEqual(plugin.kind("A.esm", esl), "esm+esl")
        self.assertEqual(plugin.kind("A.esl", plain), "esl")
        self.assertTrue(plugin.is_plugin_name("Thing.ESP"))
        self.assertFalse(plugin.is_plugin_name("Thing.esp.bak"))


if __name__ == "__main__":
    unittest.main()
