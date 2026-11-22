"""Pressing one button in another program's window, through Windows' own interface for assistive tools (WHY§93).

Some tools have no switch to do their work unasked, only a button (TL01§21). A window drawn the modern way has no
handle for its buttons, so the messages ModTrap sends xEdit do not reach it (XE01§13); what does is UI Automation,
the interface screen readers use. This file speaks it with nothing but Python's own ctypes.

It is a program of its own, started by ModTrap for one press and ending after it, because a mistake in talking to
that interface would end the process that made it: this one, not ModTrap. Before it presses anything it checks
itself against what it can know another way: the window's process is the one asked for, the window is a window,
and exactly one button with the asked-for name stands outside a list. Anything else, and it presses nothing and
says why.

    python uia.py press IMAGE AUTOMATION_ID

prints one line of JSON: {"pressed": bool, "enabled": bool or null, "candidates": int, "why": str}.
The button must be enabled; a disabled one is the tool saying it is not ready, and is left alone.
"""

from __future__ import annotations

import json
import os
import sys

CONTROL_BUTTON, CONTROL_LIST_ITEM, CONTROL_WINDOW = 50000, 50007, 50032
PATTERN_INVOKE = 10000
SCOPE_DESCENDANTS = 4
ELEMENTS_MAX = 20000
PARENTS_MAX = 60


def press(image: str, automation_id: str) -> dict:
    out = {"pressed": False, "enabled": None, "candidates": 0, "why": ""}
    if os.name != "nt":
        out["why"] = "not Windows"
        return out
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32")
    oleaut32 = ctypes.WinDLL("oleaut32")

    class GUID(ctypes.Structure):
        _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

    def guid(text: str) -> GUID:
        g = GUID()
        if ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(g)) != 0:
            raise OSError("a GUID could not be read")
        return g

    ole32.CLSIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]
    ole32.CLSIDFromString.restype = ctypes.c_long
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(GUID),
                                       ctypes.POINTER(ctypes.c_void_p)]
    ole32.CoCreateInstance.restype = ctypes.c_long
    oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
    oleaut32.SysFreeString.restype = None

    def method(obj: ctypes.c_void_p, index: int, *argtypes):
        """The method at `index` of a COM object's table, as a callable that returns the HRESULT."""
        table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(table[index])

    def ok(hr: int) -> bool:
        return hr >= 0

    def release(obj) -> None:
        if obj:
            method(obj, 2)(obj)

    # --- the window of the program asked for ---------------------------------------------------------------------
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    found: list[tuple[int, int]] = []
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def each(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.GetWindowTextLengthW(hwnd) <= 0:
            return True
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(0x1000, False, pid.value)          # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return True
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                if os.path.basename(buf.value).casefold() == image.casefold():
                    found.append((int(hwnd), int(pid.value)))
        finally:
            kernel32.CloseHandle(handle)
        return True

    keep = callback(each)
    user32.EnumWindows.argtypes = [callback, wintypes.LPARAM]
    user32.EnumWindows(keep, 0)
    if not found:
        out["why"] = "no window of %s is open" % image
        return out

    # --- UI Automation ----------------------------------------------------------------------------------------------
    hr = ole32.CoInitializeEx(None, 0)
    if not ok(hr) and hr != -2147417850:                                  # RPC_E_CHANGED_MODE: already set up otherwise
        out["why"] = "COM could not be set up"
        return out
    automation = ctypes.c_void_p()
    clsid, iid = guid("{ff48dba4-60ef-4201-aa87-54103eef594e}"), guid("{30cbe57d-d9d0-452a-ab13-7ac5ac4825ee}")
    if not ok(ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(automation))) or not automation:
        out["why"] = "UI Automation is not there on this PC"
        return out
    PV = ctypes.POINTER(ctypes.c_void_p)

    def number(el, index: int) -> int | None:
        value = ctypes.c_int(0)
        return value.value if ok(method(el, index, ctypes.POINTER(ctypes.c_int))(el, ctypes.byref(value))) else None

    def words(el, index: int) -> str | None:
        b = ctypes.c_void_p()
        if not ok(method(el, index, PV)(el, ctypes.byref(b))):
            return None
        try:
            return ctypes.wstring_at(b.value) if b.value else ""
        finally:
            if b:
                oleaut32.SysFreeString(b)

    # IUIAutomationElement: 6 FindAll, 16 GetCurrentPattern, 20 process id, 21 control type, 28 is enabled,
    # 29 automation id. IUIAutomation: 6 ElementFromHandle, 14 control view walker, 21 CreateTrueCondition.
    # IUIAutomationElementArray: 3 length, 4 element. IUIAutomationTreeWalker: 3 parent. Invoke pattern: 3 Invoke.
    condition, walker = ctypes.c_void_p(), ctypes.c_void_p()
    if not ok(method(automation, 21, PV)(automation, ctypes.byref(condition))) or not condition:
        out["why"] = "UI Automation gave no condition"
        return out
    if not ok(method(automation, 14, PV)(automation, ctypes.byref(walker))) or not walker:
        out["why"] = "UI Automation gave no way to walk a window"
        return out

    mains: list = []
    for hwnd, pid in found:
        window = ctypes.c_void_p()
        if not ok(method(automation, 6, wintypes.HWND, PV)(automation, hwnd, ctypes.byref(window))) or not window:
            continue
        # The check of this program against itself: what it reads here must be what the window system said.
        if number(window, 20) != pid or number(window, 21) != CONTROL_WINDOW:
            out["why"] = "what UI Automation says of the window does not match the window: nothing was pressed"
            return out
        array = ctypes.c_void_p()
        if not ok(method(window, 6, ctypes.c_int, ctypes.c_void_p, PV)(window, SCOPE_DESCENDANTS, condition, ctypes.byref(array))) or not array:
            continue
        count = number(array, 3) or 0
        for i in range(min(count, ELEMENTS_MAX)):
            el = ctypes.c_void_p()
            if not ok(method(array, 4, ctypes.c_int, PV)(array, i, ctypes.byref(el))) or not el:
                continue
            if words(el, 29) != automation_id or number(el, 21) != CONTROL_BUTTON:
                release(el)
                continue
            out["candidates"] += 1
            # A button of that name inside a list belongs to one row of it (one group of patchers), not to the whole.
            in_list, at, steps = False, el, 0
            while steps < PARENTS_MAX:
                parent = ctypes.c_void_p()
                if not ok(method(walker, 3, ctypes.c_void_p, PV)(walker, at, ctypes.byref(parent))) or not parent:
                    break
                steps += 1
                kind = number(parent, 21)
                if at is not el:
                    release(at)
                at = parent
                if kind == CONTROL_LIST_ITEM:
                    in_list = True
                    break
                if kind == CONTROL_WINDOW:
                    break
            if at is not el:
                release(at)
            if in_list:
                release(el)
            else:
                mains.append(el)
    if len(mains) != 1:
        out["why"] = ("no button called %s stands outside a list in the window" % automation_id if not mains else
                      "%d buttons called %s stand outside a list: ModTrap cannot tell which is meant" % (len(mains), automation_id))
        return out
    button = mains[0]
    enabled = number(button, 28)
    out["enabled"] = bool(enabled) if enabled is not None else None
    if not enabled:
        out["why"] = "the button is there and greyed: the program is not ready to run"
        return out
    pattern = ctypes.c_void_p()
    if not ok(method(button, 16, ctypes.c_int, PV)(button, PATTERN_INVOKE, ctypes.byref(pattern))) or not pattern:
        out["why"] = "the button cannot be pressed through UI Automation"
        return out
    invoke = ctypes.c_void_p()
    iid_invoke = guid("{fb377fbe-8ea6-46d5-9c73-6499642d3059}")
    if not ok(method(pattern, 0, ctypes.POINTER(GUID), PV)(pattern, ctypes.byref(iid_invoke), ctypes.byref(invoke))) or not invoke:
        out["why"] = "the button's way of being pressed is not the one expected"
        return out
    if not ok(method(invoke, 3)(invoke)):
        out["why"] = "the press was refused"
        return out
    out["pressed"] = True
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[1] != "press":
        print(json.dumps({"pressed": False, "enabled": None, "candidates": 0, "why": "asked for the wrong way"}))
        return 2
    try:
        got = press(argv[2], argv[3])
    except Exception as e:                                               # never the text of an error: it may hold paths
        got = {"pressed": False, "enabled": None, "candidates": 0, "why": "an error inside the helper: " + type(e).__name__}
    print(json.dumps(got))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
