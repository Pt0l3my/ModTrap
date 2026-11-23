"""A plugin's header: its flags, author, description and masters (XE02). Nothing else of a plugin is ever read
(WHY§10): the reader stops at the end of the header record.

The layout is taken from the description in XE02, not from any other program's code. A file that does not fit it is
reported as unreadable, never guessed at.
"""

from __future__ import annotations

import mmap
import struct
import time
import zlib
from dataclasses import dataclass, field
from pathlib import Path

RECORD_HEADER = 24                # XE02§2: type, data size, flags, form id, version control, form version, 2 more
HEADER_CAP = 64 * 1024 * 1024     # XE02§5: a header larger than this is refused
FLAG_ESM = 0x00000001             # XE02§3
FLAG_LOCALIZED = 0x00000080
FLAG_ESL = 0x00000200
EXTENSIONS = (".esp", ".esm", ".esl")


class Unreadable(Exception):
    """This file is not a plugin ModTrap can read; the text says why, in words for the page."""


@dataclass(frozen=True)
class Header:
    flags: int
    author: str
    description: str
    masters: tuple[str, ...]
    fields: tuple[str, ...] = field(default=(), compare=False)   # the header's field types, in order
    version: float | None = field(default=None, compare=False)   # the HEDR field's version number (XE02§4)

    @property
    def esm_flag(self) -> bool:
        return bool(self.flags & FLAG_ESM)

    @property
    def esl_flag(self) -> bool:
        return bool(self.flags & FLAG_ESL)

    @property
    def localized(self) -> bool:
        return bool(self.flags & FLAG_LOCALIZED)


def is_plugin_name(name: str) -> bool:
    return name.lower().endswith(EXTENSIONS)


def kind(name: str, header: Header | None) -> str:
    """How the game treats the file: "esm" (a master), "esl" (light) or "esp", by extension first, then by flag.
    A light-flagged .esp is "esp+esl", a master-flagged one "esp+esm" (both flags: "esp+esm+esl")."""
    ext = name.lower().rsplit(".", 1)[-1]
    if ext == "esm":
        return "esm+esl" if header and header.esl_flag else "esm"
    if ext == "esl":
        return "esl"
    out = "esp"
    if header and header.esm_flag:
        out += "+esm"
    if header and header.esl_flag:
        out += "+esl"
    return out


def _text(raw: bytes) -> str:
    """A zero-ended string of a header field. Plugins carry no encoding: UTF-8 if it is valid, else Windows-1252,
    with anything that still does not decode replaced, so that a name never stops the reader."""
    raw = raw.split(b"\x00", 1)[0]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def parse(data: bytes) -> Header:
    """The header from a plugin's first bytes (at least the whole header record)."""
    if len(data) < RECORD_HEADER:
        raise Unreadable("the file is too short to be a plugin")
    if data[:4] != b"TES4":
        raise Unreadable("the file does not start with a plugin header")
    size, flags = struct.unpack_from("<II", data, 4)
    if size > HEADER_CAP:
        raise Unreadable("the plugin's header is larger than ModTrap reads")
    end = RECORD_HEADER + size
    if end > len(data):
        raise Unreadable("the plugin's header runs past the end of the file")
    author = description = ""
    version: float | None = None
    masters: list[str] = []
    fields: list[str] = []
    at = RECORD_HEADER
    big = None                      # the size an XXXX field gave for the field after it
    while at < end:
        if at + 6 > end:
            raise Unreadable("a field of the plugin's header is cut short")
        ftype = data[at:at + 4]
        (fsize,) = struct.unpack_from("<H", data, at + 4)
        at += 6
        if ftype == b"XXXX":
            if fsize != 4 or at + 4 > end:
                raise Unreadable("a size field of the plugin's header is not as expected")
            (big,) = struct.unpack_from("<I", data, at)
            at += 4
            continue
        if big is not None:
            fsize, big = big, None
        if at + fsize > end:
            raise Unreadable("a field of the plugin's header runs past the header")
        body = data[at:at + fsize]
        at += fsize
        try:
            fields.append(ftype.decode("ascii"))
        except UnicodeDecodeError:
            raise Unreadable("a field of the plugin's header has no readable type") from None
        if ftype == b"MAST":
            name = _text(body)
            if not name:
                raise Unreadable("the plugin names a master with an empty name")
            masters.append(name)
        elif ftype == b"HEDR" and fsize >= 4 and version is None:
            version = round(struct.unpack_from("<f", body)[0], 3)
        elif ftype == b"CNAM":
            author = _text(body)
        elif ftype == b"SNAM":
            description = _text(body)
    return Header(flags=flags, author=author, description=description, masters=tuple(masters),
                  fields=tuple(fields), version=version)


def read(path: Path) -> Header:
    """The header of the plugin at `path`. Reads the header record and no further."""
    try:
        with open(path, "rb") as f:
            head = f.read(RECORD_HEADER)
            if len(head) < RECORD_HEADER:
                raise Unreadable("the file is too short to be a plugin")
            if head[:4] != b"TES4":
                raise Unreadable("the file does not start with a plugin header")
            (size,) = struct.unpack_from("<I", head, 4)
            if size > HEADER_CAP:
                raise Unreadable("the plugin's header is larger than ModTrap reads")
            body = f.read(size)
    except OSError as e:
        raise Unreadable("the file could not be opened (%s)" % type(e).__name__) from None
    return parse(head + body)


COMPRESSED = 0x00040000        # a record whose fields are stored compressed


# Where records of a kind live (XE02): placed things, landscape and navmeshes under a cell; cells under their own
# top group or under a worldspace; dialogue lines under their topic.
_UNDER_CELL = frozenset(("REFR", "ACHR", "NAVM", "LAND", "PGRE", "PHZD", "PARW", "PBAR", "PBEA", "PCON", "PFLA", "PMIS"))


def _skip_group(label: int, group_type: int, kinds: frozenset[str]) -> bool:
    """May a group be passed over when only records of `kinds` are wanted? `label` and `group_type` as read from
    the group's header."""
    if group_type == 0:                                         # a top group: its label is the kind it holds
        top = struct.pack("<I", label).decode("ascii", "replace")
        if top in kinds:
            return False
        if top == "DIAL":
            return "INFO" not in kinds
        if top == "CELL":
            return not (kinds & _UNDER_CELL)
        if top == "WRLD":
            return not ("CELL" in kinds or kinds & _UNDER_CELL)
        return True
    if group_type == 7:                                         # a topic's lines
        return "INFO" not in kinds
    if group_type in (6, 8, 9, 10):                             # what is in a cell
        return not (kinds & _UNDER_CELL)
    return False


class Records:
    """The records of one plugin, found by whom they belong to and their id there, with their fields as stored.
    Read with ModTrap's own reader, nothing of xEdit: record headers to find them, and the fields of the few
    records that are asked for (WHY§64). A record's key is (the name, lower case, of the plugin it belongs to;
    its id in that plugin): a record's first id byte counts into the plugin's masters, and past them means the
    plugin's own (XE02).

    Two plugins write the same field differently where it points at another record: the pointer's last byte is
    that record's plugin's place among the writing plugin's own masters, and master lists differ. `same_field`
    compares with that in mind; plain equality of bytes would call such fields different, and could call two
    fields the same that are not (WHY§65)."""

    def __init__(self, path: Path, seconds: float = 8.0, kinds: frozenset[str] | None = None) -> None:
        """With `kinds`, only records of those kinds are looked for: whole groups that cannot hold one are passed
        over, which makes looking through a whole load order for a few records quick."""
        self.path, self.name = path, path.name
        h = read(path)
        masters = [m.casefold() for m in h.masters]
        own = path.name.casefold()
        self.own, self.masters = own, masters
        self.index: dict[tuple[str, int], tuple[int, int, int, str]] = {}      # key -> offset, length, flags, type
        self.cut = False
        self._file = open(path, "rb")
        try:
            self._data = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        except (ValueError, OSError) as e:
            self._file.close()
            raise Unreadable("the file could not be read: %s" % e) from None
        data, until = self._data, time.monotonic() + seconds
        size = len(data)
        if size < 24 or data[:4] != b"TES4":
            self.close()
            raise Unreadable("not a plugin")
        pos = 24 + struct.unpack_from("<I", data, 4)[0]
        n = 0
        while pos + 24 <= size:
            length, flags, form = struct.unpack_from("<III", data, pos + 4)
            kind = data[pos:pos + 4]
            if kind == b"GRUP":
                if length < 24:
                    break
                if kinds is not None and _skip_group(flags, form, kinds):
                    pos += length                               # nothing wanted in there: past the whole group
                    continue
                pos += 24                                       # into the group: its records follow
                continue
            at = form >> 24
            self.index[(masters[at] if at < len(masters) else own, form & 0xFFFFFF)] = (
                pos, length, flags, kind.decode("ascii", "replace"))
            pos += 24 + length
            n += 1
            if n % 8192 == 0 and time.monotonic() > until:
                self.cut = True
                break

    def fields(self, key: tuple[str, int]) -> list[tuple[str, bytes]] | None:
        """The record's fields in their order, each (type, bytes); None when the plugin does not hold the record."""
        hit = self.index.get(key)
        if hit is None:
            return None
        pos, length, flags, _kind = hit
        body = bytes(self._data[pos + 24:pos + 24 + length])
        if flags & COMPRESSED:
            try:
                body = zlib.decompress(body[4:])
            except zlib.error:
                return [("?", body)]
        out, i, big = [], 0, 0
        while i + 6 <= len(body):
            kind = body[i:i + 4].decode("ascii", "replace")
            size = struct.unpack_from("<H", body, i + 4)[0]
            if kind == "XXXX" and size == 4 and i + 10 <= len(body):        # the next field's real size
                big = struct.unpack_from("<I", body, i + 6)[0]
                i += 10
                continue
            size, big = (big or size), 0
            out.append((kind, body[i + 6:i + 6 + size]))
            i += 6 + size
        return out

    def owner_at(self, place: int) -> str | None:
        """The plugin a pointer's last byte names here: one of this plugin's masters, or the plugin itself."""
        if place < len(self.masters):
            return self.masters[place]
        return self.own if place == len(self.masters) else None

    def kind_of(self, key: tuple[str, int]) -> str:
        hit = self.index.get(key)
        return hit[3] if hit else ""

    def close(self) -> None:
        try:
            self._data.close()
        except (AttributeError, ValueError):
            pass
        self._file.close()

    def __enter__(self) -> "Records":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def canonical(ftype: str, data: bytes) -> bytes:
    """A field as it counts, where the way it is stored says more than it means (XE02§, TL01§15). A cell's place on
    the grid (XCLC) is two numbers and one byte of flags; the three bytes after that are unused and hold whatever
    was in memory when the plugin was saved, and an older plugin has the two numbers only."""
    if ftype == "XCLC" and len(data) in (8, 12):
        return data[:8] + (data[8:9] if len(data) == 12 else b"\x00") + b"\x00\x00\x00"
    return data


def same_field(a: bytes, ra: Records, b: bytes, rb: Records) -> bool:
    """Do two fields of the same type, one from each plugin, hold the same? Equal bytes do, when the two plugins
    number their masters alike. Otherwise bytes may differ, or agree, only by how each plugin numbers the plugin a
    pointer leads to. So the two are walked together, four bytes at a time from every place they could differ:
    a byte that differs is let pass only if, in each plugin's own numbering, it names the same plugin and the
    three bytes before it agree (a pointer's id, then its plugin). And where the plugins number their masters
    differently, bytes that agree in such a place while naming different plugins do not count as the same.

    Without knowing what each field means this cannot be exact: a number that merely looks like a pointer can be
    misread. It errs towards "different" for fields that agree by chance, and is exact for plain values."""
    if len(a) != len(b):
        return False
    if a == b:
        if ra.masters == rb.masters or len(a) < 4 or _text_like(a):
            return True
        # Equal bytes under different numberings: a pointer here would lead to different plugins. Look for one.
        for k in range(3, len(a)):
            oa, ob = ra.owner_at(a[k]), rb.owner_at(b[k])
            # A pointer is one in both plugins' numbering; a plain number that only looks like one in the plugin
            # with the long master list (a decimal's last byte, say) is not.
            if oa != ob and _pointer_like(a, k, ra) and _pointer_like(b, k, rb):
                return False
        return True
    for k in range(len(a)):
        if a[k] == b[k]:
            continue
        if k < 3 or a[k - 3:k] != b[k - 3:k]:
            return False
        oa, ob = ra.owner_at(a[k]), rb.owner_at(b[k])
        if oa is None or oa != ob:
            return False
    return True


def _text_like(data: bytes) -> bool:
    """Is this field written text: a name, a path? Longer than a single pointer, printable to its closing zero."""
    body = data[:-1] if data.endswith(b"\x00") else data
    return len(data) > 4 and all(32 <= c < 127 or c in (9, 10, 13) for c in body)


def _pointer_like(data: bytes, k: int, r: Records) -> bool:
    """Could the four bytes ending at k be a pointer to a record? Its plugin must be one this plugin knows, its id
    must be one a record can have (not zero, and from 0x800 up unless it points into the game's first file), and
    it must sit where pointers sit: on a four-byte boundary of the field."""
    if (k + 1) % 4 or r.owner_at(data[k]) is None:
        return False
    ident = data[k - 3] | data[k - 2] << 8 | data[k - 1] << 16
    return ident >= 0x800 or (ident > 0 and data[k] == 0)


def groups(path: Path) -> frozenset[str]:
    """The kinds of records a plugin holds ("NPC_", "WRLD", "QUST"…): the names of its top groups, read from the
    groups' own headers; what is inside them is passed over, so a large plugin costs no more than a small one."""
    out = set()
    try:
        with open(path, "rb") as f:
            head = f.read(24)
            if len(head) < 24 or head[:4] != b"TES4":
                raise Unreadable("it does not begin as a plugin does")
            f.seek(int.from_bytes(head[4:8], "little"), 1)
            while True:
                h = f.read(24)
                if len(h) < 24 or h[:4] != b"GRUP":
                    break
                size = int.from_bytes(h[4:8], "little")
                if int.from_bytes(h[12:16], "little") == 0:              # a top group: named after its records' kind
                    out.add(h[8:12].decode("ascii", "replace"))
                if size < 24:
                    break
                f.seek(size - 24, 1)
    except OSError as e:
        raise Unreadable(str(e)) from None
    return frozenset(out)


def record_ids(path: Path, seconds: float = 8.0) -> tuple[set[tuple[str, int]], bool]:
    """The records a plugin holds, by their keys (see Records), and whether the reading was cut short."""
    with Records(path, seconds) as r:
        return set(r.index), r.cut


def build(masters: tuple[str, ...] | list[str] = (), *, flags: int = 0, author: str = "",
          description: str = "", version: float = 1.7, kinds: tuple[str, ...] = ()) -> bytes:
    """A minimal plugin of our own: a header and no records; `kinds` adds an empty top group for each kind of
    record named ("NPC_"). For ModTrap's probe (DESIGN§9) and its tests: every fixture is written by this function,
    never taken from a real mod."""
    def fld(ftype: bytes, body: bytes) -> bytes:
        if len(body) > 0xFFFF:
            return b"XXXX" + struct.pack("<HI", 4, len(body)) + ftype + struct.pack("<H", 0) + body
        return ftype + struct.pack("<H", len(body)) + body

    body = fld(b"HEDR", struct.pack("<fII", version, 0, 0x800))
    body += fld(b"CNAM", author.encode("utf-8") + b"\x00")
    if description:
        body += fld(b"SNAM", description.encode("utf-8") + b"\x00")
    for m in masters:
        body += fld(b"MAST", m.encode("utf-8") + b"\x00") + fld(b"DATA", b"\x00" * 8)
    tail = b"".join(b"GRUP" + struct.pack("<I", 24) + k.encode("ascii")[:4].ljust(4, b"_") + struct.pack("<iHHHH", 0, 0, 0, 0, 0) for k in kinds)
    return b"TES4" + struct.pack("<IIIIHH", len(body), flags, 0, 0, 44, 0) + body + tail
