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
WM_CLOSE = 0x0010
MO2_MESSAGE_TITLE = "Mod Organizer"        # the caption of MO2's own message boxes (the owner's PC, WHY§50)


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

    def close(self, hwnd: int) -> bool:
        """Asks a window to close, as a click on its X does."""
        return False

    def path_of(self, hwnd: int) -> str:
        """The full path of the program the window belongs to, or ""."""
        return ""

    def programs(self, image: str) -> list[str] | None:
        """The full paths of the running programs whose file is called `image`; None when that cannot be told."""
        return None


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
        self.psapi = ctypes.WinDLL("psapi", use_last_error=True)
        self.psapi.EnumProcesses.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        self.psapi.EnumProcesses.restype = wintypes.BOOL

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

    def _path_of_pid(self, pid: int) -> str:
        handle = self.kernel32.OpenProcess(0x1000, False, pid)             # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ""
        try:
            buf = self.ct.create_unicode_buffer(32768)
            size = self.wt.DWORD(32768)
            if not self.kernel32.QueryFullProcessImageNameW(handle, 0, buf, self.ct.byref(size)):
                return ""
            return buf.value
        finally:
            self.kernel32.CloseHandle(handle)

    def path_of(self, hwnd: int) -> str:
        pid = self.wt.DWORD(0)
        self.user32.GetWindowThreadProcessId(hwnd, self.ct.byref(pid))
        return self._path_of_pid(pid.value) if pid.value else ""

    def program_of(self, hwnd: int) -> str:
        return Path(self.path_of(hwnd).replace("\\", "/")).name

    def programs(self, image: str) -> list[str] | None:
        size = 4096
        while True:
            pids = (self.wt.DWORD * size)()
            got = self.wt.DWORD(0)
            if not self.psapi.EnumProcesses(pids, self.ct.sizeof(pids), self.ct.byref(got)):
                return None
            n = got.value // self.ct.sizeof(self.wt.DWORD)
            if n < size:
                break
            size *= 2
        out = []
        for pid in pids[:n]:
            if not pid:
                continue
            path = self._path_of_pid(int(pid))
            if path and Path(path.replace("\\", "/")).name.casefold() == image.casefold():
                out.append(path)
        return out

    def click(self, hwnd: int) -> bool:
        return bool(self.user32.PostMessageW(hwnd, BM_CLICK, 0, 0))

    def close(self, hwnd: int) -> bool:
        return bool(self.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0))


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


def close_message(image: str, title: str = MO2_MESSAGE_TITLE, win: Windows | None = None) -> bool:
    """Closes a message a program is showing: every visible top window of the program whose file is `image` and
    whose caption is exactly `title` is asked to close, as a click on its X does. For the MO2 that ModTrap's own
    command started and that stops at a message once the run is over (MO01§9, WHY§54); MO2's main window has a
    longer caption and is not touched. True when a window was asked."""
    win = win or _windows()
    if win is None:
        return False
    asked = False
    try:
        for hwnd in win.top_windows():
            if not win.visible(hwnd) or win.text(hwnd).strip() != title:
                continue
            if win.program_of(hwnd).casefold() != image.casefold():
                continue
            asked = win.close(hwnd) or asked
    except Exception:
        return asked
    return asked


def same_file(a: str, b: str) -> bool:
    """Are two paths the same file? By the file itself where both can be looked at (a drive letter standing for a
    folder, or a link, gives one file two paths), else by the paths as written."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def running_paths(image: str, win: Windows | None = None) -> list[str] | None:
    """The full paths of the running programs called `image`, or None when that cannot be told (not Windows)."""
    win = win or _windows()
    if win is None:
        return None
    try:
        return win.programs(image)
    except Exception:
        return None


def ask_to_close(program: str, win: Windows | None = None) -> bool:
    """Asks the program at this path to close: each of its visible top windows is asked, as a click on its X does.
    Never ends it. For the MO2 of this modlist, when the owner has said yes (WHY§58). True when a window was asked."""
    win = win or _windows()
    if win is None:
        return False
    asked = False
    try:
        for hwnd in win.top_windows():
            if not win.visible(hwnd) or not win.text(hwnd).strip():
                continue
            path = win.path_of(hwnd)
            if path and same_file(path, program):
                asked = win.close(hwnd) or asked
    except Exception:
        return asked
    return asked


__all__ = ["Windows", "press_module_selection_ok", "close_message", "running_paths", "ask_to_close", "same_file",
           "FORM_CLASS", "FORM_TITLE"]
