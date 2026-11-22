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
  `:17277-17278`), with every loaded file selected (`:4915`). (Corrected 2026-11-21, §11: an earlier reading here said `-autoexit` then closes xEdit. It does not in script mode.)
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

## 11. What the first real run showed (2026-11-21), and the source behind it

- **FACT.** With `-script:` xEdit is in its script tool mode: the script's file ending decides it
  (`xEdit/xeInit.pas:612-631`). The window's title is then "SSEScript".
- **FACT.** `-autoload` and `-autoexit` are read only in edit mode (`xEdit/xeInit.pas:1063-1079`). In script mode
  xEdit asks which plugins to load (§13; an earlier wording here, "loaded without asking anyway", was wrong), and
  after the script xEdit writes "You can
  close this application now." and stays open (`xEdit/xeMainForm.pas:4923`): the timer that would close it runs
  only when `-autoexit` was read (`:17268-17281`), which in script mode it never is. Seen on the owner's PC with
  xEdit 4.1.5f: xEdit stayed open and MO2 waited for it.
- **METHOD.** So ModTrap closes the xEdit it started, once the script's end line is in the report: it asks it to
  close as a click on the window's X does, and ends it if it has not gone after a short while. Ending it loses
  nothing: the script has written what it writes itself.
- **FACT.** Without `-D:` xEdit works out the game's Data folder itself: a folder beside its own program, else the
  game's installation as the shop's client or the registry names it (`xEdit/xeInit.pas:360-420`). It then drops
  from the plugins file every plugin that is not in that folder.
- **FACT (the owner's PC).** MO2's `-a` replaces the executable's own arguments (MO01§3). The modlist's xEdit
  entry carries its own arguments; with them replaced by ModTrap's, xEdit read the Data folder of another
  installation of the game, not the one MO2 fills, found none of the three plugins it was told to load, and
  loaded the game's own 81 files. Its log names the folder it used.
- **METHOD.** ModTrap now carries the executable's own arguments over, less the switches it sets itself and those
  that put xEdit into another mode, and adds `-D:` with the game folder MO2 manages when the executable's own
  arguments name none. The script reports xEdit's data path and file count (`DataPath`,
  `xEdit/JvI/xejviScriptHost.pas:131-132`), and a run in which xEdit did not load a plugin it was told to is a
  failure that says where xEdit looked.

## 12. What the first passing probe showed (2026-11-21, xEdit 4.1.5f on the owner's PC)

- **FACT.** Started in script mode with `-P:` and `-D:`, xEdit loaded the game's own plugins and exactly the
  plugins of the plugins file (84 files for 3 listed). §3's LIKELY item holds.
- **FACT.** xEdit loaded ModTrap's invented plugins (XE02, `modtrap/probe.py`): a header, groups of global
  variables and a form list, written from the format's description alone.
- **FACT.** The reading script's chain for a form-list entry: the entry is `LNAM - FormID`, a sub-record whose
  value is an integer; its list is `FormIDs`, of element kind `etSubRecordArray`, with no value kind given.
  ModTrap's list of arrays that may be shortened names it rightly.
- **FACT.** The owner's xEdit entry carries `-pseudoesl`: the invented plugins were numbered as light plugins, and
  the form ids the reading script reported were the ones the changing script then found.
- **FACT.** The changing script removed one entry and one record as told, `CleanMasters` took the master off, and
  the plugin written through `FileWriteToStream` reads, by ModTrap's own reader, as a plugin with no master.
- **FACT.** After the changing script had taken the "changed" marks off, xEdit closed when asked, without a
  question, and every original was byte for byte unchanged. §9's open point on `esUnsaved` holds for this case.

## 13. The "Module Selection" window in script mode (source, and the owner's PC, 2026-11-21)

- **FACT.** xEdit loads without asking only in its plugin modes (quick clean and the like) or when `-autoload` was
  read; otherwise it opens its module selection window, preset to the active plugins, and loads what is ticked
  when OK is pressed; closing the window any other way ends xEdit (`xEdit/xeMainForm.pas:5296-5330`). `-autoload`
  is read only in edit mode (§11), and script mode is not a plugin mode, so a run with `-script:` always shows
  the window. Seen on the owner's PC: the window appeared on every run, with the plugins of the plugins file
  ModTrap had passed already ticked, and the owner pressed OK each time.
- **FACT.** The window is a form of class `TfrmModuleSelect` with the caption "Module Selection"; its OK is a
  `TButton` with the caption "OK" (`xEdit/xeModuleSelectForm.dfm:1-39`). xEdit opens the same form for other
  things the user asks for in its window (adding masters, comparing), which no ModTrap run does.
- **METHOD.** For a run ModTrap started, the ticked list is ModTrap's own list, so nothing is to be chosen.
  ModTrap presses that OK itself (`modtrap/winauto.py`): a visible top window of that class and caption, owned by
  the xEdit program the run started, and in it an enabled button named OK; it looks every few seconds only until
  the script's first line arrives, and presses a limited number of times. LIKELY until seen on the owner's PC:
  that the press, sent as a message from another program, is taken (it is not when xEdit runs with higher
  rights than ModTrap). If it is not, the owner presses OK as before; the page and the log say so.

## 14. Telling where a part of a record comes from (source; unproven on a real list until the next dry run)

- **FACT.** A script can walk every version of a record: `MasterOrSelf` gives the first, `OverrideCount` and
  `OverrideByIndex` the rest (`xEdit/JvI/xejviScriptAdapter.pas:2173-2180`), and `GetLoadOrder` of each version's
  file says where it loads (`:2207`). `ElementByName` finds a named part of a version (`:2133`), and
  `GetEditValue` gives a value as text (`:2093`).
- **FACT.** There is a ready-made comparison (`SortKey`, `:2090`), but a container's key is built from its
  members' keys (`Core/wbImplementation.pas:7090-7103`) and a definition may give a member a key of its own, so
  two different parts could share a key. **METHOD.** ModTrap's script therefore compares its own text of a part:
  every element's name and value, all the way down.
- **FACT.** A script can also copy a part from one version of a record into another (`wbCopyElementToRecord`,
  `:2113`) and take an element out (`RemoveElement`, `:2145`): what putting a part back would use. Not used yet.
- **METHOD.** For a record of another plugin that the dependant overrides, and each direct part of it that needs
  a trapped plugin, the reading script writes one line (`C`): the last plugin before the dependant whose version
  of the part is the same as the dependant's; the dependant's last master, not trapped, whose version needs no
  trapped plugin, and whether that version is present, absent, or would need a master the dependant lacks; and,
  for a list, whether the list without the entries that need a trapped plugin is exactly that master's list.
  The script only reads.

## 15. A script's file writes fail while another program has the file open (the owner's PC, 2026-11-21)

- **FACT (the owner's PC).** The second real dry run stopped part-way: the script's write of its progress file
  failed with "Cannot create file … The process cannot access the file because it is being used by another
  process", raised at the line that saves the list. Nothing had been changed; the run was read-only.
- **LIKELY.** A string list saved to a file creates the file anew and asks for it alone, so the write fails
  while any other program holds the file open, however that program opened it. The script wrote the file twice
  within the same second; the other holder was ModTrap reading it, or a virus scanner looking at a file just
  written. The first real run did the same writes and was lucky.
- **FACT.** The script engine has no `Sleep`; `Now` is there (the engine's own SysUtils unit is registered,
  `xEdit/JvI/xejviScriptAdapter.pas:2289`), and `try … except` catches the failure (the run's own handler caught
  it and reported it).
- **METHOD.** In all three scripts a missed write of the progress file is let go (the next line writes the whole
  list again, and the end is told by the report), and the report's write is tried again for some seconds before
  it counts as a failure. ModTrap reads only the last bytes of the report when it looks for the end line.

## 16. Putting a part back, and what the first evidence run showed (2026-11-21)

- **FACT (the owner's PC).** The reading script of §14 ran on the real list: 74 `C` lines for 17 dependants, in
  90 seconds, nothing changed. `MasterOrSelf`, `OverrideByIndex`, `GetLoadOrder` and `ElementByName` behave as
  §14 reads them; the same part was found in an earlier plugin for most parts, and not for lists that a big
  patch had merged itself.
- **FACT.** xEdit's own shipped scripts copy a whole part from one version of a record to another with
  `ElementAssign(target, LowInteger, source, False)`, lists included
  (`Build/Edit Scripts/Worldspace copy landscape.pas:219-225`). **METHOD.** ModTrap's changing script uses the same
  call to put a part back, then reads the part again: it must no longer need a trapped plugin and its text
  (§14) must equal the source's, or the action is refused and that dependant is not written. LIKELY until the
  probe has run it: that the call does this for a single link; unproven for a script attachment (`VMAD`) until
  the first real run, where the same check guards it.
- **METHOD.** For a list, the reading script also says, for each entry that needs a trapped plugin, which
  earlier plugin's version of the list has the very same entry (`G`). For conditions it reads each entry's
  type (`CTDA\Type`, whose lowest bit is "or") and marks an entry whose removal would join the conditions on
  either side differently: one that ends a run of "or". Such an entry is never taken out automatically.

## 17. A record's group of children keeps its master in use (the owner's PC and the source, 2026-11-21)

- **FACT (the owner's PC).** In the first real demasters one plugin was kept back twice: all 49 of its actions were
  done, no record in it needed the trapped plugin any more, and yet after Clean Masters the trapped plugin was
  still among its masters. The plugin held copies of six of the trapped mod's dialogue topics with their lines.
- **FACT.** Clean Masters keeps every master that anything in the file uses, and a group counts: for a group of
  type 1 or 6 to 10 (the children of a world, a cell or a topic), the plugin its label's id belongs to is marked
  as used (`Core/wbImplementation.pas:16645-16683`). A topic's lines lie in such a group, labelled with the
  topic's id.
- **FACT.** Taking a record out does not take its group of children out (`TwbMainRecord.Remove`,
  `Core/wbImplementation.pas:12512-12545`): with the topic gone, its group stayed, empty, still labelled with the
  trapped plugin's id. Taking a group out takes everything in it out first and then unhooks it from its record
  (`TwbGroupRecord.Remove`, `:17087-17100`).
- **FACT.** A script reaches that group with `ChildGroup` (`xEdit/JvI/xejviScriptAdapter.pas:2188`).
- **METHOD.** When the changing script takes out a whole record, it first takes out the record's group of
  children, if it has one. What was in the group cannot live without its record. A record of the job that went
  with such a group counts as done. If a master is still in use although no record needs it, the report now says
  that, in those words.

## 18. What a plugin really changes is xEdit's to say, not a reader of bytes (the owner's list, 2026-11-21)

- **FACT (the owner's list).** ModTrap's own reader, comparing a mod's version of a record with its master's,
  called several worldspaces and cells "changed" that the mod only holds. The fields named were the
  worldspace's name and a cell's list of regions.
- **FACT.** The game's own files keep names in strings files, and a record holds only a number into them; a
  plugin made later holds the name as text. A list such as a cell's regions is saved in sorted order by xEdit and
  by tools built on it, and in another order by the game's editor. In both cases the bytes differ and the
  meaning is the same. Only a program that knows what each field of each record is can tell: xEdit does.
- **FACT.** A script reads every part of a record as xEdit shows it (`GetEditValue`, §14): a name as its text,
  whichever way it is stored, and a sorted list in sorted order whichever way it was saved.
- **METHOD.** In the dry run, the reading script looks through the trapped plugins and the patches made for
  them, and for each record such a plugin holds but does not own, compares each of its parts with the same part
  in the last of the plugin's own masters that holds the record. A record with no differing part is not
  reported. For one that differs it writes a line (`T`) with the record and the four-letter types of the fields
  that differ, and for each plugin looked through a line (`V`). ModTrap judges tools from these lines alone
  (TL01§11). Unproven until the owner's next dry run; the probe runs the new lines of the script on the invented
  plugins first.

## 19. A change is not yet a stake: what a tool's output can owe to a plugin (the owner's list, 2026-11-21)

- **FACT (the owner's list, a dry run with §18's lines).** For a dialogue mod the script reported, truthfully, a
  worldspace changed in its table of heights, and several cells changed in their place on the grid. A patcher's
  plugin held the same table of heights, and was told to run again.
- **LIKELY.** These are values the game's editor writes when it saves a plugin that holds such a record: the
  same in every plugin saved that way, and different from the game's own files. Many plugins of a large list
  then say the same thing in that part. The patcher's copy need not come from this mod at all.
- **METHOD.** The script now also tells, for each record a leaving plugin holds but does not own, the parts in
  which it has a **stake** (line W). A part is a stake in one of two ways. (1) The plugin has the last word on
  the record among the plugins no tool made, and the version that would win with the leaving plugins gone says
  something else in that part: a tool that works from the winning version saw this plugin's value, and will
  see another. (2) The plugin changed the part (§18), and no version of the record in a plugin that stays, the
  record's own plugin included, says the same: a tool that merges from every version could have it from here
  only. The leaving plugins are those of `touch.N`; the plugins tools made are named in the job as `made.N`,
  and have no say in what wins.
- **METHOD.** Tools are judged from the stakes only (TL01§11's second question, asked of fewer parts). The count
  of all changes (T) is kept and shown beside it.
- **Limit.** A part the plugin removes, where the next in line has it, is not told. A tool's plugin ModTrap
  does not know as such counts as an ordinary plugin: where it wins a record, the mod has no stake there.
- **Not checked** on a real xEdit yet: the lines are exercised by the probe's dry run, on invented plugins.

## 20. An OK pressed the moment Module Selection appears can make xEdit show an error (the owner's PC, 2026-11-21)

- **FACT (the owner's PC, xEdit 4.1.5f).** In one run xEdit showed a message of its own right after start:
  "Access violation at address … in module 'SSEEdit64.exe'. Execution of address …". ModTrap's log has the
  press of OK in Module Selection four seconds after xEdit's session began, as its last line before the
  message. In that run MO2 was already open, so xEdit came up sooner than in the runs before it.
- **FACT.** xEdit's own log of that run has no error. It loaded the 445 plugins of ModTrap's list, ran the
  script to its end, and the five new plugins passed every check.
- **FACT (xEdit's source, `xEdit/xeModuleSelectForm.pas:466-489` at commit `f5c00f3`).** When the window shows,
  it still works: it walks the list as a load would, sets the focus, picks a row. Its OK handler is at
  `:621-627`.
- **LIKELY.** ModTrap looked for the window every three seconds and pressed OK at the first look that found the
  button enabled. This time that look fell while the window was still being set up. Not proven: the source at
  hand is not 4.1.5f's, and the message names no place.
- **METHOD.** OK is pressed only once the window has stood ready, button enabled, for two and a half seconds:
  the first look that finds it only notes the time (`winauto.press_module_selection_ok`). A window that stops
  being ready starts the wait over. ModTrap looks every second and a half.
- **Not done.** ModTrap does not answer xEdit's error message: it cannot know what it says. The owner sees it
  and presses its OK; the run then goes on, or fails with its reason as any run can.

## 21. A script's properties are a list whose entries can be taken out (2026-11-22)

- **FACT (xEdit's source, `Core/wbDefinitionsTES5.pas` at commit `f5c00f3`).** A script on a record has
  `Properties`, a sorted list of `Property` (`:4744`). A property has a name, a type, and a `Value` that is,
  by its type, nothing, an object, a text, a number, or a list of one of those; a list of objects is
  `Array of Object` (`:4713-4736`). An object is the record it points at, inside `Object Union` (`:4689`).
- **FACT (the owner's list).** The reading script reported such a pointer as: the record's script data, its
  scripts, a script, its `Properties`, a `Property`, its value, the object, the id. The nearest list above the
  pointer is `Properties` (or, in a property that is a list, `Array of Object`).
- **METHOD.** ModTrap takes that entry out, as it takes an entry out of a list of keywords (§7): by its route
  from the record, highest place first, after checking that the element there is the one the dry run named and
  still needs the trapped plugin. With the property gone the script has nothing there; with the mod gone and the
  property left, it would point at nothing as well. xEdit keeps the list's count.
- **Not proven by the probe.** The probe's invented plugins have no script. The run's own checks apply: an entry
  xEdit will not take out leaves that plugin as it was; the new plugin must no longer name the mod; xEdit must
  find nothing left that needs it.

## 22. Unused bytes are no part of what an element says (2026-11-22)

- **FACT (xEdit's source, commit `f5c00f3`).** xEdit names the padding inside a field `Unused` and marks it to be
  ignored when plugins are compared, as in a cell's grid field (`Core/wbDefinitionsCommon.pas:513`); the name
  stands in about a hundred places of the definitions for this game (`Core/wbDefinitionsTES5.pas`).
- **FACT (the owner's list).** ModTrap's scripts compared elements part by part and took those bytes for content.
  Every "stake" in a cell that a dialogue mod and a follower mod were said to have was this (TL01§15, WHY§77).
- **METHOD.** When the scripts put an element into comparable text (`Shape`, in both scripts), a part named
  `Unused` is left out. Nothing else changes; the scripts changed, so the probe runs again.
