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
- **LIKELY.** `modlist.txt` lists mods one a line, highest priority first, each with `+` (enabled), `-` (disabled)
  or `*` (not managed by MO2) before its name. `plugins.txt` marks an active plugin with `*` before its name;
  `loadorder.txt` lists every plugin in order. From long use of MO2, not yet read in its source.
- **LIKELY.** The executables set up in MO2 (their names, programs and arguments) are kept in `ModOrganizer.ini`
  under `[customExecutables]`. Not yet read in its source.

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

- **METHOD.** §2's two LIKELY items: read `profile.cpp`, `pluginlist.cpp` and `executableslist.cpp` before the
  reader is written.
- **METHOD.** §4 and §5: the probe on the owner's PC (DESIGN§9).
