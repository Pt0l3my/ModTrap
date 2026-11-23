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

## 12. What a behaviour tool reads of a mod: lists and patch folders, not animation files (2026-11-21)

Read in Pandora Behaviour Engine+'s source (GPL-3.0; facts only, nothing copied), commit `1f26bbc` of 2026-10-01.

- **FACT.** Its patch mods are folders under `Nemesis_Engine/mod/` holding `info.ini`, and under
  `Pandora_Engine/mod/` holding `info.xml` (`Pandora.Core/Mods/Providers/NemesisModInfoProvider.cs:13-15`,
  `PandoraModInfoProvider.cs:17-19`, `FileBasedModInfoProvider.cs:20-26`).
- **FACT.** For each project it looks at every folder under that project's `animations` folder
  (`Pandora.Skyrim/Format/FNIS/FNISParser.cs:199-206`). A folder is taken in only if it holds
  `FNIS_<folder>_List.txt` and the project's behaviour folder holds `FNIS_<folder>_Behavior.hkx`; for a creature
  the names carry the creature's name too (`FNISParser.cs:137-159`, `:162-179`, `:291-347`). Otherwise the
  folder is passed over with a warning.
- **FACT.** Nothing there reads an animation file for its own sake: an animation reaches the output through a
  list or a patch.
- **LIKELY (not read in source).** Nemesis reads its own patch folders and the same lists; FNIS reads the lists.
- **METHOD.** A behaviour tool is told to run again for a mod only if the mod carries a list or a patch folder
  that tool reads. A mod with plain animation files only gives it nothing: the game, or an animation framework,
  loads those as they are. As a second witness ModTrap searches the files of the tool's output mod for the
  names of the mod's own animation folders (`animations\<folder>\`) and of its graph files: a file that names
  one was built with the mod in it, whatever the mod's files look like.
- **Limit.** The search assumes that such names stand in the output as plain text. Not checked on real output.
  Packed archives are not looked into. Whether a patch folder was ticked in the tool cannot be told from files.
- **Later, 2026-11-21 (the owner's list).** The mod has one animation list, and none of the 31 files read in
  the behaviour tool's output names its animation folder. By the second FACT above a list alone is not enough
  for this tool: it also wants `FNIS_<folder>_Behavior.hkx` in the game's behaviour folder, and passes the
  folder over otherwise. ModTrap now looks for that file, in the mod and in every enabled mod, and counts a
  list as read by this tool only where it is there. For the older engines, which make that file themselves,
  the list alone counts (LIKELY, as above).

## 13. What reading a tool's plugin can and cannot show (2026-11-21)

- **FACT.** ModTrap compares a field in a tool's plugin with the mod's by bytes (§10, §11). That holds only where
  both were written the same way. A tool built on xEdit writes a record as xEdit does. A tool with a writer of
  its own (the patcher framework and its library, the Bashed Patch's builder) reads a record into its own model
  and writes it out in its own form: the same value can come out as other bytes.
- **FACT.** A patcher builds its copy of a record from the version that wins in the load order, then works new
  values into it. A value in its copy can be the winner's, or worked out from the winner's, or the patcher's own.
- **So:** for a patcher with its own writer, "other bytes than the mod's" does not show "another value than the
  mod's", and even another value may have been worked out from the mod's. If its plugin holds a record in which
  the mod has a stake (XE01§19), ModTrap cannot rule out that the copy was built from the mod's version.
- **METHOD.** Such a patcher is told to run again, "to be sure", with that reason; it is cleared only where its
  plugins hold no record in which the mod has a stake. Proof (the mod's very bytes in its plugin) is still said as
  proof. A tool built on xEdit is judged by bytes as before. `tools.json` says for each tool how it writes.
- **Limit, for every tool.** What a tool would make without the mod is known for certain only by running it. A
  tool that left a record alone, or left something out, because of the mod leaves no trace in its output.
- **Could be built later.** Letting xEdit compare, in the dry run, each tool plugin's copy with the mod's version
  and with the next in line, by meaning: the same as the mod's, the same as the next in line's, or neither. It
  would clear a patcher whose copies all match the next in line.

## 14. What a tool's own files say it made: the patcher framework's settings, and a plugin's records by kind (2026-11-22)

Read in Synthesis's source (facts only, nothing copied), commit `14cf3fa` of 2026-08-13.

- **FACT.** Its settings are in `PipelineSettings.json` in the folder it runs in, beside its program
  (`Synthesis.Bethesda.GUI/Settings/PipelineSettingsPathProvider.cs:17`).
- **FACT.** The file holds profiles (`Synthesis.Bethesda.Execution/Settings/V2/PipelineSettings.cs:9`); a profile
  holds groups (`V2/SynthesisProfile.cs:16`); a group has a name, whether it is on, its patchers in order, and a
  list of plugins left out for it (`V2/PatcherGroupSettings.cs:7-11`). Each patcher has a nickname and whether
  it is on (`Settings/PatcherSettings.cs:10-11`), and where it comes from (`GithubPatcherSettings.cs:22`). The
  older layout had the patchers straight under the profile (`Settings/V1/SynthesisProfile.cs:12`).
- **FACT.** A group is one output plugin, named after the group (the tests build it as the group's name with
  `.esp`: `Synthesis.Bethesda.IntegrationTests/Pipeline/SinglePatcherPipelineTest.cs:60`).
- **FACT.** Patchers keep their own settings under `Data` in the same folder
  (`Synthesis.Bethesda.Execution/Pathing/ExtraDataPathProvider.cs:21`).
- **METHOD.** ModTrap reads that file to say, for each plugin the framework made, which patchers made it and
  whether each is on. A plugin made with the mod's plugin on the group's left-out list holds nothing of the mod:
  that output is cleared, with the list as the reason. The patchers' own settings are searched for the mod's
  plugin name: a patcher set up with the mod in mind is a reason to run again.
- **METHOD.** For every tool-made plugin, ModTrap counts its records by kind (record headers only). The evidence
  then says what the plugin works on, in how many records of those kinds the mod has a stake, and how many of
  those the plugin holds. A plugin that holds only kinds in which the mod has no stake is cleared on firmer
  ground than by values.
- **Limit.** Kinds and names say what a patcher works on, not what it does to it. Whether a patcher would write
  something else without the mod is still known for certain only by running it (§13).

## 15. A cell's place on the grid: three bytes of it mean nothing (2026-11-22)

- **FACT (xEdit's source, `Core/wbDefinitionsCommon.pas:507-514` at commit `f5c00f3`).** For this game a cell's
  grid field (XCLC) is two numbers, one byte of land flags, and three bytes named Unused, marked to be ignored;
  only the two numbers must be there, so an older plugin's field is eight bytes long.
- **FACT (the owner's list).** Every cell in which a dialogue mod and a follower mod "had a stake" had it in this
  field alone. The reading script compares every part of a field, the unused bytes among them: they hold
  whatever was in memory when a plugin was saved, and differ from plugin to plugin.
- **METHOD.** ModTrap's own comparison takes this field as its two numbers and its flags byte, a missing flags
  byte counting as none (`plugin.canonical`). With §16 of the reasoning (the whole load order looked through),
  such a cell is no stake.
- **Not done.** The reading script still tells these as stakes; they are sorted out afterwards, for the records a
  tool's plugin holds. Teaching the script to pass over parts xEdit marks as ignored would change the script, and
  with it ask for the probe again.

## 16. Tools that run and close by themselves, and a compiler crash inside MO2 (2026-11-22)

Read in the tools' public sources (both GPL-3.0: facts only, nothing copied), each at the commit named.

- **FACT (Pandora Behaviour Engine, `Pandora.Skyrim/CLI/CommandLineParser.cs:24-30` at commit `1f26bbc`).** Its
  switches: `--output` (`-o`), the output folder; `--tesv`, the game's folder; `--auto_run` (`-ar`);
  `--auto_close` (`-ac`); `--skyrim_debug64`.
- **FACT (`Pandora.Engine/Views/Controls/LaunchElementViewModel.cs:46-74`, same commit).** With `--auto_run` the
  engine's launch starts as soon as the window is up, for the mods that are active in it (its own saved choice);
  with `--auto_close` the program shuts down when the launch has ended.
- **FACT (same file as the first, `:55-70`).** If the arguments cannot be parsed, none is applied: the output
  folder and the game's folder among them. LIKELY harmless here: the switches added are the program's own.
- **FACT (Synthesis, `Synthesis.Bethesda.GUI/Args/StartCommand.cs` at commit `14cf3fa`).** The window program
  takes one command, `start`, with one option: the profile to open. Nothing that runs the patchers and closes.
  A separate command-line program of the same project runs a pipeline (`Synthesis.Bethesda.CLI`).
- **FACT (`Synthesis.Bethesda.Execution/Reporters/Classifications/CscCrashError.cs`, same commit).** The
  framework has a name for one build failure: the C# compiler ending with exit code -1073741819 (an access
  violation, reported as build error MSB6006). Its own text gives the usual causes as other software getting in
  the compiler's way, "such as antivirus or Mod Organizer 2's virtual file system", and it notes whether it is
  itself running inside MO2.
- **FACT (`Synthesis.Bethesda.GUI/ViewModels/Top/Mo2PrepModeProvider.cs`, same commit).** It has a setting that
  blocks building inside MO2, and with it a mode in which the program, started outside MO2, only builds the
  patchers, so that a later start inside MO2 finds them built.
- **FACT (the owner's PC, version 0.35.5 of the framework).** Started through MO2, every patcher showed
  "Blocking Error" with exactly that compiler exit code; nothing was written.
- **LIKELY.** The patchers had to be built anew (a new version of a patcher or of the build tools does that), and
  building inside MO2 crashed the compiler. Not established: whether the same shows from MO2's own Run button on
  that PC, and whether the owner's version has the setting named above.

## 17. A second failure of the patcher framework inside MO2, and what MO2 hands a tool (2026-11-22)

- **FACT (the owner's PC, a picture of the framework's window).** On the next start through MO2 every patcher
  again showed "Blocking Error", with another error: "Error compiling", a Windows error 5, "Access is denied",
  raised where the framework starts the build program and makes the pipes to read its output. So the failure
  is not always the compiler's crash of §16; both come while the patchers are built, before a load order is read.
- **FACT (MO2, `src/spawn.cpp:421-435` and `:463-466` at commit `4ba22f0`).** MO2 starts a program with no
  handles passed on, unless MO2 itself redirects the program's output. What a `run` command's own start gave MO2
  (ModTrap gives it none to read or write) therefore does not reach the tool: in that respect a tool started
  through ModTrap gets what MO2's Run button gives it.
- **Not established.** Why building fails inside MO2 on this PC, and whether it does from MO2's own Run button.

## 18. The patcher framework's own log, and what four of them showed (2026-11-22)

- **FACT (the owner's PC).** Synthesis writes a log for each time it is opened into a folder `logs` beside its
  program, one file a session, named by date and time. A line has a time, a level in brackets (INF, WRN, ERR)
  and the text.
- **FACT (the logs).** Lines ModTrap goes by: "Opening Synthesis v…" (its version); "Swapped profile … to
  (Mutagen ==> Manual: … )(Synthesis ==> Manual: … )" (the library versions the profile is set to, written again
  when they change); "Swapping to net…" (the .NET version a patcher's project is set to before it is built);
  "error NU1202: Package … is not compatible with net…" (a library that does not support that .NET version);
  "csc.exe" exited with code -1073741819; "Win32Exception (5): Access is denied"; "Encountered blocking overall
  error".
- **FACT (Synthesis, `Synthesis.Bethesda.Execution/Patchers/Git/Services/ModifyProject/SwapToProperNetVersion.cs:83-102`
  at commit `14cf3fa`).** The .NET version a patcher is built for is looked up from the library version aimed at,
  in a table the program carries: the entry at or below that version. A library version newer than the
  program's table gets the last .NET version the program knows.
- **FACT (the owner's four logs of one day, version 0.35.5 of the program).**
  1. Started through MO2, profile set to library versions 0.53.1 and 0.35.5: patchers set to net8.0; the compiler
     crashed 42 times; nothing else.
  2. Started through MO2, the same versions at first: the compiler's crash and "Access is denied". Three minutes
     in, the profile's versions were changed to 0.54.4 and 0.36.6; from then on NU1202 for every patcher: those
     libraries support net9.0 and net10.0, and the patchers were still set to net8.0.
  3. Started through MO2 by MO2's own Run button (the owner's word), the raised versions: NU1202, and a few of the
     crash and the refusal.
  4. Started from its own folder, outside MO2 (no arguments in the log), the raised versions: NU1202 only.
- **LIKELY.** With the profile's versions back at the first pair, the patchers build outside MO2: outside MO2
  neither the crash nor the refusal showed. Not established.

## 19. Where the patcher framework keeps its library versions, and what its log's first lines state (2026-11-22)

Read in Synthesis's source (facts only, nothing copied), commit `14cf3fa`.

- **FACT (`Synthesis.Bethesda.Execution/Settings/V1/SynthesisProfile.cs:9-19`).** A profile in
  `PipelineSettings.json` has, beside its name (`Nickname`): `MutagenVersioning` and `SynthesisVersioning`, each
  one of Latest, Match, Manual; and `MutagenManualVersion` and `SynthesisManualVersion`, the versions used when
  that is Manual.
- **FACT (`Synthesis.Bethesda.Execution/Settings/NugetVersioningEnum.cs:3-8`, `Constants.cs:14-20`).** The three
  ways are numbered Latest 1, Match 2, Manual 3, and the file is written with such values as words.
- **FACT (`Synthesis.Bethesda.Execution/Settings/GithubPatcherSettings.cs:31-34`).** A patcher can override the
  profile: `MutagenVersionType` and `SynthesisVersionType` (Profile, Latest, Match, Manual), with
  `ManualMutagenVersion` and `ManualSynthesisVersion`.
- **FACT (`Mutagen.Bethesda.Synthesis/Versioning/ProvideCurrentVersions.cs:48-49` and `:97-99`,
  `Synthesis.Bethesda.GUI/Services/Startup/Startup.cs:69`).** At its start the program writes "Mutagen version: …"
  and "Synthesis version: …" into its log: the versions of the two libraries in the program's own files, the ones
  it was built with.
- **FACT (the owner's logs, TL01§18).** Program 0.35.5 states 0.53.1 and 0.35.5 there, the pair its profile was
  set to before the change, and with that pair no build error of the "does not fit" kind showed.

## 20. When the patcher framework builds a patcher, and when it takes the build as done (2026-11-22)

Read in Synthesis's source (facts only, nothing copied), commit `14cf3fa`.

- **FACT (`Synthesis.Bethesda.Execution/Patchers/Running/Git/GitPatcherCompilation.cs:62-66`).** Before it
  builds, it reads the patcher's record file and asks whether the build can be passed over; if so it logs
  "Short circuiting … compilation because meta matched" and builds nothing.
- **FACT (`…/ShouldShortCircuitCompilation.cs:26-40`).** The build is passed over when the setting for it is on
  (it is by default, `Settings/V2/PipelineSettings.cs:10`), the record is there, and it names the same commit of
  the patcher, the same two library versions and the same version of the program, and the built program it
  names still exists.
- **FACT (`GitPatcherCompilation.cs:86-98` and `:104-112`).** Otherwise the record file is deleted
  ("Clearing short circuit meta"), the project is built, and only after a build that did not fail is the record
  written anew.
- **FACT (the owner's logs, version 0.35.5).** Each start logs, for each patcher, "Compiling RunnerRepoInfo { … ,
  MetaPath = …Build.meta, … }": the record's place, in a folder of the program's under the user's temporary
  folder, the same place whether started through MO2 or not; and "Cleared short circuit meta" before each build.
  Thirteen records were named in each of the four logs, as many as the settings file has patchers.
- **LIKELY.** A patcher built in a start outside MO2 is passed over in the next start through MO2: nothing the
  check looks at differs between the two.

## 21. Running the patcher framework without a hand on it: what there is and is not (2026-11-22)

Read in Synthesis's source (facts only, nothing copied), commit `14cf3fa`, and in the owner's log of version 0.35.5.

- **FACT (`Synthesis.Bethesda.GUI/Args/StartCommand.cs`).** The window program's only command opens a profile
  (§16). No command or switch of it runs the patchers.
- **FACT (`Synthesis.Bethesda.CLI/Program.cs:17-30`, `Synthesis.Bethesda.Execution/Commands/RunPatcherPipelineCommand.cs:11-52`).**
  A separate command-line program has `run-pipeline`, which wants an output folder and the settings file's path.
- **FACT (`.github/workflows/publish.yml:47-55`).** A release is made from the window program alone, packed as
  one archive. The command-line program is not in it.
- **FACT (`Synthesis.Bethesda.GUI/Views/Config/MainConfigView.xaml:197-199`,
  `…/Group/GroupConfigListingView.xaml:309`).** The button that runs every group is named `GoButton` in the
  window's own description; each group's own run button, inside the list of groups, has the same name. No
  keyboard shortcut is declared for either.
- **FACT (`Synthesis.Bethesda.Execution/Running/Runner/PrintRunStart.cs:22`,
  `Synthesis.Bethesda.GUI/ViewModels/Profiles/Running/RunVm.cs:259-297`).** A run logs
  "================= Starting Pipeline Run =================" at its start, and "Finished patcher run" when the
  run has come to its end, whether it went well or not.
- **FACT (the owner's log, version 0.35.5, started through MO2 after its patchers had been built outside MO2).**
  For each of thirteen patchers: "Short circuiting … compilation because meta matched". One "Error checking
  runnability … Access is denied", reported three times as a blocking error within eleven seconds; then
  "State returned success!" thirteen times and "No global error", and nothing more until it was closed.
- **LIKELY (Windows' UI Automation, from its published interface; not read in a file here).** A window of this
  kind exposes each named control under that name as its "automation id", with its kind (button, list item,
  window) and whether it is enabled, and a button can be pressed through it. ModTrap's helper goes by exactly
  these, and checks itself before pressing (WHY§93). Not yet seen working on a PC.

## 22. What a run of the patcher framework does first, in the owner's version and in the current source (2026-11-22)

- **FACT (the owner's log, version 0.35.5, a run begun by its run button inside MO2).** In the same second as
  "Starting Pipeline Run" the log shows `dotnet build "<patcher>.csproj" --runtime win-x64 -c Release` for each
  patcher of the group, though each had been taken as built seconds before ("Short circuiting …"). Three of the
  builds ended "Build FAILED" with the compiler's exit code -1073741819 after "All projects are up-to-date for
  restore"; the log's own trace names the place as the preparing of a patcher for a run
  (`SolutionPatcherPrep.cs:42` of that version). The run ended 26 seconds after it began; "Finished patcher run"
  follows the errors.
- **FACT (the same log and those of §18).** The compiler's crash shows in every session inside MO2 in which a
  compile was made, and in no session outside MO2.
- **FACT (Synthesis's source at commit `14cf3fa`,
  `Synthesis.Bethesda.Execution/Patchers/Running/Git/GitPatcherRunner.cs:36-55`).** The current source runs a
  patcher's built program directly, by the path its build record names, and wraps that start in a retry "on
  transient spawn failure" that is named for MO2. So what failed on the owner's PC (building again at a run, and
  a refused start) is what later versions were changed to avoid.
- **FACT (the compiler's error line).** The program that crashed is named `csc.exe` by the build tool.
  LIKELY (the .NET build tools as published; not read in a file here): the build tool may also start the
  compiler as a server, by a command line that names `VBCSCompiler.dll`. Both names are what ModTrap adds to
  MO2's list (MO01§11, WHY§94).

## 23. Settings files of two frameworks that work while the game runs: a line's layout, and a plugin that is not loaded (2026-11-22)

Read in the frameworks' public sources, facts only, nothing copied: Spell Perk Item Distributor (MIT) at commit
`105725c`, Keyword Item Distributor (GPL-3.0) at commit `99adaaa`. The version a modlist carries may differ.

- **FACT (both).** Such a file is named by its ending (`_DISTR.ini`, `_KID.ini`). A line is a key, an equals
  sign, and fields divided by `|`: the first field is the thing the line gives or works on, later fields are
  conditions (KID: `src/LookupConfigs.cpp:17-45`). A condition that begins with `-` leaves out what it names
  (KID: `include/Data/BaseFilters.h:61-63`, an "exclude" mark on a rule); conditions joined by `+` must all hold.
  A form of a plugin is written as a number, `~`, and the plugin's file name; a plugin's name alone stands for
  everything of that plugin.
- **FACT (SPID, `SPID/src/FormData.h:307-357`).** A condition whose form or plugin cannot be found is passed
  over, with a line in the framework's own log ("SKIP - mod cannot be found", "SKIP - formID doesn't exist").
  A list of conditions then counts as usable when every one of them was found, or, for a list of which one is
  enough, when at least one was.
- **FACT (SPID, `SPID/src/FormData.h:611-616`).** An entry is kept only when each of its three lists of
  conditions is usable: those that must all hold, those that leave out, those of which one is enough. So an
  entry whose only exclusion names a plugin that is not loaded is dropped whole, in this version; with a second
  exclusion that is found, it goes on without the first.
- **FACT (KID, `include/Data/BaseFilters.h:73-90`).** A condition that cannot be found is noted for the log as
  "SKIP - (mod not found)" or "(form not found)" and is not used.
- **LIKELY.** A line whose first field names the plugin has nothing to give once the plugin is gone, and a line
  that reaches only the plugin's things reaches nothing: neither changes what happens to anything else.
- **Not read.** FormList Manipulator and Base Object Swapper (their sources were not at hand), and any settings
  file of another kind: ModTrap leaves those to the owner.

## 24. FormList Manipulator's settings files (2026-11-22)

Read in its public source and its own description (MIT), commit `82a694e` of the repository `FormList-Manipulator`
of its author; facts only, nothing copied. The version a modlist carries may differ.

- **FACT (its `README.md`, "Config Files" and "General usage").** A settings file is an INI file whose name ends
  with `_FLM`, or any INI file in a folder `FLM`. A line is `FormList = list|form, form, …|filter`: forms are
  added to the list; a form or a list is an editor name or a number, `~`, and a plugin's file name. In its
  words: the list "is skipped if is not found", and a form "is skipped if it already exists in FormList or is
  not found".
- **FACT (the same, "Filters").** A filter is made of conditions: a plugin's name with `+` if the plugin must be
  active, or `-` if it must not be; several joined by `&` must all hold, and of several conditions one is enough.
  A filter can be written in the line or named once by `Filter = name|conditions` and used by `#name`.
- **FACT (`src/Utility/Utility.hpp:73-89`).** A form that cannot be found is noted in the framework's log
  ("Can't find Form …") and not added.
- **So.** A line that names a plugin as the list's or a form's origin adds nothing once the plugin is gone. A
  line with `+plugin` is passed over once the plugin is gone. A line with `-plugin` was held back while the
  plugin was there and is carried out once it is gone: its author wrote it for a modlist without that plugin.

## 25. The program files of the three frameworks (2026-11-22)

Read in each framework's own build files, at the commits named in §23 and §24; facts only, nothing copied.

- **FACT (Spell Perk Item Distributor, `SPID/CMakeLists.txt:2` at `105725c`).** The program is named
  `po3_SpellPerkItemDistributor`; its own settings file is `po3_SpellPerkItemDistributor.ini` in `SKSE\Plugins`
  (`SPID/src/main.cpp:115`).
- **FACT (Keyword Item Distributor, `CMakeLists.txt:2` at `99adaaa`).** The program is named
  `po3_KeywordItemDistributor`.
- **FACT (FormList Manipulator, `CMakeLists.txt:7-9` and `:116` at `82a694e`).** The project is named
  `FormListManipulator`, and the build copies `FormListManipulator.dll`.
- **So.** A modlist has one of these frameworks installed when an enabled mod carries that program file, with the
  ending `.dll`, in `SKSE/Plugins`. ModTrap's scanner (WHY§98) lists them by that, in its data (`mentions.json`,
  "dll"). A release may name the file otherwise; then the framework shows among the other programs, and its
  settings files are read all the same, by their own names.

## 26. The animation replacer's folders and condition files (2026-11-22)

Read in the public source of Open Animation Replacer (GPL-3.0), commit `f4e7688`; facts only, nothing copied. The
version a modlist carries may differ.

- **FACT (`src/Parsing.cpp:1914-1953`).** It walks the whole of `data\meshes` for folders named
  `openanimationreplacer` or `dynamicanimationreplacer`, compared without case, at any depth, and does not look
  for more of them inside one it found.
- **FACT (`src/Parsing.cpp:946-952`, `:1043-1049`, `:1150-1154`, `:893-903`).** In such a folder it reads
  `config.json` and `user.json` of a mod's folder and of each folder below it; in the older layout,
  `_conditions.txt` in the numbered folders of `_CustomConditions`.
- **FACT (`src/Parsing.cpp:1296-1305`).** In the older layout a folder named after a plugin holds folders named by
  a form's number; one is used only if that form is found.
- **FACT (`src/SharedTypes.h:163-164`).** A thing is named in a JSON file by `pluginName` and `formID`.
- **FACT (`src/Utils.cpp:610-623`).** A form is looked up by plugin name and number; nothing is returned when it
  is not found.
- **FACT (`src/BaseConditions.h:23`).** A condition marked negated gives the opposite of what it evaluates to.
- **FACT (`src/OpenAnimationReplacer.cpp:828-980`).** The names conditions have in files, each with the code that
  evaluates it; 146 names, the older layout's among them.
- **FACT (`src/Conditions.cpp`, every `EvaluateImpl` read by a script over the file, the odd ones by eye).** Of 124
  conditions 39 are about a form, a keyword or a faction. 25 begin by asking whether that thing is valid and
  otherwise end as not holding (for example `:411-418`, `:648-655`). Of the other 14, twelve compare the thing
  with something that is known to be there, or ask a list of found keywords, and so do not hold when the thing
  was not found. Two differ: `IsInSpecifiedScene` compares the scene an actor is in with the thing, and both are
  nothing for an actor in no scene; `IsEquippedHasEnchantment` also compares the enchantment's base enchantment
  with the thing, and both are nothing for an enchantment with no base.
- **FACT (`CMakeLists.txt:3`).** The program is named `OpenAnimationReplacer`.
- **So.** Once a plugin is gone, a condition about one of its things does not hold (or, negated, always holds),
  as for anyone who never had the thing, for 43 of the names in files. For the two named it can hold where it was
  not meant. **LIKELY**, not read: `IsForm` compares the actor itself with the thing, which only matters if there
  is no actor. A condition added by another program is not in this source at all.

## 27. A Wabbajack file (2026-11-22)

Read in Wabbajack's public source (GPL-3.0), commit `a44228e`; facts only, nothing copied. Its licence note says
that modlists made with it are under CC BY-NC-SA 4.0; ModTrap only reads the owner's own copy on the owner's PC.

- **FACT (`Wabbajack.Installer/AInstaller.cs:192`).** A `.wabbajack` file is a zip archive; the list itself is the
  entry called `modlist`, a JSON text.
- **FACT (`Wabbajack.DTOs/ModList/ModList.cs`).** The list holds `Archives`, `Directives`, `Name`, `Version`,
  `GameType` and more.
- **FACT (`Wabbajack.DTOs/Archive.cs`).** An archive has `Hash`, `Name`, `Size`, `Meta` and `State`: where it is
  downloaded from.
- **FACT (`Wabbajack.DTOs/DownloadStates/Nexus.cs`, `Http.cs`, `Wabbajack.DTOs/JsonConverters/Generated.cs`).** A
  state names its kind in `$type`: `NexusDownloader, Wabbajack.Lib` with `GameName`, `ModID`, `FileID`,
  `Version`; `HttpDownloader, Wabbajack.Lib` with `Url`; others for a file of the game, the list's own store,
  files fetched by hand, and other hosts.
- **FACT (`Wabbajack.DTOs/ModList/Directive.cs`, `Directives/FromArchive.cs`,
  `JsonConverters/HashRelativePathConverter.cs:15-18`).** A directive has `To`, the place a file goes to inside
  the installed list (for a mod's file, `mods`, the mod's folder, the file), and, where the file comes from an
  archive, `ArchiveHashPath`: a list whose first entry is that archive's hash.
- **FACT (`Wabbajack.DTOs/Game/GameRegistry.cs:94-115`).** Its names for the games map to Nexus's as in MO01§12.
- **So.** The mods a list fills are the folders named under `mods` in its directives, each with the archives its
  files come from; a mod of the installed list that the file does not name was added afterwards. **LIKELY**, not
  seen: how large such a text is for a list of some 3,500 mods (hundreds of megabytes are expected, so ModTrap
  reads it piece by piece and keeps only a summary).

## 28. How Wabbajack is let in by Nexus and by LoversLab, and what it does where it is not (2026-11-22)

Read in Wabbajack's public source, commit `a44228e`; facts only, nothing copied.

- **FACT (`Wabbajack.Networking.NexusApi/OAuth/NexusOAuthLogin.cs:62-63`, `NexusApi.cs:337-343`).** Wabbajack asks
  Nexus for the user's permission through Nexus's own sign-in pages, as the application `wabbajack`: a name Nexus
  knows it by. The user's password never reaches Wabbajack.
- **FACT (`Wabbajack.Downloaders.Nexus/NexusDownloader.cs:117-124`).** With that permission, it still fetches a
  file by itself only for a Premium account. For any other it stops with "Nexus Premium is required for
  automatic downloads" and treats the file as one the user has to fetch by hand.
- **FACT (`Wabbajack.Downloaders.ManualSources/LoversLabSource.cs`).** In this version LoversLab is among the
  sources fetched by hand.
- **FACT (`Wabbajack.Installer/Preflight/Manual/ManualDownloadAcquirer.cs:23-36`).** For files fetched by hand it
  watches a folder, normally the user's Downloads folder, takes a file as finished when it can be opened alone,
  matches it to what it is waiting for, and moves it in. It deletes none of the user's files.
- **So.** Permission through a site's own pages is given to applications the site knows. And for Nexus it does
  not change what a free account may do: the download still begins with the user's press on the site.

## 29. Nexus's public service: what it answers without a key (2026-11-22)

Asked of the live service on 2026-11-22 by a helper session of this work, with no key and no sign-in, only for two
well-known public mods; and read on the service's own documentation page. Nothing copied but the names a question
needs.

- **FACT (asked).** The older service refuses a question without a key: status 401, "Please provide an
  authentication method".
- **FACT (its documentation page).** Of the newer service: "Most of GraphQL V2 is accessible without
  authentication, but some endpoints do require an OAuth token." And: "Existing stuff may change, evolve, or even
  disappear without warning".
- **FACT (asked).** The newer service takes a question as a text, posted to `https://api.nexusmods.com/v2/graphql`,
  and answered each of these without a key:
  - `game(domainName: …) { id }`: a game's number (1704 for the game ModTrap is for).
  - `legacyModsByDomain(ids: [{ gameDomain, modId } …]) { nodes { modId gameId status updatedAt } }`: several mods
    in one question. A page of mods held at most 80, whatever was asked for.
  - `modFiles(modId, gameId) { fileId uri version categoryId date groupId }`: a mod's files. `uri` is the file's
    name as it is downloaded; `date` is in seconds; `categoryId` has the numbers of MO01§13. Several such
    questions went in one request under names of their own.
- **FACT (asked, for both mods).** A mod's `updatedAt` was the time of its newest main file. The mod's own
  `version` lagged behind its newest file for one of them, so it is not what to compare.
- **FACT (asked).** There is no word of which file replaced which. Files of one line of versions shared a
  `groupId` (every main file of the one mod from its first to its newest; its translation patch another; its
  developer kit a third). **LIKELY**: that is what the group means; it is inferred from the data, not documented.
- **FACT (asked).** No header of an answer spoke of an allowance of questions. How many the service allows without
  a key is not known.
- **FACT (Nexus's page on acceptable use, of 2020).** A program is asked to name itself in `Application-Name` and
  `Application-Version`; a personal key is tolerated for a program meant for personal use; a program meant for
  the public is asked to get in touch with Nexus first.

## 30. What the public service tells of one file, and what it does not (2026-11-23)

Asked of the live service on 2026-11-23, without a key, for two mods of the game ModTrap is for (one with 62
files, one with 55), by a session that can reach it.

- **FACT (asked, by the service's own description of itself).** A file has these fields: `category`,
  `categoryId`, `changelogText`, `count`, `date`, `description`, `detectedFileExtension`, `fileId`, `game`,
  `groupId`, `id`, `manager`, `mod`, `modId`, `modUid`, `name`, `owner`, `primary`, `reportLink`,
  `requirementsAlert`, `scanned`, `scannedV2`, `size`, `sizeInBytes`, `sqid`, `totalDownloads`, `uCount`, `uid`,
  `uniqueDownloads`, `uri`, `version`.
- **FACT (asked).** `size` is in units of 1,024 bytes; `sizeInBytes` is the size to the byte, given as a text of
  digits, not a number.
- **FACT (asked, both mods).** For files uploaded up to the summer of 2026, `uri` is the name the download is
  saved under ("…-<mod's number>-<version>-<time of upload>.7z"). For every file uploaded since, in both mods,
  `uri` is a storage code instead: three pairs of hexadecimal digits and a longer code of such digits and dashes,
  divided by slashes. This corrects §29, which took `uri` for the name in every case.
- **FACT (asked).** No field gives the name a storage-coded file is saved under: `fileName`, `originalFileName`
  and `downloadName` do not exist. `name` is the file's name on the mod's page, which several files of a mod
  share. `detectedFileExtension` gave "zip" for the newest such files of one mod and nothing for the other's.
- **Not known.** Under which name a browser saves a storage-coded file. It is not asked for here: a download
  needs the owner's signed-in browser.
