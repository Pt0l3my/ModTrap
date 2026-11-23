# MO03. Where MO2 puts a mod's plugins, and how it renames a mod

## 1. Source

`github.com/ModOrganizer2/modorganizer`, `master` at `4ba22f0` (2026-10-05), GPL-3.0: the same source as MO01. Read
only, for what MO2 does when a mod is enabled, disabled or renamed; cited as file and line. ModTrap's own code
(`modtrap/loadcheck.py`, `modtrap/listjob.py`) is written from the facts below, not from this code (MT56).

## 2. A plugin new to the list goes to the end; one that is gone is dropped

- **FACT (`src/pluginlist.cpp:294`).** When MO2 reads the plugins of its virtual Data folder, a plugin its list
  does not have yet is added with the priority -1.
- **FACT (`src/pluginlist.cpp:458-476`).** The priorities are then put in order, -1 counting as the highest number
  there is, and numbered anew from 0: a new plugin ends up last. Several new ones keep no order among themselves
  that the code promises.
- **FACT (`src/pluginlist.cpp:303-313`).** A plugin of the list that is no longer in the virtual Data folder (its
  mod was disabled) is taken out of the list. The two files are written from the list, so its lines go from
  `plugins.txt` and `loadorder.txt` at MO2's next write; enabled again later, the plugin is new and goes last.

## 3. Masters stay in the masters' block

- **FACT (`src/pluginlist.cpp:2142-2144`, `:396-397`).** For this rule a master is a plugin with the extension
  `.esm` or `.esl`, or one flagged as a master in its header. A light-flagged `.esp` is not one.
- **FACT (`src/pluginlist.cpp:409-438`).** With the masters counted, each master whose priority is above that
  count is given the count as its priority, and each other plugin whose priority is below the count is given the
  count plus one: masters above, the others below.
- **FACT (`src/pluginlist.cpp:1962-1981`).** Where a priority is set, a plugin that is no master is not put above
  a master, and a master is not put below a plugin that is none: the wanted place is stepped past them.
- **LIKELY, read but not seen run.** Taken to the letter, the two together put a new master one place before the
  block's last plugin, not after it. ModTrap puts it after the block's last plugin: the game's rule is met either
  way, and MO2 leaves a master there alone (its priority is not above the count).

## 4. No plugin before a master of its own

- **FACT (`src/pluginlist.cpp:440-455`).** For every plugin the priority becomes the highest of its own and its
  masters' (those the list has): a plugin that stood before one of its masters is moved to it.
- **FACT (`src/pluginlist.cpp:1986-1998`).** Where a plugin is moved up, it is not put above a master of its own:
  the place becomes the one right after that master.
- **FACT (`src/pluginlist.cpp:2000-2014`).** Where a plugin is moved down, it is not put below a plugin that lists
  it as a master.

## 5. What enabling or disabling a mod does to its plugins

- **FACT (`src/organizercore.cpp:1365-1424`).** For each `.esm`, `.esl` and `.esp` at the top of the mod's folder:
  if the plugin's state differs from the mod's new state, and no other mod holds a file of the same name, the
  plugin is activated or deactivated. Where another mod has such a file, the plugin's state is left as it is.
- **FACT (`src/organizercore.cpp:1416-1419`).** When more than one `.esl` or `.esp` was activated together, MO2
  says "Multiple esps/esls activated, please check that they don't conflict."
- **FACT (`src/organizercore.cpp:1421-1423`).** The load order is then worked out again and both lists are written
  at once.
- **FACT (`src/pluginlist.cpp:480-486`).** A plugin MO2 holds as always loaded stays active, and one it holds as
  never loaded stays inactive, whatever is asked.

## 6. Renaming a mod (a separator is one)

- **FACT (`src/modinforegular.cpp:470-500`).** A name with `/` or `\` in it is refused. The mod's folder is
  renamed; where only the letters' case changes, by way of a temporary name.
- **FACT (`src/mainwindow.cpp:2497`, `src/profile.cpp:317-329`).** The new name is then written into the
  `modlist.txt` of every profile that has one.
- **FACT (`src/profile.cpp:333-386`).** In each, the line whose name is exactly the old name gets the new name;
  its first character, the sign, stays, and every other line is written back as it was.
