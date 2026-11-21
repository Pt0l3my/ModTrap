# Design 0001: ModTrap

*2026-11-20 · Adopted as the working design under MT17; revised the same day after the owner's answers (MT4 to
MT11, MT14, MT15, MT17, MT18). Built so far: the reader and the page (WHY§29), the dry run (WHY§31), sessions (WHY§33), the Steps tab (WHY§35). The demaster itself is written and tested against a stand-in for xEdit but switched off (WHY§36, WHY§39): nothing the page can do writes to an instance. Adding mods (§16, MT21) is built as far as it only reads (WHY§40). Open choices are in [DECISIONS.md](../DECISIONS.md); findings are cited by code: `WHY§n` is
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
- **History.** §12. Every change ModTrap made, with **Re-enable** on each disabled mod and **Revert** on each job.

## 5. What happens to each dependant

For each dependant plugin, one treatment. ModTrap proposes it; the owner can change it (MT6):

- **Demaster** (§6): the plugin does other things too, and should go on working without the trapped mod.
- **Switch off** (patch-only): the plugin exists only for the trapped mod. ModTrap **disables its mod** when every
  plugin that mod provides is patch-only, and **deactivates the plugin alone** when it is one among others, as in a
  patch collection (WHY§26). The first reading comes from the headers (which of a mod's plugins depend on the
  trapped mod); the dry run settles it (nothing, or almost nothing, of the plugin would remain).
  Where most of a mod's plugins depend on the trapped mod and nothing else needs the rest, ModTrap proposes
  disabling the mod whole and names the leftover plugins for the owner to judge (WHY§28).
- **Run the tool again**: the plugin is the generated output of a patcher or generator (§13). The output of an
  editor such as xEdit cannot be made again by ModTrap, and is demastered (WHY§28).
- **Skip**: the owner will deal with it another way; the job then cannot disable the trapped mod, and says so.

Within a dependant that is demastered, each thing that needs a trapped plugin is one of these cases (MT4): A and B
are done automatically, C is reported at first and automatic later, D always becomes a step for the owner (§14):

| Case | What needs the trapped plugin | What ModTrap does (proposed) |
|---|---|---|
| A | The record itself belongs to the trapped plugin (the dependant overrides it) | Take the dependant's copy of the record out of the dependant |
| B | An entry in a list inside a record that belongs to someone else (a FormID list entry, a levelled list entry, a keyword in a keyword list) | Take that entry out, keep the record |
| C | A single field that cannot simply be absent (for example the one race of an actor) | At first: as D. Later: put back the value the record has in the dependant's remaining masters, if they have the record |
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

`ModOrganizer.exe -p "<profile>" run -e -a "<arguments>" "<xEdit's name in MO2>"` (MO01§3), where the arguments are
our script (`-script:`), our plugins file (`-P:`), `-autoload`, `-autoexit`, a backup folder (`-B:`) and a log
file (`-R:`) (XE01§2 to XE01§6). An open MO2 takes the command over (MO01§4); ModTrap never starts a second MO2 on
the instance. ModTrap watches the script's progress file and xEdit's process for the end (WHY§7), with a time limit
and a **Stop** button that asks first.

MO2 must be closed only while ModTrap writes to the profile (§6.5 step 2, Re-enable and Revert): an open MO2 keeps
the mod list in memory and writes it back (MO01§2). ModTrap checks, and asks the owner to close MO2 for that step.

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

Before any real mod is touched, a **probe**: ModTrap writes three tiny invented plugins into a test mod of its own
(a "bad" one, and two that depend on it in the ways of cases A and B), and runs §6 on them, safe folder and Revert
included. It proves or disproves WHY§4, WHY§5, WHY§7 and WHY§8, and it is also how ModTrap decides whether the
owner's xEdit version is one it can work with (MT8, WHY§15). Only when the probe passes does the page allow a real
job; it runs again when the tools change.

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

## 16. Adding mods (MT21)

Beside taking mods out, ModTrap helps to put extra mods in. The owner's own way is to add a mod last and its plugin
last; that works until the new files or records land after something that was meant to stay last, or the plugin
needs something that is not there. This section is what ModTrap does about it. Built so far: §16.1 to §16.4, §16.6
and §16.7, none of which changes a modlist (WHY§40, WHY§41). Not built: §16.5 and §16.8.

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
- **An installer that asks questions.** An archive with a `fomod` installer, or with several folders to choose
  from, is said so and handed to MO2 for now: the owner installs it there, and ModTrap carries on from the
  installed mod. ModTrap asking those questions on its own page is the next piece (§16.8).
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

- **Among the mods:** after every ordinary mod, so that it wins each file it shares with them, as it does when the
  owner puts it last; but before the mods that hold what the modlist's tools made (§13), which stay last and are
  made again. A mod counts as a tool's output when MO2 sends a tool's new files to it, when every plugin in it was
  made by a tool, or, failing both, when its name says "output". A separator right before the outputs stays with
  them. With no output found, the mod goes last.
- **In the load order:** after every master the plugin names, and before the run of tool-made plugins at the end
  (§13; an editor's output does not count, TL01§6). A master-flagged plugin goes to the end of the masters' block
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

### 16.5 Records (not built)

- Which records the new plugin overrides, and which other plugins change the same records, only xEdit can read. It
  can tell a script whether a record is in conflict (XE01§10). ModTrap is to read this through the same read-only
  run as the dry run (§7) and list, for each record the new plugin takes from a patch of the modlist, what is lost;
  from that, whether a patch is needed and for which records.
- Until then the step list says how to look in xEdit by hand.

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

### 16.8 Carrying the steps out (not built)

What "Add it" is to do on its own, in order, each step in the history (§12) and undone by Revert (§11):

1. With MO2 closed (§8): copy the unpacked mod into MO2's mods folder under its name, with a `meta.ini` naming the
   archive (MO01§7), so that MO2 knows it as an installed mod.
2. Put it in its place in the mod list and enable it; put its plugins in their place and activate them (§16.3).
3. The health check (§3).
4. Start xEdit through MO2 for the read-only record check (§16.5), and list what it finds.
5. For each tool that must run again (§16.6): start it through MO2 for the owner, who works it; ModTrap waits and
   checks the tool's output afterwards.

Left to the owner: an installer's questions (asked on ModTrap's own page, once that is built: the installer's
description file names the choices and what each installs), the tools themselves, a patch where the record check
shows one is needed, and playing. "Take it out again" disables the mod and deactivates its plugins; nothing is
deleted (MT9).

Later, if they prove worth it: comparing packed files; reading the owner's own installed copy of a sorting tool's
rules for known incompatibilities (its licence is to be read first); proposing a patch from §16.5.
