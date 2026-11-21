"""Taking in an archive (DESIGN§16.1): what is unpacked, what is refused, and where the mod is inside it."""

from __future__ import annotations

import io
import os
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from modtrap import plugin, unpack

FAKE = Path(__file__).with_name("fake_7zip.py")


def zipped(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


class Unpacking(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        os.environ.pop("FAKE_7ZIP", None)
        self.tmp.cleanup()

    def archive(self, name: str, data: bytes) -> Path:
        p = self.dir / name
        p.write_bytes(data)
        return p

    def fake_7zip(self) -> Path:
        """A launcher for the stand-in, as one program file."""
        if sys.platform == "win32":
            p = self.dir / "fake7z.cmd"
            p.write_text('@"%s" "%s" %%*\r\n' % (sys.executable, FAKE))
        else:
            p = self.dir / "fake7z"
            p.write_text('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, FAKE))
            p.chmod(p.stat().st_mode | stat.S_IXUSR)
        return p

    def test_a_zip_is_unpacked_with_python_alone(self) -> None:
        src = self.archive("Thistle.zip", zipped({"Thistle/Thistle.esp": plugin.build(("Skyrim.esm",)),
                                                  "Thistle/textures/a.dds": b"x"}))
        got = unpack.unpack(src, self.dir / "out")
        self.assertEqual(got, {"kind": "zip", "files": 2})
        self.assertTrue((self.dir / "out" / "Thistle" / "textures" / "a.dds").is_file())

    def test_the_kind_is_read_from_the_file_not_its_name(self) -> None:
        src = self.archive("Thistle.7z", zipped({"a.txt": b"x"}))
        self.assertEqual(unpack.kind(src), "zip")
        with self.assertRaises(unpack.Refused):
            unpack.unpack(self.archive("readme.zip", b"just words"), self.dir / "out")
        self.assertFalse((self.dir / "out").exists())

    def test_a_name_that_leaves_the_folder_is_refused_and_nothing_is_left(self) -> None:
        for bad in ("../outside.txt", "/rooted.txt", "C:/drive.txt", "ok/../../up.txt", "con.txt", "a/b:stream"):
            src = self.archive("bad.zip", zipped({"fine.txt": b"x", bad: b"x"}))
            with self.assertRaises(unpack.Refused, msg=bad):
                unpack.unpack(src, self.dir / "out")
            self.assertFalse((self.dir / "out").exists(), bad)
        self.assertFalse((self.dir / "outside.txt").exists())

    def test_safe_names(self) -> None:
        self.assertEqual(unpack.safe_parts("Data\\Meshes\\a.nif"), ("Data", "Meshes", "a.nif"))
        self.assertEqual(unpack.safe_parts("./a//b"), ("a", "b"))
        for bad in ("", "..", "a/..", "/a", "\\\\server\\share", "D:a", "nul", "trailing. ", "x" * 300):
            self.assertIsNone(unpack.safe_parts(bad), bad)

    def test_a_link_in_a_zip_is_refused(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            info = zipfile.ZipInfo("shortcut")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "C:/Elsewhere")
        with self.assertRaises(unpack.Refused):
            unpack.unpack(self.archive("link.zip", buf.getvalue()), self.dir / "out")

    def test_too_much_is_refused_before_anything_is_written(self) -> None:
        src = self.archive("big.zip", zipped({"a.bin": b"0" * 5000, "b.bin": b"0" * 5000}))
        old = unpack.MAX_BYTES
        unpack.MAX_BYTES = 6000
        try:
            with self.assertRaises(unpack.Refused):
                unpack.unpack(src, self.dir / "out")
        finally:
            unpack.MAX_BYTES = old
        self.assertFalse((self.dir / "out").exists())

    def test_7z_and_rar_go_through_the_owners_7zip(self) -> None:
        inner = zipped({"Wrapper/meshes/a.nif": b"x", "Wrapper/Thistle.esp": plugin.build(())})
        for magic, k in ((b"7z\xbc\xaf\x27\x1c", "7z"), (b"Rar!\x1a\x07\x00", "rar")):
            src = self.archive("Thistle." + k, magic + inner)
            self.assertEqual(unpack.kind(src), k)
            got = unpack.unpack(src, self.dir / ("out-" + k), seven_zip=self.fake_7zip())
            self.assertEqual(got, {"kind": k, "files": 2})

    def test_without_7zip_a_7z_is_refused_in_words(self) -> None:
        src = self.archive("Thistle.7z", b"7z\xbc\xaf\x27\x1c" + zipped({"a.txt": b"x"}))
        os.environ["MODTRAP_7ZIP"] = str(self.dir / "not-there.exe")
        try:
            with self.assertRaises(unpack.Refused) as c:
                unpack.unpack(src, self.dir / "out")
        finally:
            os.environ.pop("MODTRAP_7ZIP", None)
        self.assertIn("7-Zip", str(c.exception))

    def test_what_7zip_reports_is_checked_too(self) -> None:
        src = self.archive("Thistle.7z", b"7z\xbc\xaf\x27\x1c" + zipped({"a.txt": b"x"}))
        for how in ("link", "encrypted", "broken"):
            os.environ["FAKE_7ZIP"] = how
            with self.assertRaises(unpack.Refused, msg=how):
                unpack.unpack(src, self.dir / "out", seven_zip=self.fake_7zip())
            self.assertFalse((self.dir / "out").exists(), how)

    def test_a_7zip_listing_is_read_block_by_block(self) -> None:
        text = "7-Zip\r\n\r\n--\r\nPath = x.7z\r\nType = 7z\r\n\r\n----------\r\nPath = a\\b.esp\r\nSize = 12\r\n\r\nPath = a\r\nFolder = +\r\n"
        got = unpack.parse_7z_listing(text)
        self.assertEqual([(e["Path"], e.get("Size")) for e in got], [("a\\b.esp", "12"), ("a", None)])


class Layout(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make(self, *files: str) -> Path:
        for f in files:
            p = self.dir / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x")
        return self.dir

    def where(self, got: dict) -> str:
        return got["root"].relative_to(self.dir).as_posix()

    def test_the_mod_at_the_top(self) -> None:
        got = unpack.layout(self.make("Thistle.esp", "meshes/a.nif"))
        self.assertEqual((self.where(got), got["installer"], got["sure"]), (".", "", True))

    def test_inside_wrapping_folders(self) -> None:
        got = unpack.layout(self.make("Thistle 1.2/readme.txt", "Thistle 1.2/Inner/textures/a.dds"))
        self.assertEqual(self.where(got), "Thistle 1.2/Inner")

    def test_inside_a_data_folder(self) -> None:
        got = unpack.layout(self.make("Data/Thistle.esp", "Docs/readme.txt"))
        self.assertEqual(self.where(got), "Data")

    def test_an_installer_is_recognised(self) -> None:
        got = unpack.layout(self.make("Thistle/fomod/ModuleConfig.xml", "Thistle/Core/Thistle.esp", "Thistle/Extra/x.esp"))
        self.assertEqual((self.where(got), got["installer"]), ("Thistle", "fomod"))

    def test_folders_to_choose_from_are_recognised(self) -> None:
        got = unpack.layout(self.make("00 Core/Thistle.esp", "01 Extra/meshes/a.nif"))
        self.assertEqual((got["installer"], got["options"]), ("options", ["00 Core", "01 Extra"]))

    def test_what_is_not_recognised_is_said_to_be_unsure(self) -> None:
        got = unpack.layout(self.make("a.dll", "b.ini"))
        self.assertEqual((got["installer"], got["sure"]), ("", False))


if __name__ == "__main__":
    unittest.main()
