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

## 9. Holding the same record is not carrying the mod's change (the owner's list, 2026-11-21)

- **FACT (the owner's list).** By §8's count, the distant-view generator's three plugins and one of the patcher's
  shared a handful of records with a dialogue mod and its patches, and the page told the owner to run both again,
  hours of work, while a second list on the same page said the same tools needed no run (they had been judged
  once by records and once by files, and both answers were shown). The owner: "So which one is it? … Does
  ModTrap know what each tool actually is for and what they need to do? How does it know they are really needed".
- **LIKELY.** A mod holds records it does not change: a cell or worldspace it only puts things into is written
  into the plugin as it stood. A tool holds records for its own reasons: the generator writes its own data into
  the same cells. Sharing such a record says nothing about the mod.
- **METHOD.** §8's count is replaced by two questions, answered with ModTrap's own reader, which now reads a
  record's fields (compressed ones too):
  1. What does the mod change? Its version of a record it does not own is compared, field by field, with the
     version in the last of that plugin's own masters that holds the record. No differing field: the mod does
     not change the record, and it is left out. The differing fields are the mod's changes.
  2. Does the tool's plugin carry one of those changed fields, byte for byte? Then it carries the mod's change,
     and the tool is to run again. If it holds the record without any of them, that is said, and is not a reason
     to run the tool.
- **Limit, stated on the page's own terms.** Fields are compared as bytes. A field that points at another record
  is written with that record's place among the plugin's own masters, so the same value can be written
  differently in two plugins. (An earlier wording here, that plain comparison of bytes "can miss a carried change
  but does not invent one", was wrong: it invented both a change and its carrying on the owner's list. §10.)
- **METHOD.** Each tool has one verdict, from all the evidence together: the kinds of file the mod carries that
  the tool feeds on, the changes its plugins carry, the files of its output mod at the mod's own paths. Any of
  them: run again, with what speaks against it said beside it. None: the tool is named as needing no run. The
  records and files behind each verdict are shown, folded away until asked for.
- **LIKELY (the tools' own public descriptions; not read in their source).** What each tool is for, in a
  sentence, is in ModTrap's tools data ('does') and is shown with the verdict: the patcher, the Bashed Patch,
  the model patcher and the distant-view generator from §2 to §5, and the behaviour engines, the body builder,
  and the distant-view generator's two companions, which have no plugin of their own to be known by.

## 10. The same pointer is written differently by different plugins (the owner's list, 2026-11-21)

- **FACT (the owner's list).** With §9's comparison of bytes, the distant-view generator still came out as
  carrying changes of a dialogue mod in eleven records. The owner doubted it, rightly.
- **FACT.** A pointer to a record is four bytes: the record's id, then the place of the record's plugin among
  the writing plugin's own masters (XE02). Two plugins with different master lists write the same pointer with
  a different last byte, and can write different pointers with the same bytes.
- **FACT (how the false alarm came about).** A patch made for the mod listed its masters in another order than
  the plugin it patches. Every field of an untouched record that held a pointer therefore differed in bytes from
  the earlier version: "changed". The generator's plugin happened to number the same masters as the patch did,
  so its untouched copy of the same field matched the patch's bytes: "carried". Neither had anything of the mod.
- **METHOD.** Fields are now compared with each plugin's own numbering in mind (`plugin.same_field`): a byte
  that differs is let pass only where it names the same plugin in both numberings and the three bytes before it
  agree; and where the numberings differ, equal bytes that would be a pointer in both plugins, to different
  plugins, are not the same. Written text (names, paths) is compared as written.
- **Limit.** ModTrap does not know what each field of each record type means; xEdit does. A number that looks
  like a pointer in both plugins can still be misread, in either direction. The evidence is therefore shown
  record by record with the fields named, for the owner to judge, and written into the log; and for a tool whose
  need depends on what kind of thing was changed, the step says so.

## 11. What the mod changes comes from xEdit; ModTrap only looks for it in the tools' plugins (2026-11-21)

- **FACT (the owner's list).** With §10's comparison the distant-view generator was still told to run for a
  dialogue mod. The evidence, now shown, named a worldspace's name and a cell's list of regions: the same
  values, stored differently (XE01§18). §9's first question, "what does the mod change", cannot be answered by
  reading bytes, however carefully.
- **METHOD.** That question is now answered by xEdit in the dry run (XE01§18). ModTrap keeps §9's second
  question: for each record the mod really changes, does a tool's plugin hold one of the changed fields as the
  mod wrote it, and not as the mod's own master had it? For that it still reads bytes, with §10's care for how
  plugins number their masters.
- **METHOD.** Without a dry run that told what the mod changes, no tool is judged by records. Such tools are
  named in a step of their own, "Tools ModTrap can judge only from a dry run", which says how to get them
  judged. Evidence from files (§8) does not wait.
- **Limit.** The second question is still asked of bytes. A changed name kept as text, or a changed list, is
  found in a tool's plugin only if that plugin writes it the same way; tools built on xEdit do. A tool whose
  plugin writes it otherwise would be missed.
