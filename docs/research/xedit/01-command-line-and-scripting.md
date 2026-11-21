# XE01. xEdit: the command line and scripting

## 1. Source

`github.com/TES5Edit/TES5Edit`, tag `xedit-4.1.5f` at `f5c00f3` (2024-04-27), the version the owner's screenshots
show. Licence: MPL-2.0 (its `LICENSE.txt`). Cited as `file:line`. Read only; nothing copied, and ModTrap's script is
written from scratch.

## 2. Script mode

- **FACT.** `-script:<file>` puts xEdit into its script tool mode (`xEdit/xeInit.pas:616-630`, `:682-684`). A
  relative name is looked up in the scripts folder; an absolute path is taken as given
  (`xEdit/xeMainForm.pas:4895-4898`). The scripts folder then becomes the script's own folder (`:4912`), which a
  script reads as `ScriptsPath` (`xEdit/JvI/xejviScriptHost.pas:126-128`); `DataPath` and `ProgramPath` are there
  too (`:121-132`).
- **FACT.** Script mode sets "I know what I'm doing", loads BSAs and builds references (`xeInit.pas:1307-1311`);
  `-nobuildrefs` turns reference building off (`:1385`).
- **FACT.** A switch such as `-sse` sets the game (`xeInit.pas:545-560`).
- **LIKELY.** Without one, the game comes from the program's file name (`SSEEdit.exe`). Read only in passing.

## 3. What gets loaded

- **FACT.** `-autoload` skips the module selection window and loads the active plugins of the plugins file
  (`xeInit.pas:1075`; `xeMainForm.pas:5299-5307`).
- **FACT.** `-P:<file>` names the plugins file to use in place of the game's own (`xeInit.pas:493-510`); `-D:` the
  data folder, `-B:` the backup folder, `-R:` a second log file (`:518-535`).
- **LIKELY.** A plugins file listing only some plugins, each marked active, makes xEdit load those and their
  masters and nothing else. The loading code was read only as far as `:5307`.

## 4. Running and closing

- **FACT.** When loading ends, script mode runs the script by itself (`xeMainForm.pas:20427-20431`,
  `:17277-17278`), with every loaded file selected (`:4915`). `-autoexit` then closes xEdit (`:17280`, `:16980`).
- **FACT.** `Initialize`, `Process` and `Finalize` are each called only if the script has them
  (`xeMainForm.pas:8434-8459`); a script may do all its work in `Initialize`.
- **LIKELY.** There is no hidden or headless mode: none of the switches read in `xeInit.pas` hides the window.

## 5. Saving and backups

- **FACT.** Script mode is one of the "auto modes" (`Core/wbInterface.pas:4753-4765`). On close, an auto mode saves
  every changed file without showing the "Save changed files" window (`xeMainForm.pas:15588-15630`).
- **FACT.** A save writes `<plugin>.save.<timestamp>` beside the plugin, then renames it over the plugin, at once
  or at shutdown; a file whose contents did not change is not replaced (`xeMainForm.pas:15690-15760`).
- **FACT.** The replaced file goes to the backup folder, `<Data>\SSEEdit Backups\` unless `-B:` says otherwise
  (`xeInit.pas:518-520`), unless backups are switched off in xEdit's settings (`xeMainForm.pas:15614-15626`).

## 6. Logs

- **FACT.** The message log is written on close to a file in xEdit's folder named from the game and the mode,
  and to the file named with `-R:` (`xeMainForm.pas:6221-6225`). Neither is written while xEdit works.
- **FACT (the owner's screenshot, 2026-11-20).** In an SSEEdit folder the two names are `SSEEdit_log.txt` and, for
  script mode, `SSEScript_log.txt`. An earlier draft of this note had the second name wrong.

## 7. Functions a script can call

All in `xEdit/JvI/xejviScriptAdapter.pas`:

- **FACT.** `ReportRequiredMasters` (`:641-655`, `:2117`): the plugins an element needs.
- **FACT.** `Remove` (`:2097`), `RemoveElement`, `RemoveByIndex`: remove a record, an element, an entry.
- **FACT.** `CleanMasters`, `SortMasters` (`:1520-1533`, `:2214-2215`); `MasterCount`, `MasterByIndex`, `HasMaster`.
- **FACT.** `FileWriteToStream` (`:1658-1675`, `:2230`): writes a loaded plugin to a stream the script opens.
- **FACT.** `GetElementState`, `SetElementState`, `ClearElementState` with `esModified` and `esUnsaved`
  (`:262-264`, `:280-290`, `:1994-1996`).
- **FACT.** `AddMessage` writes to xEdit's Messages tab. xEdit's own scripts save string lists to files
  (for example `Build/Edit Scripts/Save script source.pas:30`).

- **FACT.** A script's call `ReportRequiredMasters(element, list, a, b)` reaches the element with `a` as "as new"
  and `b` as "recursive" (`:641-655`). For a main record with "as new" false it adds the plugin the record itself
  belongs to; with "recursive" true it goes through everything under the element that can hold form IDs
  (`Core/wbImplementation.pas:7572-7592`, `:12735-12749`). So one call on a record, false and true, gives every
  plugin that record needs, and the same call on a part of it gives what that part needs.
- **FACT.** `RecordCount` and `RecordByIndex` go over a plugin's records as one flat list
  (`Core/wbImplementation.pas:4269-4272`, `:4325-4328`). `FileCount` and `FileByIndex` go over the loaded files
  (`xEdit/JvI/xejviScriptHost.pas:173-181`).
- **FACT.** `GetElementState`, `SetElementState` and `ClearElementState` take a number for the state, `esUnsaved`
  among them, and answer whether it was set (`:259-325`).
- **FACT.** A named parameter is matched whole and without regard to case: `-P:` only as `P:`, `-script:` only as
  `script:` (`Core/wbCommandLine.pas:37-64`). `-script:` does not collide with `-S:`.

## 8. xEdit's own "Report masters" script

- **FACT.** `Build/Edit Scripts/Report masters.pas` asks which masters to check, then for each record calls
  `ReportRequiredMasters` on the record and on each of its elements, and prints the record, or the record and
  element, that needs a chosen master. It changes nothing.

## 9. Open points

- **METHOD.** Whether clearing `esUnsaved` on a file keeps §5's save from touching it, whether `CleanMasters`
  behaves from a script as from the menu, whether a script can append to a file as it goes, and §3's LIKELY item:
  the probe on the owner's PC (DESIGN§9).

## 10. Reading conflicts from a script

- **FACT.** A script can ask whether a record is in conflict: `ConflictAllForMainRecord(record)` and
  `ConflictThisForMainRecord(record)` are answered by xEdit's script host (`xEdit/JvI/xejviScriptHost.pas:293,
  301`), and xEdit ships a script that uses them (`Build/Edit Scripts/Detect conflict between elements.pas`; read
  for what it shows of the interface, not copied).
- **FACT.** Both answer with a level. Over all plugins (`TConflictAll`, `Core/wbInterface.pas:449-457`): unknown,
  only one, no conflict, benign conflict, override, conflict, critical conflict, numbered from 0. For the one
  plugin's copy (`TConflictThis`, `:464-477`): unknown, ignored, not defined, identical to master, only one, hidden
  by mod group, master, benign conflict, override, identical to master but wins a conflict, wins a conflict, loses
  a conflict. The names are also given to scripts as constants (`xEdit/JvI/xejviScriptAdapter.pas:2032-2048`).
- **FACT.** A script can walk a record's copies: `IsMaster`, `MasterOrSelf`, `OverrideCount` and `OverrideByIndex`
  (`xEdit/JvI/xejviScriptAdapter.pas:2173-2182`).
- **METHOD.** Used by ModTrap's record check (DESIGN§16.5, `modtrap/xedit/ModTrapRecords.pas`), which loads the
  whole active load order. The script takes the levels as numbers and guards each call. LIKELY that the levels are
  worked out when a script asks in an xEdit started with `-autoexit`; to be seen on the owner's PC.
