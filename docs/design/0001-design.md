# Design 0001: ModTrap

*2026-11-20 · Proposed. Nothing here is built. Open choices are in [DECISIONS.md](../DECISIONS.md) (MT4 onwards);
findings are cited from [REASONING.md](../REASONING.md) as R-numbers.*

## 1. What ModTrap does

The owner picks a modlist folder (an MO2 instance). ModTrap lists the mods installed in it. The owner ticks the mods
to take out and presses **Demaster Selected**. ModTrap then does, by itself, what the community's "Master Removal"
procedure has the user do by hand in xEdit (R1), for every plugin that depends on the ticked mods, and shows its
work line by line in a terminal on the page. At the end the ticked mods can be disabled in MO2 without "missing
master" errors.

Words used below:

- **trapped mod**: a mod the owner ticked. Its plugins are the **trapped plugins**.
- **dependant**: a plugin of another mod that lists a trapped plugin among its masters.
- **output mod**: a new mod folder ModTrap makes in the instance, holding the demastered copies of the dependants.

Out of scope: the other steps a modlist's guide may ask for afterwards (installing replacements, re-running tools
such as an animation or patcher step). ModTrap ends when the masters are gone, and says what it did.

## 2. Shape (the DataPiler pattern)

- One program on the owner's PC, Python standard library only, started by a launcher. It serves one page on
  `127.0.0.1` and opens it in the browser. Host, Origin and per-start token checks, a strict content policy, no CDN,
  no remote fonts, no analytics: DataPiler's server, reused and credited (R24).
- The page reads the instance; it never writes to it. Writing happens only in a job, only after the owner confirms
  a plan, and only into ModTrap's work folder and its output mod.
- A job is data: the instance, the profile, the trapped plugins, the dependants and what to do with each. The
  script that xEdit runs is one fixed file of ours; it reads the job from a small file beside it (R4, R28).
- ModTrap contains no part of MO2 or xEdit. It finds and calls the owner's installed copies.

## 3. Reading the instance (no xEdit needed)

From `ModOrganizer.ini` and the chosen profile (R20, R21), read-only:

1. the mods folder, the profiles folder, the game's folder, the selected profile, and the configured executables
   (to find the owner's xEdit);
2. `modlist.txt`: every mod, its priority, whether it is enabled;
3. each mod folder's plugins (`.esp`, `.esm`, `.esl` at its top level);
4. each plugin's header, read by ModTrap's own small reader: its master list and its flags. Nothing else of a
   plugin is read by our code (R26);
5. `plugins.txt` and `loadorder.txt`: which plugins are active and in what order.

Where the same plugin name exists in several enabled mods, the one MO2 would use (highest priority) counts, and the
page says so. From this ModTrap builds, for every mod: its plugins, their masters, and their dependants.

## 4. The page

- **Instance bar.** The modlist folder (picked once, remembered), the profile, the game, the xEdit found, and
  whether MO2 is open.
- **Mod list.** Every mod, as MO2 orders them, with a search box and filters (enabled only; has plugins; has
  dependants). Each row: tick box, name, its plugins, and a count of dependants. A mod with no plugins, or whose
  plugins nothing depends on, cannot be ticked: there is nothing to demaster, and the row says "can be disabled as
  it is".
- **Selection panel.** For the ticked mods: every dependant, grouped by the mod it lives in, with what ModTrap
  proposes for it (§5) and a way to change that per dependant.
- **Demaster Selected.** Opens the plan (§6.1). Nothing has run yet.
- **Terminal.** A live, scrolling log of the job: ModTrap's own steps, and the lines our script writes as xEdit
  works (R13). A copy is kept in ModTrap's work folder.
- **Result.** Per dependant: masters before and after, what was removed, what was left alone and why; then the
  next steps for the owner in MO2.

## 5. What happens to each dependant

For each dependant, one of three treatments. ModTrap proposes one; the owner can change it (MT6):

- **Demaster** (the default): §6.
- **Leave for me to disable**: the dependant exists only for a trapped mod (the guide's "patch" case, R2). ModTrap
  proposes this when the dry run shows that nothing, or almost nothing, of the plugin would remain; the plan lists
  it under "disable these yourself".
- **Skip**: the owner will deal with it another way.

Within a dependant that is demastered, each thing that needs a trapped plugin is one of these cases (MT4):

| Case | What needs the trapped plugin | What ModTrap does (proposed) |
|---|---|---|
| A | The record itself belongs to the trapped plugin (the dependant overrides it) | Remove the dependant's copy of the record |
| B | An entry in a list inside a record that belongs to someone else (a FormID list entry, a levelled list entry, a keyword in a keyword list) | Remove that entry, keep the record |
| C | A single field that cannot simply be absent (for example the one race of an actor) | Put back the value the record has in the dependant's remaining masters, if they have the record; otherwise case D |
| D | Anything else, or anything xEdit refuses to remove | Change nothing in this dependant; report it as "needs you", with the record and field |

A dependant with any case D is not half-done: it is left exactly as it was and named in the result. Nothing is
forced. After the removals, the script runs xEdit's Clean Masters on the dependant and reports again; a dependant
counts as done only if the trapped plugins are gone from its master list **and** the report is empty.

## 6. A job, step by step

### 6.1 Plan

Built from §3 alone, shown before anything runs: the trapped plugins; every dependant and its treatment; the
plugins xEdit will load (the dependants and all their masters, in load order, and nothing else, R6); the folders
ModTrap will write to; the exact command it will run. The owner confirms or goes back.

### 6.2 Dry run

Always first. xEdit is started through MO2 (§7) with our script in **report** mode: it changes nothing in memory
and writes nothing but its report. The report lists, per dependant, every case A to D it found. The page shows it
as the detailed plan: "this is exactly what will be removed". Treatments proposed in §5 are refined from it. The
owner confirms again, now knowing every change.

### 6.3 The run

xEdit is started again with the script in **apply** mode. For each dependant: do the removals, Clean Masters,
report again, and if the dependant is done, write the changed plugin to the output mod with `FileWriteToStream`
(R10), then mark the loaded original as not needing a save (R11, R12), so that xEdit's own save on close never
touches the original. The script writes a line to its progress file after each step.

Belt and braces, whatever the script does:

- before the run, ModTrap records the size and SHA-256 of every plugin xEdit will load, and copies each dependant
  into its work folder as a backup;
- xEdit's own backup folder is pointed at ModTrap's work folder (`-B:`, R8);
- after the run, every recorded plugin is hashed again. If an original differs, ModTrap puts its backup back at
  once and says so plainly.

**Fallback if R12 does not hold on the owner's PC** (R15): the output mod is made first, holding plain copies of
the dependants, and enabled above the originals; xEdit then loads and saves those copies, in place, and the
originals are still never touched. This needs the output mod to be enabled before the run (MT9), so it is the
second choice.

### 6.4 Check

ModTrap's own reader (§3.4) opens each plugin in the output mod: it must be well-formed, the trapped plugins must be
absent from its masters, and every remaining master must exist in the load order. A plugin that fails is removed
from the output mod and reported.

### 6.5 Hand-over

The output mod is a normal mod folder, `ModTrap - <name>`, in the instance's mods folder, containing only the
demastered plugins, under their original file names, plus a small text file saying what ModTrap did and when. The
page then lists the owner's steps in MO2: refresh; enable the output mod (it wins over the originals by priority);
disable the trapped mods and the dependants listed "disable these yourself". To undo: disable or delete the output
mod; every original is as it was.

## 7. Starting xEdit through MO2

`ModOrganizer.exe -p "<profile>" run -e -a "<arguments>" "<xEdit's name in MO2>"` (R16), where the arguments are
our script (`-script:`), our plugins file (`-P:`), `-autoload`, `-autoexit`, a backup folder (`-B:`) and a log
file (`-R:`) (R4 to R9). MO2 may be open or closed (R17); ModTrap never starts a second MO2 on the instance (R23).
ModTrap watches the script's progress file and xEdit's process for the end (R18), with a time limit and a
**Stop** button that closes xEdit; a stopped or crashed run writes nothing to the output mod.

Our script and the job file live in ModTrap's work folder, outside the instance's mods and outside xEdit's folder:
nothing is installed into either.

## 8. Safety rules (the guard)

1. ModTrap writes only inside its own work folder and its own output mod folder. Every path a job would write is
   checked against these two roots after resolving links, before the job starts.
2. It never writes in the game's folder, in any other mod's folder, in `overwrite`, or in a profile (MT9 may relax
   the last, for `modlist.txt` only, if the owner chooses).
3. An output mod folder that already exists is never overwritten: a new run makes a new folder, or the owner
   confirms replacing ModTrap's own earlier output.
4. Originals are hashed before and after every run (§6.3).
5. A job is refused if a trapped plugin is one of the game's own files, or if a dependant is.
6. The script has a closed set of actions (report, remove a record, remove an entry, restore a value, Clean
   Masters, write out). The job file can only choose among them.

## 9. What must be proven on the owner's PC first

Before any real mod is touched, a **probe**: ModTrap writes three tiny invented plugins into a test mod of its own
(a "bad" one, and two that depend on it in the ways of cases A and B), and runs the whole of §6 on them. It proves
or disproves R12, R13, R18 and R22. Only when the probe passes does the page allow a real job.

## 10. Build order (proposed)

1. **0.1 Read.** Launcher, server, page; instance picker; mod list with masters and dependants. No xEdit. Useful by
   itself: it answers "what depends on this mod?".
2. **0.2 Report.** Finding xEdit; the script in report mode; the probe; the dry run and the terminal.
3. **0.3 Trap.** Apply mode, the output mod, the checks, the result page.
4. **Later.** The updater and the built launcher, as in DataPiler; other games (MT7).

Tests at every step use invented plugins written by the test code. The xEdit script itself can only be tested on
the owner's PC (R15); everything around it is tested here.
