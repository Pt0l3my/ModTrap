"""A .7z reader (WHY§123): ModTrap's own, written from the published description of the format, as its writer is
(`sevenz.py`). Python's standard library does the decompression (lzma, zlib, bz2); what is here reads the archive's
header, puts each folder's coders together, and hands out each file's bytes with its checksum checked.

Read: LZMA and LZMA2, alone or behind the filters 7-Zip puts before them (BCJ for programs of several processors,
BCJ2 for x86, Delta), Deflate, BZip2 and stored data; solid and non-solid archives; a compressed header. Not read,
and said so (`Unsupported`), so that the caller can hand the archive to another program: PPMd and other rare
methods, and anything protected by a password (`Locked`).
"""

from __future__ import annotations

import bz2
import lzma
import struct
import zlib
from pathlib import Path
from typing import BinaryIO, Iterator

SIGNATURE = b"7z\xbc\xaf\x27\x1c"
END, HEADER, ARCHIVE_PROPS, ADDITIONAL_STREAMS, MAIN_STREAMS, FILES_INFO, PACK_INFO, UNPACK_INFO, SUBSTREAMS, SIZE, CRC, FOLDER = range(12)
CODERS_UNPACK_SIZE, NUM_UNPACK_STREAM, EMPTY_STREAM, EMPTY_FILE, ANTI, NAMES, CTIME, ATIME, MTIME, ATTRIBUTES = 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15
ENCODED_HEADER = 0x17
HEADER_MAX = 256 * 1024 * 1024             # a header larger than this is not read
BCJ2_MAX = 512 * 1024 * 1024               # a BCJ2 folder is decoded in memory: up to this size
CHUNK = 1024 * 1024

COPY, LZMA, LZMA2_ID, DEFLATE, BZIP2, BCJ2, DELTA, AES = b"\x00", b"\x03\x01\x01", b"\x21", b"\x04\x01\x08", b"\x04\x02\x02", b"\x03\x03\x01\x1b", b"\x03", b"\x06\xf1\x07\x01"
BCJ = {b"\x03\x03\x01\x03": lzma.FILTER_X86, b"\x04": lzma.FILTER_X86, b"\x03\x03\x02\x05": lzma.FILTER_POWERPC, b"\x05": lzma.FILTER_POWERPC,
       b"\x03\x03\x04\x01": lzma.FILTER_IA64, b"\x06": lzma.FILTER_IA64, b"\x03\x03\x05\x01": lzma.FILTER_ARM, b"\x07": lzma.FILTER_ARM,
       b"\x03\x03\x07\x01": lzma.FILTER_ARMTHUMB, b"\x08": lzma.FILTER_ARMTHUMB, b"\x03\x03\x08\x05": lzma.FILTER_SPARC, b"\x09": lzma.FILTER_SPARC}


class Bad(Exception):
    """The file is not a .7z archive this reader can make sense of: damaged, or cut short."""


class Unsupported(Exception):
    """A sound archive, packed in a way this reader does not read; the text names it."""


class Locked(Exception):
    """The archive is protected by a password."""


class _In:
    """Bytes of a header, read forwards."""

    def __init__(self, data: bytes):
        self.d, self.i = data, 0

    def byte(self) -> int:
        if self.i >= len(self.d):
            raise Bad("the header ends too soon")
        self.i += 1
        return self.d[self.i - 1]

    def take(self, n: int) -> bytes:
        if n < 0 or self.i + n > len(self.d):
            raise Bad("the header ends too soon")
        self.i += n
        return self.d[self.i - n:self.i]

    def number(self) -> int:
        """7z's number: the leading 1-bits of the first byte say how many bytes follow, least significant first."""
        first = self.byte()
        mask, value = 0x80, 0
        for k in range(8):
            if not first & mask:
                return value | ((first & (mask - 1)) << (8 * k))
            value |= self.byte() << (8 * k)
            mask >>= 1
        return value

    def bits(self, n: int) -> list[bool]:
        raw = self.take((n + 7) // 8)
        return [bool(raw[k // 8] & (0x80 >> (k % 8))) for k in range(n)]

    def defined(self, n: int) -> list[bool]:
        return [True] * n if self.byte() else self.bits(n)

    def digests(self, n: int) -> list[int | None]:
        on = self.defined(n)
        return [struct.unpack("<I", self.take(4))[0] if x else None for x in on]


class _Coder:
    def __init__(self, cid: bytes, n_in: int, n_out: int, props: bytes):
        self.id, self.n_in, self.n_out, self.props = cid, n_in, n_out, props


class _Folder:
    def __init__(self) -> None:
        self.coders: list[_Coder] = []
        self.binds: list[tuple[int, int]] = []          # (in stream, out stream that feeds it)
        self.packed: list[int] = []                     # in streams fed by the archive's packed streams, in their order
        self.out_sizes: list[int] = []
        self.crc: int | None = None
        self.first_pack = 0                             # index of its first packed stream
        self.sub_sizes: list[int] = []
        self.sub_crcs: list[int | None] = []

    def main_out(self) -> int:
        fed = {o for _i, o in self.binds}
        outs = sum(c.n_out for c in self.coders)
        free = [o for o in range(outs) if o not in fed]
        if len(free) != 1:
            raise Bad("a folder of the archive has no single output")
        return free[0]

    def size(self) -> int:
        return self.out_sizes[self.main_out()]


def _streams(r: _In) -> tuple[int, list[int], list[_Folder]]:
    """A StreamsInfo block: where the packed streams begin, their sizes, and the folders."""
    pack_pos, pack_sizes, folders = 0, [], []
    counts: list[int] | None = None
    while True:
        t = r.byte()
        if t == END:
            break
        if t == PACK_INFO:
            pack_pos, n = r.number(), r.number()
            while True:
                t2 = r.byte()
                if t2 == END:
                    break
                if t2 == SIZE:
                    pack_sizes = [r.number() for _ in range(n)]
                elif t2 == CRC:
                    r.digests(n)
                else:
                    raise Bad("the header holds something this reader does not know")
        elif t == UNPACK_INFO:
            if r.byte() != FOLDER:
                raise Bad("the header's folders are not where they should be")
            n = r.number()
            if r.byte():
                raise Unsupported("its folders are described outside the header")
            pack_index = 0
            for _ in range(n):
                f = _Folder()
                for _c in range(r.number()):
                    flag = r.byte()
                    cid = r.take(flag & 0x0F)
                    n_in, n_out = (r.number(), r.number()) if flag & 0x10 else (1, 1)
                    props = r.take(r.number()) if flag & 0x20 else b""
                    if flag & 0x80:
                        raise Unsupported("a coder with alternative methods")
                    f.coders.append(_Coder(cid, n_in, n_out, props))
                ins, outs = sum(c.n_in for c in f.coders), sum(c.n_out for c in f.coders)
                f.binds = [(r.number(), r.number()) for _b in range(outs - 1)]
                n_packed = ins - len(f.binds)
                if n_packed == 1:
                    bound = {i for i, _o in f.binds}
                    f.packed = [i for i in range(ins) if i not in bound]
                else:
                    f.packed = [r.number() for _p in range(n_packed)]
                if len(f.packed) != n_packed or n_packed < 1:
                    raise Bad("a folder's streams do not add up")
                f.first_pack = pack_index
                pack_index += n_packed
                folders.append(f)
            while True:
                t2 = r.byte()
                if t2 == END:
                    break
                if t2 == CODERS_UNPACK_SIZE:
                    for f in folders:
                        f.out_sizes = [r.number() for _o in range(sum(c.n_out for c in f.coders))]
                elif t2 == CRC:
                    for f, c in zip(folders, r.digests(len(folders))):
                        f.crc = c
                else:
                    raise Bad("the header holds something this reader does not know")
        elif t == SUBSTREAMS:
            counts = [1] * len(folders)
            sized = False
            while True:
                t2 = r.byte()
                if t2 == END:
                    break
                if t2 == NUM_UNPACK_STREAM:
                    counts = [r.number() for _ in folders]
                elif t2 == SIZE:
                    sized = True
                    for f, n in zip(folders, counts):
                        sizes = [r.number() for _ in range(max(0, n - 1))]
                        f.sub_sizes = sizes + [f.size() - sum(sizes)] if n else []
                elif t2 == CRC:
                    need = [f for f, n in zip(folders, counts) for _ in range(n) if not (n == 1 and f.crc is not None)]
                    got = iter(r.digests(len(need)))
                    for f, n in zip(folders, counts):
                        f.sub_crcs = [f.crc] if n == 1 and f.crc is not None else [next(got) for _ in range(n)]
                else:
                    raise Bad("the header holds something this reader does not know")
            if not sized:
                for f, n in zip(folders, counts):
                    if n > 1:
                        raise Bad("the header does not say how large the files of a folder are")
                    f.sub_sizes = [f.size()] if n else []
        else:
            raise Bad("the header holds something this reader does not know")
    for f in folders:
        if counts is None:
            f.sub_sizes = [f.size()]
        if len(f.sub_crcs) != len(f.sub_sizes):
            f.sub_crcs = [f.crc] if len(f.sub_sizes) == 1 else [None] * len(f.sub_sizes)
        if any(s < 0 for s in f.sub_sizes):
            raise Bad("a folder's files are larger than the folder")
    return pack_pos, pack_sizes, folders


# --- putting a folder's coders together ----------------------------------------------------------------------------------

def _lzma_filter(c: _Coder) -> dict | None:
    if c.id == LZMA2_ID:
        if len(c.props) != 1 or c.props[0] > 40:
            raise Bad("LZMA2's settings in the archive are not valid")
        p = c.props[0]
        return {"id": lzma.FILTER_LZMA2, "dict_size": 0xFFFFFFFF if p == 40 else (2 | (p & 1)) << (p // 2 + 11)}
    if c.id == LZMA:
        if len(c.props) != 5 or c.props[0] >= 9 * 5 * 5:
            raise Bad("LZMA's settings in the archive are not valid")
        d, rest = c.props[0], struct.unpack("<I", c.props[1:5])[0]
        return {"id": lzma.FILTER_LZMA1, "lc": d % 9, "lp": (d // 9) % 5, "pb": d // 45, "dict_size": max(rest, 4096)}
    return None


def _simple_filter(c: _Coder) -> dict | None:
    if c.id in BCJ:
        if c.props not in (b"", b"\x00\x00\x00\x00"):
            raise Unsupported("a program filter with a start offset")
        return {"id": BCJ[c.id]}
    if c.id == DELTA:
        return {"id": lzma.FILTER_DELTA, "dist": (c.props[0] if c.props else 0) + 1}
    return None


class _Pack:
    """One packed stream of the archive, as a source of bytes."""

    def __init__(self, f: BinaryIO, start: int, size: int):
        self.f, self.pos, self.left = f, start, size

    def read(self, n: int) -> bytes:
        n = min(n, self.left)
        if n <= 0:
            return b""
        self.f.seek(self.pos)
        data = self.f.read(n)
        if len(data) != n:
            raise Bad("the archive ends too soon")
        self.pos += n
        self.left -= n
        return data


class _Decoded:
    """What a decompressor makes of a source, up to the size the archive names for it."""

    def __init__(self, src, make, size: int):
        self.src, self.dec, self.left, self.done = src, make(), size, False

    def read(self, n: int) -> bytes:
        out = b""
        while not out and self.left > 0:
            want = min(n, self.left)
            try:
                if isinstance(self.dec, lzma.LZMADecompressor):
                    if self.dec.needs_input and not self.done:
                        block = self.src.read(CHUNK)
                        self.done = not block
                        out = self.dec.decompress(block, max_length=want)
                    else:
                        out = self.dec.decompress(b"", max_length=want)
                        if not out and self.done:
                            raise Bad("the packed data ends too soon")
                else:
                    held = getattr(self, "held", b"")
                    if held:
                        out, self.held = held[:want], held[want:]
                    else:
                        block = self.src.read(CHUNK)
                        if not block:
                            raise Bad("the packed data ends too soon")
                        got = self.dec.decompress(block)
                        out, self.held = got[:want], got[want:]
            except (lzma.LZMAError, zlib.error, OSError, EOFError, ValueError) as e:
                raise Bad("the packed data is damaged (%s)" % type(e).__name__) from None
        self.left -= len(out)
        return out


class _Refilter:
    """A filter of 7-Zip's (BCJ, Delta) undone over bytes that are already unpacked. Python's decoder takes such a
    filter only in a chain that ends in LZMA2, so the bytes are packed again, lightly, and unpacked through the
    chain: slower than need be, and only met where the filter stands before something other than LZMA2."""

    def __init__(self, src, filters: list[dict], size: int):
        last = {"id": lzma.FILTER_LZMA2, "preset": 0}
        try:
            self.comp = lzma.LZMACompressor(lzma.FORMAT_RAW, filters=[last])
            self.dec = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=filters + [last])
        except (lzma.LZMAError, ValueError) as e:
            raise Unsupported("a chain of filters Python's decoder does not take (%s)" % e) from None
        self.src, self.left, self.flushed, self.buf = src, size, False, b""

    def read(self, n: int) -> bytes:
        while not self.buf and self.left > 0:
            if self.flushed:
                raise Bad("the packed data ends too soon")
            block = self.src.read(CHUNK)
            if block:
                packed = self.comp.compress(block)
            else:
                packed, self.flushed = self.comp.flush(), True
            if packed:
                try:
                    self.buf = self.dec.decompress(packed)
                except (lzma.LZMAError, EOFError) as e:
                    raise Bad("the packed data is damaged (%s)" % type(e).__name__) from None
        n = min(n, self.left)
        out, self.buf = self.buf[:n], self.buf[n:]
        self.left -= len(out)
        return out


class _Bytes:
    def __init__(self, data: bytes):
        self.d, self.i = data, 0
        self.left = len(data)

    def read(self, n: int) -> bytes:
        out = self.d[self.i:self.i + n]
        self.i += len(out)
        return out


def _all(src, size: int) -> bytes:
    parts, left = [], size
    while left > 0:
        block = src.read(min(CHUNK, left))
        if not block:
            raise Bad("the packed data ends too soon")
        parts.append(block)
        left -= len(block)
    return b"".join(parts)


def bcj2(main: bytes, call: bytes, jump: bytes, rc: bytes, size: int) -> bytes:
    """Undoes 7-Zip's BCJ2 filter for x86 programs: the main stream with the targets of calls and jumps taken out
    into two streams of their own (stored as absolute addresses), and a range-coded stream of bits saying, for
    each E8, E9 or 0F 8x byte, whether a target was taken out. From the format's published description."""
    if len(rc) < 5:
        raise Bad("a program filter's data ends too soon")
    probs = [1024] * 258
    code, rng, rc_pos = int.from_bytes(rc[1:5], "big"), 0xFFFFFFFF, 5
    out = bytearray()
    pos, n, call_pos, jump_pos, prev = 0, len(main), 0, 0, 0
    while len(out) < size:
        # Plain bytes, up to the next byte that may begin a call or a jump.
        start = pos
        while pos < n:
            b = main[pos]
            if (b & 0xFE) == 0xE8 or (prev == 0x0F and (b & 0xF0) == 0x80):
                break
            prev = b
            pos += 1
        out += main[start:pos]
        if pos >= n or len(out) >= size:
            break
        b = main[pos]
        pos += 1
        out.append(b)
        if len(out) >= size:
            break
        k = prev if b == 0xE8 else 256 if b == 0xE9 else 257
        p = probs[k]
        bound = (rng >> 11) * p
        if code < bound:
            rng = bound
            probs[k] = p + ((2048 - p) >> 5)
            bit = 0
        else:
            rng -= bound
            code -= bound
            probs[k] = p - (p >> 5)
            bit = 1
        if rng < 0x1000000:
            if rc_pos >= len(rc):
                raise Bad("a program filter's data ends too soon")
            rng = (rng << 8) & 0xFFFFFFFF
            code = ((code << 8) | rc[rc_pos]) & 0xFFFFFFFF
            rc_pos += 1
        if not bit:
            prev = b
            continue
        if b == 0xE8:
            v, call_pos = call[call_pos:call_pos + 4], call_pos + 4
        else:
            v, jump_pos = jump[jump_pos:jump_pos + 4], jump_pos + 4
        if len(v) < 4:
            raise Bad("a program filter's data ends too soon")
        dest = (int.from_bytes(v, "big") - (len(out) + 4)) & 0xFFFFFFFF
        out += dest.to_bytes(4, "little")
        prev = dest >> 24
    if len(out) < size:
        raise Bad("a program filter's data ends too soon")
    return bytes(out[:size])


def _source(f: BinaryIO, folder: _Folder, out_index: int, packs: list[tuple[int, int]]):
    """A reader of one out stream of the folder: the coder that makes it, fed by what feeds that coder."""
    first_in = first_out = 0
    coder = None
    for c in folder.coders:
        if first_out <= out_index < first_out + c.n_out:
            coder = c
            break
        first_in, first_out = first_in + c.n_in, first_out + c.n_out
    if coder is None:
        raise Bad("a folder's streams do not add up")
    size = folder.out_sizes[out_index]

    def feed(in_index: int):
        for i, o in folder.binds:
            if i == in_index:
                return _source(f, folder, o, packs)
        if in_index in folder.packed:
            start, length = packs[folder.first_pack + folder.packed.index(in_index)]
            return _Pack(f, start, length)
        raise Bad("a folder's streams do not add up")

    # The filters 7-Zip puts before a packer (BCJ, Delta), from the output down to what they filter.
    simple, c, c_in, c_out = [], coder, first_in, out_index
    while True:
        flt = _simple_filter(c)
        if flt is None:
            break
        if c.n_in != 1 or c.n_out != 1:
            raise Unsupported("a filter with several streams")
        simple.append(flt)
        feeder = next((o for i, o in folder.binds if i == c_in), None)
        if feeder is None:
            return _Refilter(feed(c_in), simple, size)          # a filter over stored data
        at_in = at_out = 0
        for nxt in folder.coders:
            if at_out <= feeder < at_out + nxt.n_out:
                break
            at_in, at_out = at_in + nxt.n_in, at_out + nxt.n_out
        else:
            raise Bad("a folder's streams do not add up")
        c, c_in, c_out = nxt, at_in, feeder
    if simple:
        if c.id == LZMA2_ID and c.n_in == 1 and c.n_out == 1:
            # LZMA2 says where it ends, so Python's decoder takes the filters and the packer as one chain.
            chain = simple + [_lzma_filter(c)]
            try:
                lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=chain)
            except (lzma.LZMAError, ValueError) as e:
                raise Unsupported("a chain of filters Python's decoder does not take (%s)" % e) from None
            return _Decoded(feed(c_in), lambda: lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=chain), size)
        return _Refilter(_source(f, folder, c_out, packs), simple, size)
    if coder.id == AES:
        raise Locked("the archive is protected by a password")
    if coder.id == BCJ2:
        if coder.n_in != 4 or size > BCJ2_MAX:
            raise Unsupported("a program filter (BCJ2) over more data than this reader holds in memory")
        ins = []
        for k in range(4):
            src = feed(first_in + k)
            ins.append(_all(src, src.left))
        return _Bytes(bcj2(ins[0], ins[1], ins[2], ins[3], size))
    if coder.n_in != 1 or coder.n_out != 1:
        raise Unsupported("a coder with several streams (%s)" % coder.id.hex())
    if coder.id == COPY:
        return feed(first_in)
    if coder.id == DEFLATE:
        return _Decoded(feed(first_in), lambda: zlib.decompressobj(-15), size)
    if coder.id == BZIP2:
        return _Decoded(feed(first_in), bz2.BZ2Decompressor, size)
    flt = _lzma_filter(coder)
    if flt is None:
        raise Unsupported("a packing method this reader does not know (%s)" % coder.id.hex())
    return _Decoded(feed(first_in), lambda: lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[flt]), size)


# --- the archive -----------------------------------------------------------------------------------------------------------

class Entry:
    __slots__ = ("name", "size", "folder", "crc", "is_dir", "link", "mtime")

    def __init__(self, name: str):
        self.name, self.size, self.folder, self.crc, self.is_dir, self.link, self.mtime = name, 0, False, None, False, False, None


class Archive:
    """A .7z file opened for reading: `entries` lists what it holds; `extract` hands out the files' bytes."""

    def __init__(self, path: Path):
        self.path = path
        self._f = open(path, "rb")
        try:
            self._open()
        except (Bad, Unsupported, Locked):
            self._f.close()
            raise
        except (struct.error, IndexError, OverflowError, MemoryError, RecursionError):
            self._f.close()
            raise Bad("the archive's header is damaged") from None

    def close(self) -> None:
        self._f.close()

    def __enter__(self) -> "Archive":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _open(self) -> None:
        head = self._f.read(32)
        if len(head) < 32 or head[:6] != SIGNATURE:
            raise Bad("this is not a .7z archive")
        if zlib.crc32(head[12:32]) & 0xFFFFFFFF != struct.unpack("<I", head[8:12])[0]:
            raise Bad("the archive's first bytes are damaged")
        offset, size, crc = struct.unpack("<QQI", head[12:32])
        if size == 0:
            self.entries: list[Entry] = []
            self._folders, self._packs = [], []
            return
        if size > HEADER_MAX:
            raise Unsupported("a header larger than this reader takes")
        self._f.seek(32 + offset)
        raw = self._f.read(size)
        if len(raw) != size or zlib.crc32(raw) & 0xFFFFFFFF != crc:
            raise Bad("the archive is cut short or damaged")
        r = _In(raw)
        t = r.byte()
        for _ in range(4):                                  # a compressed header: unpacked, then read as a header
            if t != ENCODED_HEADER:
                break
            pos, sizes, folders = _streams(r)
            if len(folders) != 1 or folders[0].size() > HEADER_MAX:
                raise Bad("the archive's compressed header is not valid")
            packs = self._pack_places(pos, sizes)
            raw = _all(_source(self._f, folders[0], folders[0].main_out(), packs), folders[0].size())
            if folders[0].crc is not None and zlib.crc32(raw) & 0xFFFFFFFF != folders[0].crc:
                raise Bad("the archive's header is damaged")
            r = _In(raw)
            t = r.byte()
        if t != HEADER:
            raise Bad("the archive's header is not where it should be")
        self._folders, self._packs = [], []
        names: list[str] = []
        empty_stream: list[bool] = []
        empty_file: list[bool] = []
        attrs: list[int | None] = []
        mtimes: list[int | None] = []
        n_files = 0
        while True:
            t = r.byte()
            if t == END:
                break
            if t == ARCHIVE_PROPS:
                while r.byte() != END:
                    r.take(r.number())
            elif t == ADDITIONAL_STREAMS:
                raise Unsupported("its header's data lies outside the header")
            elif t == MAIN_STREAMS:
                pos, sizes, self._folders = _streams(r)
                self._packs = self._pack_places(pos, sizes)
            elif t == FILES_INFO:
                n_files = r.number()
                if n_files > 5_000_000:
                    raise Unsupported("more files than this reader takes")
                while True:
                    kind = r.byte()
                    if kind == END:
                        break
                    body = _In(r.take(r.number()))
                    if kind == EMPTY_STREAM:
                        empty_stream = body.bits(n_files)
                    elif kind == EMPTY_FILE:
                        empty_file = body.bits(sum(empty_stream))
                    elif kind == NAMES:
                        if body.byte():
                            raise Unsupported("its names are kept outside the header")
                        text = body.d[body.i:].decode("utf-16-le", "replace")
                        names = text.split("\x00")[:n_files]
                    elif kind == ATTRIBUTES:
                        on = body.defined(n_files)
                        if body.byte():
                            raise Unsupported("its attributes are kept outside the header")
                        attrs = [struct.unpack("<I", body.take(4))[0] if x else None for x in on]
                    elif kind == MTIME:
                        on = body.defined(n_files)
                        if body.byte():
                            raise Unsupported("its times are kept outside the header")
                        mtimes = [struct.unpack("<Q", body.take(8))[0] if x else None for x in on]
            else:
                raise Bad("the header holds something this reader does not know")
        if len(names) != n_files:
            raise Bad("the archive does not name all its files")
        empty_stream = empty_stream or [False] * n_files
        streams = [(fi, k) for fi, f in enumerate(self._folders) for k in range(len(f.sub_sizes))]
        self.entries = []
        s = e = 0
        for i, name in enumerate(names):
            x = Entry(name)
            a = attrs[i] if i < len(attrs) else None
            x.mtime = mtimes[i] if i < len(mtimes) else None
            if a is not None:
                x.link = bool(a & 0x400) or (bool(a & 0x8000) and ((a >> 16) & 0o170000) == 0o120000)
            if empty_stream[i]:
                x.is_dir = not (empty_file[e] if e < len(empty_file) else False)
                e += 1
            else:
                if s >= len(streams):
                    raise Bad("the archive names more files than it holds")
                fi, k = streams[s]
                s += 1
                x.folder = (fi, k)
                x.size, x.crc = self._folders[fi].sub_sizes[k], self._folders[fi].sub_crcs[k]
            if a is not None and a & 0x10:
                x.is_dir = True
            self.entries.append(x)

    def _pack_places(self, pos: int, sizes: list[int]) -> list[tuple[int, int]]:
        out, at = [], 32 + pos
        for n in sizes:
            out.append((at, n))
            at += n
        return out

    def check(self) -> None:
        """Can everything in it be unpacked by this reader? Raises `Unsupported` or `Locked` if not, before any
        file is written."""
        for f in self._folders:
            if f.first_pack + len(f.packed) > len(self._packs):
                raise Bad("the archive does not hold all its packed data")
            for c in f.coders:
                if c.id == AES:
                    raise Locked("the archive is protected by a password")
                if c.id not in (COPY, LZMA, LZMA2_ID, DEFLATE, BZIP2, BCJ2, DELTA) and c.id not in BCJ:
                    raise Unsupported("a packing method this reader does not know (%s)" % c.id.hex())
                if c.id == BCJ2 and f.size() > BCJ2_MAX:
                    raise Unsupported("a program filter (BCJ2) over more data than this reader holds in memory")
                if c.id not in (BCJ2,) and (c.n_in != 1 or c.n_out != 1):
                    raise Unsupported("a coder with several streams (%s)" % c.id.hex())

    def extract(self) -> Iterator[tuple[Entry, Iterator[bytes]]]:
        """Each file with its bytes as blocks, in the archive's order. The blocks of one file must be read through
        before the next file is asked for. A file whose checksum is not the one the archive names raises `Bad` at
        its last block."""
        by_folder: dict[int, list[Entry]] = {}
        for x in self.entries:
            if x.folder is not False:
                by_folder.setdefault(x.folder[0], []).append(x)
        for x in self.entries:
            if x.folder is False and not x.is_dir:
                yield x, iter(())                             # an empty file
        for fi in sorted(by_folder):
            folder = self._folders[fi]
            src = _source(self._f, folder, folder.main_out(), self._packs)
            for x in sorted(by_folder[fi], key=lambda y: y.folder[1]):
                yield x, self._blocks(src, x)

    @staticmethod
    def _blocks(src, x: Entry) -> Iterator[bytes]:
        left, crc = x.size, 0
        while left > 0:
            block = src.read(min(CHUNK, left))
            if not block:
                raise Bad("the packed data ends too soon")
            crc = zlib.crc32(block, crc)
            left -= len(block)
            yield block
        if x.crc is not None and crc & 0xFFFFFFFF != x.crc:
            raise Bad("a file of the archive does not unpack to what the archive says it is: %s" % x.name)


__all__ = ["Archive", "Bad", "Entry", "Locked", "Unsupported", "bcj2"]
