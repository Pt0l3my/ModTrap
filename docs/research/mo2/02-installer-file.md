# MO02. A mod's installer file, as MO2 reads it

## 1. Source

`github.com/ModOrganizer2/modorganizer-installer_fomod`, `master` at `7c39956` (2026-10-06): MO2's installer for
archives that carry `fomod/ModuleConfig.xml`. No licence file at its root; read only, for what the file format means
and how MO2 treats it. Cited as `fomodinstallerdialog.cpp:line`. ModTrap's reader (`modtrap/fomod.py`) is written
from the facts below, not from this code.

## 2. The file

- **FACT.** The installer's description is `fomod/ModuleConfig.xml` under the archive's own top folder; an optional
  `fomod/info.xml` gives the mod's name, author, version and website (`:236-249`, `:669-678`).
- **FACT.** MO2 first reads the XML as it is. If that fails, it drops the XML header and tries the text as UTF-16,
  then UTF-8, then Latin-1, because such files often name the wrong encoding in their header (`:181-229`).
- **FACT.** The root's parts: `moduleName`, `moduleImage`, `moduleDependencies`, `requiredInstallFiles`,
  `installSteps`, `conditionalFileInstalls` (`:1261-1280`).

## 3. Steps, groups and options

- **FACT.** `installSteps` holds `installStep` elements (attribute `name`), each with an optional `visible`
  condition and `optionalFileGroups`; these hold `group` elements (`name`, `type`), each with `plugins` holding
  `plugin` elements (`name`): the options (`:1045-1140`).
- **FACT.** `installSteps`, `optionalFileGroups` and `plugins` each take an `order` attribute: `Ascending`,
  `Descending` or `Explicit`; without it, `Ascending` (`:697-702`, `:934-937`, `:1126-1128`). Ascending and
  descending sort by name; explicit keeps the file's order.
- **FACT.** A group's `type` is `SelectAtLeastOne`, `SelectAtMostOne`, `SelectExactlyOne`, `SelectAny` or
  `SelectAll` (`:711-720`). For "at most one" MO2 adds a "None" choice (`:1038`).
- **FACT.** An option has a `description`, an `image`, `files`, `conditionFlags` (each `flag` has a `name` and its
  text as the value) and a `typeDescriptor` (`:889-903`, `:868-870`). The type is `Required`, `Optional`,
  `Recommended`, `NotUsable` or `CouldBeUsable` (`:729-738`): either one fixed `type`, or a `dependencyType` with a
  `defaultType` and `patterns`, where the first pattern whose `dependencies` hold gives the type
  (`:833-857`, `:914-926`).

## 4. Files

- **FACT.** A `file` or `folder` entry has `source`, `destination` (the source when the attribute is absent),
  `priority` (0 when absent), and `alwaysInstall` and `installIfUsable`. An entry with an empty source is passed
  over (`:749-786`).
- **FACT.** What is installed: the `requiredInstallFiles`; the files of each `conditionalFileInstalls` pattern
  whose `dependencies` hold; and the files of each chosen option on a step that shows (`:548-582`). MO2 does not
  act on `alwaysInstall` or `installIfUsable` there.
- **FACT.** The entries are then put in order of priority and, within one priority, in the order the file names
  them (`:584`, `:878-884`), and copied in that order. A folder's contents are merged into the destination; a
  file replaces one already there (`:318-366`).
- **FACT.** A source is taken relative to the folder that holds `fomod` (`:326-329`). A file's destination that is
  empty or ends in a slash names a folder, and the file keeps its own name there (`:307-310`).
- **FACT.** A source the archive does not have is reported, and the owner may install anyway (`:521-545`).

## 5. Conditions

- **FACT.** `dependencies` (and a step's `visible`) hold conditions joined by the attribute `operator`: `And`
  (also without it) or `Or`; and may nest (`:1158-1195`, `:387-410`).
- **FACT.** `fileDependency` (`file`, `state`) holds when the plugin of that name is in the named state, one of
  `Active`, `Inactive`, `Missing`, in the load order (`:412-442`).
- **FACT.** `flagDependency` (`flag`, `value`) looks through the earlier steps that show, latest first, for a
  chosen option that sets the flag, and holds when that value equals the one asked for. A flag nobody set equals
  only the empty value (`:1358-1399`).
- **FACT.** `gameDependency`, `fommDependency` and `foseDependency` compare a version (`:476-518`).
- **METHOD.** ModTrap does not know the game's version (DESIGN§16.2), so it takes a version condition as met.

## 6. What is chosen to begin with

- **FACT.** In a group that is not "all", a `Required` option is chosen and cannot be unticked, a `Recommended` one
  is chosen, a `NotUsable` one cannot be chosen (`:1535-1600`). In "all", every option is chosen.
- **FACT.** Where one must be chosen and none is, MO2 picks the first merely optional one, else the first that
  "could be usable", else the first of all (`:1603-1620`). "At least one" with nothing chosen keeps the owner from
  going on (`:1452-1485`).

## 7. Open points

- **METHOD.** Not read: `moduleDependencies`' effect on whether the installer runs at all, images, and the older
  script-based installers (C# scripts), which ModTrap does not run and hands to MO2.
