"""ModTrap's .7z writer (WHY§48), read back two ways: by a small reader written here from the same description of
the format, and, where it is installed, by an independent library."""

from __future__ import annotations

import lzma
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

from modtrap import sevenz

try:
    import py7zr
except ImportError:                      # not a dependency of ModTrap: only an independent check where available
    py7zr = None


REAL_7Z = shutil.which("7z") or shutil.which("7zz")


def read_number(data: bytes, at: int) -> tuple[int, int]:
    first = data[at]
    extra = 0
    while extra < 8 and first & (0x80 >> extra):
        extra += 1
    low = int.from_bytes(data[at + 1:at + 1 + extra], "little")
    high = (first & ((1 << (8 - extra)) - 1 if extra < 8 else 0)) if extra < 8 else 0
    return low | (high << (8 * extra)), at + 1 + extra


def read_back(path: Path) -> dict[str, bytes]:
    """A reader for exactly what the writer writes, checking every size and checksum on the way."""
    data = path.read_bytes()
    assert data[:6] == sevenz.SIGNATURE and data[6:8] == b"\x00\x04"
    start_crc, = struct.unpack_from("<I", data, 8)
    assert zlib.crc32(data[12:32]) & 0xFFFFFFFF == start_crc
    offset, hsize, hcrc = struct.unpack_from("<QQI", data, 12)
    h = data[32 + offset:32 + offset + hsize]
    assert len(h) == hsize and zlib.crc32(h) & 0xFFFFFFFF == hcrc and 32 + offset + hsize == len(data)
    at = 0
    assert h[at] == 0x01
    at += 1
    sizes, crcs, unpacked = [], [], 0
    if h[at] == 0x04:
        at += 1
        assert h[at] == 0x06
        _pos, at = read_number(h, at + 1)
        streams, at = read_number(h, at)
        assert (streams, h[at]) == (1, 0x09)
        packed, at = read_number(h, at + 1)
        assert packed == offset and h[at] == 0x00
        at += 1
        assert h[at:at + 2] == b"\x07\x0b"
        folders, at = read_number(h, at + 2)
        assert folders == 1 and h[at] == 0x00
        coders, at = read_number(h, at + 1)
        assert coders == 1 and h[at:at + 2] == b"\x21\x21"
        plen, at = read_number(h, at + 2)
        prop = h[at]
        at += plen
        assert h[at] == 0x0C
        unpacked, at = read_number(h, at + 1)
        assert h[at] == 0x00
        at += 1
        assert h[at:at + 2] == b"\x08\x0d"
        count, at = read_number(h, at + 2)
        if count > 1:
            assert h[at] == 0x09
            at += 1
            for _ in range(count - 1):
                n, at = read_number(h, at)
                sizes.append(n)
        sizes.append(unpacked - sum(sizes))
        assert h[at:at + 2] == b"\x0a\x01"
        at += 2
        for _ in range(count):
            crcs.append(struct.unpack_from("<I", h, at)[0])
            at += 4
        assert h[at:at + 2] == b"\x00\x00"
        at += 2
        raw = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[
            {"id": lzma.FILTER_LZMA2, "dict_size": (2 | (prop & 1)) << (prop // 2 + 11)}]).decompress(data[32:32 + packed])
        assert len(raw) == unpacked
    else:
        raw = b""
    assert h[at] == 0x05
    nfiles, at = read_number(h, at + 1)
    empty = [False] * nfiles
    names: list[str] = []
    while h[at] != 0x00:
        kind = h[at]
        size, at = read_number(h, at + 1)
        body = h[at:at + size]
        at += size
        if kind == 0x0E:
            empty = [bool(body[i // 8] & (0x80 >> (i % 8))) for i in range(nfiles)]
        elif kind == 0x11:
            assert body[0] == 0
            names = body[1:].decode("utf-16-le").split("\x00")[:-1]
        elif kind == 0x14:
            assert body[:2] == b"\x01\x00" and len(body) == 2 + 8 * nfiles
    assert h[at:at + 2] == b"\x00\x00" and at + 2 == len(h) and len(names) == nfiles
    out, pos, k = {}, 0, 0
    for name, is_empty in zip(names, empty):
        if is_empty:
            out[name] = b""
            continue
        chunk = raw[pos:pos + sizes[k]]
        assert zlib.crc32(chunk) & 0xFFFFFFFF == crcs[k], name
        out[name] = chunk
        pos += sizes[k]
        k += 1
    assert pos == len(raw)
    return out


FILES = {"log.txt": b"line one\r\nline two\r\n" * 4000, "jobs/dryrun-1/report.tsv": b"H\tmodtrap-report/2\r\n",
         "empty.txt": b"", "about.json": b'{"name": "ModTrap"}', "names/été ☃.txt": "snow ☃".encode("utf-8"),
         "also-empty.json": b""}


class SevenZ(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "out.7z"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, files: dict[str, bytes]) -> int:
        w = sevenz.Writer(self.path)
        for name, data in files.items():
            w.add(name, 1_700_000_000, [data[i:i + 5000] for i in range(0, len(data), 5000)])
        return w.close()

    def test_numbers_are_written_the_formats_way(self) -> None:
        for v, want in ((0, "00"), (127, "7f"), (128, "8080"), (0x3FFF, "bfff"), (0x4000, "c00040"),
                        (0x12345678, "f078563412"), (2 ** 56 - 1, "feffffffffffffff"), (2 ** 64 - 1, "ff" + "ff" * 8)):
            self.assertEqual(sevenz.number(v).hex(), want, v)
            self.assertEqual(read_number(sevenz.number(v), 0)[0], v)
        self.assertEqual(sevenz.dict_property(8 * 1024 * 1024), 22)
        self.assertEqual(sevenz.bits([True, False, False, False, False, False, False, False, True]).hex(), "8080")
        self.assertEqual(sevenz.filetime(0), 116444736000000000)

    def test_what_goes_in_comes_out(self) -> None:
        self.assertEqual(self.write(FILES), 4)
        self.assertEqual(read_back(self.path), FILES)

    def test_one_file_and_only_empty_files(self) -> None:
        self.write({"only.txt": b"x"})
        self.assertEqual(read_back(self.path), {"only.txt": b"x"})
        self.assertEqual(self.write({"a.txt": b"", "b.txt": b""}), 0)
        self.assertEqual(read_back(self.path), {"a.txt": b"", "b.txt": b""})

    @unittest.skipIf(py7zr is None, "py7zr is not installed here")
    def test_an_independent_reader_agrees(self) -> None:
        self.write(FILES)
        with py7zr.SevenZipFile(self.path) as z:
            self.assertTrue(z.testzip() is None)                # every file's checksum, by the library's own count
            self.assertEqual(sorted(z.getnames()), sorted(FILES))
        with py7zr.SevenZipFile(self.path) as z:                # the library reads an archive once for each opening
            z.extractall(Path(self.tmp.name) / "x")
        for name, data in FILES.items():
            self.assertEqual((Path(self.tmp.name) / "x" / name).read_bytes(), data, name)
        self.write({"only.txt": b"alone"})
        with py7zr.SevenZipFile(self.path) as z:
            self.assertEqual(z.getnames(), ["only.txt"])
            self.assertTrue(z.testzip() is None)


    @unittest.skipIf(REAL_7Z is None, "the 7-Zip program is not installed here")
    def test_7zip_itself_agrees(self) -> None:
        self.write(FILES)
        got = subprocess.run([REAL_7Z, "t", str(self.path)], capture_output=True, text=True)
        self.assertEqual(got.returncode, 0, got.stdout + got.stderr)
        self.assertIn("Everything is Ok", got.stdout)
        subprocess.run([REAL_7Z, "x", "-y", "-o" + str(Path(self.tmp.name) / "x7"), str(self.path)], check=True,
                       stdout=subprocess.DEVNULL)
        for name, data in FILES.items():
            self.assertEqual((Path(self.tmp.name) / "x7" / name).read_bytes(), data, name)
        self.write({"a.txt": b"", "b.txt": b""})                    # only empty files: no streams at all
        self.assertEqual(subprocess.run([REAL_7Z, "t", str(self.path)], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
