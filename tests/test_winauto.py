"""Pressing OK in xEdit's "Module Selection" window (XE01§13): only that window, of that program, and only its OK."""

from __future__ import annotations

import unittest

from modtrap import dryrun, winauto


class FakeWindows(winauto.Windows):
    """Windows as a table: handle -> (class, text, visible, enabled, program, children)."""

    def __init__(self, table: dict) -> None:
        self.table, self.clicked = table, []

    def top_windows(self):
        return [h for h, w in self.table.items() if w.get("top")]

    def children(self, hwnd):
        return self.table[hwnd].get("children", [])

    def class_name(self, hwnd):
        return self.table[hwnd]["cls"]

    def text(self, hwnd):
        return self.table[hwnd]["text"]

    def visible(self, hwnd):
        return self.table[hwnd].get("visible", True)

    def enabled(self, hwnd):
        return self.table[hwnd].get("enabled", True)

    def program_of(self, hwnd):
        return self.table[hwnd].get("program", "")

    def click(self, hwnd):
        self.clicked.append(hwnd)
        return True

    def close(self, hwnd):
        self.clicked.append(("close", hwnd))
        return True


def desk(**changes) -> FakeWindows:
    t = {
        1: {"top": True, "cls": "TfrmMain", "text": "SSEScript 4.1.5f x64", "program": "SSEEdit64.exe", "children": []},
        2: {"top": True, "cls": "TfrmModuleSelect", "text": "Module Selection", "program": "SSEEdit64.exe", "children": [21, 22, 23]},
        21: {"cls": "TEdit", "text": "OK"},
        22: {"cls": "TButton", "text": "Cancel"},
        23: {"cls": "TButton", "text": "OK"},
        3: {"top": True, "cls": "TfrmModuleSelect", "text": "Module Selection", "program": "SomethingElse.exe", "children": [31]},
        31: {"cls": "TButton", "text": "OK"},
        4: {"top": True, "cls": "#32770", "text": "Module Selection", "program": "SSEEdit64.exe", "children": [41]},
        41: {"cls": "Button", "text": "OK"},
    }
    for h, vals in changes.items():
        t[int(h[1:])].update(vals)
    return FakeWindows(t)


class Pressing(unittest.TestCase):
    def test_only_the_ok_of_xedits_own_module_selection_window_is_pressed(self) -> None:
        w = desk()
        self.assertTrue(winauto.press_module_selection_ok("sseedit64.exe", w, settle=0))
        self.assertEqual(w.clicked, [23])

    def test_the_window_is_pressed_only_once_it_has_stood_ready_a_moment(self) -> None:
        """WHY§72: a press the moment the window appears reaches xEdit while it still sets the window up."""
        w, now = desk(), [100.0]
        look = lambda: winauto.press_module_selection_ok("SSEEdit64.exe", w, settle=2.5, clock=lambda: now[0])
        self.assertFalse(look())                                  # seen ready for the first time: not yet
        now[0] += 1.5
        self.assertFalse(look())
        self.assertEqual(w.clicked, [])
        now[0] += 1.5
        self.assertTrue(look())                                   # ready for three seconds: pressed
        self.assertEqual(w.clicked, [23])
        # A window that was ready, then was not (still filling), starts the wait over.
        w2 = desk()
        look2 = lambda: winauto.press_module_selection_ok("SSEEdit64.exe", w2, settle=2.5, clock=lambda: now[0])
        self.assertFalse(look2())
        w2.table[23]["enabled"] = False
        now[0] += 3
        self.assertFalse(look2())
        w2.table[23]["enabled"] = True
        self.assertFalse(look2())
        now[0] += 3
        self.assertTrue(look2())

    def test_no_such_window_or_not_ready_presses_nothing(self) -> None:
        for change in ({"h2": {"visible": False}}, {"h2": {"text": "Something Else"}}, {"h2": {"program": "Other.exe"}},
                       {"h23": {"enabled": False}}, {"h23": {"text": "Load"}}, {"h2": {"cls": "TfrmOther"}}):
            w = desk(**change)
            self.assertFalse(winauto.press_module_selection_ok("SSEEdit64.exe", w), change)
            self.assertEqual(w.clicked, [], change)

    def test_only_the_programs_own_message_is_closed(self) -> None:
        w = FakeWindows({
            1: {"top": True, "cls": "Qt", "text": "Invented List - Mod Organizer v2", "program": "ModOrganizer.exe"},
            2: {"top": True, "cls": "Qt", "text": "Mod Organizer", "program": "ModOrganizer.exe"},
            3: {"top": True, "cls": "Qt", "text": "Mod Organizer", "program": "ModOrganizer.exe", "visible": False},
            4: {"top": True, "cls": "X", "text": "Mod Organizer", "program": "Notes.exe"},
        })
        self.assertTrue(winauto.close_message("modorganizer.exe", win=w))
        self.assertEqual(w.clicked, [("close", 2)])              # not MO2's main window, not another program's
        self.assertFalse(winauto.close_message("Other.exe", win=w))
        self.assertFalse(winauto.close_message("ModOrganizer.exe"))          # off Windows: nothing

    def test_off_windows_it_does_nothing(self) -> None:
        self.assertFalse(winauto.press_module_selection_ok("SSEEdit64.exe"))

    def test_a_run_looks_every_few_seconds_and_stops_after_a_few_presses(self) -> None:
        calls = []
        p = dryrun.OkPresser("SSEEdit64.exe", lambda image: calls.append(image) or True)
        p.look()
        p.look()                                        # too soon: not looked again
        self.assertEqual((len(calls), p.pressed), (1, 1))
        for _ in range(20):
            p._next = 0
            p.look()
        self.assertEqual(p.pressed, dryrun.PRESS_LIMIT)
        broken = dryrun.OkPresser("SSEEdit64.exe", lambda image: 1 / 0)
        broken.look()                                   # a failure in the pressing never stops a run
        self.assertEqual(broken.pressed, 0)


if __name__ == "__main__":
    unittest.main()
