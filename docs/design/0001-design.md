# Design 0001: ModTrap

*2026-11-20 · Adopted as the working design under MT17; revised the same day after the owner's answers (MT4 to
MT11, MT14, MT15, MT17, MT18). Built so far: the reader and the page (WHY§29), the dry run (WHY§31), sessions (WHY§33), the Steps tab (WHY§35). The demaster itself and the adding of a mod are written, tested against stand-ins, and on the page behind a switch that is off: only a ModTrap started with `--allow-changes` can write to an instance (WHY§39, WHY§44, WHY§46). A History tab shows what was changed (§12). Adding mods (§16, MT21) is built as far as it only reads (WHY§40). Open choices are in [DECISIONS.md](../DECISIONS.md); findings are cited by code: `WHY§n` is
[REASONING.md](../REASONING.md), `MO01` and `XE01` are [the research notes](../research/README.md).*

## 1. What ModTrap does

The owner picks a modlist folder (an MO2 instance). ModTrap shows the whole modlist as MO2 has it: every mod with its
priority, every plugin with its place in the load order. The owner ticks the mods to take out and presses **Demaster
Selected**. ModTrap then does, by itself, what the community's "Master Removal" procedure has the user do by hand in
xEdit (WHY§2), for every plugin that depends on the ticked mods, and shows its work line by line in a terminal on the
page. At the end the ticked mods are **disabled, never removed** (MT9), with no "missing master" errors, and
everything ModTrap changed can be put back with **Revert** (MT14).

Words used below:

- **trapped mod**: a mod the owner ticked. Its plugins are the **trapped plugins**.
- **dependant**: a plugin of another mod that lists a trapped plugin among its masters.
- **patch-only**: a plugin that exists only for a trapped mod. It is switched off, not demastered (MT6): its mod is
  disabled, or the plugin alone is deactivated when its mod holds other plugins (WHY§26).
- **safe folder**: ModTrap's copies of every file a job will change, taken before it changes any (MT14).
- **history**: ModTrap's dated record of every change it made to the instance (MT15).

Out of scope: the other steps a modlist's guide may ask for afterwards (installing replacements, re-running an
animation or patcher tool). ModTrap ends when the masters are gone and the mods are disabled, says what it did, and
reminds the owner which of the instance's tools may need a re-run (§13).

## 2. Shape (the DataPiler pattern)

- One program on the owner's PC, Python standard library only, started by a launcher (MT11). It serves one page on
  `127.0.0.1` and opens it in the browser. Host, Origin and per-start token checks, a strict content policy, no CDN,
  no remote fonts, no analytics: DataPiler's server, reused and credited (WHY§9).
- Looking never writes. Writing happens only in a job, only after the owner confirms a plan, only after the safe
  folder is complete, and only to the files the plan named (§8).
- A job is data: the instance, the profile, the trapped plugins, the dependants and what to do with each. The
  script that xEdit runs is one fixed file of ours; it reads the job from a small file beside it (XE01§2, WHY§11).
- ModTrap contains no part of MO2 or xEdit. It finds and calls the owner's installed copies.
- One ModTrap runs at a time, and it knows its version (§17).

## 3. Reading the instance (no xEdit needed)

From `ModOrganizer.ini` and the chosen profile (MO01§2), read-only:

1. the mods folder, the profiles folder, the game's folder, the selected profile, and the configured executables;
2. `modlist.txt`: every mod, its priority, whether it is enabled;
3. each mod folder's plugins (`.esp`, `.esm`, `.esl` at its top level);
4. each plugin's header, read by ModTrap's own small reader: its master list and its flags. Nothing else of a
   plugin is read by our code (WHY§10);
5. `plugins.txt` and `loadorder.txt`: which plugins are active and in what order.

Where the same plugin name exists in several enabled mods, the one MO2 would use (highest priority) counts, and the
page says so. From this ModTrap builds, for every mod: its plugins, their masters, and their dependants; and for the
whole instance, a **health check**: every active plugin whose master is missing or inactive, which is what MO2's own
warning reports.

Skyrim Special Edition and every Anniversary Edition version are supported (MT7): the plugin header ModTrap reads
is the same across them, and xEdit does the rest.

## 4. The page

- **Instance bar.** The modlist folder (dropped on the page or pasted, MT19; found as in WHY§30; remembered), the profile, the game and its version, the tools
  found (§13), whether MO2 is open, and the health check's result.
- **Mods.** The full modlist in MO2's order, under its separators as groups that fold (WHY§32), each row with its priority number, enabled or disabled, its plugins,
  and a count of dependants; a search box and filters (enabled only; has plugins; has dependants; changed by
  ModTrap). A mod with no plugins, or whose plugins nothing depends on, shows "can be disabled as it is".
- **Plugins.** The full load order, each row with its position, its kind (esm, esp, esl or light-flagged), its mod,
  active or not, its masters and its dependants.
- **Selection panel.** For the ticked mods: every dependant, grouped by the mod it lives in, with what ModTrap
  proposes for it (§5) and a way to change that per dependant.
- **Demaster Selected.** Opens the plan (§6.1). Nothing has run yet.
- **Terminal.** A live, scrolling log of the job: ModTrap's own steps, and the lines our script writes as xEdit
  works (WHY§5). A copy is kept in ModTrap's work folder.
- **Steps.** §14: the whole job as an ordered list, ModTrap's steps and the owner's.
- **Result.** Per dependant: masters before and after, what was taken out of it, what was left alone and why.
- **Process.** §18. The demaster as it goes: each stage a box linked to the next, its tasks inside, coloured by
  state.
- **History.** §12. Every change ModTrap made, with **Re-enable** on each disabled mod and **Revert** on each job.

## 5. What happens to each dependant

For each dependant plugin, one treatment. ModTrap proposes it; the owner can change it (MT6):

- **Demaster** (§6): the plugin does other things too, and should go on working without the trapped mod.
- **Switch off** (patch-only): the plugin exists only for the trapped mod. ModTrap **disables its mod** when every
  plugin that mod provides is patch-only, and **deactivates the plugin alone** when it is one among others, as in a
  patch collection (WHY§26). The first reading comes from the headers (which of a mod's plugins depend on the
  trapped mod); the dry run settles it: the plugin is a patch for the mod by its few masters and its name
  (at most two masters besides the game's own and the trapped ones, and the mod's name or initials in its own:
  WHY§52), or nothing of it would remain.
  Where most of a mod's plugins depend on the trapped mod and nothing else needs the rest, ModTrap proposes
  disabling the mod whole and names the leftover plugins for the owner to judge (WHY§28).
- **Run the tool again**: the plugin is the generated output of a patcher or generator (§13). The output of an
  editor such as xEdit cannot be made again by ModTrap, and is demastered (WHY§28).
- **Skip**: the owner will deal with it another way; the job then cannot disable the trapped mod, and says so.

Within a dependant that is demastered, each thing that needs a trapped plugin is one of these cases (MT4): A, B
and (since the first real dry runs, WHY§55) C are done automatically, D always becomes a step for the owner (§14):

| Case | What needs the trapped plugin | What ModTrap does (proposed) |
|---|---|---|
| A | The record itself belongs to the trapped plugin (the dependant overrides it) | Take the dependant's copy of the record out of the dependant |
| B | An entry in a list inside a record that belongs to someone else (a FormID list entry, a levelled list entry, a keyword in a keyword list) | Take that entry out, keep the record |
| C | A part of a record that the dependant only carries on from the trapped mod (a condition, a script attachment, a single field) | Put the part back as the dependant's last master without the mod has it (or take it out, if that master has none); in a list the dependant merged itself, take out the entries that are the mod's. Only where the dry run's evidence shows the part is not the dependant's own doing (XE01§14, XE01§16, WHY§55); else as D |
| D | Anything else, or anything xEdit refuses to change | Change nothing in this dependant; report it as "needs you", with the record and field |

These are edits inside the dependant plugins only. The trapped mod's own files are never edited and never deleted.
A dependant with any case D is not half-done: it is left exactly as it was and named in the result. Nothing is
forced. After the edits the script runs xEdit's Clean Masters on the dependant and reports again; a dependant counts
as done only if the trapped plugins are gone from its master list **and** the report is empty.

## 6. A job, step by step

### 6.1 Plan

Built from §3 alone, shown before anything runs: the trapped plugins; every dependant and its treatment; the
plugins xEdit will load (the dependants and all their masters, in load order, and nothing else, XE01§3); every file
the job would change; the exact command it will run. The owner confirms or goes back.

### 6.2 Dry run, then the safe folder

Always first. xEdit is started through MO2 (§7) with our script in **report** mode: it changes nothing and writes
nothing but its report. The report lists, per dependant, every case A to D it found. The page shows it as the
detailed plan: "this is exactly what will be changed, in which files".

At that point ModTrap knows every file the job will touch, and copies each into the job's **safe folder** (§11):
this step is automatic and cannot be skipped. Only then can the owner confirm the run.

### 6.3 The run: on copies

The dependants are never worked on where they live. ModTrap works on copies, by one of two routes; the probe (§9)
settles which the owner's setup supports, and the first is preferred:

1. **Write-out.** xEdit loads the dependants as they are, our script changes them in memory, writes each changed
   plugin into ModTrap's work folder (XE01§7), and marks the loaded file as not needing a save, so that xEdit's own
   save on close leaves it alone (WHY§4).
2. **Work mod.** ModTrap puts copies of the dependants in a temporary mod of its own at the top of the modlist, so
   that xEdit loads and saves those copies; the temporary mod is removed afterwards.

For each dependant the script does the edits, Clean Masters, and the report again, and writes a line to its
progress file after each step. A stopped or failed run leaves the instance exactly as it was.

### 6.4 Verify the copies

Before anything is put into the modlist, each demastered copy is checked by ModTrap's own reader (§3.4): it must be
well-formed, the trapped plugins must be absent from its masters, every remaining master must be active in the load
order, and the script's second report for it must be empty. Every original is hashed again and must be unchanged.
A copy that fails is dropped and its dependant reported; the others can go on.

### 6.5 Put in place, then verify the instance

1. **Insert.** The verified copies go into the modlist under their original file names, in a ModTrap mod placed
   above the originals (MT5), which MO2 then uses in their place. The originals stay as installed.
2. **Disable** (MT9, Auto on by default). With MO2 closed, ModTrap disables the trapped mods and the patch-only
   mods in the profile's `modlist.txt`, and deactivates the patch-only plugins of other mods in `plugins.txt`
   (WHY§26); with Auto off, it lists them for the owner to do in MO2.
3. **Verify the instance.** ModTrap reads the instance again (§3) and runs the health check: no active plugin may
   list a master that is missing or inactive, and the load order must otherwise be as it was. Then it asks the
   owner to open MO2 and confirm that MO2 shows no missing-master warning; the answer is kept in the history.
4. If any check fails, ModTrap offers **Revert** at once and says which check failed.

## 7. Starting xEdit through MO2

`ModOrganizer.exe -p "<profile>" run -e -a "<arguments>" "<xEdit's name in MO2>"` (MO01§3). MO2's `-a` replaces
the executable's own arguments, so the arguments are: those the modlist set for its xEdit, less the ones ModTrap
sets itself or that put xEdit into another mode; the game's Data folder as MO2 manages it (`-D:`), unless theirs
names one; our script (`-script:`), our plugins file (`-P:`), a backup folder (`-B:`) and a log file (`-R:`)
(XE01§2 to XE01§6, XE01§11). An open MO2 takes the command over (MO01§4); ModTrap never starts a second MO2 on
the instance. ModTrap watches the script's progress file and xEdit's process for the end (WHY§7), with a time limit
and a **Stop** button that asks first. xEdit stays open after a script, so ModTrap closes the xEdit it started
when the script's end line is written (XE01§11). xEdit in script mode first asks which plugins to load, with
the job's own list ticked; ModTrap presses that window's OK itself, and says so in the log (XE01§13). A run in which xEdit did not load a plugin it was told to is a
failure that names the folder xEdit read.

MO2 must be closed only while ModTrap writes to the profile (§6.5 step 2, Re-enable and Revert): an open MO2 keeps
the mod list in memory and writes it back (MO01§2). ModTrap checks whether this modlist's own MO2 is running,
shows it on the page, and before such a step asks whether to close MO2; on yes it asks MO2 to close as a click on
its X does, and waits. It never ends MO2 (WHY§58). Two cases need no question (WHY§67): a MO2 that ModTrap itself
started for a run and that is still leaving is waited for; and the last step of a demaster done in one go closes an
open MO2 the same gentle way, because the plan the owner confirmed said it would.

ModTrap notes its own files when it starts. If they change while it runs (an update), it starts nothing more and
asks to be quit and started again: the scripts are read from disk, the program is not (WHY§67).

Our script and the job file live in ModTrap's work folder, outside the instance's mods and outside xEdit's folder:
nothing is installed into either.

## 8. Safety rules (the guard)

1. ModTrap writes only: inside its own work folder (the safe folders and the history are there); the files a
   confirmed plan named, which are ModTrap's own mod in the instance (MT5) and the profile's `modlist.txt` and
   `plugins.txt`. Every path is checked after resolving links, before the job starts and again before each write.
2. It never writes in the game's folder, in a trapped mod's folder, in `overwrite`, or to any file the plan did
   not name. It never deletes a mod or a plugin.
3. No file is changed before its copy in the safe folder exists and matches it by size and SHA-256.
4. Every write is atomic (written beside the file, checked, then swapped in), and recorded in the history.
5. Every plugin xEdit loads is hashed before and after a run; an unplanned change is put back at once and reported.
6. A job is refused if a trapped plugin or a dependant is one of the game's own files.
7. The script has a closed set of actions (report, take out a record, take out an entry, restore a value, Clean
   Masters, write out). The job file can only choose among them.
8. The profile is written only while MO2 is closed (§7).

## 9. What must be proven on the owner's PC first

Before any real mod is touched, a **probe** (built: WHY§47). From the Tools tab, in a ModTrap started with
`--allow-changes`, one button does ModTrap's whole work once on invented plugins, with the same code real work
uses, and undoes it:

1. two test mods of ModTrap's own go into MO2, in place and enabled: a "bad" mod with one plugin, and a mod with
   two plugins that depend on it in the ways of cases A and B (§5);
2. the dry run through the owner's xEdit must report exactly what those plugins hold;
3. after MO2 has run, the mod list and both plugin lists must still be as ModTrap wrote them;
4. the changing script must write a new plugin that no longer names the bad one, and
5. must have saved nothing over an original;
6. putting it in place must leave a clean health check with the bad mod disabled;
7. Revert must leave the lists as before the probe and the test mods gone.

It proves or disproves WHY§4, WHY§5, WHY§7, WHY§8 and WHY§26, and it is how ModTrap decides whether the owner's
xEdit is one it can work with (MT8, WHY§15). **Only when the probe has passed, on this modlist and with the xEdit
now set up in MO2, do "Add it for me" and "Demaster Selected" work**; with another xEdit it is run again. A step
that fails says what the owner's xEdit or MO2 did differently, and whatever the probe changed is put back.

## 10. Build order (proposed)

1. **0.1 Read.** Launcher, server, page; instance picker; the Mods and Plugins views with priorities, masters and
   dependants; the health check; the tools found. No xEdit, no writes.
2. **0.2 Report.** The script in report mode; the probe; the dry run and the terminal; the safe folder.
3. **0.3 Trap.** The run on copies, verification, insertion, Auto disable, the history, Re-enable and Revert.
4. **Later.** The updater and the built launcher, as in DataPiler.

Tests at every step use invented plugins and an invented instance written by the test code. The xEdit script itself
can only be tested on the owner's PC (WHY§6); everything around it is tested here.

## 11. The safe folder and Revert

- One safe folder per job, in ModTrap's work folder, made after the dry run and before the run (§6.2). It holds a
  copy of every file the job will change: each dependant plugin to be demastered, and the profile's `modlist.txt`,
  `plugins.txt` and `loadorder.txt`.
- Beside the copies, a manifest: for each file, where it came from (relative to the instance), its size and
  SHA-256, its mod and that mod's priority, and for a plugin its position in the load order.
- **Revert** on a job copies every original back to where it came from, removes what ModTrap added, restores the
  profile's three files, re-reads the instance and runs the health check. It works on the newest job first; an older
  job can be reverted only after the newer ones that touched the same files.
- Before Revert writes, it checks that each file it would overwrite is still the one ModTrap put there (by hash). A
  file changed since by something else is not overwritten silently: the page shows it and asks.
- Safe folders are never deleted by ModTrap by itself. The page shows their size and lets the owner delete old ones.
- **When the lists have changed since** (WHY§47). MO2 writes its lists whenever it runs, and the owner goes on
  using MO2 after a job. Putting the old files back would then undo their changes too, so Revert does not: it
  takes back only ModTrap's own changes, line by line. For an add: the lines of the mod and plugins ModTrap put in
  are taken out (a mod MO2 already had is disabled again and keeps its new place). For a demaster: the mods it
  disabled are enabled, the plugins it deactivated are activated, the line of ModTrap's own mod is taken out and
  the plugins it wrote are removed if still as written. Everything else in the lists stays as it is.

**Revert ends where the demaster began (WHY§81).** Beside the lists and ModTrap's own mod, Revert puts back every
plugin of the safe folder that a tool has made anew since, and the output of each tool ModTrap started after the
demaster, as it was kept just before the tool ran (up to 5,000 files and one gibibyte for a tool; a larger output is
named as one to make again). What is there at the time is set aside in the job's folder. A job in place is never
cleared from the job history; its Revert stays.

**The plugin lines MO2 dropped (WHY§83).** A MO2 that runs while a mod is disabled writes its two plugin lists
without that mod's plugins. So the line-by-line Revert, after enabling the mods again, puts their plugins and the
ones the demaster deactivated back into both lists: each directly before the plugin that followed it in the safe
folder's copy of the load order, active or not as it was. A Revert that did not do this (made by an earlier
ModTrap, or cut short) is said on the job, which stays listed, and one press finishes it.

## 12. History

A dated, append-only record in ModTrap's work folder, shown on the page, of everything ModTrap changed in the
instance:

- each job: when, which mods were trapped, which dependants were demastered (masters before and after), which were
  left alone and why, the result of each verification, and the owner's confirmation from MO2;
- each mod disabled or re-enabled: its name, its **priority in the modlist**, and for each of its plugins its
  **position in the load order** and its kind (esm, esp, esl), as they were at that moment;
- each plugin deactivated or reactivated by itself: its name, position and kind, and its mod and that mod's
  priority;
- each change of order: the file, the old and new positions, with date and time;
- each Revert.

Above that record the History tab lists the session's jobs (demasters and adds), newest first, with their state;
a job still in place has its Revert there. The other tabs show only the jobs still in place. **Clear job history**
takes the jobs that no longer stand off the list; nothing is deleted, and the record itself is kept (WHY§67).

Every disabled mod in the history has **Re-enable**: it enables the mod again at the priority it had, puts its
plugins back at the positions recorded, and warns if a demastered dependant would not need it any more or if the
order around it has changed since.

## 13. The tools of the modlist, and the patches they made

- ModTrap finds tools in two places: the executables configured in MO2 (MO01§2), and a `tools` folder inside the
  instance, where modlists commonly keep them (WHY§14).
- For each tool it shows the name, where it was found, and its version, read from the program file's own version
  details and its date. For xEdit it also notes the 64-bit program beside the 32-bit one and prefers the one MO2 is
  set up to start. Only xEdit is ever run by ModTrap.
- **Generated patches** (MT18). A plugin is marked as made by a tool on evidence, strongest first, and the page
  shows which evidence it was:
  1. it lives in the mod that MO2 sends that tool's new files to (the profile's per-executable output mod, MO01§2);
  2. its header's author or description carries the tool's mark (XE02§4);
  3. its file name is one the tool is known to use;
  4. it lives under one of the modlist's separators for tool output.

  The marks and names for 2 and 3 are in a data file ModTrap ships (`modtrap/data/tools.json`), one entry a tool,
  each with its source in TL01; they are not in code (WHY§22, WHY§37). With only weak evidence the page says "probably made by", never more.
- A generated patch among a job's dependants is not demastered by default: its treatment is **run the tool again**,
  after the trapped mods are disabled, so that the tool rebuilds it without them. Demastering it is the
  alternative the owner can pick, for a tool they no longer have.
- **What masters cannot show.** Some tools' output is not a plugin and names no master: generated animations and
  behaviours, LOD meshes and textures, texture atlases. ModTrap looks at what kinds of files the trapped mod itself
  contains (by folder and file name only) and, where a kind matches what one of the instance's tools consumes, adds
  a "may need a re-run" step that says why. These are hints, worded as such.

**ModTrap's copy of a tool's plugin (WHY§80).** A plugin a tool made that named the mod is demastered like any
other: a copy in ModTrap's mod, above the original. When the tool makes the plugin anew without the mod, ModTrap
retires its copy: moved into the job's folder, never deleted, and only if the new original names no ticked plugin
and all its masters are active. By itself after a tool's run that ModTrap started (a setting), or by a button on
the Selection tab. Every executable of MO2's list can be started from the Tools tab.

**What the tools made (WHY§74).** The Tools tab lists every tool-made plugin of the load order: the tool, how
ModTrap knows, the patchers behind it where the tool's own settings file says so, and its records by kind. The same
facts stand in a tool's step, with the mod's stakes among those kinds. A plugin made with the mod's plugin left out
is cleared by that; a patcher's settings that name the mod's plugin ask for a new run (TL01§14).

## 14. The Steps tab

Every job has a **Steps** tab: the whole demaster as one ordered list, compiled from the plan and refined by the
dry run. Each step says who does it (ModTrap or the owner), why it is needed (the evidence: which plugin, which
master, which tool), its state (to do, running, done, failed, waiting for you), and for the owner's steps exactly
what to do and how ModTrap will know it is done.

A typical job's steps:

1. *ModTrap:* dry run through xEdit; the list of every change (§6.2).
2. *ModTrap:* the safe folder (§11).
3. *ModTrap:* demaster the dependants on copies; verify the copies (§6.3, §6.4).
4. *You:* any dependant that "needs you" (case C or D): the record and field, and what the guide's manual fix
   would be. Done when ModTrap's reader finds the trapped plugin gone from that dependant's masters.
5. *You:* close MO2, if Auto is to write the profile (§7).
6. *ModTrap:* put the ModTrap mod in place; disable the trapped mods and the patch-only mods (§6.5).
7. *You:* run each tool whose generated patch depended on a trapped mod (§13), in the order the modlist runs
   them. Done when ModTrap finds the rebuilt patch no longer lists a trapped plugin.
8. *You:* the "may need a re-run" hints (§13); ticked off by the owner, since nothing in a file can prove them.
9. *ModTrap:* verify the instance: the health check (§3), and the load order otherwise as it was.
10. *You:* open MO2 and confirm it shows no missing-master warning; then play, and report anything odd.

**Ticks, and a tool's step (MT29, WHY§91).** A tool that ModTrap can start has no tick: its step is done when
ModTrap has noted a run of it, with its output written, since the demaster in place was put in place; a Revert or a
new demaster asks for it again. "I have done this" is left for what no record can show (the play test, settings
files to look at, a tool outside MO2's list), and a play-test tick goes with the demaster it was made for.

**The settings files, and the checks after (MT33, WHY§95).** Settings files of other mods that name a ticked plugin
are read line by line; the step is ModTrap's and done where every line only gives something of the mod's or reaches
only its things, and the owner's where a line leaves the mod's things out or the file is of a kind ModTrap has not
read the handling of. With the demaster in place the steps carry one account of ModTrap's checks (masters, mods
disabled, each tool's noted run, the settings files): "complete and checked" only when all hold. Each step
says who really does it (WHY§97): ModTrap where it runs a tool itself, ModTrap and the owner where it can only start
one. What is left to the owner in a settings file is said with the file's path, the line and what to do.

**The scanner (MT34, WHY§98).** Those files are found by one scanner that looks through the whole modlist: the
game's Data folder, every enabled mod and Overwrite, the winning copy of each path, each read to its end, with no
time limit. The step is there also when no file names the plugin, and states what was looked through. What the
scanner could not list or read is named, and the step is then the owner's. The Tools tab shows what the scanner
covers and the frameworks installed.

**Animation replacers, and the log (MT35, MT36, WHY§99).** The scanner also walks all of `meshes` for the folders
of animation replacers and reads their condition files. Which condition a mention belongs to is read from the
file's structure: one that does not hold once the mod is gone is ModTrap's; one that can hold then, or one ModTrap
does not know, is the owner's, with the line and what to do. Every look is written to the log: what was listed
and read, the time, and each folder or file that failed, with its reason. A scanner that fails is said as failed.

**Nothing is foretold (MT26, WHY§86).** While the dry run of the ticked mods is still to be made, or is going, the
tab shows two steps only: the dry run, and one that says the steps after it follow from what it reads, naming the
plugins concerned. Once it is done the steps are stated from what was read. A verdict on a tool does not change
with the demaster: a plugin the tool made that names the mod as a master is proof that the tool is to run again,
before the demaster (when it is a dependant) as after it (when a copy of it stands in ModTrap's mod).

The job is **complete** only when every step is done and the health check passes (MT17). Until then it is shown as
"in progress, waiting for you", and **Revert** stays one click away. The steps and their states are part of the
history (§12).

## 15. Sessions, and Quit

- A **session** (MT20) is one piece of work on one modlist. It lives in a folder of its own under ModTrap's work
  folder and holds: its name, the modlist's folder and profile, what the page looked like (the ticked mods, the
  tab, the search and filters, the order, the folded groups, the plugin being looked at), its log, and its jobs
  with their safe folders (§11) and results. It is written as the owner works, not only at the end.
- Opening a modlist goes to the session that holds it; if none does, a new session is made and named after the
  modlist's folder. The owner can rename a session, start another, and switch between them from the header.
- **One session holds a modlist at a time.** A second session on the same modlist can be started, but it waits,
  locked: it can look and tick, but cannot start a dry run or a demaster. Sessions on different modlists do not
  hold each other up.
- **Finish** hands the modlist to the session that has waited longest. Before it does, ModTrap checks that the
  session is safe to leave: nothing of it is still going; and, once ModTrap can demaster, every step of its jobs is
  done (§14) and the health check is clean (§3). A session that is not safe is not finished, and the page says what
  is still open. A finished session stays, to be looked at; no more work is done in it.
- **Quit** saves the session and stops ModTrap; the page then says so, since a browser lets a page close only a
  tab the page itself opened. Starting ModTrap again reads the modlist afresh (plugin headers come from a cache, so
  only changed plugins are read) and puts the page back as it was, the last dry run and the log included. If the
  modlist changed in between (a mod no longer there), what cannot be restored is dropped, and the rest is.
- Quitting while a job is going asks first. A dry run cut short this way is shown afterwards as not finished; the
  rule for a demaster cut short belongs with Revert (§11) and is not yet designed.
- **Save this session** (WHY§48). A button on the Log tab packs the session's log and its jobs' text records,
  with a description of the setup and the profile's three lists, into one `.7z` and downloads it, for the owner to
  send when asking for help. The owner's folders and user name are taken out as it is packed; no plugin, archive
  or other content of a mod goes in. The archive is written with Python alone.

## 16. Adding mods (MT21)

Beside taking mods out, ModTrap helps to put extra mods in. The owner's own way is to add a mod last and its plugin
last; that works until the new files or records land after something that was meant to stay last, or the plugin
needs something that is not there. This section is what ModTrap does about it. Built so far: §16.1 to §16.4, §16.6
and §16.7, none of which changes a modlist (WHY§40, WHY§41). §16.8's changing part is behind a switch that is off (WHY§42, WHY§44); the record check
(§16.5) and starting the tools are built (WHY§45). None of it has run on a real modlist.

### 16.1 What is dropped

- **The owner drops the mod's archive on the page, and ModTrap takes it from there** (MT21's note of 2026-11-21,
  WHY§41). MO2 cannot be told from outside to install an archive (MO01§8), so ModTrap unpacks it itself: in the
  session's own folder (§15), never in the modlist. If the archive lies in MO2's Downloads it is read there;
  otherwise its bytes are copied to the session's folder as they arrive.
- A `.zip` is unpacked by ModTrap's own code; `.7z` and `.rar` by the owner's installed 7-Zip, which ModTrap calls
  and does not contain. An archive is someone else's file: before anything is written, every name in it is checked
  (none may leave its folder; no links), and its file count and unpacked size are capped; the kind of archive is
  read from the file, not from its name.
- ModTrap then finds the folder in it that would become the mod: through wrapping folders and a `Data` folder, to
  the one that holds plugins or the game's usual folders. The mod's name is the archive's, without the numbers a
  download site adds.
- **An installer that asks questions** (MO02). An archive with a `fomod` installer file, or with several folders
  to choose from, is not taken as it is: ModTrap shows the installer's own questions on the Add mods tab, every
  step that applies on one card, with what the installer recommends already chosen and the options that do not
  suit the load order marked. The answers build the mod's folder in the session's folder, in the installer's own
  order of files; the owner can change the answers and build it again. An installer ModTrap cannot read (an older
  script-based one, or a damaged file) is handed to MO2: the owner installs it there and finds it by name.
- The unpacked mod is analysed where it lies (§16.2 to §16.7), exactly as it would be once in MO2.
- A mod MO2 has already installed is found by name, or by dropping its folder or the archive it was installed from
  (MO01§7): a page learns only the name of what was dropped, so the name is matched.
- Up to twenty mods are analysed together. The list, and what was taken in, are kept in the session (§15); taking
  an archive off the list removes ModTrap's own copy of it and nothing else.

### 16.2 What the mod needs

- Every master of every plugin it brings, and where that master is: active in the modlist; in the modlist but not
  active; in a disabled mod (which is then offered to be added too); coming along with another mod of the same
  batch; or nowhere.
- Room in the load order: the full and the light plugins active now, and with the new ones, against the game's
  limits (XE02§6).
- A plugin that cannot be read, a master-flagged plugin that needs one that is not, and a header in the newer
  format (XE02§6) are pointed out.

### 16.3 Where it goes

- **A list with a heading for its outputs** (WHY§49). A curated modlist keeps what its tools made under a
  separator of its own, named for it ("Outputs"), often with more sections after it (options, presets). Where
  there is one, the new mod goes right before that heading, and every mod under the heading counts as an output,
  whether or not ModTrap knows the tool; its plugins count as tool-made for the load order. What follows applies
  to a list without such a heading.
- **Among the mods:** after every ordinary mod, so that it wins each file it shares with them, as it does when the
  owner puts it last; but before the mods that hold what the modlist's tools made (§13), which stay last and are
  made again. A mod counts as a tool's output when MO2 sends a tool's new files to it, when every plugin in it was
  made by a tool, or, failing both, when its name says "output". A separator right before the outputs stays with
  them. With no output found, the mod goes last.
- **In the load order:** after every master the plugin names, and before the run of tool-made plugins at the end
  (§13; an editor's output does not count, TL01§6). One or two plugins of unknown making among them do not end
  the run. A master-flagged plugin goes to the end of the masters' block
  instead, since the game loads those first. Several new plugins are ordered among themselves, masters first.
- The place is a proposal with its reason. The report shows what the mod wins and loses there (§16.4), so the owner
  can judge it.

### 16.4 Files it shares with other mods

- For each mod to add: the enabled mods (and the overwrite folder) that hold a loose file of the same path, split
  into those the new mod would replace and those it would lose to in its place, with counts by kind of file (§14's
  kinds) and a few examples.
- The kinds that go wrong quietly are pointed out: a plugin of the same name, compiled scripts, a script extender
  plugin, face files, an archive of the same name, menu files. Files lost to a tool's output mean that tool runs
  again (§16.6).
- METHOD: only folders the new mod also has are entered in the other mods, so a mod that shares nothing costs one
  listing of its top folder; the search has a time limit and says when it was cut short.
- Not compared: files packed inside archives (`.bsa`). A loose file always wins over a packed one.

### 16.5 Records

- Which records the new plugin overrides, and which other plugins change the same records, only xEdit can read.
  ModTrap starts the owner's xEdit through MO2 with a script of its own that only reports (as the dry run does, §7;
  XE01§10), with the whole active load order loaded, since a conflict is between all plugins that hold a record.
  The plugin must be active, so this comes after the mod is in.
- For each overriding record the script reports xEdit's own conflict level and every plugin that holds the record,
  in load order. ModTrap sorts them: records only the new plugin changes (or where the changes agree); records it
  wins that other plugins also change, whose change is then lost, by plugin; records a later plugin wins; and
  records identical to what they override.
- "Needs a look" means: it takes records from a plugin made by hand (a patch of the modlist had settled them), or
  loses records to one. What a tool made is settled by running the tool again (§16.6). ModTrap names the records
  and says how a patch is made; it does not write the patch.
- Nothing is changed: the plugins looked at are hashed before and after.

### 16.6 Tools that must run again

- A tool that made a plugin of this modlist from what the new mod brings: the tools data says what each tool reads
  (plugins; meshes and textures; LOD), and words the condition where it depends on what the mod changes. A tool
  ModTrap does not know is taken to read plugins, and the step says "if it applies".
- A tool fed by the mod's loose files, as in §14: animations, LOD, grass cache, BodySlide data.

### 16.7 The steps

In order, each with who does it, why, and whether the modlist's files show it done (as §14): get what the mod
needs; enable it in its place; activate its plugins in their place; look at the shared files that go wrong quietly;
check the records in xEdit; run the tools again; the health check (§3); play. `python -m modtrap add FOLDER --mod
NAME` prints the same report.

### 16.8 Carrying the steps out

What "Add it for me" does on its own, in order, each step in the history (§12) and undone by "Take it out again"
(§11). It exists only when ModTrap is started with `--allow-changes` (WHY§42, WHY§44); the page shows the plan and
asks before anything is done.

1. With MO2 closed (§8): copy the unpacked mod into MO2's mods folder under its name, with a `meta.ini` naming the
   archive (MO01§7), so that MO2 knows it as an installed mod.
2. Put it in its place in the mod list and enable it; put its plugins in their place and activate them (§16.3).
3. The health check (§3).

Then, each from its own step and without the switch, since ModTrap itself changes nothing in them (WHY§45):

4. The record check (§16.5).
5. For each tool that must run again (§16.6): "Start it through MO2" starts the tool the way MO2's own Run button
   does (MO01§3). The owner works it; ModTrap waits for it to close, says which files in the tool's output mod, in
   `overwrite` and among the plugins that tool made were written, and reads the modlist again.

Left to the owner: an installer's questions (§16.1), working the tools, a patch where the record check shows one is
needed, and playing. "Take it out again" disables the mod and deactivates its plugins by putting the lists back;
nothing but ModTrap's own copy of the mod is removed (MT9, WHY§42).

Later, if they prove worth it: comparing packed files; reading the owner's own installed copy of a sorting tool's
rules for known incompatibilities (its licence is to be read first); proposing a patch from §16.5.

**A tool's own log (WHY§88).** Where a tool keeps a log of its own and ModTrap knows its lines (data, `tools.json`),
the log written during a run ModTrap started is read once the tool has closed: what shows in it is said on the
tool's card and in ModTrap's log, and a copy is kept with the session and packed into a saved session file.

**Installing a new mod, as amended (MT53, WHY§118).** "Install mods" has two tabs: the "Installer tool" and
"Installed mods". "Install mod" does everything with one press: the mod goes last, before what the tools made, unless
the owner chose its place by hand on the Mods tab ("Manual placement": a line between two rows follows the pointer, a
click is the place, a box tells what the mod overwrites there and what overwrites it, OK installs it there). The
steps hold nothing to tick: what the mod overwrites and what overwrites it, and the tools that have to do with it,
are told. A tool that builds a plugin from plugins is named only where its output and the new plugin hold records of
a common kind. "Installed mods" lists what ModTrap installed that still stands, as the modlist lists mods, each with
its update and "Uninstall" (the add's Revert). A dropped archive is read and shown, and "Install mod" installs it;
installing at the drop is a setting, off (MT54, MT55). The Mods tab's menu adds a separator below an entry, through
the add job (MT55). The Mods tab, the Updater list and Installed mods sort by a click on a column's title.

## 17. Versions, and one ModTrap at a time (MT22)

1. **The version** is `0.3.n`, kept in `modtrap/version.json` with a mark of the contents of ModTrap's own files.
   `n` rises with every change (`tools/bump.py`; a test fails while the files and the mark disagree). It is shown
   on the page, in ModTrap's window, at the start of its log, in the log line of each job, and in every saved
   session file (WHY§68).
2. **The program and the files.** A running ModTrap is the program as read at its start; the scripts for xEdit are
   read from disk at each use. Before a dry run, a probe, a demaster, an add or a tool is started, ModTrap compares
   the mark of the files on disk with the one it started from. If they differ it starts nothing and says which
   version is running and which is on disk, with Quit beside it. Looking goes on (WHY§67).
3. **Files that do not belong.** If the files ModTrap started from are not those its version was written for, the
   page says "files differ" beside the version and the log says what that means. An update is best unpacked into an
   empty folder.
4. **One at a time.** A running ModTrap leaves a note in its work folder (port, version, a key of that start). A new
   start asks the running one, with the key, to save its session and close, and takes its place on the same
   address; the session comes back as after Quit (§15). One in the middle of a job is not interrupted: the new start
   says so, shows the running one's page, and ends. The request is not open to a web page: it needs the key, which
   only a program on this PC can read, and it does nothing but this.
5. **A page of the one that closed** is refused by the new one and loads itself again.
6. ModTrap does not fetch updates. The owner replaces the folder; the steps above make sure the new one is what runs.

**The package for Windows (MT51, MT52, MT53, WHY§116, WHY§117).** `tools/build_exe.py` builds
`ModTrap-<version>-win64.zip`, holding one folder named `ModTrap`: ModTrap's files and ModTrap's own launcher,
`ModTrap.exe`, which passes the switch for changes and carries the version for Windows' Properties. The launcher starts the Python that lies beside it where the package was built with one (CPython
as published, with a `._pth` file that keeps the rest of the PC out of its path), else the Python installed on the
PC. The package is never committed.

## 18. The Process tab

The demaster from start to finish, shown as it happens (WHY§70). It adds nothing to what ModTrap does: it shows it.

1. **Stages**, each a box linked to the next by an arrow, in order: the probe (where it is required), the dry run,
   the plan, the demaster on copies, putting it in place, and what comes after the demaster. A box's title leads to
   the tab where that stage is worked.
2. **Tasks** inside each box: what finishes the stage, in order, each with a short note of how far it is (how many
   dependants read, which plugin is being changed, how many files in the safe folder, why it stopped).
3. **Colours**, for a task and for its box: white, to come; amber, going on now; green, done; red, stopped with an
   error; purple, waits for the owner; grey, not needed this time.
4. **Where it comes from.** Each job tells its tasks when it starts and marks them as it goes; for xEdit's part,
   from the lines ModTrap's scripts write as they work. The page reads this with the state, every second. The
   last box is made of the steps of §14 that follow the demaster: the tools to run again and what only the owner
   can judge; until the demaster is in place they are to come, then they wait for the owner.
5. The probe's own dry run and change are shown as the probe's steps, not as the real ones.
6. **What the owner presses is in the box** (WHY§71), at the task it belongs to: “Demaster Selected” at the first
   stage still to come, “Go ahead” and “Not now” at the plan with what the plan amounts to, “Put them in place”
   where new plugins wait, a tool's start button and “I have done this” in the last box. Beside each is a way to
   the tab the button comes from, to look before pressing. They are the same actions as on those tabs. A demaster
   started from this tab stays on it.
8. Where the demaster stopped short (something still needs the mod), putting in place ends with "Left to you",
   and the box waits for the owner (WHY§76).
7. A demaster that is in place stays shown as done until Revert, or until a new one starts. A dry run of the modlist
   as it was before it was read again is not shown as this demaster's.

**ModTrap's own work first (MT30, WHY§92).** The header says whether ModTrap is still reading or scanning, and what.
Until it has finished, nothing that changes the modlist or starts a program is begun: those buttons are greyed, the
starts are refused, and the one go holds its place and takes its step again by itself.

## 19. Settings, sections, and another modlist's MO2

1. **Settings** (a tab of their own; kept in ModTrap's folder for every session; WHY§77). Each is a switch:
   after the dry run, go ahead without asking when the plan leaves nothing to the owner (off); show the Process tab
   when a demaster starts (on); close this modlist's MO2 without asking when a step needs it closed (off); open
   MO2 again once a demaster is in place (off); take script properties that point at the mod out (on, MT4);
   after a tool's run, retire ModTrap's copy of a plugin the tool made anew (on, WHY§80); after the demaster, start
   the tools that are to run again one after another (off, WHY§81); let a tool that can do so run and close by
   itself, by switches of its own that ModTrap knows as data, or, where a tool has only a button, by ModTrap
   pressing it once it is ready and closing the window when the tool's log says the run is over (on, MT25, MT31,
   WHY§84, WHY§93).
   Before the patcher framework starts, library versions that its own last log proves unfit for the program are
   set to the pair the program was built with, in its settings file, a copy kept first (on, MT27, WHY§89).
   And patchers its last log shows as not built are built first with the program opened by itself, outside MO2,
   which ModTrap then closes before the start through MO2 (on, MT28, WHY§90).
   A compiler that a tool's own log shows crashing inside MO2 is added to MO2's list of programs its virtual file
   system leaves alone, in MO2's settings file, with MO2 closed and a copy kept (on, MT32, WHY§94).
   What keeps a modlist safe is not a setting: the probe, the safe folder, the checks, Revert.
2. **Sections.** The tabs stand in two rows: the section (Modlist, Demaster, Add mods, History, Settings) and the
   tabs of the section in view (Modlist: Mods, Plugins, Health, Tools; Demaster: Selection, Dry run, Steps,
   Process; History: History, Log).
3. **Another modlist's MO2.** MO2 hands a command to the MO2 that is already open, whichever modlist that one is
   for. So while a MO2 of another modlist is open, ModTrap starts nothing through MO2: the start is refused before
   anything is begun, the one go holds its place and says what it waits for, and it takes the same step again by
   itself once that MO2 is closed.

## 20. The update check (MT37)

An **Updates** tab, beside Tools. It lists every mod with where it came from and whether a newer file of it is out
(WHY§101).

**Where a mod came from** is read on this PC: the mod's `meta.ini`, the `.meta` beside its downloaded archive
(MO01§12), and the modlist's own Wabbajack file if the owner names it (TL01§27). The Wabbajack file also says which
mods are the list's own; the tab filters by the list's own mods, mods added afterwards, and mods added by ModTrap.

**Whether a newer file is out** is asked of Nexus and of GitHub, and of nothing else (MO01§13). ModTrap asks and
reads: it downloads nothing and changes nothing. Nexus is asked only with the owner's key, kept on this PC under
Windows' protection for the owner's account, shown to no one and written nowhere else. The account's allowance of
questions is spared; what did not fit in one scan follows at the next. States: update out, unclear, up to date,
not asked yet, cannot be asked, gone from its page. What cannot be told is never shown as up to date.

**When.** On "Scan for updates", and once at each start of ModTrap (a setting, on). The last answers are kept and
shown without asking.

**Sources given by hand (MT38, WHY§103).** A right click on a mod, here and on the Mods tab, opens a menu; "Add a
source link…" asks for the web address the mod comes from and keeps it in ModTrap's own folder, before every other
record. A drop zone, with "Add files…" and "Add a folder…" in its middle, takes the modlist's Wabbajack file, `.meta`
files of downloads and mods' folders; of a Wabbajack file the page sends only the list. Nothing of a mod is changed.

**The list (MT39, WHY§104).** As the Mods tab: lowest priority first, under the modlist's separators, which fold.
Columns: Priority, Mod, From, Installed, Notes (what the owner wrote of the mod in MO2), Update (the state by the
last asking), a button, What is known. The button, an upward arrow shown where a newer file is out, opens that
file's own page for a download through MO2, or the newest release at GitHub. ModTrap downloads and installs
nothing; whether it should is open (MT40).

**Getting the newer file (MT40, MT41, WHY§105).** The button fetches the file where its host gives one to a program:
Nexus for the key of a paying account, GitHub for a release's file. Otherwise it opens the file's page and says
why: Nexus without a key or for another kind of account, LoversLab and other sites always. A fetched file, and one
the owner downloaded and names through the mod's menu, go to Add mods (§16) as a newer version of the mod: placed
right above the old one, which is disabled and not deleted; a plugin the load order already names keeps its place.
Nothing is changed before the owner has seen the plan and gone ahead; Revert puts all of it back.

**A download started in the browser (MT42, WHY§106).** Where the button opens a page, ModTrap waits 45 minutes for
the archive in MO2's downloads folder or the folder the browser saves to, and takes it to Add mods once it is
whole, read where it lies. The row shows that ModTrap is waiting, with a way to stop.

**One press all the way (MT43).** With the setting "Add a newer file without asking, when its plan leaves nothing
to you", the add of a newer version goes ahead by itself when it is the only thing on the Add mods list, has no
installer with questions and lacks nothing. Otherwise it waits on the Add mods tab as before.

**No key for scanning (MT44, WHY§108).** A scan asks Nexus's public service, which needs no key: when each mod last
had a file uploaded, and a mod's files only where the installed one is not plainly its newest. The owner's key is
optional: it lets the update button fetch for a Premium account, and serves for scanning only where the public
service does not answer as expected.

**A source without typing (MT45, WHY§109).** Where no record names a mod's source, ModTrap reads the mark the
browser left on the archive the mod was installed from, if it still lies in MO2's downloads folder. A mod ModTrap
adds gets its source written into its own record, so that it can be asked about afterwards like any other.

**Manual update, favourites, the site's window (MT46, WHY§110, WHY§111).** A mod's menu has "Manual update…", a box
with a coloured drop zone and "Add file…" for an archive the owner downloaded themselves, which goes to Add mods as
the mod's newer version; and "Mark as favourite", the owner's own mark, kept in ModTrap's folder. The row of states
is named "Filter:" and ends with "★ Favourites". A site's page for a download opens in a small window beside ModTrap
(a setting, on), cut loose from ModTrap; a second setting, off, keeps it tied for Nexus, GitHub and LoversLab so
that ModTrap can close it. A download is known by MO2's numbers, the browser's mark, its exact name, or the mod's
number and the upload's time in its name; a storage code given for a name is never shown or waited for.

**A tab, and the download whatever its name (MT47, WHY§112, amending the above).** The site's page opens as a tab;
the small window is a setting, off. The update button is a real link: with Ctrl or the middle button the browser
opens the page behind ModTrap's tab and ModTrap only watches. Nexus's page is opened for a download by the browser
itself, not by a mod manager. The watch runs by itself while a download is waited for, knows an archive by its first
bytes and a download by its size to the byte, asked at the press, and tells the log of every file that came.

**An update is not a new mod (MT49, WHY§114; amends §16 for a newer version).** Where every mod of an add is a newer
version of a mod of the modlist, the steps are: what it needs; put it right after the older version, disable that
one, the plugins keeping their places; place a plugin the older version did not have; what the newer version changes
(by its files' names and sizes, with the tools that build from what changed: told, not asked); the load order's
health. The steps of a new mod (its place among all mods, shared files, records, tools, the game) are not shown, and
the older version is not counted among the mods it shares files with. The Updates tab shows a mod whose newer file is
installed as another, enabled mod as "Older version".

**The Updater (MT50, WHY§115; amends this section and §16).** The update check's list is the "Updater list"; beside it
the "Updater tool" shows an update as it goes, a box for each stage: find the newer file (asked of the site at the
press, and looked for on the PC), download it (fetched by ModTrap where the host gives it to a program; else the
owner's press on the site's button, on the page ModTrap opens), unpack it, check what it needs, put it in the older
version's place (the add job of §16.8, with its Revert), check the result. One press starts it and it goes through
by itself, on the server; it stops for the owner only at an installer's questions, a missing master, or MO2 open.
ModTrap keeps downloads in a folder of its own with a list of what each is ("Downloads"): a fetched file goes there,
a browser's download for an update is moved there (a setting), a file in MO2's downloads folder is used where it
lies, and a file that is on the PC already is never downloaded again. "Add mods" is "Install mods", for new mods.

**Staying on ModTrap's tab, and the key (MT52, WHY§117).** When the page opens a site's page in a new tab, ModTrap's
program takes the browser back to ModTrap's tab with the browser's own key for the tab before, on Windows, guarded
by the kind and the title of the window in front (a setting, on). The Nexus key is asked for on the Updater tool
where an update waits for the press at Nexus; with a Premium account's key the file is fetched with no page.

**Closing the tab (MT48, WHY§113).** ModTrap closes the tab it opened for a download when the file is whole and
taken, or the waiting ends (a setting, on; only for Nexus, GitHub and LoversLab). While a file is being written, the
row says how far it is; before that, that the press on the site's download button is the owner's.

## 21. The Modlist page as MO2's own list (MT56)

The mods' table serves two tabs. **Demaster › Pick mods** is the list with the demaster's ticks (§4). **Modlist ›
Mods** is the list as MO2 shows its own: the box is the mod's state, and a change there is made at once, as in MO2.

**A change is a job** (`listjob`, WHY§121): enable or disable mods, move a block of entries, rename a separator.
Each keeps §8: MO2 closed, a copy of every list it touches in its safe folder first, the lists read back from disk
and put back when they are not as planned, the change in the history, and Undo (§11: the whole files while they are
as the job left them, else its own lines).

**Plugins follow MO2's rule** (`loadcheck.place`, MO03§2 to §5): on enabling, the mod's plugins that no other
enabled mod has become active; one new to the load order goes to the end, a master to the end of the masters'
block, none before a master of its own. On disabling they are switched off and keep their lines.

**What is not safe is asked first** (`loadcheck.plan_set`): a missing or inactive master, plugins that would lose
a master, the game's limit. The rest is told after the change.

**The scanner** (`loadcheck.overrides`, `loadcheck.files`) reads, for one mod, its plugins' place and masters, the
records they change, the plugins that change the same records before and after them, and the files shared with the
mods below and above. Record headers only, bounded in time; no xEdit.

**Moving** is by dragging a row (a folded separator with its mods) or "Move to priority…"; a place is always
"directly before" an entry of MO2's list, or last.

**A file dropped on the list (MT57).** Over the rows of Modlist › Mods a dragged file shows the line of a place;
let go, the page runs the install itself with the dropped archives alone and that place (taken in, unpacked, read,
installed, checked), in a box on the Modlist page, and hands over to the Installer tool, with the place, where an
installer asks questions or something the mod needs is missing. Every list keeps its place when it is shown again
(WHY§122).

**The Plugins tab (MT58).** The same jobs serve the load order: a plugin activated or deactivated, a plugin moved
(`loadcheck.place_moved` keeps MO2's limits and says where it stands and why). Nothing is asked; a row carries ⚠
for what is wrong with its plugin and ⇄ or ✓ for what a scan of it found, and the pane beside the list tells it.

## 22. Unpacking, and ModTrap's own update (MT58)

**Archives.** A .zip and a .7z are unpacked by ModTrap's own readers (`unpack._unzip`, `sevenz_read`); a .7z its
reader does not read, and a .rar, by the owner's 7-Zip or else Windows' `tar.exe` (WHY§123). §16.1's checks hold
for all of them.

**ModTrap's own update** (`selfupdate`, WHY§124). The version on the page is a button; a release package given
there is checked, the version in use is copied to ModTrap's own folder, the files are replaced, the new program is
tried, and ModTrap starts again and takes over (§17). ModTrap run from its source folder is not updated this way.

**The split view (MT59).** A tab of the Modlist section shows the mods' and the plugins' sections side by side,
parted by a line the owner drags; nothing is built twice (WHY§125). A mod looked at marks its plugins on the other
side, a plugin its mod.


## 23. One mod and its web (MT62)

A click on a mod's name, on the mods' list, opens a box that shows the mod in the middle of every mod it has to do
with. The name glows under the mouse; the rest of the row still only shows the mod's card. The same box opens from
the mod's menu ("Show its web…") and from its card ("Its web…"). ModTrap only reads for it.

### 23.1 What is read, and in which order

Two passes (`modweb`), because the second takes seconds on a large modlist and the first none:

- **What the plugins' headers say** (`modweb.near`), there at once: the mods whose plugins this mod's plugins name
  as masters; the mods whose plugins name this mod's; of those, the patches made for it and the outputs of the
  modlist's tools; and masters no enabled mod has.
- **What the files and the records say** (`modweb.far`, on §21's scanner): the mods whose files this mod overwrites
  and the mods that overwrite its files, by kind of file and with examples; and the plugins that change the same
  records as this mod's plugins, with the kinds of record. Bounded in time as the scanner is; a look cut short says
  so in the box.

The box opens on the first pass and draws itself anew when the second is there. Both are kept by the page for the
modlist as it stands, so a mod opened again is there at once; any change to the lists forgets them.

### 23.2 The kinds of tie, and their colours

Ten kinds. A box has the colour of its kind, a second line that names the kind in words (colour alone is never the
only sign) and how much of it there is.

| Kind | Colour | What it says |
|---|---|---|
| It needs | blue | a plugin of this mod names one of that mod's plugins as a master |
| Needs it | teal | a plugin of that mod names one of this mod's as a master |
| A patch for it | violet | every plugin of that mod needs this one, and the mod or a plugin of it is named a patch, a fix, a tweak, an add-on or the like |
| A tool's output | sand | that mod is where a tool of the modlist writes (§13), and a plugin in it has this mod's among its masters |
| Overwrites its files | orange | that mod has files of the same name and the higher priority |
| Files it overwrites | green | this mod has files of the same name and the higher priority |
| Conflict | red | plugins of both change the same records, neither is the other's master, and no active plugin has both as masters |
| Conflict, settled | yellow | as a conflict, but an active third plugin has both as masters: a patch that can carry both changes |
| Changes its records | pale orange | a plugin that knows this mod (one is the other's master) changes records this mod changes, and loads later |
| Records it changes | pale green | the same, with this mod's plugin the later one |

**What a patch is** cannot be read from masters alone: a mod with two masters may be a patch between them or a mod
built on both. So a patch is told by both signs together, the whole mod depending on this one and its name saying
so; anything else that needs the mod is "Needs it", with the other mods it needs named beside it.

**What a conflict is, and is not.** The game takes a record whole from the plugin that loads last. Two plugins that
change the same record, with neither made in view of the other, therefore lose the earlier one's change: that is
the conflict. Where one plugin has the other as a master, its change over the other's is what it was made for, and
is shown as such, not as a conflict. ModTrap reads which records a plugin changes (their headers), not what is
changed inside them: whether anything that matters is lost, and whether the third plugin of a settled conflict
does carry both changes, is for xEdit to show, and the box says so.

### 23.3 The picture

The mod stands in the middle. Around it, by what the tie means:

- **left, "It needs":** the mods it stands on;
- **right, "Built on it":** the mods that need it, the patches for it, the tools' outputs;
- **above, "Win over it":** the mods that overwrite its files or whose changes to its records the game takes;
- **below, "It wins over":** the mods whose files it overwrites or over whose changes its own win.

A conflict stands above when the other mod's change wins, below when this mod's does.

**One box for one mod**, however many things tie the two. The weightiest kind names the box, colours it and gives
it its side, in this order: conflict, patch, tool's output, it needs, needs it, settled conflict, files overwritten
either way, records either way. The further kinds show as small dots of their colours in the box's corner, and in
full when the box is pressed.

**A line** joins each box to the middle, in the box's colour, the thicker the more there is of the tie. Its arrow
points at the mod that is needed, or the mod that is overwritten; where each of two mods wins somewhere, at both.

**Room.** Nine boxes in a column, eight above and eight below. A side with more mods ends in a box "+ N more",
which lists the rest beside the picture; within a side the weightiest kinds come first, then the ties with the
most in them. A disabled mod's box has a broken border. The picture keeps its shape and scrolls sideways in a
narrow window, never squeezing the boxes into each other.

### 23.4 Beside the picture

- **The kinds**, each with its colour and its count, as buttons: a press takes a kind out of the picture, or puts
  it back, and the room it leaves goes to the others. While the second pass runs, its kinds show "…".
- **The overview**, when no box is chosen: how many mods have to do with this one, masters nobody has, the largest
  conflicts as rows to press, how much was looked through, and whether the look was cut short.
- **A box pressed:** everything between the two mods, kind by kind: which plugin needs which; which kinds of files
  are overwritten, how many of each, with examples; which plugin wins over which in how many records, by kind of
  record; for a settled conflict, the plugin that has both as masters. From there: "Put it in the middle" (as a
  double-click on the box), "Show it in the list".
- **"Put it in the middle"** draws that mod's own web; "Back to …" returns, step by step.

Esc leaves a chosen box, then closes the box; the keyboard stays inside it while it is open.

### 23.5 Where the mod came from, and its one picture

Under the mod's name stands its page: "From Nexus", "From GitHub", "From LoversLab", or the host of any other
address the modlist or the owner gave for it (§20), as a link that opens a new tab with no tie to ModTrap's tab.
A mod without one offers "Add a source link…".

Where the page is at Nexus or a GitHub repository, the box shows **the one picture that page opens with**
(`updates.picture_address`, TL01§32): for Nexus the mod's own preview picture, asked of its public service without
a key; for GitHub the preview picture GitHub draws for the repository. Other sites give none without an account,
and ModTrap never signs in anywhere.

- The page asks ModTrap's server for it; the server fetches it and hands it over as data. The page itself still
  loads nothing from outside (§2's content policy stands unchanged).
- Only from the three hosts those two sites serve pictures from, only over https, only a file that is a picture by
  its first bytes, and no larger than a few megabytes. No key is sent.
- Kept in ModTrap's own folder for a month, so each is fetched once; a site that had none is asked again after a
  day.
- Fetched only when a mod's web is opened, one mod at a time: never for the whole list.
- The setting "Show a mod's picture in its web" switches it off.

### 23.6 Limits

- The game's own files have no web: everything is built on them.
- Record conflicts are read for an enabled mod with plugins; files for any mod.
- On a mod with hundreds of ties the picture shows the weightiest and lists the rest; nothing is left out of the
  lists but lines beyond the first dozen of one tie, which are counted.

## 24. Tables' columns, and no window but the browser (MT61 to MT63)

**Columns (MT61, MT62).** Every table with a heading row has a line at the right edge of every heading, the last
one's included, and the same thin lines run down between the columns of its rows. A line held and moved sets the
width of the column to its left and nothing else: the columns to its right move with it and keep their widths, the
table growing or shrinking by as much, and the list scrolls sideways when the columns are wider than their pane.
While a line is held it glows from the heading to the foot of the list. A heading held and moved sideways moves
its whole column to another place; the leading columns of a table stay where they are (the ticks, the priority or
position, and the name). Widths and order are kept with the session by the table's kind; a double-click on a line
puts both back.

**The console window (MT63).** ModTrap's program writes to a console, and every line of it is on the page (History,
Log). Nothing needs the window, so the launcher starts it hidden and the browser is all there is to see. The
console itself stays, hidden: the console programs ModTrap starts write to it and would each open a window without
it. `console` hides only a console that is ModTrap's own (the launcher says so, or ModTrap is alone in it), shows
it minimised where the setting says so, and shows it whole, waiting for a key, when a start fails. Quit on the page
ends ModTrap; a closed tab does not, and starting ModTrap again brings its page back (§17).

## 25. A mod weighed at its place, and the scan of the whole list (MT65)

§21's scanner says which files a mod shares with which mods. **The evaluation** (`evaluate`) says what that comes
to, and looks at the mod's own files. It only reads, and is bounded in time.

**Where it shows.** In the install box of §21, which has two tabs once a mod is in: *Overwrites* (the lists as
before; a list cut short opens whole on a press, and the tab's body scrolls) and *Evaluation*, made as soon as the
list has been read anew with the mod in it. From a mod's menu, "Evaluate it at its place…" shows the same for any
mod.

**Every finding** has a level (likely a fault; worth a look; a note; fine), a title, why it matters in a
sentence, and the files or mods it is about. The verdict is the gravest level found.

**What its overwrites come to** (each shared file compared with the file it wins over or loses to):

- the same file byte for byte, and papers the game never loads (read-mes, licences, pictures, installer files):
  counted, and said to change nothing;
- a plugin of the same name: the whole plugin is replaced; the two plugins' masters are compared and told where
  they differ;
- the same script extender plugin twice; compiled scripts; a skeleton (with the sizes compared: a much smaller
  winner has fewer bones); face files; an archive of the same name; animation and behaviour files; distant-view
  files; menus; settings files; meshes; textures;
- a texture set put together from two mods (the colour picture from one, the surface picture from the other);
  a smaller texture over a larger one;
- files a tool of the modlist built, overwritten by the mod: the mod stands above an output it belongs below.

**The mod's own files** (TL01§33): an archive in the older game's format or another game's; a plugin saved in the
older game's form; deleted references and deleted navmeshes; animations in the older game's 32-bit format; meshes
in the older game's format; a script extender plugin built for another version of the game than the one installed
(the game's version is read from its program file); and files that lie one folder too deep for the game to find.

**What it does not do.** It does not read what two plugins change inside the same record (§23 names the records;
xEdit shows their content), and it starts no tool.

**The same mod twice** (`dupes.same_as`). A file given to be installed is compared with the modlist before
anything is installed: a mod installed from a file of the same name at the same Nexus page, a mod that has the
name the file would give its mod, or one installed from a file of the same name. Where there is one, the box says
so, with the version in the modlist and the version of the file, and offers: update that mod with it (the default
where the file is newer), install it as a second mod, or cancel (the default where it is older or the same).

**The scan of the whole list** (`dupes`), with its findings on the Health tab and their count on the tab and in
the header:

- *when a modlist is opened* (`quick`, from what is in memory and one listing per mod): the same file of the same
  Nexus page installed twice; a mod named as a copy of another; a plugin of the same name in two enabled mods; the
  same script extender plugin in two enabled mods;
  *Later, 2026-11-23 (MT68):* this list is replaced. What is looked for now: mods of the same title (and mods from
  the same file) where the older one is disabled and a newer one enabled (obsolete, a note), where an enabled one
  is wholly inside its newer version (redundant, a note), or where two are enabled and do not cover each other
  (worth a look). Each is one finding that lists its mods. A plugin or a script extender plugin of the same name
  in two enabled mods is what a patch does, and is not told. The look runs in a thread of its own;
- *on "Scan" in the header* (`deep`): every enabled mod's files are listed once, from the highest priority down.
  A mod whose every file is overwritten does nothing where it stands; a mod nine tenths of whose files are in one
  mod above it is likely that mod again; archives of the older game's format and script extender plugins for
  another version of the game are named. It runs off the page's requests, shows how far it is, and nothing that
  changes the modlist is begun while it runs (§18's rule).

**Uninstall** in a mod's menu is §16's "take it out again", for a mod ModTrap installed. A mod it did not install
it can only disable (MT9); whether that should change is MT66.

*Later, 2026-11-23:* MT66 is answered; §27 has Uninstall for any mod.

## 26. ModTrap closes with its page, and starts from it (MT64)

**Closing.** ModTrap has no window (§24), so it closes when its page does (`pagewatch`). Every request carries the
mark of the page it comes from; a page that is left says goodbye as it goes; a page the browser puts to sleep
says so first. ModTrap closes, saving its session as Quit does, when

- the last page said goodbye and none has asked anything for eight seconds (a page loaded anew is back within
  that), or
- no page has asked anything for four minutes and none said it was asleep (a browser ended without a word).

It never closes in the middle of a job, a tool's run, a download being unpacked or a scan: it waits until that has
ended. It never closes before a page was first open. A PC that slept ends nothing: the time it slept is not
counted. The setting "Close ModTrap when its page is closed" switches it off.

**Starting from the page.** A page cannot start a program, and a tab the browser brings back when ModTrap is not
running would show the browser's own error. Two things together make it work:

- *ModTrap's worker in the browser* (`page/sw.js`), entered by the page when it is first open. It answers one
  kind of request itself, and only when ModTrap does not answer: the page being asked for. Its answer is a small
  page it kept (`page/offline.html`), which says that ModTrap is not running and offers to start it. Nothing of
  ModTrap's own page is kept in the browser, and the kept page holds no token: it cannot ask ModTrap anything
  but whether it is there.
- *A link of ModTrap's own kind* (`modtrap:`, `startlink`), entered for the owner's Windows account when ModTrap
  starts from its package: Windows starts this ModTrap.exe for it. The kept page opens that link (by itself after
  ten seconds without ModTrap, on a press at once, and never by itself after a Quit), then waits for ModTrap and
  loads its page.

**Why that is safe.** The entry names one program and hands on nothing of the link: whatever a link says, ModTrap
is started the one same way, as a double-click does, and its launcher takes that start as a plain one. Any page
on the web can show such a link, and the browser asks before opening it; all it can do is start ModTrap, which
then answers only its own page, by this start's token, as always (§2). The entry is under the account's own part
of the registry, is written only for a ModTrap run from its package, and the setting "Let ModTrap's page start
ModTrap" takes it out again. A ModTrap started this way that finds no page asking within 25 seconds opens its
page itself.

## 27. Uninstall, rename, and every list change in the History (MT66)

**Uninstall** (`listjob.uninstall`) takes any mod out of MO2 without deleting anything: the mod's line leaves
every profile's mod list, the plugins that only it gives leave the load order, and its folder is moved, whole, out
of MO2's mods folder into `ModTrap - removed mods/<the job>` beside it (the same drive, so the move is a renaming
and takes no time). It is a job like §21's: MO2 closed, the lists copied first, read back, in the history.

**Asked first.** What follows from it is told as for disabling (plugins that would lose a master). A mod that came
with the modlist (it is in the list's own file, §20) is named as an original part of the modlist and asked about
a second time, in a box of its own. Where no list file was given, ModTrap says that it cannot tell.

**Rename** (`listjob.rename`) serves mods as it serves separators, as MO2 does it (MO03§6): the folder, and the
line in every profile's list. What ModTrap keeps under the mod's name in its own folder (a source link, a
favourite's mark) goes with it. The mod a tool writes into is not renamed: MO2's settings name it, and neither MO2
nor ModTrap changes those with a mod's name.

**The History** has a table of its own for every change made on the Modlist page (`Changes.list_jobs`): mods and
separators moved, renamed, enabled, disabled, mods uninstalled, plugins switched and moved; newest first, each
with its Revert while it stands. It is never cleared: "Clear job history" leaves it alone, and an uninstalled
mod's folder stays where ModTrap moved it until its Revert moves it back. A Revert puts the whole lists back
while nothing else has changed them since, and else only that change's own lines (§11), so changes can be
reverted in any order.

## 28. A mod's name, and a side of the web shown whole (MT67)

**A mod is named by its title and its version**, as in "Example Mod 1.2", when it is installed and when it is
updated (`adding.mod_name`).

- *The title* is the download's name without what the site added to it (the mod's number, the version, the time
  of upload, the site's code, a browser's "(1)"). For a newer version of a mod of the modlist it is that mod's
  name without the version at its end (`adding.title_of`), so the owner's own name for a mod carries on.
- *The version* comes from three places, in this order: what the source says of the file (the update check's
  answer for an update the Updater carries out; the record MO2 keeps beside a download); the file's name (as Nexus
  writes it, in both of its forms, or a version at the end of any other name); a file inside the archive (the
  version in the mod's own installer file), which is known only once it is unpacked and renames the mod then.
- A name that is taken gets "(2)", after §25's question about a mod that is there already. An update whose
  version nothing tells is named "Title (new)".
- A version is written with dots, without a leading "v", and without anything a folder's name cannot hold. It is
  not added to a title that ends with it already.

**The name is asked** at every install and update (a setting, on): a box shows ModTrap's name in a text field;
Enter keeps it, anything typed over it is the name. For a file given to ModTrap the box comes when the file is
taken in, while it is still being unpacked, so nothing waits on it; for an update through the Updater it comes
before the update starts (`/api/add/propose` gives the name to offer, `/api/add/name` takes the owner's). A name
that is taken or cannot be a folder's name is said and asked again. A name the owner gave is not changed by a
version found later. On the Installer tool a pen beside each mod on its list changes the name at any time before
the install.

**A side of the web shown whole.** In §23's picture, the box "+ N more" of a side now shows every mod of that
side as a box: rows are added above or below, columns to the left or the right (twelve boxes each), and the
sheet grows with them inside its frame, which scrolls. The mods are still listed beside the picture. "Show fewer"
folds the side again. A side shows up to 240 boxes; beyond that the rest stay listed.

*Later, 2026-11-23 (MT69):* a side whose mods all fit the window without scrolling is shown whole from the start,
with no "+ N more" and no "Show fewer"; the picture is drawn as large as the window allows.

## 29. MO2's own columns, and the plugins' list in groups (MT70)

**Three columns of MO2's mod list** stand in ModTrap's, before Dependants, worked out by MO2's own rules (MO04,
`modcols`):

- **Conflicts.** For every enabled mod, as MO2 marks it for loose files: its files win over other mods' (⚡+),
  lose to them (⚡−), both (⚡±), or every one of them loses (⚡∅, redundant). Left out of the reckoning, as MO2
  leaves them out: a mod's own record, a read-me and an installer's folder at its top, and everything hidden with
  `.mohidden`. A file only the game's own folder has besides is no conflict. Files inside archives are not looked
  at, as in MO2 unless its archive parsing is switched on. A folded separator shows the marks of its mods
  together. **A press on a mark opens the mod's web** (§23) with the conflicts alone: the mods whose files it
  wins over and loses to, and the plugins that change the same records; the other kinds are a press away in the
  list beside the picture.
- **Installation.** When the mod's folder was made, shown as the browser writes a date.
- **Notes.** The comments kept with the mod or the separator.

Each sorts the list by a press on its title. Installation and Notes are left out of the split view, which is
narrow; Conflicts stays.

*How it is worked out.* Installation and Notes are read from each mod's folder and record. For Conflicts every
enabled mod's files are listed once, from the highest priority down; a path is kept as a number with the mods
that have it. This runs in a thread of its own when a modlist is read; the cells show "…" until it is done and
keep what they showed before while a changed list is reckoned anew. A mod's list of files is kept in memory for
as long as its folder looks the same from above (its top entries and their times), so that a move or a tick costs
no listing; "Rescan" lists every folder anew.

**The plugins' list in groups.** Each run of plugins whose mods stand under the same separator of the mods' list
is a group under that separator's name, with its count and its positions; a group folds on a press, "Fold all"
and "Unfold all" stand beside the search box, and what is folded is kept with the session. The order stays the
load order's, so a separator's name heads a group again wherever the load order comes back to its mods. A search
or a filter opens every group; a plugin gone to is unfolded. The game's own plugins are a group of their own.

## 30. An open MO2, and a modlist read anew (MT71)

**While this modlist's MO2 is open** nothing that changes MO2's lists or its mods folder at once can be begun on
the page: the controls are greyed, a press on one says why, and the menus' entries are off with the reason. The
list of them is MT71's. Reading, scanning, a mod's web, the update check, a dry run and the tools are not touched
by it. The page does not close MO2 for a tick or a move; the chip in the header does, at the owner's press. The
server's own guard is unchanged and does not rest on the page: a job that changes the lists refuses to begin
unless it sees MO2 closed (§8).

**A modlist read anew** (after any change, a Rescan, another profile of the same modlist) leaves the page as it
is: tabs, lists and their places stay, a bar across the top says that it is being read, and the lists are drawn
anew when it has ended. The buttons that change the modlist are greyed for as long, as before (§18).

**The plugins' groups** (§29, amended): one group for each separator of the mods' list, named once, its plugins
in the load order's order, the groups in the order of their first plugins. Where a group's plugins do not stand
together in the load order, its line says so.

**A file swapped in** (`paths.write_atomic`): every write has a temporary name of its own, and a swap Windows
refuses because the file is held open for a moment is tried again for about four seconds before it is given up.

## 31. MO2's plugin groups, kept; a tool's last word (MT73)

**Which groups the Plugins tab shows.** Where the profile has a `plugingroups.txt` (MO05), the groups are MO2's
own: each plugin carries the name the file gives it, a group's line stands wherever that name changes from one
plugin of the load order to the next, and a run of plugins without a name stands under "No group", with a button
to give them one. Where the profile has no such file, §30's groups by the mods' separators stay. A word beside the
filters says which of the two is shown. Reading the groups is part of reading the lists and needs nothing switched
on.

**Writing a group** (`plugingroups.set_groups`) changes the lines of the plugins named and no other byte of the
file: a line is changed in place, added at its place by name, or taken out; the file's own line ends are kept. It
is refused where the file is not there, and for a name that could not stand in it. It is never done outside a job:
the list job and the add job take the file into their safe (§8) with MO2's other lists whenever it is there.

**When ModTrap writes one** (MT73):

| What happens | The plugin's group |
|---|---|
| A plugin is new in the load order (install, enable, first activation) | between two plugins of one group: that group; else the name of its mod's separator, unless plugins elsewhere carry that name and no neighbour does; else none |
| ModTrap moves a plugin | between two plugins of one group: that group; else its own, where a new neighbour has it or it stood alone in it; else none |
| The owner says (Plugins tab) | the name given, or none; for a whole group, its new name |
| A mod is uninstalled | nothing is written (MO2 drops the line itself); the group is remembered, and written again by a Revert that finds it gone |

Each is in the History ("Plugin's group", or with the move), and each Revert puts it back: the whole file while
nothing else has changed it, otherwise only the lines that still say what ModTrap wrote; a line changed again
since stays, and the Revert says so.

**The mods' table side by side** keeps MO2's Installation and Notes columns (§29); only the count of a mod's
plugins is hidden there.

**A mod's web** (§23), amended:

- Two plugins that change the same records without one being the other's master are a conflict only where the
  later one was made by hand. Where a tool made the later one from the load order as a whole (`adding.generated`:
  a tool's output), or it is ModTrap's demastered copy of such a plugin (it lies in ModTrap's own mod and a tool's
  output mod holds the plugin it was made from), the link is told as that plugin's change winning, with "made by a
  tool to have the last word", and the pair's block says why it is no conflict.
- The overview says what "It needs" means: how many mods the mod's plugins are built on, and that there is
  nothing to do while all of them are there and active. A master that is missing, or not active while the plugin
  that needs it is, is a warning line above it.

## 32. ModTrap's own copies in a mod's web; a demaster and the plugins' groups (MT74)

**A demastered copy** is a plugin whose file lies in a mod ModTrap made for a demaster (its name begins with
"ModTrap - "); it stands for the plugin of the same name in the highest other enabled mod that has it. In a mod's
web (§23, §31), a pair of plugins that change the same records without one naming the other as a master is, in
this order:

1. *as before the demaster*, where one of the two is such a copy and the other plugin's mod is not younger than
   the copy's file: told as the later one's change winning, with the reason; never a conflict;
2. *a tool's last word*, where the later one was made by a tool, or is a copy of a plugin a tool made (§31);
3. *settled*, where an active third plugin has both as masters;
4. *a conflict*.

The overview of ModTrap's own mod names the mods its copies stand for and says that a copy adds no conflict and
takes none away.

**A demaster's safe folder** (§8) holds MO2's groups file with the three lists, where the profile has one. A
demaster writes no group. Its Revert by lines (§11), and the finishing of an earlier Revert, give each plugin they
put back in the load order its group again where it has none: the one the safe's copy names, or, without such a
copy, the one it stands inside.

## 33. What ModTrap warns of (MT76)

**The rule.** A warning (a red or amber finding, a mark on a row, a question before a change, a note on the Health
tab) is given only for something that breaks the game or the load order. Who overwrites whom, in files or in
records, is never one.

| Warned of | Where it is read |
|---|---|
| a master missing, not active, or loading after the plugin that needs it; a master-flagged plugin needing one that is not | the plugins' headers and the load order (§5) |
| a plugin that cannot be read; more full or light plugins than the game loads | the same |
| an archive, animations or meshes in the older game's format; a script extender plugin for another game version | the files' first bytes (§26, TL01§33) |
| a deleted navmesh; deleted references; files one folder too deep | the plugin's records by kind; the mod's folders |
| a skeleton that wins with fewer bones | the two files' sizes |
| a mod's files winning over what a tool built | the files, and which mods are a tool's output (§20) |
| the same mod enabled twice | the mods' titles and files (§27, MT68) |

**Told as information, on the owner's asking:** which mod's files win (the evaluation's findings of that kind, the
web's "overwrites" and "is overwritten", MO2's Conflicts column), and, through "Scan what it overwrites", which
plugins hold the same records before and after a plugin.

**No longer told at all:** whether two plugins that change the same records "conflict". §23.2's four kinds for
records, §31's and §32's rules about them, the scan after enabling (§18) with its note and its row marks, and the
setting for it are gone. A mod's web (§23) has six kinds: it needs, needs it, a patch for it, a tool's output,
overwrites its files, files it overwrites; its second pass looks through the files only.

## 34. The tool check through xEdit, and the owner's choice on a tool's step (MT23, MT24)

**Why.** Whether a tool's plugin holds something of the mod is judged by reading bytes (§13, §14), which cannot
settle it for a patcher that writes records in a form of its own (TL01§13): such a tool is told to run again "to
be sure". xEdit knows what every field means. So the owner can have xEdit say it, before the mod is taken out.

**The run** (`toolcheck`, the script `xedit/ModTrapTools.pas`) is the record check's (§16.5) with another script:
the owner's xEdit, started through MO2, the whole active load order loaded, a script of ModTrap's own that only
reads, the plugins looked at hashed before and after. It is started only by the owner, from a tool's step
("Check through xEdit…", asked about first), and is one run for every tool's plugin at once. The mods must be
enabled: xEdit compares with their records.

**What the script compares.** The job names the tools' plugins to look through, the leaving plugins (the mods'
own and, where a dry run told them, the patches made for them) and every plugin a tool made. For each record a
tool's plugin holds that is not its own:

1. Among the plugins no tool made, the last leaving plugin that holds the record, the last plugin that stays (the
   next in line), and which of all has the last word. No leaving plugin holds it: passed over. A plugin that
   stays has the last word: counted, and nothing more (the tool built on that one).
2. Otherwise, part by part (the record's direct elements, each as text of what it means, unused bytes left out, as
   the dry run's script reads them): where the leaving plugin and the next in line say the same, nothing can be
   told. Else the tool's copy says what the leaving plugin says, or what the next in line says, or neither. Parts
   the leaving plugin has and the tool's copy lacks are weighed the same way.

**The report** (`modtrap-tools/1`): for each plugin, the records with a part of the mod's or of the tool's own
(with the parts' signatures, the leaving plugin and the next in line), up to 80 of those parts with the three
values, and the counts. **The verdict for a plugin:** it holds the mod's value (a record with a part that says
what the leaving plugin says): the tool is to run again, as proof; a value of its own where the mod has the last
word, and none of the mod's: it cannot be ruled out, "to be sure" as before, now with the records named; neither:
nothing of the mod is in it, and the plugin is cleared, a patcher's too.

**In the steps.** A finished check of this session for the same mods stands in place of the verdict from bytes for
each plugin it looked at, as long as the plugin is still the same file (its size and time of writing): a tool that
has run since is judged anew. The tool's step shows the values xEdit told, says that it was checked, and offers
the check where a plugin of the tool was judged by bytes with a stake of the mod's in it. With the mods disabled
it says that the check needs them in the load order.

**The owner's choice (MT24).** On a tool's step that is not yet done: "Leave it until the tool's next run". The
step then counts as settled by the owner (it is shown as left, ModTrap's run of the tools passes it over), and the
note says what follows: the tool's output keeps what it has of the mod until then. Kept in the session, for these
mods; "Take that back" undoes it. ModTrap does not change a tool's plugin to put such a value right (MT24's
option (a) is not built).

## 35. The plugins' list: picking, creating groups, and a drop on a group's line (MT77)

**Picking.** On the Plugins tab a click picks a plugin (and shows its details, as before), Ctrl-click adds or
takes one, Shift-click picks every shown plugin from the last one to this one. The picked rows are marked. A
right-click on a picked row is about all picked plugins; on another row it picks that one alone.

**The menus**, where MO2 keeps plugin groups (§31):

| On | Entries |
|---|---|
| a plugin, or the picked plugins | "Create group…" (one without a group), "Create group of these N…", "Change its group…"; "Take it out of its group" / "Take them out of their groups" |
| a group's line | "Rename the group…", "Dissolve the group" |
| the line of a run without a group | the button "Create group…", for the run |

Each writes MO2's groups file as one job (§31). While nothing may be changed, the entries are greyed and the menu
begins with the reason in words and, where MO2 is open, the entry "Close MO2…" (§30).

**Dragging a plugin** (§18, MO03§3 and §4) is unchanged in its limits. Added: a drag that cannot begin because
MO2 is open says so; and a group's line is a place to let go on. The move then asks for the place directly before
the group's first plugin and names the group (`group` of `/api/list/plugins/move`). The job takes that group only
where the plugin then stands beside a plugin of it; otherwise §31's rule for a moved plugin decides. A plugin that
already stands there is only given the group.

## 36. The bulk installer; clearing the Installer tool; picking several mods; a drag's aim (MT78)

**Bulk install** is the second tab of Install mods. Its list is the page's own: the ids of archives taken in,
kept with the page's state for the session.

| Stage | What happens | Routes |
|---|---|---|
| A file is added (dropped, or chosen as files or a folder) | not an archive: passed over; its name on the list already: turned away | none |
| Its turn in the queue | MO2 has installed this file: turned away. Else it is read where it lies in MO2's Downloads or sent, unpacked and named (§16.1, MT67) | `/api/add/resolve`, `/api/add/take` or `/api/add/upload` |
| Taken in | the same mod in the modlist, or the same title and version on the list: forgotten again, turned away | `/api/add/forget` |
| On the list | its state is asked for all lines at once, without any analysis; its name is typed over; its installer's questions are answered as on the Installer tool | `/api/add/status`, `/api/add/name`, `/api/add/installer`, `/api/add/choose` |
| "Bulk install" | greyed until a mod is ready and none is being taken in or waits for answers; then the place is chosen on the Mods tab (as §16.8's "Manual placement") and confirmed | none |
| The run | lots of eight in the list's order, each analysed at that place and installed as one job (§16.8); a refused lot mod by mod; the failed once more at the end | `/api/add`, `/api/add/run` |

`/api/add/status` takes up to 5,000 ids and answers each archive's state as the Installer tool's answer does,
with the mod's title; it starts nothing. The Installer tool's own analysis keeps its limit of twenty.

What was turned away or failed is listed above the lines; the header counts warnings and errors. A run that
cannot go on at all (MO2 open) stops and says so; what was installed stays.

**Clearing the Installer tool:** "Clear" on a mod's card and "Clear all" in the header take mods off the page; an
unpacked copy in ModTrap's work folder is removed (`/api/add/forget`), a mod of MO2 only leaves the page.

**Picking several mods** (Mods tab, Updater list): click, Ctrl-click, Shift-click, as §35 has it for plugins; the
picked mods are one set for both lists. A right-click on a picked row gives the menu for all of them; a drag of a
picked row moves all picked mods as one block (`/api/list/move` takes them so).

**A drag's aim** (mods and plugins): the place is worked out from the element under the pointer's last position,
at every move of the pointer and after every step by which the list scrolls at its edge. For a plugin, the room
of the list's pane below the last row is the end of the load order.

## 37. Names in use; the lists' arrows and where a list begins (MT79)

**A name in use** (`Api._names_taken`), for naming a mod about to be installed (§16.1, MT67): the names of every
mod and folder of the modlist, and of every archive taken in whose state is still copying, unpacking, ready or
waiting for its installer's answers. Records in the states "installed" and "failed" hold no name.

**Numbers nothing calls for.** The Health tab lists each mod whose name ends in a number in brackets (up to two
digits) where no entry of the modlist has the name without it; of several with one plain name the first gets it.
"Take the numbers off…" asks, then renames them one after another with `/api/list/rename` (§27), each a job with
its Revert. ModTrap's own demaster mods are left out.

**Arrows.** ▲ and ▼ stand in the header of the mods' list, the plugins' list and the Updater list, and scroll
that list's pane to its top or its bottom.

**Where a list begins.** When the lists are drawn for a session for the first time in a page (a start, a page
loaded anew, another modlist), and when they are drawn after "Rescan", each of the three lists is owed its
bottom: the ones shown go there at once, the others when they are first shown. In every other reading anew the
lists keep their places (§30).

## 38. Source links by any page, asked at once; a fix for a plugin the game does not load (MT80)

**An address the owner gives** (`sources.parse_link`, WHY§147). A mod's page at Nexus is known by its game and
number, with whatever follows (a tab, a file's number, a mark in the page), under `www.`, `next.` or neither, with
`games/` before the game or not, and as a "mod manager download" link. A repository at GitHub is known by its
owner and name from any page of it, and from GitHub's hosts for code and for programs; the page of one release, a
file of one release, or the packed code of a tag also names the release installed. GitHub's own pages (an
organisation's, the settings) and an account's page are not repositories. An address without `https://` gets it.
Anything else is kept as a plain address. The answer to the page says what was made of it.

**Asked at once** (`Updating.ask_soon`). A link to Nexus or GitHub, once kept, starts a scan of that one mod, as
"Ask about this mod now" does. While a scan is going the mod is noted and asked about when that scan ends.

**The installed version** (`sources.gather`). The mod's own record first, then the list's file, then the version
the mod's name ends with, then the one its archive's name ends with; the last two are marked "by its name" on the
Updater list. `addjob` writes that version into the record of a mod it installs.

**GitHub** (`updates.github_releases`, `github_verdict`). One question for a repository: its ten newest
releases. Kept: the newest full release with its files; a pre-release that came after it; or, with no full
release, the newest pre-release in its place. The verdict, in this order: the release named by a link or a record;
the version (the same as the newest: current; both numbers and the newest higher: update; lower: current, said
so); the newest release's version found whole in the mod's or the archive's name: current; else unclear.

**A script extender plugin for another version of the game** (§25, §33; `evaluate.plugin_use`, `pex.py`,
WHY§146). Judged only where the game loads that copy. Then the mod's compiled scripts are read, up to 600 of
them, the mod's own copies and the copies the game loads:

| what the scripts say | what is told |
| --- | --- |
| no script declares functions that this plugin names | a likely fault, as before |
| scripts the game loads still call those functions | a likely fault, naming the scripts and the mods above that replace other files |
| the scripts that called them are replaced, and none calls them now | a note, naming the mod that replaced them |
| the declaring script is replaced by one that declares none of them | a note, naming that mod |

The same holds in a mod's own weighing (§25), which also says where a mod above replaces the plugin itself. An
archive in the older game's format is named only where the game loads that copy. The scan of every mod lists a
mod's files up to two million and for up to a minute, within its own limit of time.

## 39. One installer; the Installer tool in parts; versions in order (MT81)

**The run** (`installRun`, the page). Started by a drop on the mods' list (with the place under the pointer,
MT57) or on the Installer tool (without one), for up to ten archives. Its stages, shown in one box:

| stage | what happens | where it waits for the owner |
| --- | --- | --- |
| Taken in | the archive goes to ModTrap's work folder | a mod that is in the modlist already (§25); the name (MT67) |
| Unpacked | ModTrap's own unpacking | |
| Answers | only where the archive has an installer: its questions, in the box | "Use these answers" |
| Read | the analysis of §16 for the place | stops where something the mod needs is missing |
| Placed | only for a drop without a place, with "Always place a new mod by hand": the box steps aside, one click on the Mods tab | the click; Esc ends the run with nothing installed |
| Installed, Checked | the add job (§16.8): MO2 closed, safe copies, the lists read back | |

A drop without a place and without that setting goes last, before what the tools made; an update takes the older
version's place. Off the run: with "Install a dropped mod by itself" switched off (on as ModTrap comes), with MO2
open, or without the switch for changes, a drop on the tool is taken in and read, and "Install mod" does the rest
as before. More than ten archives at once are handed to the bulk installer (§36).

**An installer's options** (`fomod.needs`, `Api._installer_marks`). For each option: the plugins its conditions
ask to be active, and the masters of the plugins it installs, less the game's own and the installer's own. Each
is looked up in the load order: active, not active, in a disabled mod, or missing. All active: "✅ in your
modlist". Otherwise the option names what is not. Up to 600 options are read for masters.

**What is in hand, and what is done.** The tool's list holds what is still to be installed, and mods of MO2 the
owner asked to look at. A mod installed leaves it. "Installed lately" lists the newest fifty installs from their
records (`/api/installed`, which gives the newest two hundred and the count of all). ModTrap's unpacked copies of
installed mods: the newest fifty are kept (`Api._prune_staged`), at an install and at the opening of a session.

**The tool's page, top to bottom:** Install (the button, the place, the tool card where one runs); the installer's
questions where one waits outside a run; The mod (room in the load order, a card for each mod); The steps, in four
parts (what the mod needs first: `needs`; the install itself: `install`, `update`, `enable`, `activate`, `health`;
what it changes at its place: `files`, `differs`, `records`; afterwards: `tools`), each part with its number, its
state, and its steps as rows, a step's reason behind "Why"; Installed lately.

**Drop zones.** While a dragged file is over one, it has the class `glow` (the page's bar, the welcome page's
zone, the Updater's, the bulk installer's, the one for ModTrap's own update).

**Versions in order** (`updates.rank`, `updates.order`, WHY§148). Numbers, then pre-release, release, or release
with a letter. Used by the GitHub verdict (§38) in place of numbers alone, and by the Nexus verdict where the
installed file could not be told: a version that is a current file's is current; on a page with one current file
in all, a lower version is an update and a higher one is said so.
