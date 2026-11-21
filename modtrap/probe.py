"""Invented plugins with real records, for the probe (DESIGN§9): the harmless test that must pass on the owner's
PC before ModTrap touches a real mod. Every byte here is written by this module; nothing comes from a real mod.

Used by the probe's run (modtrap/probejob.py, WHY§47). The record layout below is the Skyrim SE plugin format as
it is widely documented (XE02 covers the header from xEdit's definitions; the records and groups are LIKELY until
xEdit has loaded these files on the owner's PC, which is the first thing the probe shows).

The four plugins:
- "ModTrap Probe - Base.esp": a plugin that stays, and that Bad builds on. Two material types, "stone" and
  "brick"; brick's parent is stone.
- "ModTrap Probe - Bad.esp": the mod to take out. Two global variables and a material type of its own, and its
  own version of Base's brick, whose parent it makes its own material.
- "ModTrap Probe - Override.esp": a plugin that must go on working. It overrides one of Bad's globals (to be taken
  out whole), has a global of its own, and a form list of its own with two entries: its own global and one of Bad's
  (that one entry to be taken out, the list kept). It also carries Bad's version of Base's brick on, parent and
  all (that parent to be put back as Base has it: MT4's case C, WHY§55).
- "ModTrap Probe - Patch.esp": a patch made only for Bad: it overrides both of Bad's globals and has nothing else.
"""

from __future__ import annotations

import struct

from . import plugin

BASE = "ModTrap Probe - Base.esp"
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


def matt(form_id: int, editor_id: str, name: str, parent: int | None = None) -> bytes:
    """A material type (MATT): an editor id, optionally its parent (PNAM, another material type) and a name."""
    fields = [(b"EDID", _zstr(editor_id))]
    if parent is not None:
        fields.append((b"PNAM", struct.pack("<I", parent)))
    return record(b"MATT", form_id, fields + [(b"MNAM", _zstr(name))])


STONE, BRICK, BAD_STUFF = 0x00000800, 0x00000801, 0x01000802        # as Base and Bad number them (Bad: Base is 00)


def probe_set() -> dict[str, bytes]:
    """The four probe plugins, by file name. A form id's first byte says whose it is: a plugin's masters in their
    order from 00, then the plugin's own."""
    note = "Invented by ModTrap for its probe. Safe to delete."
    base = plugin_file([], [group(b"MATT", [matt(STONE, "MTP_Stone", "stone"), matt(BRICK, "MTP_Brick", "brick", STONE)])],
                       2, 0x802, note)
    bad = plugin_file([BASE], [
        group(b"GLOB", [glob(0x01000800, "MTP_BadOne", 1.0), glob(0x01000801, "MTP_BadTwo", 2.0)]),
        group(b"MATT", [matt(BRICK, "MTP_Brick", "brick", BAD_STUFF), matt(BAD_STUFF, "MTP_BadStuff", "bad stuff")]),
    ], 4, 0x803, note)
    # In Override, Base is 00, Bad is 01 and its own records are 02.
    override = plugin_file([BASE, BAD], [
        group(b"GLOB", [glob(0x01000800, "MTP_BadOne", 10.0), glob(0x02000800, "MTP_OwnGlobal", 3.0)]),
        group(b"FLST", [flst(0x02000801, "MTP_OwnList", [0x02000800, 0x01000801])]),
        group(b"MATT", [matt(BRICK, "MTP_Brick", "brick", BAD_STUFF)]),
    ], 4, 0x802, note)
    # In Patch, Bad is 00 (Bad's own records, which Bad itself numbers 01).
    patch = plugin_file([BAD], [group(b"GLOB", [glob(0x00000800, "MTP_BadOne", 20.0), glob(0x00000801, "MTP_BadTwo", 21.0)])],
                        2, 0x800, note)
    return {BASE: base, BAD: bad, OVERRIDE: override, PATCH: patch}


# The brick's parent as the demastered Override must hold it: put back to Base's stone, and not Bad's material.
PARENT_BACK = b"PNAM" + struct.pack("<HI", 4, STONE)
PARENT_BAD = b"PNAM" + struct.pack("<HI", 4, BAD_STUFF)

# What a dry run of the probe must report, and what a demaster of it must leave (the probe's pass mark).
EXPECTED = {
    OVERRIDE: {"records": 4, "own": 1, "entries": 1, "parts": 1, "needs_you": 0, "reading": "can be demastered",
               "masters_after": [BASE]},
    PATCH: {"records": 2, "own": 2, "entries": 0, "parts": 0, "needs_you": 0, "reading": "patch only"},
}


def check_headers(files: dict[str, bytes]) -> None:
    """The probe's own files, read back by ModTrap's header reader: a slip here must never reach the owner's PC."""
    for name, data in files.items():
        h = plugin.parse(data)
        want = {BASE: (), BAD: (BASE,), OVERRIDE: (BASE, BAD), PATCH: (BAD,)}[name]
        assert h.masters == want, name
