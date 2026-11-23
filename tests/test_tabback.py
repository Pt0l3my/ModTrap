"""Back to ModTrap's tab (MT52), with a stand-in for the window in front."""

import unittest

from modtrap import tabback


class FakeWindows:
    """A browser with tabs: `tabs` are their titles, `at` the one in front; a key press moves by one."""

    def __init__(self, tabs, at, kind="MozillaWindowClass", suffix=" — Mozilla Firefox", takes_keys=True):
        self.tabs, self.at, self._kind, self.suffix, self.takes_keys = tabs, at, kind, suffix, takes_keys
        self.pressed = []

    def title(self):
        return self.tabs[self.at] + self.suffix

    def kind(self):
        return self._kind

    def press(self, *keys):
        self.pressed.append(keys)
        if not self.takes_keys:
            return False
        if keys == (tabback.VK_CONTROL, tabback.VK_PRIOR):
            self.at = (self.at - 1) % len(self.tabs)
        elif keys == (tabback.VK_CONTROL, tabback.VK_NEXT):
            self.at = (self.at + 1) % len(self.tabs)
        return True


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.now += s


class BackToModTrapsTab(unittest.TestCase):
    def back(self, win):
        c = Clock()
        return tabback.back(win, sleep=c.sleep, clock=c)

    def test_the_new_tab_in_front_is_left_for_modtraps_with_one_key(self):
        win = FakeWindows(["Some site", "ModTrap", "A mod at Nexus Mods"], 2)
        self.assertEqual(self.back(win), {"back": True, "why": ""})
        self.assertEqual((win.at, win.pressed), (1, [(tabback.VK_CONTROL, tabback.VK_PRIOR)]))
        for suffix, kind in ((" - Google Chrome", "Chrome_WidgetWin_1"), (" and 3 more pages - Personal - Microsoft Edge", "Chrome_WidgetWin_1")):
            win = FakeWindows(["ModTrap", "A mod at Nexus Mods"], 1, kind=kind, suffix=suffix)
            self.assertTrue(self.back(win)["back"], suffix)

    def test_nothing_is_pressed_where_modtraps_tab_stayed_in_front(self):
        win = FakeWindows(["ModTrap", "A mod at Nexus Mods"], 0)
        self.assertEqual(self.back(win), {"back": True, "why": "ModTrap's tab stayed in front"})
        self.assertEqual(win.pressed, [])

    def test_nothing_is_pressed_in_a_window_that_is_no_browsers(self):
        win = FakeWindows(["A document"], 0, kind="Notepad", suffix=" - Notepad")
        self.assertEqual(self.back(win), {"back": False, "why": "the window in front is not a browser's"})
        self.assertEqual(win.pressed, [])

    def test_where_the_tab_before_was_not_modtraps_the_browser_is_put_back(self):
        win = FakeWindows(["ModTrap", "Some site", "A mod at Nexus Mods"], 2)            # the new tab opened at the far end
        self.assertEqual(self.back(win), {"back": False, "why": "the tab before the new one was not ModTrap's"})
        self.assertEqual(win.at, 2)                                                      # back on the new tab, as the browser was
        self.assertEqual(win.pressed, [(tabback.VK_CONTROL, tabback.VK_PRIOR), (tabback.VK_CONTROL, tabback.VK_NEXT)])

    def test_a_page_whose_title_only_begins_like_modtraps_is_not_taken_for_it(self):
        self.assertIsNone(tabback.OURS.match("ModTrapper's guide — Mozilla Firefox"))
        self.assertIsNone(tabback.OURS.match("Opening the mod's page… — Mozilla Firefox"))
        self.assertIsNotNone(tabback.OURS.match("ModTrap"))
        self.assertIsNotNone(tabback.OURS.match("ModTrap — Mozilla Firefox Private Browsing"))

    def test_elsewhere_than_windows_nothing_is_done(self):
        self.assertEqual(tabback.back()["back"], False)

    def test_windows_not_taking_the_key_is_said(self):
        win = FakeWindows(["ModTrap", "A mod at Nexus Mods"], 1, takes_keys=False)
        self.assertEqual(self.back(win), {"back": False, "why": "Windows did not take the key press"})


if __name__ == "__main__":
    unittest.main()
