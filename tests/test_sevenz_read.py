"""ModTrap's own .7z reader (WHY§123): archives written by ModTrap's own writer, and, where 7-Zip is installed,
archives 7-Zip made of invented files in each way of packing the reader reads. No real mod's file is used."""

import os
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from modtrap import sevenz, sevenz_read, unpack

REAL_7Z = shutil.which("7z") or shutil.which("7zz")


def invented_tree(root: Path) -> dict:
    """A small mod-like tree: text that packs well, noise that does not, an empty file, an empty folder, a name with
    letters outside ASCII, and two files with the endings 7-Zip puts its program filter on, holding x86-like bytes."""
    rnd = random.Random(7)
    files = {
        "Wrapper/Thistle.esp": b"TES4" + bytes(rnd.getrandbits(8) for _ in range(4000)),
        "Wrapper/textures/x/b c.dds": bytes(rnd.getrandbits(8) for _ in range(60000)) + b"A" * 90000,
        "Wrapper/docs/Invénted ünï.txt": ("text " * 9000).encode(),
        "Wrapper/empty.txt": b"",
    }
    code = bytearray()
    for i in range(60000):                                    # calls and jumps with addresses, as a program has them
        code += rnd.choice((b"\xe8", b"\xe9", b"\x0f\x84", b"\x90\x8b\xc3")) + (i * 37 % 5000).to_bytes(4, "little")
    files["Wrapper/SKSE/Plugins/Invented.dll"] = bytes(code)
    files["Wrapper/SKSE/Plugins/Second.exe"] = bytes(code[::-1])
    wave, v = bytearray(), 0
    for _ in range(50000):
        v = (v + rnd.randint(-3, 3)) % 256
        wave.append(v)
    files["Wrapper/sound.wav"] = bytes(wave)
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (root / "Wrapper" / "empty-folder").mkdir()
    return files


def read_all(path: Path) -> dict:
    out = {}
    with sevenz_read.Archive(path) as a:
        a.check()
        for x, blocks in a.extract():
            out[x.name] = b"".join(blocks)
    return out


class ModTrapsOwnArchives(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_what_the_writer_wrote_the_reader_reads(self):
        files = {"a/first.txt": b"one " * 5000, "a/b/second.bin": bytes(range(256)) * 300, "empty.txt": b"", "third": b"x"}
        w = sevenz.Writer(self.dir / "own.7z")
        for name, data in files.items():
            w.add(name, 1_700_000_000, [data])
        w.close()
        self.assertEqual(read_all(self.dir / "own.7z"), files)
        with sevenz_read.Archive(self.dir / "own.7z") as a:
            self.assertEqual([(x.name, x.size, x.is_dir, x.link) for x in a.entries], [(n, len(d), False, False) for n, d in files.items()])

    def test_what_is_no_archive_or_is_cut_short_is_said_to_be_damaged(self):
        w = sevenz.Writer(self.dir / "own.7z")
        w.add("a.txt", 0, [b"some text " * 3000])
        w.close()
        whole = (self.dir / "own.7z").read_bytes()
        for name, data in (("short.7z", whole[:len(whole) // 2]), ("noise.7z", whole[:6] + b"\x00" * 200), ("flipped.7z", whole[:40] + bytes([whole[40] ^ 0xFF]) + whole[41:])):
            (self.dir / name).write_bytes(data)
            with self.assertRaises(sevenz_read.Bad, msg=name):
                read_all(self.dir / name)


@unittest.skipIf(REAL_7Z is None, "the 7-Zip program is not installed here")
class ArchivesMadeBy7Zip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.files = invented_tree(cls.dir / "src")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def made(self, name: str, *switches: str) -> Path:
        out = self.dir / name
        subprocess.run([REAL_7Z, "a", "-bd", *switches, str(out), "Wrapper"], cwd=self.dir / "src", check=True, stdout=subprocess.DEVNULL)
        return out

    def test_every_way_of_packing_the_reader_reads_gives_the_files_back(self):
        ways = {"default": (), "ultra": ("-mx=9",), "not solid": ("-ms=off",), "header not packed": ("-mhc=off",), "LZMA": ("-m0=LZMA",),
                "BCJ": ("-m0=BCJ", "-m1=LZMA2"), "BCJ2": ("-m0=BCJ2", "-m1=LZMA", "-m2=LZMA", "-m3=LZMA", "-mb0:1", "-mb0s1:2", "-mb0s2:3"),
                "Delta": ("-m0=Delta:2", "-m1=LZMA2"), "ARM": ("-m0=ARM", "-m1=LZMA2"), "Deflate": ("-m0=Deflate",), "BZip2": ("-m0=BZip2",), "stored": ("-m0=Copy",)}
        for i, (way, switches) in enumerate(ways.items()):
            got = read_all(self.made("way%d.7z" % i, *switches))
            self.assertEqual(got.keys(), self.files.keys(), way)
            for name in self.files:
                self.assertEqual(got[name], self.files[name], "%s: %s" % (way, name))

    def test_folders_links_and_sizes_are_told_before_anything_is_unpacked(self):
        with sevenz_read.Archive(self.made("listing.7z")) as a:
            dirs = sorted(x.name for x in a.entries if x.is_dir)
            self.assertIn("Wrapper/empty-folder", dirs)
            self.assertEqual({x.name: x.size for x in a.entries if not x.is_dir}, {n: len(d) for n, d in self.files.items()})
            self.assertFalse(any(x.link for x in a.entries))

    @unittest.skipIf(os.name == "nt", "making a link needs rights Windows does not give by default")
    def test_a_link_is_told_as_one(self):
        os.makedirs(self.dir / "ln" / "Wrapper")
        (self.dir / "ln" / "Wrapper" / "a.txt").write_bytes(b"x")
        os.symlink("/etc/hostname", self.dir / "ln" / "Wrapper" / "link.txt")
        subprocess.run([REAL_7Z, "a", "-bd", "-snl", str(self.dir / "link.7z"), "Wrapper"], cwd=self.dir / "ln", check=True, stdout=subprocess.DEVNULL)
        with sevenz_read.Archive(self.dir / "link.7z") as a:
            self.assertEqual([x.name for x in a.entries if x.link], ["Wrapper/link.txt"])
        with self.assertRaises(unpack.Refused) as c:
            unpack.unpack(self.dir / "link.7z", self.dir / "link-out")
        self.assertIn("link", str(c.exception))

    def test_a_password_and_a_method_not_read_are_told_apart(self):
        for name, switches in (("locked.7z", ("-pSecret",)), ("hidden.7z", ("-pSecret", "-mhe=on"))):
            with self.assertRaises(sevenz_read.Locked, msg=name):
                read_all(self.made(name, *switches))
        with self.assertRaises(sevenz_read.Unsupported) as c:
            read_all(self.made("ppmd.7z", "-m0=PPMd"))
        self.assertIn("does not know", str(c.exception))

    def test_unpack_uses_modtraps_own_reader_and_needs_no_other_program(self):
        os.environ["MODTRAP_7ZIP"] = str(self.dir / "no-7-zip.exe")
        os.environ["MODTRAP_TAR"] = str(self.dir / "no-tar.exe")
        try:
            got = unpack.unpack(self.made("mod.7z"), self.dir / "mod-out")
            self.assertEqual((got["kind"], got["files"], got["by"]), ("7z", len(self.files), "ModTrap itself"))
            self.assertEqual((self.dir / "mod-out" / "Wrapper" / "SKSE" / "Plugins" / "Invented.dll").read_bytes(), self.files["Wrapper/SKSE/Plugins/Invented.dll"])
            with self.assertRaises(unpack.Refused) as c:
                unpack.unpack(self.made("ppmd2.7z", "-m0=PPMd"), self.dir / "ppmd-out")
            self.assertIn("ModTrap's own reader does not unpack this .7z", str(c.exception))
            self.assertFalse((self.dir / "ppmd-out").exists())
        finally:
            os.environ.pop("MODTRAP_7ZIP", None)
            os.environ.pop("MODTRAP_TAR", None)


if __name__ == "__main__":
    unittest.main()
