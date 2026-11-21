"""A minimal .7z writer (WHY§48): several files in one solid LZMA2 stream, written with Python's standard library
alone (lzma, zlib, struct). Our own code, from the published description of the format; it writes only what
ModTrap's "Save this session" needs: file names, sizes, checksums and modification times.

The file is: a 32-byte signature header, the packed stream, then the header that describes it. The signature
header is written as zeros first and filled in at the end, when the sizes and checksums are known.
"""

from __future__ import annotations

import lzma
import struct
import zlib
from pathlib import Path
from typing import Iterable

SIGNATURE = b"7z\xbc\xaf\x27\x1c"
DICT_SIZE = 8 * 1024 * 1024
# The format's ids.
END, HEADER, MAIN_STREAMS, FILES_INFO, PACK_INFO, UNPACK_INFO, SUBSTREAMS, SIZE, CRC, FOLDER = \
    0x00, 0x01, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B
CODERS_UNPACK_SIZE, NUM_UNPACK_STREAM, EMPTY_STREAM, EMPTY_FILE, NAMES, MTIME = 0x0C, 0x0D, 0x0E, 0x0F, 0x11, 0x14
LZMA2_ID = 0x21
FILETIME_EPOCH = 116444736000000000        # 1601-01-01 to 1970-01-01, in 100-nanosecond steps


def number(v: int) -> bytes:
    """7z's variable-length number: the leading 1-bits of the first byte say how many more bytes follow, least
    significant first; what is left of the first byte holds the highest bits."""
    for extra in range(8):
        if v < (1 << (7 * (extra + 1))):
            first = ((0xFF << (8 - extra)) & 0xFF) | (v >> (8 * extra))
            return bytes([first]) + (v & ((1 << (8 * extra)) - 1)).to_bytes(extra, "little")
    return b"\xff" + v.to_bytes(8, "little")


def dict_property(size: int) -> int:
    """LZMA2's one property byte: the smallest p whose dictionary size is at least `size`."""
    for p in range(41):
        if (2 | (p & 1)) << (p // 2 + 11) >= size:
            return p
    return 40


def bits(flags: list[bool]) -> bytes:
    """A bit field: the first item is the high bit of the first byte."""
    out = bytearray((len(flags) + 7) // 8)
    for i, on in enumerate(flags):
        if on:
            out[i // 8] |= 0x80 >> (i % 8)
    return bytes(out)


def filetime(seconds: float) -> int:
    return max(0, int(seconds * 10_000_000) + FILETIME_EPOCH)


class Writer:
    """Writes one archive. `add` takes a file's name, its time, and its bytes as blocks; `close` finishes the
    archive and returns how many files have data. Nothing is held in memory but the current block."""

    def __init__(self, path: Path):
        self.path = path
        self._f = open(path, "wb")
        self._f.write(b"\x00" * 32)
        self._lz = lzma.LZMACompressor(format=lzma.FORMAT_RAW,
                                       filters=[{"id": lzma.FILTER_LZMA2, "dict_size": DICT_SIZE}])
        self._files: list[tuple[str, float, int, int]] = []      # name, time, size, crc32
        self.packed = 0
        self.unpacked = 0
        self._closed = False

    def add(self, name: str, mtime: float, blocks: Iterable[bytes]) -> int:
        size, crc = 0, 0
        for block in blocks:
            if not block:
                continue
            crc = zlib.crc32(block, crc)
            size += len(block)
            out = self._lz.compress(block)
            if out:
                self._f.write(out)
                self.packed += len(out)
        self._files.append((name.replace("\\", "/"), mtime, size, crc & 0xFFFFFFFF))
        self.unpacked += size
        return size

    def abort(self) -> None:
        if not self._closed:
            self._closed = True
            self._f.close()

    def close(self) -> int:
        out = self._lz.flush()
        self._f.write(out)
        self.packed += len(out)
        with_data = [f for f in self._files if f[2]]
        h = bytearray([HEADER])
        if with_data:                                            # no streams block at all when nothing has data
            h += bytes([MAIN_STREAMS])
            h += bytes([PACK_INFO]) + number(0) + number(1) + bytes([SIZE]) + number(self.packed) + bytes([END])
            h += bytes([UNPACK_INFO, FOLDER]) + number(1) + b"\x00" + number(1)
            h += bytes([0x21, LZMA2_ID]) + number(1) + bytes([dict_property(DICT_SIZE)])     # one coder, with a property
            h += bytes([CODERS_UNPACK_SIZE]) + number(self.unpacked) + bytes([END])
            h += bytes([SUBSTREAMS, NUM_UNPACK_STREAM]) + number(len(with_data))
            if len(with_data) > 1:
                h += bytes([SIZE]) + b"".join(number(f[2]) for f in with_data[:-1])
            h += bytes([CRC, 0x01]) + b"".join(struct.pack("<I", f[3]) for f in with_data) + bytes([END])
            h += bytes([END])
        h += bytes([FILES_INFO]) + number(len(self._files))
        empty = [f[2] == 0 for f in self._files]
        if any(empty):
            field = bits(empty)
            h += bytes([EMPTY_STREAM]) + number(len(field)) + field
            field = bits([True] * sum(empty))                    # each is an empty file, not a folder
            h += bytes([EMPTY_FILE]) + number(len(field)) + field
        names = b"".join(f[0].encode("utf-16-le") + b"\x00\x00" for f in self._files)
        h += bytes([NAMES]) + number(len(names) + 1) + b"\x00" + names
        times = b"".join(struct.pack("<Q", filetime(f[1])) for f in self._files)
        h += bytes([MTIME]) + number(len(times) + 2) + b"\x01\x00" + times
        h += bytes([END, END])
        self._f.write(h)
        start = struct.pack("<QQI", self.packed, len(h), zlib.crc32(bytes(h)) & 0xFFFFFFFF)
        self._f.seek(0)
        self._f.write(SIGNATURE + b"\x00\x04" + struct.pack("<I", zlib.crc32(start) & 0xFFFFFFFF) + start)
        self._f.close()
        self._closed = True
        return len(with_data)


__all__ = ["Writer", "number", "dict_property", "bits", "filetime"]
