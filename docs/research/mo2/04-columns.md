# MO04. What MO2's Conflicts, Installation and Notes columns show

## 1. Source

`github.com/ModOrganizer2/modorganizer`, `master` at `4ba22f0` (2026-10-05), GPL-3.0: the same source as MO01. Read
only, for what three columns of MO2's mod list show; cited as file and line. ModTrap's own code
(`modtrap/modcols.py`) is written from the facts below, not from this code (MT70).

## 2. Conflicts

- **FACT (`src/modinfowithconflictinfo.cpp:116-122`).** The check goes through the files of the mod as MO2's tree
  of files holds them: the tree of every enabled mod's files, Overwrite's and the game's own Data folder's. A mod
  that is not enabled has no files there, and so no state.
- **FACT (`src/directoryrefresher.cpp:194-204`).** `meta.ini` and `readme.txt` at a mod's top, and a folder
  `fomod` at its top, are taken out of that tree.
- **FACT (`src/modinfowithconflictinfo.cpp:123-153`, `src/modinfo.cpp:59`).** A file whose name ends in
  `.mohidden`, and every file under a folder whose name does, is passed over: hidden from the game, and no
  conflict.
- **FACT (`:155-161`).** A file no other mod has, or one that only the game's own Data folder has besides, is no
  conflict, and counts as something the mod provides.
- **FACT (`:176-190`).** Where another mod's copy is the one in use (the file's origin is not this mod), this mod
  is overwritten by that mod; where this mod's copy is in use, it provides something.
- **FACT (`:193-205`).** For every other mod that has the file: this mod overwrites it where this mod's priority
  is the higher, and is overwritten by it otherwise.
- **FACT (`:230-240`).** The state, for a mod with files: redundant where it has files that are not hidden and
  provides nothing; else mixed where it both overwrites and is overwritten; else "overwrite"; else "overwritten";
  else none.
- **FACT (`:164-175`, `:206-222`, `:242-258`).** Files inside archives have states of their own (archive against
  archive, archive against loose file). They exist only where MO2 has read the archives' contents, which is a
  setting of MO2's. **Not read further:** how the archives' order is worked out. ModTrap shows the loose files'
  state alone.
- **FACT (`src/modinfooverwrite.cpp:57`).** Overwrite has a mark of its own when files of it are in conflict.

## 3. Installation

- **FACT (`src/modinforegular.cpp:40`, `:792-794`; `src/modlist.cpp:257-262`).** The column shows the mod's
  "creation time", which is the time the mod's folder was made (its birth time), as the file system has it.

## 4. Notes

- **FACT (`src/modinforegular.cpp:88-89`; `src/modlist.cpp:264-265`).** The column shows the mod's `comments`, a
  line of text in the `[General]` part of its `meta.ini`. (`notes` in the same file is the long text of the mod's
  Notes tab, and is not what the column shows.)
- **FACT (MO2's settings files generally).** A value with a comma or the like stands in quotes, with `\"`, `\\`,
  `\n` and `\xNNNN` for what cannot stand as it is.
