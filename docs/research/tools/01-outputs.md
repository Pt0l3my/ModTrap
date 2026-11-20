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
