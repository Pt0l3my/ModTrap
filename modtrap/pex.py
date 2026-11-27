"""A compiled Papyrus script (`.pex`), read for what it declares and what it calls (WHY§146).

Our own reader of the game's script format, after its public description: a header, a table of strings, debug lines,
user flags, and the script's objects with their variables, properties, states and functions. Nothing is run, and
nothing here is taken from a script: only names are read, to answer one question, whether a script extender
plugin the game does not load is still called by the scripts the game does load.

A file this reader does not follow to its end is `None`, never a guess.
"""

from __future__ import annotations

import struct

MAGIC = 0xFA57C0DE
BYTES = 4 * 1024 * 1024                  # a script larger than this is not read
# The values each instruction carries, by its code; a call carries a counted list after them.
_ARGS = (0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 1, 2, 2, 3, 2, 3, 1, 3, 3, 3, 2, 2, 3, 3, 4, 4)
_CALL_METHOD, _CALL_PARENT, _CALL_STATIC = 0x17, 0x18, 0x19


class _Short(Exception):
    pass


class _Reader:
    def __init__(self, data: bytes, big: bool):
        self.data, self.at, self.e = data, 0, ">" if big else "<"

    def take(self, fmt: str):
        size = struct.calcsize(fmt)
        if self.at + size > len(self.data):
            raise _Short()
        value = struct.unpack_from(self.e + fmt, self.data, self.at)[0]
        self.at += size
        return value

    def u8(self) -> int:
        return self.take("B")

    def u16(self) -> int:
        return self.take("H")

    def u32(self) -> int:
        return self.take("I")

    def skip(self, n: int) -> None:
        if self.at + n > len(self.data):
            raise _Short()
        self.at += n

    def text(self) -> str:
        n = self.u16()
        if self.at + n > len(self.data):
            raise _Short()
        raw = self.data[self.at:self.at + n]
        self.at += n
        return raw.decode("utf-8", "replace")


def _value(r: _Reader):
    """One value of an instruction: ("name", index of a string), ("int", number), or (kind, None)."""
    kind = r.u8()
    if kind == 0:
        return "none", None
    if kind in (1, 2):
        return ("name" if kind == 1 else "text"), r.u16()
    if kind == 3:
        return "int", r.take("i")
    if kind == 4:
        r.skip(4)
        return "float", None
    if kind == 5:
        r.skip(1)
        return "bool", None
    raise _Short()


def _function(r: _Reader, strings: list[str], calls: set, methods: set) -> bool:
    """Reads one function to its end; says whether it is a native one (the script only declares it: a script
    extender plugin, or the game, does the work)."""
    r.skip(2 + 2 + 4)                          # what it returns, its note, its user flags
    native = bool(r.u8() & 2)
    for _ in range(2):                         # what it is given, then what it keeps
        r.skip(4 * r.u16())
    for _ in range(r.u16()):
        code = r.u8()
        if code >= len(_ARGS):
            raise _Short()
        fixed = [_value(r) for _ in range(_ARGS[code])]
        if code in (_CALL_METHOD, _CALL_PARENT, _CALL_STATIC):
            kind, n = _value(r)
            if kind != "int" or n is None or not 0 <= n <= 4096:
                raise _Short()
            for _ in range(n):
                _value(r)
            names = [strings[i].lower() if k == "name" and i is not None and i < len(strings) else "" for k, i in fixed]
            if code == _CALL_STATIC and names[0] and names[1]:
                calls.add((names[0], names[1]))
            elif code == _CALL_METHOD and names[0]:
                methods.add(names[0])
    return native


def read(data: bytes) -> dict | None:
    """What a compiled script says of itself: {"name": the script's name, "names": every name and text it holds
    (lower case), "natives": the functions it only declares, "calls": {(script, function)} it calls by the script's
    name, "methods": the functions it calls on something it holds}. None where the bytes are not a script this
    reader follows to its end."""
    if len(data) < 16 or len(data) > BYTES:
        return None
    if struct.unpack_from(">I", data, 0)[0] == MAGIC:
        big = True
    elif struct.unpack_from("<I", data, 0)[0] == MAGIC:
        big = False
    else:
        return None
    r = _Reader(data, big)
    try:
        r.skip(4 + 1 + 1 + 2 + 8)              # the mark, the format's version, the game, when it was compiled
        for _ in range(3):
            r.text()                           # the source's name, and who compiled it where: passed over, never kept
        strings = [r.text() for _ in range(r.u16())]
        if r.u8():                             # debug lines
            r.skip(8)
            for _ in range(r.u16()):
                r.skip(2 + 2 + 2 + 1)
                r.skip(2 * r.u16())
        r.skip(3 * r.u16())                    # user flags
        out = {"name": "", "names": {s.lower() for s in strings}, "natives": set(), "calls": set(), "methods": set()}
        for n in range(r.u16()):
            name = r.u16()
            if name >= len(strings):
                return None
            if n == 0:
                out["name"] = strings[name]
            end = r.at + r.u32()               # the object's length counts its own four bytes
            r.skip(2 + 2 + 4 + 2)              # its parent, its note, its user flags, the state it begins in
            for _ in range(r.u16()):           # variables
                r.skip(2 + 2 + 4)
                _value(r)
            for _ in range(r.u16()):           # properties
                r.skip(2 + 2 + 2 + 4)
                flags = r.u8()
                if flags & 4:
                    r.skip(2)
                else:
                    if flags & 1:
                        _function(r, strings, out["calls"], out["methods"])
                    if flags & 2:
                        _function(r, strings, out["calls"], out["methods"])
            for _ in range(r.u16()):           # states, each with its functions
                r.skip(2)
                for _ in range(r.u16()):
                    fn = r.u16()
                    if fn >= len(strings):
                        return None
                    if _function(r, strings, out["calls"], out["methods"]):
                        out["natives"].add(strings[fn].lower())
            if r.at != end:
                return None
        return out if r.at == len(data) and out["name"] else None
    except (_Short, struct.error, IndexError):
        return None


__all__ = ["read"]
