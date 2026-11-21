"""A mod's installer file (MO02, DESIGN§16.1): read, answered, and built into a mod's folder. The installer below
is invented."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modtrap import fomod

from ._fixtures import write

XML = """<?xml version="1.0" encoding="utf-8"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <moduleName>Heather</moduleName>
  <requiredInstallFiles>
    <file source="Core\\Heather.esp" destination="Heather.esp"/>
    <folder source="Core\\textures" destination="textures"/>
  </requiredInstallFiles>
  <installSteps order="Explicit">
    <installStep name="Colour">
      <optionalFileGroups order="Explicit">
        <group name="Pick a colour" type="SelectExactlyOne">
          <plugins order="Explicit">
            <plugin name="Purple">
              <description>The purple set.</description>
              <files><folder source="Purple" destination="" priority="1"/></files>
              <conditionFlags><flag name="colour">purple</flag></conditionFlags>
              <typeDescriptor><type name="Recommended"/></typeDescriptor>
            </plugin>
            <plugin name="White">
              <description>The white set.</description>
              <files><folder source="White" destination=""/></files>
              <conditionFlags><flag name="colour">white</flag></conditionFlags>
              <typeDescriptor><type name="Optional"/></typeDescriptor>
            </plugin>
          </plugins>
        </group>
        <group name="Extras" type="SelectAny">
          <plugins order="Ascending">
            <plugin name="Zebra patch">
              <description/>
              <files><file source="Patches\\Zebra.esp" destination=""/></files>
              <typeDescriptor><dependencyType><defaultType name="NotUsable"/>
                <patterns><pattern><dependencies><fileDependency file="Zebra.esp" state="Active"/></dependencies>
                  <type name="Recommended"/></pattern></patterns></dependencyType></typeDescriptor>
            </plugin>
            <plugin name="Bright">
              <description>Brighter.</description>
              <files><file source="Extras\\bright.dds" destination="textures\\heather\\"/></files>
              <typeDescriptor><type name="Optional"/></typeDescriptor>
            </plugin>
          </plugins>
        </group>
      </optionalFileGroups>
    </installStep>
    <installStep name="For white only">
      <visible><flagDependency flag="colour" value="white"/></visible>
      <optionalFileGroups>
        <group name="Snow" type="SelectAtMostOne">
          <plugins><plugin name="Snowy"><description/><files><file source="Extras\\snow.dds"/></files>
            <typeDescriptor><type name="Optional"/></typeDescriptor></plugin></plugins>
        </group>
      </optionalFileGroups>
    </installStep>
  </installSteps>
  <conditionalFileInstalls><patterns>
    <pattern><dependencies operator="And"><flagDependency flag="colour" value="purple"/></dependencies>
      <files><file source="Extras\\purple-note.txt" destination="note.txt" priority="5"/></files></pattern>
  </patterns></conditionalFileInstalls>
</config>
"""


def archive(root: Path, xml: str | bytes = XML) -> Path:
    write(root / "fomod" / "ModuleConfig.xml", xml)
    for name, data in {"Core/Heather.esp": b"core", "Core/textures/heather/base.dds": b"base",
                       "Purple/textures/heather/base.dds": b"purple", "White/textures/heather/base.dds": b"white",
                       "Patches/Zebra.esp": b"zebra", "Extras/bright.dds": b"bright", "Extras/snow.dds": b"snow",
                       "Extras/purple-note.txt": b"note"}.items():
        write(root / name, data)
    return root


def nothing_active(name: str) -> str:
    return "Missing"


class Reading(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = archive(Path(self.tmp.name) / "a")
        self.inst = fomod.read(fomod.find(self.root))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_the_questions_are_read_in_the_order_the_file_asks_for(self) -> None:
        self.assertEqual(self.inst.name, "Heather")
        self.assertEqual([s.name for s in self.inst.steps], ["Colour", "For white only"])
        self.assertEqual([g.name for g in self.inst.steps[0].groups], ["Pick a colour", "Extras"])
        self.assertEqual([o.name for o in self.inst.steps[0].groups[1].options], ["Bright", "Zebra patch"])   # by name
        self.assertEqual([(f.source, f.destination, f.folder) for f in self.inst.required],
                         [("Core\\Heather.esp", "Heather.esp", False), ("Core\\textures", "textures", True)])

    def test_the_file_is_found_whatever_its_case_and_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = write(Path(d) / "FOMod" / "moduleconfig.XML", XML.replace("utf-8", "utf-16").encode("utf-16"))
            self.assertEqual(fomod.find(Path(d)), p)
            self.assertEqual(fomod.read(p).name, "Heather")
            wrong = write(Path(d) / "x" / "fomod" / "ModuleConfig.xml", XML.replace("utf-8", "utf-16").encode("latin-1"))
            self.assertEqual(fomod.read(wrong).name, "Heather")          # a header that names the wrong encoding

    def test_a_file_with_its_own_document_rules_is_refused(self) -> None:
        bomb = '<?xml version="1.0"?><!DOCTYPE config [<!ENTITY a "aaaa">]><config><moduleName>&a;</moduleName></config>'
        with tempfile.TemporaryDirectory() as d:
            for data in (bomb.encode(), bomb.encode("utf-16")):
                with self.assertRaises(fomod.Unreadable):
                    fomod.read(write(Path(d) / "ModuleConfig.xml", data))
            with self.assertRaises(fomod.Unreadable):
                fomod.read(write(Path(d) / "ModuleConfig.xml", b"<notconfig/>"))
            with self.assertRaises(fomod.Unreadable):
                fomod.read(write(Path(d) / "ModuleConfig.xml", b"not xml at all"))

    # --- answering ------------------------------------------------------------------------------------------------

    def chosen(self, v: dict) -> dict:
        return {g["key"]: [o["name"] for o in g["options"] if o["chosen"]] for s in v["steps"] for g in s["groups"]}

    def test_with_no_answers_the_recommended_options_are_chosen(self) -> None:
        v = fomod.view(self.inst, {}, nothing_active)
        self.assertEqual(self.chosen(v), {"0.0": ["Purple"], "0.1": []})
        self.assertEqual([s["name"] for s in v["steps"]], ["Colour"])            # the white-only step does not show
        self.assertEqual(v["problems"], [])

    def test_an_answer_shows_the_step_that_depends_on_it(self) -> None:
        v = fomod.view(self.inst, {"0.0": [1]}, nothing_active)
        self.assertEqual([s["name"] for s in v["steps"]], ["Colour", "For white only"])
        self.assertEqual(self.chosen(v)["1.0"], [])
        self.assertTrue(v["steps"][1]["groups"][0]["none_allowed"])

    def test_one_of_a_kind_groups_take_one_answer(self) -> None:
        v = fomod.view(self.inst, {"0.0": [1, 0]}, nothing_active)
        self.assertEqual(self.chosen(v)["0.0"], ["White"])
        v = fomod.view(self.inst, {"0.0": []}, nothing_active)                   # none given: one is chosen for it
        self.assertEqual(self.chosen(v)["0.0"], ["White"])                       # the first that is merely optional
        v = fomod.view(self.inst, {"0.0": [7, "x", -1]}, nothing_active)
        self.assertEqual(len(self.chosen(v)["0.0"]), 1)

    def test_an_option_depends_on_the_load_order(self) -> None:
        v = fomod.view(self.inst, {"0.1": [1]}, nothing_active)                  # Zebra patch: not usable, not chosen
        zebra = v["steps"][0]["groups"][1]["options"][1]
        self.assertEqual((zebra["type"], zebra["chosen"], zebra["locked"]), ("NotUsable", False, True))
        v = fomod.view(self.inst, {}, lambda n: "Active" if n == "Zebra.esp" else "Missing")
        zebra = v["steps"][0]["groups"][1]["options"][1]
        self.assertEqual((zebra["type"], zebra["chosen"]), ("Recommended", True))

    # --- building -------------------------------------------------------------------------------------------------

    def built(self, picks: dict, state=nothing_active) -> tuple[dict, dict]:
        v = fomod.view(self.inst, picks, state)
        dest = Path(self.tmp.name) / ("built-%d" % len(list(Path(self.tmp.name).iterdir())))
        got = fomod.build(v["files"], self.root, dest)
        return got, {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()}

    def test_the_answers_build_the_mod(self) -> None:
        got, files = self.built({})
        self.assertEqual(files, {"Heather.esp": b"core", "textures/heather/base.dds": b"purple", "note.txt": b"note"})
        self.assertEqual(got["missing"], [])
        got, files = self.built({"0.0": [1], "0.1": [0], "1.0": [0]})
        self.assertEqual(files, {"Heather.esp": b"core", "textures/heather/base.dds": b"white",
                                 "textures/heather/bright.dds": b"bright", "Extras/snow.dds": b"snow"})

    def test_what_the_archive_does_not_have_is_named(self) -> None:
        (self.root / "Extras" / "bright.dds").unlink()
        got, files = self.built({"0.1": [0]})
        self.assertEqual(got["missing"], ["Extras\\bright.dds"])
        self.assertNotIn("textures/heather/bright.dds", files)

    def test_a_path_that_leaves_the_archive_or_the_mod_is_refused(self) -> None:
        for src, dst in (("..\\outside.txt", "a.txt"), ("Core\\Heather.esp", "..\\..\\climbed.esp"), ("C:\\x", "a")):
            with tempfile.TemporaryDirectory() as d:
                root = archive(Path(d) / "a", '<config><requiredInstallFiles><file source="%s" destination="%s"/>'
                                              '</requiredInstallFiles></config>' % (src, dst))
                write(Path(d) / "outside.txt", b"x")
                v = fomod.view(fomod.read(fomod.find(root)), {}, nothing_active)
                with self.assertRaises(fomod.Unreadable):
                    fomod.build(v["files"], root, Path(d) / "built")
                self.assertFalse((Path(d) / "built").exists())
                self.assertFalse((Path(d) / "climbed.esp").exists())

    def test_folders_to_choose_from_become_one_question(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "a"
            write(root / "00 Core" / "Heather.esp", b"core")
            write(root / "01 Extra" / "Heather.esp", b"extra")
            write(root / "01 Extra" / "meshes" / "a.nif", b"mesh")
            inst = fomod.from_folders(["00 Core", "01 Extra"])
            v = fomod.view(inst, {"0.0": [0, 1]}, nothing_active)
            fomod.build(v["files"], root, Path(d) / "built")
            self.assertEqual((Path(d) / "built" / "Heather.esp").read_bytes(), b"extra")      # the later folder wins
            self.assertTrue((Path(d) / "built" / "meshes" / "a.nif").is_file())


if __name__ == "__main__":
    unittest.main()
