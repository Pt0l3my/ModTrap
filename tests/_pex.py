"""An invented compiled script, written by the tests' own code: the least a script holds, for `modtrap.pex` to read."""

import struct


def script(name: str, natives=(), calls=(), methods=(), big: bool = True, debug: bool = True) -> bytes:
    """A script `name` that declares the functions `natives` without doing their work, and whose one function of
    its own calls `calls` ((script, function), by the script's name) and `methods` (on itself)."""
    e = ">" if big else "<"
    strings: list[str] = []

    def s(text: str) -> bytes:
        if text not in strings:
            strings.append(text)
        return struct.pack(e + "H", strings.index(text))

    def text(t: str) -> bytes:
        raw = t.encode("utf-8")
        return struct.pack(e + "H", len(raw)) + raw

    def name_value(t: str) -> bytes:
        return b"\x01" + s(t)

    def function(flags: int, code: bytes = b"", count: int = 0) -> bytes:
        return s("None") + s("") + struct.pack(e + "I", 0) + bytes([flags]) + struct.pack(e + "HH", 0, 0) + struct.pack(e + "H", count) + code

    code, count = b"", 0
    for cls, fn in calls:
        code += b"\x19" + name_value(cls) + name_value(fn) + name_value("::temp0") + b"\x03" + struct.pack(e + "i", 1) + b"\x05\x01"
        count += 1
    for fn in methods:
        code += b"\x17" + name_value(fn) + name_value("self") + name_value("::temp0") + b"\x03" + struct.pack(e + "i", 0)
        count += 1
    code += b"\x1a\x00"                                  # return none
    count += 1
    functions = [s(n) + function(3) for n in natives] + [s("Run") + function(0, code, count)]
    body = s("") + s("") + struct.pack(e + "I", 0) + s("") + struct.pack(e + "H", 1) + s("counter") + s("Int") + struct.pack(e + "I", 0) + b"\x03" + struct.pack(e + "i", 7)
    body += struct.pack(e + "H", 1) + s("Count") + s("Int") + s("") + struct.pack(e + "I", 0) + b"\x07" + s("counter")       # one property, kept in the variable
    body += struct.pack(e + "H", 1) + s("") + struct.pack(e + "H", len(functions)) + b"".join(functions)
    obj = s(name) + struct.pack(e + "I", len(body) + 4) + body
    dbg = (b"\x01" + struct.pack(e + "Q", 0) + struct.pack(e + "H", 1) + s(name) + s("") + s("Run") + b"\x00" + struct.pack(e + "H", 2) + struct.pack(e + "HH", 3, 4)) if debug else b"\x00"
    flags = struct.pack(e + "H", 1) + s("hidden") + b"\x00"
    table = struct.pack(e + "H", len(strings)) + b"".join(text(t) for t in strings)
    head = struct.pack(e + "IBBHQ", 0xFA57C0DE, 3, 2, 1, 0) + text(name + ".psc") + text("") + text("")
    return head + table + dbg + flags + struct.pack(e + "H", 1) + obj
