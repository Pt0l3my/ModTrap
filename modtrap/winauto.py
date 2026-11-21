"""Pressing OK in xEdit's "Module Selection" window (XE01§13, WHY§51).

In script mode xEdit always asks which plugins to load, with the ones of the plugins file already ticked. For a
run ModTrap started, that list is ModTrap's own: there is nothing to choose, only OK to press. This module finds
that window, by its class and title, in a program of the given file name, and presses its OK button, as the owner's
click would. It touches no other window and no other program. Windows only; elsewhere it does nothing.

It is written against an interface (`Windows`) so that the choosing can be tested without Windows.
"""

from __future__ import annotations

import os
from pathlib import Path

FORM_CLASS = "TfrmModuleSelect"            # xEdit's form: xeModuleSelectForm.pas:25
FORM_TITLE = "Module Selection"            # its caption: xeModuleSelectForm.dfm:5
OK_TEXTS = ("ok", "&ok")                   # its OK button's caption: xeModuleSelectForm.dfm:36
BM_CLICK = 0x00F5


class Windows:
    """What is needed of the window system. The real one is `_Real`; tests give their own."""

    def top_windows(self) -> list[int]:
        return []

    def children(self, hwnd: int) -> list[int]:
        return []

    def class_name(self, hwnd: int) -> str:
        return ""

    def text(self, hwnd: int) -> str:
        return ""

    def visible(self, hwnd: int) -> bool:
        return False

    def enabled(self, hwnd: int) -> bool:
        return False

    def program_of(self, hwnd: int) -> str:
        """The file name of the program the window belongs to, or ""."""
        return ""

    def click(self, hwnd: int) -> bool:
        return False


class _Real(Windows):
    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes
        self.ct, self.wt = ctypes, wintypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        u, k = self.user32, self.kernel32
        u.EnumWindows.argtypes = [self.proc, wintypes.LPARAM]
        u.EnumChildWindows.argtypes = [wintypes.HWND, self.proc, wintypes.LPARAM]
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsWindowEnabled.argtypes = [wintypes.HWND]
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        u.PostMessageW.restype = wintypes.BOOL
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                 ctypes.POINTER(wintypes.DWORD)]
        k.QueryFullProcessImageNameW.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]

    def _enum(self, call) -> list[int]:
        found: list[int] = []

        def each(hwnd, _lparam):
            found.append(int(hwnd))
            return True
        cb = self.proc(each)
        call(cb)
        return found

    def top_windows(self) -> list[int]:
        return self._enum(lambda cb: self.user32.EnumWindows(cb, 0))

    def children(self, hwnd: int) -> list[int]:
        return self._enum(lambda cb: self.user32.EnumChildWindows(hwnd, cb, 0))

    def _string(self, fn, hwnd: int) -> str:
        buf = self.ct.create_unicode_buffer(512)
        fn(hwnd, buf, 512)
        return buf.value

    def class_name(self, hwnd: int) -> str:
        return self._string(self.user32.GetClassNameW, hwnd)

    def text(self, hwnd: int) -> str:
        return self._string(self.user32.GetWindowTextW, hwnd)

    def visible(self, hwnd: int) -> bool:
        return bool(self.user32.IsWindowVisible(hwnd))

    def enabled(self, hwnd: int) -> bool:
        return bool(self.user32.IsWindowEnabled(hwnd))

    def program_of(self, hwnd: int) -> str:
        pid = self.wt.DWORD(0)
        self.user32.GetWindowThreadProcessId(hwnd, self.ct.byref(pid))
        if not pid.value:
            return ""
        handle = self.kernel32.OpenProcess(0x1000, False, pid.value)       # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        try:
            buf = self.ct.create_unicode_buffer(32768)
            size = self.wt.DWORD(32768)
            if not self.kernel32.QueryFullProcessImageNameW(handle, 0, buf, self.ct.byref(size)):
                return ""
            return Path(buf.value.replace("\\", "/")).name
        finally:
            self.kernel32.CloseHandle(handle)

    def click(self, hwnd: int) -> bool:
        return bool(self.user32.PostMessageW(hwnd, BM_CLICK, 0, 0))


_real: Windows | None = None


def _windows() -> Windows | None:
    global _real
    if os.name != "nt":
        return None
    if _real is None:
        try:
            _real = _Real()
        except Exception:
            return None
    return _real


def press_module_selection_ok(image: str, win: Windows | None = None) -> bool:
    """Presses OK in the "Module Selection" window of a running program whose file is `image`. True when the
    button was pressed; False when there is no such window, its OK is not ready, or the press was not allowed
    (a program started with higher rights than ModTrap's does not take it)."""
    win = win or _windows()
    if win is None:
        return False
    try:
        for hwnd in win.top_windows():
            if win.class_name(hwnd) != FORM_CLASS or not win.visible(hwnd):
                continue
            if win.text(hwnd).strip() != FORM_TITLE or win.program_of(hwnd).casefold() != image.casefold():
                continue
            for child in win.children(hwnd):
                if win.text(child).strip().casefold() in OK_TEXTS and "button" in win.class_name(child).casefold():
                    if win.visible(child) and win.enabled(child):
                        return win.click(child)
            return False
    except Exception:
        return False
    return False


__all__ = ["Windows", "press_module_selection_ok", "FORM_CLASS", "FORM_TITLE"]
