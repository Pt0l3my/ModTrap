# TL01. How patching tools name and mark their output

## 1. Sources

Each tool's own repository, read only, never built or run, each cloned in its own folder outside this repository:

- **Wrye Bash**: `github.com/wrye-bash/wrye-bash` at `09ab760` (2026-11-16); GPL-3.0 by its `LICENSE.md`.
- **Synthesis**: `github.com/Mutagen-Modding/Synthesis` at `14cf3fa` (2026-08-21); GPL-3.0 by its `LICENSE.md`.
- **ParallaxGen**: `github.com/hakasapl/ParallaxGen` at `423ad78` (2026-11-19); GPL-3.0 by its `LICENSE`.

Nothing of them is copied: ModTrap keeps only names and marks, as data (`modtrap/data/tools.json`).

## 2. Wrye Bash

- **FACT.** A Bashed Patch's header author is `BASHED PATCH`, and Wrye Bash itself tells a Bashed Patch by exactly
  that (`Mopy/bash/bosh/__init__.py:864`; set at `Mopy/bash/patcher/patch_files.py:47`).
- **FACT.** A new one is named `Bashed Patch, <number>.esp` (`Mopy/bash/bosh/__init__.py:3009`).
- **FACT.** Its description starts `Updated: ` with the time (`Mopy/bash/patcher/patch_files.py:365`).

## 3. Synthesis

- **FACT.** The default output is `Synthesis.esp` (`Synthesis.Bethesda/Constants.cs:7-8`).
- **FACT.** Patchers run in groups, and a group has a plugin name of its own (`Synthesis.Bethesda.Execution/Running/
  Runner/PrintRunStart.cs:25`); a modlist can therefore have several outputs with names its maker chose.
- **LIKELY.** Synthesis writes no mark of its own into the header's author field: no such assignment was found in
  its source. So an output with a chosen name is known only through MO2's output setting, or by a name that begins
  like the default, which is weak evidence.

## 4. ParallaxGen

- **FACT.** Its plugin patcher names split outputs `PG_<number>.esp` (`PGMutagen/PGMutagen.cs:1614`); the main
  output is `PGPatcher.esp` in the current source (`PGPatcher/src/main.cpp:508`), and was `ParallaxGen.esp` with
  `ParallaxGen_<number>.esp` in earlier releases (its `CHANGELOG.md:467-468`).
- **FACT.** It chooses its own output folder (`PGTools/src/main.cpp:95`), which is why MO2's per-executable output
  setting says nothing about it (WHY§28).

## 5. DynDOLOD

- **LIKELY.** Its output plugins are `DynDOLOD.esm`, `DynDOLOD.esp` and `Occlusion.esp`. Its source is not public;
  the names are as its users know them, and ParallaxGen's source checks the load order for `dyndolod.esp`
  (`PGPatcher/src/main.cpp:475`). Its own documentation is still to be read.

## 6. Editors

- **FACT.** xEdit is an editor: a plugin found in the mod MO2 sends xEdit's new files to was written by one of its
  scripts or by hand (WHY§28). ModTrap cannot make it again, so such a plugin is demastered, not regenerated.
- **LIKELY.** The same holds for zEdit.

## 7. What ModTrap does with this

- **METHOD.** Evidence that a tool made a plugin, strongest first: MO2's own record of where the tool's new files
  go (MO01§2); the header's author field; a file name the tool is known to use; a file name that merely begins like
  one (weak: the page says "probably"). The page shows which it was.
- **METHOD.** A patcher's or generator's output is proposed for "run the tool again"; an editor's for demastering.

## 8. Which tools must run again when a mod is taken out: by what their output holds (2026-11-21)

- **FACT (the owner's list).** The list's patcher writes three plugins that do not name the demastered mod as a
  master. The guide ends its steps for that mod with running the patcher and the behaviour tool again all the
  same. §7's rule (a tool's output that depends on the mod is made again) says nothing about such plugins.
- **LIKELY.** A patcher builds each record of its output from the versions of that record in the load order. It
  may copy values from a mod's version without pointing into the mod, so its output can carry what a mod did
  and still not need the mod as a master. It cannot carry anything of a mod whose records it holds none of.
- **METHOD.** For every active plugin that a tool made and that does not depend on the mod, ModTrap counts the
  records it holds that the mod's own plugins, or the patches made for the mod, also hold. It reads only record
  headers, with its own reader. Some shared: the tool is to run again, and the step names the plugins and the
  counts. None: the tool is named among those that need no run, with that reason. Not read to the end in time:
  said so, and running again is called the safe side.
- **METHOD.** A tool that works on files is judged by files. For every mod that MO2 sends a tool's new files to
  (MO01§2), known tool or not, and for the mod that holds the plugin of a tool known to work on models or
  textures, ModTrap counts the files that lie at the path of one of the mod's own loose files. Some: run again.
- **METHOD (unchanged).** A tool that feeds on a kind of file the mod carries (animations and behaviours, LOD,
  grass cache, body data) is to run again because the mod carries such files; the step names how many and gives
  examples. It is not a standing reminder: without such files in the mod, the step is not there.
- Not judged: what lies inside a mod's archives (.bsa), which ModTrap does not open; and a tool that keeps its
  output outside MO2's mods, of which MO2 records nothing.
