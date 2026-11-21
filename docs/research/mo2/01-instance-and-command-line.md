# MO01. MO2: the instance and the command line

## 1. Source

`github.com/ModOrganizer2/modorganizer`, `master` at `4ba22f0` (2026-10-05). Licence: GPL-3.0 (its `LICENSE`).
Cited as `file:line` under `src/`. Read only; nothing copied.

## 2. The instance's files

- **FACT.** `ModOrganizer.ini` holds, under `[General]`, `gamePath`, `gameName` and `selected_profile`
  (`settings.cpp:663-706`), and under `[Settings]`, `base_directory`, `download_directory`, `mod_directory`,
  `profiles_directory` and `overwrite_directory` when they differ from the defaults (`settings.cpp:1706-1770`).
- **FACT.** A profile folder holds `modlist.txt`, `plugins.txt`, `loadorder.txt`, `lockedorder.txt`, `archives.txt`
  and `settings.ini` (`profile.cpp:94-99`, `:946-966`).
- **FACT.** A portable instance is one whose files sit in MO2's own folder; MO2 uses it when it exists
  (`instancemanager.cpp:559-566`).
- **FACT.** `modlist.txt` is UTF-8 with CRLF line ends. Its first line is a `#` comment; then one mod a line,
  highest priority first, each with `+` (enabled), `-` (disabled) or `*` (not managed by MO2) before its name
  (`profile.cpp:243-281`). On reading, the order of the lines gives the priorities, empty and `#` lines are
  skipped, a line with no sign counts as enabled, and a mod folder the file does not name is added above the others
  (`profile.cpp:392-470`).
- **FACT.** MO2 writes the file itself from what it holds in memory, and writes pending changes before it re-reads
  (`profile.cpp:426`). So a change made to the file while MO2 is open can be lost.
- **FACT.** The executables set up in MO2 are stored as the `customExecutables` array of `ModOrganizer.ini`
  (`settings.cpp:369-401`); an entry has `title`, `binary`, `arguments`, `workingDirectory`, `steamAppID` and the
  flags `toolbar`, `ownicon` and `hide` (`executableslist.cpp:79-125`).
- **FACT.** For each executable, the profile can name a mod that receives the files the program creates, in place
  of `overwrite`: the profile setting `custom_overwrites`, keyed by the executable's title
  (`editexecutablesdialog.cpp:140-148`, `:210`). This ties a tool to the mod its output lands in.
- **FACT (MO2's Bethesda game plugins, `github.com/ModOrganizer2/modorganizer-game_bethesda` at `a6a2340`,
  2026-10-06; no licence file at its root, read only).** For Skyrim SE, `plugins.txt` starts with a `#` comment and
  has one plugin a line, in load order, CRLF line ends, in the system's text encoding: `*Name` for an active plugin,
  the bare name for an inactive one; the game's own primary plugins are not written
  (`src/creation/creationgameplugins.cpp:39-104`). Reading skips `#` lines, and a plugin the file does not name
  counts as inactive (`:106-175`).
- **FACT (same source).** For Skyrim SE the game's primary plugins are `Skyrim.esm`, `Update.esm`, `Dawnguard.esm`,
  `HearthFires.esm` and `Dragonborn.esm`, then every plugin named in `Skyrim.ccc` in the game's folder (the Creation
  Club list) (`src/games/skyrimse/gameskyrimse.cpp:247-307`).
- **FACT (same source).** `loadorder.txt` has every plugin, one a line, in load order, in UTF-8
  (`src/gamebryo/gamebryogameplugins.cpp:87-116`). MO2 reads the order from whichever of the two files is newer
  (`:39-61`; `creationgameplugins.cpp:22-37`).
- **FACT.** At a refresh MO2 empties its plugin list and builds it again from the plugin files then present in the
  virtual folder, so a disabled mod's plugins are no longer in it; a plugin it has not placed yet starts with no
  place (`pluginlist.cpp:211-294`). The saved lists are then read for the order and the active marks.
- **LIKELY.** So when a mod is enabled again, its plugins come back at the end unless `loadorder.txt` still places
  them. Not read to the end; to be confirmed on the owner's PC before Re-enable is built.

## 3. Running a program in the virtual file system

- **FACT.** `ModOrganizer.exe [-i <instance>] [-p <profile>] run [-e] [-a <arguments>] [-c <folder>] NAME` runs a
  program, a file or a configured executable with the virtual file system (`commandline.cpp:700-735`; the global
  options at `:315-330`). With `-e`, NAME is the name of an executable configured in the instance, matched with
  case first and then without (`:756-773`); `-a` replaces its arguments and `-c` its working folder (`:779-785`).
- **FACT.** The command waits for the program to end (`commandline.cpp:787`).
- **FACT.** Other commands include `refresh`, the same as F5 (`commandline.cpp:934`).

## 4. MO2 open or closed

- **FACT.** If MO2 is already open, a `run` command is passed to the open MO2, which carries it out
  (`commandline.cpp:195-202`, `:740`; `main.cpp:55`).
- **LIKELY.** The second, short-lived process then returns at once, without waiting for the program. Not read to
  the end in the source; to be seen on the owner's PC.
- **FACT.** MO2's own help advises against several MO2 processes on the same instance, which `--multiple` would
  allow (`commandline.cpp:446-465`).

## 5. What a program's writes do

- **LIKELY.** A file a program changes inside the virtual file system is changed where it lives, in its mod's
  folder; a file it creates goes to `overwrite`, or to a mod chosen for that executable in MO2's settings. From long
  use of MO2 and from how the modding community describes saving in xEdit; not read in the source of MO2 or of its
  file system library.

## 6. Open points

- **METHOD.** §2's last LIKELY item (what MO2 does with a re-enabled mod's plugins): read `pluginlist.cpp` before
  Re-enable is built, and confirm on the owner's PC.
- **METHOD.** §4 and §5: the probe on the owner's PC (DESIGN§9).

## 7. A mod's meta.ini, and the downloads folder

- **FACT.** When MO2 installs a mod from an archive it writes `installationFile` into the mod's `meta.ini`, in the
  first, unnamed group, which Qt writes as `[General]` (`installationmanager.cpp:526, 550`). The value is the
  archive's file name alone when the archive is in MO2's downloads folder, and its full path otherwise
  (`installationmanager.cpp:719-721`).
- **FACT.** The downloads folder is the `download_directory` setting, `downloads` under the base folder by default
  (`settings.cpp:1711`, `shared/appconfig.inc:5`).
- **METHOD.** ModTrap reads that one line of each mod's `meta.ini`, and takes the file name after the last slash, to
  tell which mod a dropped archive was installed as (DESIGN§16.1).

## 8. No command to install an archive

- **FACT.** What MO2's command line takes beside its options is a shortcut, a download link of the Nexus site
  (`nxm:`), or a program to run (`commandline.cpp:163-174`, `277-281`); the `run` and `refresh` commands are §3's.
  There is no way to hand MO2 an archive file to install.
- **METHOD.** So a dropped archive is unpacked by ModTrap (DESIGN§16.1). MO2 takes a folder that appears in its
  mods folder as a mod, disabled, at its next refresh (§2).

## 9. What the first passing probe showed (2026-11-21), and the source behind it

- **FACT (the owner's PC).** Twice in one probe MO2 was started by its `run` command on lists ModTrap had just
  written (two new mods placed and enabled; three new plugins placed and activated in both plugin lists). After
  MO2 had closed, the lists were byte for byte what ModTrap had written: the probe's comparison passed, and the
  safe folder's Revert, which refuses a file changed by anything else, put the whole files back. So a MO2 started
  by `run` did not rewrite its lists. Not shown: what a MO2 opened as a window by the owner writes.
- **FACT (the owner's PC).** A folder ModTrap created in MO2's mods folder, with a `meta.ini` of one line, was
  taken as a mod: its plugins were in the game's Data folder as xEdit saw it.
- **FACT.** After the program ends, MO2 calls what its plugins registered for "a run has finished"
  (`organizercore.cpp:2062`). The `run` command catches an error raised there and shows it in a message window
  that begins "Failed to run", though the program ran, then ends with exit code 1 (`commandline.cpp:797-805`).
- **FACT (the owner's PC).** One of the modlist's own MO2 plugins raised such an error after every run started
  this way, so MO2 stopped at that message until it was dismissed. LIKELY: that plugin sets itself up when MO2's
  window is ready (`organizercore.cpp:340-343`), which never happens in a `run` without a window. It is not
  ModTrap's to fix; ModTrap asks a MO2 it started itself to close when it does not go by itself (XE01§11).
