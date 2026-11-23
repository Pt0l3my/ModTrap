"""ModTrap's console window on Windows (MT63).

ModTrap's program writes what it does to a console. Every line of it is on the page too (History, then Log), and
nothing ModTrap does needs the window: so, where the console is ModTrap's own, it is hidden. It stays there, hidden,
because the programs ModTrap starts (7-Zip, tar, its own helper) are console programs and write to the console of
whoever started them: without one, each would open a window of its own.

Whose console it is: ModTrap's own when its launcher made it (the launcher says so, with `--own-console`) or when
this program is the only one in it. A console ModTrap was started in from a command prompt is the owner's, and is
never hidden.

The setting "Show ModTrap's console window" brings it back, minimised. A start that fails shows it, with what went
wrong, and waits for a key.
"""

from __future__ import annotations

import sys

HIDE, NORMAL, MINIMISED = 0, 1, 7           # ShowWindow's SW_HIDE, SW_SHOWNORMAL, SW_SHOWMINNOACTIVE
SWITCH = "--own-console"


def own(argv: list[str]) -> bool:
    """Is the console this program writes to ModTrap's own?"""
    if sys.platform != "win32":
        return False
    if SWITCH in argv:
        return True
    try:
        import ctypes
        seen = (ctypes.c_uint32 * 4)()
        return ctypes.windll.kernel32.GetConsoleProcessList(seen, 4) == 1
    except (OSError, AttributeError, ValueError):
        return False


def show(how: int) -> bool:
    """Shows the console window as `how` says (HIDE, NORMAL, MINIMISED). False where there is none to show."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        kernel, user = ctypes.windll.kernel32, ctypes.windll.user32
        kernel.GetConsoleWindow.restype = ctypes.c_void_p
        user.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        window = kernel.GetConsoleWindow()
        if not window:
            return False
        user.ShowWindow(window, how)
        return True
    except (OSError, AttributeError, ValueError):
        return False


def stay(words: str = "") -> None:
    """A start that went wrong in a console of ModTrap's own: the window is shown and waits for a key, so that what
    it says can be read."""
    show(NORMAL)
    try:
        if words:
            print(words, file=sys.stderr, flush=True)
        input("\nPress Enter to close this window. ")
    except (EOFError, OSError, RuntimeError, KeyboardInterrupt):
        pass


__all__ = ["HIDE", "MINIMISED", "NORMAL", "SWITCH", "own", "show", "stay"]
