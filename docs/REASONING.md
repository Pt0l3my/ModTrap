# Reasoning log

Append-only. Each entry is dated and labelled: **FACT** (read in a named source), **LIKELY** (inferred, not yet
proven), **SPECULATION**, **METHOD** (how something was or will be found out) or **DECIDED** (points to a decision).
An entry is never rewritten; a later entry corrects it and names it (R-number).

Sources, read only, never built or run, each cloned outside this repository:

- **xEdit**: `github.com/TES5Edit/TES5Edit`, tag `xedit-4.1.5f` (commit `f5c00f3`, 2024-04-27), the version the
  owner's screenshots show. Licence file: MPL-2.0. Cited as `xEdit:<file>:<line>`.
- **MO2**: `github.com/ModOrganizer2/modorganizer`, `master` at commit `4ba22f0` (2026-10-05). Licence file:
  GPL-3.0. Cited as `MO2:<file>:<line>`.
- **DataPiler**: the owner's own MIT project, `main` at `6c9ec49` (2026-11-15).
- **The guide**: screenshots the owner supplied on 2026-11-20 of a modlist community's "Master Removal" procedure.
  Described here in our own words; nothing of it is copied into the repository.

## 2026-11-20

### What the manual procedure is

- **R1 · FACT (the guide).** To disable a mod whose plugin is a master of other plugins, the guide has the user,
  for each dependant plugin: keep the unwanted mod enabled; open xEdit through MO2 and load the dependant (its
  masters load with it); run xEdit's own "Report masters" script on the dependant and tick the unwanted plugin;
  read the list of records and elements that need it; for each, remove the whole record from the dependant, or
  remove just the element that refers to the unwanted plugin (the example removes one entry from a FormID list);
  run "Clean Masters" on the dependant; run the report again until it shows no hits; save. Then the unwanted mod can
  be disabled.
- **R2 · FACT (the guide).** The same guide does not demaster every dependant: patches that exist only for the
  unwanted mod are simply disabled, and only plugins that serve other purposes too are demastered.
- **R3 · DECIDED.** This procedure is what "demaster" means for ModTrap (MT1).

### xEdit 4.1.5f

- **R4 · FACT.** `-script:<file>` puts xEdit into its script tool mode; a relative name is looked up in the scripts
  folder, an absolute path is taken as given (`xEdit:xEdit/xeInit.pas:616-630`,
  `xEdit:xEdit/xeMainForm.pas:4895-4898`). The scripts folder then becomes the script's own folder (`:4912`), and a
  script can read it as `ScriptsPath` (`xEdit:xEdit/JvI/xejviScriptHost.pas:126-128`).
- **R5 · FACT.** In script mode xEdit sets "I know what I'm doing", loads BSAs and builds references
  (`xeInit.pas:1307-1311`); `-nobuildrefs` turns reference building off (`:1385`).
- **R6 · FACT.** `-autoload` skips the module selection window and loads the active plugins of the plugins file
  (`xeInit.pas:1075`, `xeMainForm.pas:5299-5307`). `-P:<file>` names the plugins file to use instead of the game's
  own (`xeInit.pas:493-510`). So ModTrap can hand xEdit a short plugins file of its own and load only what a job
  needs, not the whole load order.
- **R7 · FACT.** Once loading ends, script mode runs the script by itself (`xeMainForm.pas:20427-20431`,
  `:17277-17278`), on every loaded file (`:4915`), and `-autoexit` then closes xEdit (`:17280`, `:16980`). A script
  need not have a `Process` function: `Initialize` and `Finalize` are each called only if present
  (`:8434-8459`), so a script can do all its work in `Initialize`.
- **R8 · FACT.** Script mode is one of xEdit's "auto modes" (`xEdit:Core/wbInterface.pas:4753-4765`). On close, an
  auto mode saves every changed file without showing the "Save changed files" window (`xeMainForm.pas:15618-15630`).
  A save writes `<plugin>.save.<timestamp>` beside the plugin and renames it over the plugin, at once or at shutdown
  (`:15690-15760`); the old file goes to the backup folder, by default `<Data>\SSEEdit Backups\`, or the folder given
  with `-B:` (`xeInit.pas:518-520`), unless backups are switched off in xEdit's settings.
- **R9 · FACT.** xEdit writes its message log on close to `<xEdit's folder>\SSEEditScript_log.txt`, and to a second
  file named with `-R:<file>` (`xeMainForm.pas:6221-6225`, `xeInit.pas:535`). Neither is written while it works.
- **R10 · FACT.** The scripting functions the manual procedure maps to all exist (`xejviScriptAdapter.pas`):
  `ReportRequiredMasters` (`:641`, `:2117`), `Remove` (`:2097`), `RemoveElement`, `CleanMasters` and `SortMasters`
  (`:1520-1533`), `MasterCount`, `MasterByIndex`, `HasMaster`, and `FileWriteToStream` (`:1658`), which writes a
  loaded plugin to a stream the script opens. xEdit's own "Report masters" script is a short loop over
  `ReportRequiredMasters` (`xEdit:Build/Edit Scripts/Report masters.pas`).
- **R11 · FACT.** A script can read and clear an element's states; `esUnsaved` is among them
  (`xejviScriptAdapter.pas:280-290`, `:1996`).
- **R12 · LIKELY.** A script can therefore: change a plugin in memory, write the changed plugin to a new file
  somewhere else with `FileWriteToStream`, then clear `esUnsaved` on that file so that xEdit's save on close (R8)
  leaves the original alone. Not proven: whether clearing the state on a file is enough for R8's test, and whether
  `CleanMasters` behaves the same when called from a script as from the menu.
- **R13 · LIKELY.** A script can append lines to a text file as it goes (xEdit's own scripts save string lists to
  files), which is how ModTrap's page can show progress while xEdit works, since xEdit's own log (R9) only appears
  at the end.
- **R14 · LIKELY.** xEdit has no headless mode in this version: none of its command-line switches
  (`xeInit.pas`, all read) hides the window. The owner will see xEdit's window open, work and close.
- **R15 · METHOD.** R12 and R13 cannot be proven here: xEdit is a Windows program, and the rule is that nothing
  cloned is built or run. They are to be proven on the owner's PC with a first, harmless probe: ModTrap's script run
  on invented plugins that ModTrap's own code writes into its own test mod. The design has a fallback if R12 fails
  (design §6.3).

### MO2

- **R16 · FACT.** `ModOrganizer.exe [-i <instance>] [-p <profile>] run [-e] [-a <arguments>] [-c <folder>] NAME`
  runs a program inside the virtual file system; with `-e`, NAME is one of the instance's configured executables,
  and `-a` replaces its arguments (`MO2:src/commandline.cpp:700-735`, `:315-330`).
- **R17 · FACT.** The `run` command waits for the program to end (`commandline.cpp:787`). If MO2 is already open,
  the command is passed to the open MO2 and carried out there (`commandline.cpp:195-202`, `:740`,
  `MO2:src/main.cpp:55`). So a tool can be started through MO2 whether MO2 is open or closed.
- **R18 · LIKELY.** When the command is passed to an open MO2, the second, short-lived process returns at once, so
  ModTrap cannot rely on waiting for it: it must watch for xEdit's own end (the script's "done" line and the
  process's exit). To be confirmed on the owner's PC.
- **R19 · FACT.** MO2 also has a `refresh` command, the same as F5 (`commandline.cpp:934`).
- **R20 · FACT.** `ModOrganizer.ini` holds, under `[General]`, `gamePath`, `gameName` and `selected_profile`, and
  under `[Settings]`, `base_directory`, `mod_directory`, `profiles_directory` and `overwrite_directory` when they
  differ from the defaults (`MO2:src/settings.cpp:663-706`, `:1706-1770`). A profile folder holds `modlist.txt`,
  `plugins.txt`, `loadorder.txt`, `lockedorder.txt`, `archives.txt` and `settings.ini`
  (`MO2:src/profile.cpp:98-99`, `:946-966`).
- **R21 · LIKELY.** `modlist.txt` lists mods one a line, highest priority first, each with `+` (enabled), `-`
  (disabled) or `*` (not managed by MO2) before its name; `plugins.txt` marks an active plugin with `*` before its
  name. From long use of MO2, not yet read in its source.
- **R22 · LIKELY.** A file a program changes inside the virtual file system is changed in the mod folder it comes
  from; a new file goes to `overwrite`. This is why the guide's procedure alters the original plugins in place, and
  why ModTrap's design keeps xEdit from saving in place (R12).
- **R23 · FACT.** MO2 advises against two MO2 processes on the same instance (`commandline.cpp:446-465`). ModTrap
  never starts MO2 with `--multiple`.

### DataPiler's pattern

- **R24 · FACT.** DataPiler's page server binds 127.0.0.1 only, answers only its own Host, requires its own Origin
  on a write and a per-start token on every `/api/` call, sends a strict Content-Security-Policy with nonces and no
  outside sources, caps request sizes, and logs refusals by reason only (`datapiler/server.py`). ModTrap takes this
  whole, renamed.
- **R25 · FACT.** DataPiler's rules that carry over: jobs are data, never code; a guard checks everything before it
  is written; nothing of the third-party program is bundled; the sweep comes first (its `CLAUDE.md`).

### Rejected paths

- **R26 · DECIDED against: editing plugins with our own code.** ModTrap could parse and rewrite plugins itself and
  never start xEdit. Rejected: the owner asked for xEdit inside MO2, xEdit's knowledge of every record type is years
  of work, and a wrong rewrite of someone's plugin is the worst failure this tool could have. ModTrap's own code
  reads only a plugin's header (its masters), to build the list and to check the result.
- **R27 · DECIDED against: driving xEdit's window** (sending clicks and keys to do the guide's steps). Fragile, and
  unnecessary given R4 to R10.
- **R28 · DECIDED against: generating a script per job.** The script is one fixed file of ours; a job reaches it
  as a small data file beside it (R4). Jobs stay data, never code (R25).
