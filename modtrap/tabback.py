"""Back to ModTrap's tab (MT52): after ModTrap's page opened a site's page in a new tab, which a browser always puts
in front, the browser is taken back to ModTrap's tab.

A page cannot do this for itself. ModTrap's program can, on Windows, the way the owner would: with the browser's own
key for "the tab before this one", Ctrl+Page Up. It is pressed only when the window in front is a browser's and its
title is no longer ModTrap's, and the title is looked at again afterwards: where the tab before the new one was not
ModTrap's, the key for "the tab after this one" puts things back as they were, and nothing more is tried.

Nothing is read from the browser but the title and the kind of the window in front.
"""

from __future__ import annotations

import os
import re
import time

from . import logbook

log = logbook.get("updates")

BROWSERS = ("MozillaWindowClass", "Chrome_WidgetWin_1")      # Firefox; Chrome, Edge and their kin
OURS = re.compile(r"ModTrap( (—|–|-|and \d+ more)|$)")       # ModTrap's tab in front: "ModTrap — Mozilla Firefox", "ModTrap - Google Chrome"
VK_CONTROL, VK_PRIOR, VK_NEXT = 0x11, 0x21, 0x22
WAIT_FOR_NEW_TAB = 4.0
WAIT_FOR_OURS = 1.5


class _Real:
    """The window in front, and key presses, through Windows' own user32."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        u = ctypes.WinDLL("user32", use_last_error=True)
        u.GetForegroundWindow.restype = wintypes.HWND
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.u = u
        pointer_sized = ctypes.c_size_t

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", pointer_sized)]

        class MOUSEINPUT(ctypes.Structure):          # only for the size Windows expects of the whole
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", pointer_sized)]

        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

        class INPUT(ctypes.Structure):
            _anonymous_ = ("u",)
            _fields_ = [("type", wintypes.DWORD), ("u", _U)]

        self.INPUT, self.KEYBDINPUT = INPUT, KEYBDINPUT
        u.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        u.SendInput.restype = wintypes.UINT

    def _text(self, fn) -> str:
        hwnd = self.u.GetForegroundWindow()
        if not hwnd:
            return ""
        buf = self.ctypes.create_unicode_buffer(1024)
        fn(hwnd, buf, 1024)
        return buf.value

    def title(self) -> str:
        return self._text(self.u.GetWindowTextW)

    def kind(self) -> str:
        return self._text(self.u.GetClassNameW)

    def press(self, *keys: int) -> bool:
        """The keys down in the order given, then up again in the other order."""
        steps = [(k, 0) for k in keys] + [(k, 2) for k in reversed(keys)]            # 2: the key goes up
        arr = (self.INPUT * len(steps))()
        for i, (vk, flags) in enumerate(steps):
            arr[i].type = 1                                                           # a key of the keyboard
            arr[i].ki = self.KEYBDINPUT(vk, 0, flags | (1 if vk in (VK_PRIOR, VK_NEXT) else 0), 0, 0)    # 1: a key of the extended block
        return self.u.SendInput(len(steps), arr, self.ctypes.sizeof(self.INPUT)) == len(steps)


def _windows():
    if os.name != "nt":
        return None
    try:
        return _Real()
    except Exception as e:                      # nothing of this is worth failing for
        log.warn("the window in front could not be asked about: %s", logbook.why(e))
        return None


def back(win=None, sleep=time.sleep, clock=time.monotonic) -> dict:
    """Takes the browser back to ModTrap's tab once a new tab has come to the front. {"back": True} when ModTrap's
    tab is in front at the end, else {"back": False, "why": …}."""
    win = win if win is not None else _windows()
    if win is None:
        return {"back": False, "why": "this is done on Windows only"}
    end = clock() + WAIT_FOR_NEW_TAB
    while True:
        title = win.title()
        if title and not OURS.match(title):
            break
        if clock() > end:
            return {"back": True, "why": "ModTrap's tab stayed in front"}
        sleep(0.05)
    if win.kind() not in BROWSERS:
        return {"back": False, "why": "the window in front is not a browser's"}
    sleep(0.15)                                 # the new tab has taken the front: let it settle
    if not win.press(VK_CONTROL, VK_PRIOR):
        return {"back": False, "why": "Windows did not take the key press"}
    end = clock() + WAIT_FOR_OURS
    while clock() < end:
        if OURS.match(win.title()):
            return {"back": True, "why": ""}
        sleep(0.05)
    # The tab before the new one was not ModTrap's: back to where the browser was, and no more.
    if win.kind() in BROWSERS:
        win.press(VK_CONTROL, VK_NEXT)
    return {"back": False, "why": "the tab before the new one was not ModTrap's"}


__all__ = ["back", "OURS", "BROWSERS"]
