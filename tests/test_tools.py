import unittest

from modtrap import tools


class ToolTests(unittest.TestCase):
    def names(self, *a, **k):
        return [(e.tool, e.kind, e.strong) for e in tools.identify(*a, **k)]

    def test_marks_and_names(self):
        self.assertEqual(self.names("Whatever.esp", "BASHED PATCH", "A Mod", {}), [("Wrye Bash", "patcher", True)])
        self.assertEqual(self.names("Bashed Patch, 0.esp", "", "A Mod", {}), [("Wrye Bash", "patcher", True)])
        self.assertEqual(self.names("PG_12.esp", "", "A Mod", {}), [("ParallaxGen (PGPatcher)", "generator", True)])
        self.assertEqual(self.names("Synthesis.esp", "", "A Mod", {}), [("Synthesis", "patcher", True)])
        self.assertEqual(self.names("Synthesis Invented Group.esp", "", "A Mod", {}), [("Synthesis", "patcher", False)])
        self.assertEqual(self.names("DynDOLOD.esm", "", "A Mod", {}), [("DynDOLOD", "generator", True)])
        self.assertEqual(self.names("Invented.esp", "someone", "A Mod", {}), [])

    def test_mo2s_own_record_comes_first_and_names_the_tool(self):
        out = {"xEdit64": "Editor Output", "xEdit QAC": "Editor Output", "Invented Patcher": "Tool Output"}
        binaries = {"xEdit64": "C:/Tools/SSEEdit64.exe", "xEdit QAC": "C:/Tools/SSEEditQuickAutoClean.exe"}
        ev = tools.identify("Invented.esp", "", "editor output", out, binaries)
        self.assertEqual([(e.tool, e.kind) for e in ev], [("xEdit", "editor")])          # two entries, one tool
        self.assertIn("MO2 sends the new files", ev[0].how)
        self.assertEqual(self.names("Invented.esp", "", "Tool Output", out), [("Invented Patcher", "tool", True)])

    def test_what_follows(self):
        p = lambda *a, **k: tools.proposal(tools.identify(*a, **k))   # noqa: E731
        self.assertEqual(p("Bashed Patch, 0.esp", "BASHED PATCH", "x", {}), "run the tool again")
        self.assertEqual(p("Synthesis Invented Group.esp", "", "x", {}), "probably run the tool again")
        self.assertEqual(p("Invented.esp", "", "Editor Output", {"xEdit64": "Editor Output"}), "demaster")
        self.assertEqual(p("Invented.esp", "", "Tool Output", {"Invented Patcher": "Tool Output"}), "run the tool again")
        self.assertEqual(p("Invented.esp", "", "x", {}), "demaster")

    def test_every_entry_says_where_it_comes_from(self):
        for t in tools.load():
            self.assertTrue(t.get("source", "").startswith("TL01"), t["tool"])
            self.assertIn(t["kind"], ("patcher", "generator", "editor"))
            self.assertTrue(t.get("label"))


if __name__ == "__main__":
    unittest.main()
