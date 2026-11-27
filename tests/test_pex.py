"""A compiled script read for what it declares and calls (WHY§146), on invented scripts."""

import unittest

from modtrap import evaluate, pex
from tests import _fixtures as fx
from tests._pex import script

import tempfile
from pathlib import Path


class Reading(unittest.TestCase):
    def test_a_script_says_what_it_declares_and_what_it_calls(self):
        got = pex.read(script("FrostUtil", natives=("ReadIni", "Blend")))
        self.assertEqual((got["name"], got["natives"], got["calls"]), ("FrostUtil", {"readini", "blend"}, set()))
        got = pex.read(script("FrostQuest", calls=(("FrostUtil", "ReadIni"), ("Game", "GetPlayer")), methods=("RegisterForUpdate",)))
        self.assertEqual((got["name"], got["natives"], got["methods"]), ("FrostQuest", set(), {"registerforupdate"}))
        self.assertEqual(got["calls"], {("frostutil", "readini"), ("game", "getplayer")})
        self.assertIn("frostutil", got["names"])
        for big in (True, False):                                # the older and the newer game write the numbers in opposite order
            for debug in (True, False):
                self.assertEqual(pex.read(script("A", natives=("F",), big=big, debug=debug))["natives"], {"f"})

    def test_what_is_not_a_script_or_is_cut_short_is_none(self):
        whole = script("FrostQuest", calls=(("FrostUtil", "ReadIni"),))
        self.assertIsNone(pex.read(b""))
        self.assertIsNone(pex.read(b"not a script at all, only words"))
        self.assertIsNone(pex.read(whole + b"\0"))
        for n in range(4, len(whole), 7):
            self.assertIsNone(pex.read(whole[:n]), n)
        self.assertIsNone(pex.read(whole[:-12] + b"\xff" * 12))


class APluginsUse(unittest.TestCase):
    """Whether the scripts beside a script extender plugin still call it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dll = b"MZ..SKSEPlugin_Query\0....\0FrostUtil\0ReadIni\0Blend\0...."

    def put(self, where: str, files: dict) -> dict:
        out = {}
        for name, data in files.items():
            fx.write(self.root / where / name, data)
            out[name.lower()] = self.root / where / name
        return out

    def rows(self, own: dict, fix: dict | None = None, by: str = "Frost Fixes") -> list:
        fix = fix or {}
        return [(f, p, fix.get(f, p), by if f in fix else "") for f, p in own.items()]

    def own(self) -> dict:
        return self.put("mod", {"scripts/FrostUtil.pex": script("FrostUtil", natives=("ReadIni", "Blend")),
                                "scripts/FrostQuest.pex": script("FrostQuest", calls=(("FrostUtil", "ReadIni"),)),
                                "scripts/FrostAlias.pex": script("FrostAlias", calls=(("frostutil", "BLEND"),)),
                                "scripts/FrostMenu.pex": script("FrostMenu", calls=(("Game", "GetPlayer"),))})

    def test_the_mods_own_scripts_call_it(self):
        use = evaluate.plugin_use(self.dll, self.rows(self.own()))
        self.assertEqual((use["scripts"], use["own"], use["now"], use["by"], use["taken_over"]), (["frostutil"], ["frostalias", "frostquest"], ["frostalias", "frostquest"], [], False))
        self.assertEqual(evaluate.use_told(use), "still called by 2 scripts: frostalias, frostquest")

    def test_a_fix_that_replaces_every_caller(self):
        own = self.own()
        fix = self.put("fix", {"scripts/FrostQuest.pex": script("FrostQuest", calls=(("Utility", "Wait"),)), "scripts/FrostAlias.pex": script("FrostAlias")})
        use = evaluate.plugin_use(self.dll, self.rows(own, fix))
        self.assertEqual((use["own"], use["now"], use["by"]), (["frostalias", "frostquest"], [], ["Frost Fixes"]))
        self.assertEqual(evaluate.use_told(use), "the 2 scripts that called it (frostalias, frostquest) are replaced by “Frost Fixes”, and none calls it now")

    def test_a_fix_that_replaces_only_some_callers_or_cannot_be_read(self):
        own = self.own()
        fix = self.put("fix", {"scripts/FrostQuest.pex": script("FrostQuest")})
        self.assertEqual(evaluate.plugin_use(self.dll, self.rows(own, fix))["now"], ["frostalias"])
        fix = self.put("fix2", {"scripts/FrostQuest.pex": script("FrostQuest"), "scripts/FrostAlias.pex": b"not a script"})
        self.assertEqual(evaluate.plugin_use(self.dll, self.rows(own, fix))["now"], ["frostalias"])      # unread: taken as calling still

    def test_a_fix_that_does_the_plugins_work_in_a_script(self):
        own = self.own()
        fix = self.put("fix", {"scripts/FrostUtil.pex": script("FrostUtil", calls=(("Utility", "Wait"),))})
        use = evaluate.plugin_use(self.dll, self.rows(own, fix))
        self.assertEqual((use["now"], use["by"], use["taken_over"]), ([], ["Frost Fixes"], True))
        self.assertIn("which “Frost Fixes” replaces with a script that does the work itself", evaluate.use_told(use))
        half = self.put("half", {"scripts/FrostUtil.pex": script("FrostUtil", natives=("Blend",))})     # one function still the plugin's
        use = evaluate.plugin_use(self.dll, self.rows(own, half))
        self.assertEqual((use["now"], use["taken_over"]), (["frostalias"], False))

    def test_scripts_that_do_not_say_what_the_plugin_is_for(self):
        own = self.put("mod", {"scripts/Other.pex": script("Other", natives=("Thing",)), "scripts/FrostQuest.pex": script("FrostQuest", calls=(("Other", "Thing"),))})
        self.assertIsNone(evaluate.plugin_use(self.dll, self.rows(own)))                               # the plugin does not name that script
        self.assertIsNone(evaluate.plugin_use(self.dll, []))
        self.assertIsNone(evaluate.plugin_use(b"MZ..\0FrostUtil\0", self.rows(self.own())))             # nor any function of it


if __name__ == "__main__":
    unittest.main()
