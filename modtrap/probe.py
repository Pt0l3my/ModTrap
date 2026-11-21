"""Invented plugins with real records, for the probe (DESIGN§9): the harmless test that must pass on the owner's
PC before ModTrap touches a real mod. Every byte here is written by this module; nothing comes from a real mod.

Used by the probe's run (modtrap/probejob.py, WHY§47). The record layout below is the Skyrim SE plugin format as
it is widely documented (XE02 covers the header from xEdit's definitions; the records and groups are LIKELY until
xEdit has loaded these files on the owner's PC, which is the first thing the probe shows).

The three plugins:
- "ModTrap Probe - Bad.esp": the mod to take out. Two global variables.
- "ModTrap Probe - Override.esp": a plugin that must go on working. It overrides one of Bad's globals (to be taken
  out whole), has a global of its own, and a form list of its own with two entries: its own global and one of Bad's
  (that one entry to be taken out, the list kept).
- "ModTrap Probe - Patch.esp": a patch made only for Bad: it overrides both of Bad's globals and has nothing else.
"""

from __future__ import annotations

import struct

from . import plugin

BAD = "ModTrap Probe - Bad.esp"
OVERRIDE = "ModTrap Probe - Override.esp"
PATCH = "ModTrap Probe - Patch.esp"
FORM_VERSION = 44


def _field(ftype: bytes, body: bytes) -> bytes:
    return ftype + struct.pack("<H", len(body)) + body


def _zstr(text: str) -> bytes:
    return text.encode("ascii") + b"\x00"


def record(signature: bytes, form_id: int, fields: list[tuple[bytes, bytes]], flags: int = 0) -> bytes:
    """One record: its 24-byte header (type, size of what follows, flags, form id, version control, form version,
    two more bytes), then its fields."""
    body = b"".join(_field(t, b) for t, b in fields)
    return signature + struct.pack("<IIIIHH", len(body), flags, form_id, 0, FORM_VERSION, 0) + body


def group(signature: bytes, records: list[bytes]) -> bytes:
    """A top-level group of records of one type: 'GRUP', its whole size, the type as its label, group type 0."""
    body = b"".join(records)
    return b"GRUP" + struct.pack("<I", 24 + len(body)) + signature + struct.pack("<iHHHH", 0, 0, 0, 0, 0) + body


def glob(form_id: int, editor_id: str, value: float) -> bytes:
    """A global variable (GLOB): an editor id, a type ('f', a float) and a value."""
    return record(b"GLOB", form_id, [(b"EDID", _zstr(editor_id)), (b"FNAM", b"f"), (b"FLTV", struct.pack("<f", value))])


def flst(form_id: int, editor_id: str, entries: list[int]) -> bytes:
    """A form list (FLST): an editor id and one LNAM for each form id in the list."""
    return record(b"FLST", form_id, [(b"EDID", _zstr(editor_id))] + [(b"LNAM", struct.pack("<I", e)) for e in entries])


def plugin_file(masters: list[str], groups: list[bytes], records: int, next_id: int, description: str) -> bytes:
    """A whole plugin: the header record (XE02), then the groups."""
    def fld(ftype: bytes, body: bytes) -> bytes:
        return ftype + struct.pack("<H", len(body)) + body
    head = fld(b"HEDR", struct.pack("<fII", 1.7, records + len(groups), next_id))
    head += fld(b"CNAM", _zstr("ModTrap")) + fld(b"SNAM", _zstr(description))
    for m in masters:
        head += fld(b"MAST", m.encode("ascii") + b"\x00") + fld(b"DATA", b"\x00" * 8)
    return b"TES4" + struct.pack("<IIIIHH", len(head), 0, 0, 0, FORM_VERSION, 0) + head + b"".join(groups)


def probe_set() -> dict[str, bytes]:
    """The three probe plugins, by file name. In a plugin with one master, form ids starting 00 belong to that
    master and those starting 01 are the plugin's own."""
    bad = plugin_file([], [group(b"GLOB", [glob(0x00000800, "MTP_BadOne", 1.0), glob(0x00000801, "MTP_BadTwo", 2.0)])],
                      2, 0x802, "Invented by ModTrap for its probe. Safe to delete.")
    override = plugin_file([BAD], [
        group(b"GLOB", [glob(0x00000800, "MTP_BadOne", 10.0), glob(0x01000800, "MTP_OwnGlobal", 3.0)]),
        group(b"FLST", [flst(0x01000801, "MTP_OwnList", [0x01000800, 0x00000801])]),
    ], 3, 0x802, "Invented by ModTrap for its probe. Safe to delete.")
    patch = plugin_file([BAD], [group(b"GLOB", [glob(0x00000800, "MTP_BadOne", 20.0), glob(0x00000801, "MTP_BadTwo", 21.0)])],
                        2, 0x800, "Invented by ModTrap for its probe. Safe to delete.")
    return {BAD: bad, OVERRIDE: override, PATCH: patch}


# What a dry run of the probe must report, and what a demaster of it must leave (the probe's pass mark).
EXPECTED = {
    OVERRIDE: {"records": 3, "own": 1, "entries": 1, "needs_you": 0, "reading": "can be demastered",
               "masters_after": [], "records_after": 2, "list_entries_after": 1},
    PATCH: {"records": 2, "own": 2, "entries": 0, "needs_you": 0, "reading": "patch only"},
}


def check_headers(files: dict[str, bytes]) -> None:
    """The probe's own files, read back by ModTrap's header reader: a slip here must never reach the owner's PC."""
    for name, data in files.items():
        h = plugin.parse(data)
        if name == BAD:
            assert h.masters == (), name
        else:
            assert h.masters == (BAD,), name
