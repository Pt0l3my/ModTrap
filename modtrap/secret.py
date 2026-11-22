"""A secret of the owner's, kept on this PC only (MT37, WHY§101): the personal key Nexus gives an account.

It is kept in ModTrap's own folder, outside any modlist and outside every session file. On Windows it is written
through the system's own protection for a user's data (DPAPI), so that the file is of no use to another account
or on another PC. It is never written to the log, never sent to the page once kept, and never sent anywhere but
to the one service it is for.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import paths

MAX = 4096


def _file(name: str) -> Path:
    if not name.isalnum():
        raise ValueError("not a name for a secret")
    return paths.home() / "keys" / (name + ".bin")


def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("n", wintypes.DWORD), ("p", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buf = ctypes.create_string_buffer(data, len(data))
    src = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    out = Blob()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(out)):         # 1: never show a window
        raise OSError("the system's protection for a user's data refused")
    try:
        return ctypes.string_at(out.p, out.n)
    finally:
        kernel32.LocalFree(out.p)


def keep(name: str, text: str) -> None:
    data = text.strip().encode("utf-8")
    if not data or len(data) > MAX:
        raise ValueError("not a usable key")
    blob = (b"D1" + _dpapi(data, True)) if os.name == "nt" else (b"P1" + data)
    path = _file(name)
    paths.write_atomic(path, blob)
    if os.name != "nt":
        os.chmod(path, 0o600)


def read(name: str) -> str:
    """The secret, or "" when none is kept or it cannot be read on this account."""
    try:
        with open(_file(name), "rb") as f:
            blob = f.read(MAX * 4)
    except (OSError, ValueError):
        return ""
    try:
        if blob[:2] == b"D1" and os.name == "nt":
            return _dpapi(blob[2:], False).decode("utf-8")
        if blob[:2] == b"P1" and os.name != "nt":
            return blob[2:].decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    return ""


def kept(name: str) -> bool:
    try:
        return _file(name).is_file()
    except ValueError:
        return False


def forget(name: str) -> None:
    try:
        _file(name).unlink()
    except (OSError, ValueError):
        pass


__all__ = ["forget", "keep", "kept", "read"]
