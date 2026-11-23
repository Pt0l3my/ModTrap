"""Taking in an archive (DESIGN§16.1): what is unpacked, what is refused, and where the mod is inside it."""

from __future__ import annotations

import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from modtrap import plugin, unpack

FAKE = Path(__file__).with_name("fake_7zip.py")
REAL_7Z = shutil.which("7z") or shutil.which("7zz")


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
        self.assertEqual(got, {"kind": "zip", "files": 2, "by": "ModTrap itself"})
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
            self.assertEqual(got, {"kind": k, "files": 2, "by": "7-Zip"})

    def test_without_7zip_a_7z_is_refused_in_words(self) -> None:
        src = self.archive("Thistle.7z", b"7z\xbc\xaf\x27\x1c" + zipped({"a.txt": b"x"}))
        os.environ["MODTRAP_7ZIP"] = str(self.dir / "not-there.exe")
        os.environ["MODTRAP_TAR"] = str(self.dir / "not-there-either.exe")
        try:
            with self.assertRaises(unpack.Refused) as c:
                unpack.unpack(src, self.dir / "out")
        finally:
            os.environ.pop("MODTRAP_7ZIP", None)
            os.environ.pop("MODTRAP_TAR", None)
        self.assertIn("7-Zip", str(c.exception))
        self.assertIn("Windows 11", str(c.exception))

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


@unittest.skipIf(REAL_7Z is None, "the 7-Zip program is not installed here")
class WithTheReal7Zip(unittest.TestCase):
    """The same unpacker against 7-Zip itself, where it is installed: archives made by 7-Zip from invented files."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        src = self.dir / "src" / "Wrapper"
        (src / "textures" / "x").mkdir(parents=True)
        (src / "Thistle.esp").write_bytes(plugin.build(("Skyrim.esm",)))
        (src / "textures" / "x" / "b c.dds").write_bytes(b"invented")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def made(self, name: str, *switches: str) -> Path:
        out = self.dir / name
        subprocess.run([REAL_7Z, "a", "-bd", *switches, str(out), "Wrapper"], cwd=self.dir / "src", check=True,
                       stdout=subprocess.DEVNULL)
        return out

    def test_a_7z_made_by_7zip_is_unpacked(self) -> None:
        got = unpack.unpack(self.made("plain.7z"), self.dir / "out")
        self.assertEqual(got, {"kind": "7z", "files": 2, "by": "ModTrap itself"})        # its own reader comes first (WHY§123)
        self.assertEqual((self.dir / "out" / "Wrapper" / "textures" / "x" / "b c.dds").read_bytes(), b"invented")
        self.assertEqual(unpack.layout(self.dir / "out")["root"].name, "Wrapper")

    def test_a_password_is_refused_in_words_and_nothing_is_left(self) -> None:
        for name, switches in (("locked.7z", ("-pSecret",)), ("hidden.7z", ("-pSecret", "-mhe=on"))):
            with self.assertRaises(unpack.Refused) as c:
                unpack.unpack(self.made(name, *switches), self.dir / "out")
            self.assertIn("password", str(c.exception))
            self.assertFalse((self.dir / "out").exists())

    @unittest.skipIf(os.name == "nt", "making a link needs rights Windows does not give by default")
    def test_a_link_is_refused_from_the_listing(self) -> None:
        os.symlink("/etc/hostname", self.dir / "src" / "Wrapper" / "link.txt")
        with self.assertRaises(unpack.Refused) as c:
            unpack.unpack(self.made("link.7z", "-snl"), self.dir / "out")
        self.assertIn("link", str(c.exception))
        self.assertFalse((self.dir / "out").exists())


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


@unittest.skipIf(unpack.find_tar() is None, "the system's bsdtar is not installed here")
class WithoutSevenZip(unittest.TestCase):
    """WHY§123: where 7-Zip is not installed, a .7z goes through the unpacker the system comes with (on Windows 11,
    `tar.exe`; here the same program under its own name). The archives are written by ModTrap's own .7z writer."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        os.environ["MODTRAP_7ZIP"] = str(self.dir / "no-7-zip-here.exe")

    def tearDown(self) -> None:
        os.environ.pop("MODTRAP_7ZIP", None)
        self.tmp.cleanup()

    def made(self, name: str, files: dict) -> Path:
        from modtrap import sevenz
        w = sevenz.Writer(self.dir / name)
        for n, data in files.items():
            w.add(n, 1_700_000_000, [data])
        w.close()
        return self.dir / name

    def through_tar(self, src: Path, dest: Path, said: str | None = None) -> int:
        """The system's unpacker itself, as `unpack` calls it for an archive ModTrap's own reader does not read."""
        exe, told = unpack.find_tar()
        dest.mkdir()
        return unpack._untar(exe, said or told, src, dest, "7z")

    def test_a_7z_is_unpacked_by_the_systems_own_unpacker(self) -> None:
        src = self.made("Thistle.7z", {"Wrapper/Thistle.esp": plugin.build(("Skyrim.esm",)), "Wrapper/textures/x/b c.dds": b"invented"})
        self.assertEqual(self.through_tar(src, self.dir / "out"), 2)
        self.assertEqual((self.dir / "out" / "Wrapper" / "textures" / "x" / "b c.dds").read_bytes(), b"invented")

    @unittest.skipIf(REAL_7Z is None, "the 7-Zip program is not installed here, to make the archive")
    def test_a_7z_modtraps_own_reader_does_not_read_goes_to_the_systems_unpacker(self) -> None:
        (self.dir / "src").mkdir()
        (self.dir / "src" / "a.txt").write_bytes(b"invented text " * 200)
        subprocess.run([REAL_7Z, "a", "-bd", "-m0=PPMd", str(self.dir / "ppmd.7z"), "a.txt"], cwd=self.dir / "src", check=True, stdout=subprocess.DEVNULL)
        got = unpack.unpack(self.dir / "ppmd.7z", self.dir / "out")
        self.assertEqual((got["files"], "unpacker" in got["by"]), (1, True))
        self.assertEqual((self.dir / "out" / "a.txt").read_bytes(), b"invented text " * 200)

    def test_a_name_that_leaves_the_folder_is_refused_before_anything_is_written(self) -> None:
        src = self.made("Sly.7z", {"../outside.txt": b"x", "inside.txt": b"y"})
        with self.assertRaises(unpack.Refused) as c:
            self.through_tar(src, self.dir / "out")
        self.assertIn("outside its own folder", str(c.exception))
        self.assertEqual(list((self.dir / "out").iterdir()), [])
        self.assertFalse((self.dir / "outside.txt").exists())

    def test_an_older_unpacker_that_cannot_read_7z_is_named_as_such(self) -> None:
        src = self.made("Thistle.7z", {"a.txt": b"x"})
        with self.assertRaises(unpack.Refused) as c:
            self.through_tar(src, self.dir / "out", "bsdtar 3.5.2 - libarchive 3.5.2 zlib/1.2.5.f-ipp")
        self.assertIn("older one that cannot read .7z", str(c.exception))

    def test_what_is_no_archive_inside_is_refused_in_words(self) -> None:
        src = self.dir / "Broken.7z"
        src.write_bytes(b"7z\xbc\xaf\x27\x1c" + b"not an archive at all" * 20)
        with self.assertRaises(unpack.Refused) as c:
            unpack.unpack(src, self.dir / "out")                # ModTrap's own reader first, then the system's
        self.assertIn("could not read the archive", str(c.exception))
        self.assertFalse((self.dir / "out").exists())


class TheUnpackersListing(unittest.TestCase):
    def test_a_listing_gives_each_entrys_kind_and_size(self) -> None:
        text = ("drwxr-xr-x  0 0      0           0 Nov 23 13:05 sub/\n-rw-r--r--  0 0      0           5 Nov 23 13:05 a file.txt\n"
                "lrwxrwxrwx  0 0      0           0 Nov 23 13:05 link -> /somewhere\nhrw-r--r--  0 0      0           0 Nov 23 13:05 b link to a\n"
                "something this reader does not know\n")
        self.assertEqual(unpack.parse_tar_listing(text), [("d", 0), ("-", 5), ("l", 0), ("h", 0), ("-", 0)])


if __name__ == "__main__":
    unittest.main()
