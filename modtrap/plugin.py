"""A plugin's header: its flags, author, description and masters (XE02). Nothing else of a plugin is ever read
(WHY§10): the reader stops at the end of the header record.

The layout is taken from the description in XE02, not from any other program's code. A file that does not fit it is
reported as unreadable, never guessed at.
"""

from __future__ import annotations

import mmap
import struct
import time
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


def record_ids(path: Path, seconds: float = 8.0) -> tuple[set[tuple[str, int]], bool]:
    """The records a plugin holds, each as (the name, lower case, of the plugin the record belongs to; its id
    there), and whether the reading was cut short by the time limit. Only the records' headers are read: a
    record's first id byte counts into the plugin's masters, and past them means the plugin's own (XE02). What
    the records hold is not looked at. For telling which records two plugins both hold (WHY§63)."""
    h = read(path)
    masters = [m.casefold() for m in h.masters]
    own = path.name.casefold()
    out: set[tuple[str, int]] = set()
    until = time.monotonic() + seconds
    with open(path, "rb") as f:
        try:
            data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        except (ValueError, OSError) as e:
            raise Unreadable("the file could not be read: %s" % e) from None
        try:
            size = len(data)
            if size < 24 or data[:4] != b"TES4":
                raise Unreadable("not a plugin")
            pos = 24 + struct.unpack_from("<I", data, 4)[0]
            n = 0
            while pos + 24 <= size:
                length = struct.unpack_from("<I", data, pos + 4)[0]
                if data[pos:pos + 4] == b"GRUP":
                    if length < 24:
                        break
                    pos += 24                                   # into the group: its records follow
                    continue
                form = struct.unpack_from("<I", data, pos + 12)[0]
                index = form >> 24
                out.add((masters[index] if index < len(masters) else own, form & 0xFFFFFF))
                pos += 24 + length
                n += 1
                if n % 8192 == 0 and time.monotonic() > until:
                    return out, True
        finally:
            data.close()
    return out, False


def build(masters: tuple[str, ...] | list[str] = (), *, flags: int = 0, author: str = "",
          description: str = "", version: float = 1.7) -> bytes:
    """A minimal plugin of our own: a header and no records. For ModTrap's probe (DESIGN§9) and its tests: every
    fixture is written by this function, never taken from a real mod."""
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
    return b"TES4" + struct.pack("<IIIIHH", len(body), flags, 0, 0, 44, 0) + body
