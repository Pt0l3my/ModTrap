# Reasoning log

The working-out behind findings, conclusions, rejected paths and workarounds, in brief, so that a new session or a
switch of model starts with it in view. Decisions stay in [DECISIONS.md](DECISIONS.md) and source facts in
[the research notes](research/README.md); an entry here points to them and does not repeat them.

**How to use it.**

- Read the index below at the start of a session and after a model switch, then open an entry by its code:
  `wp show WHY§4`. `wp find` and `wp grep` search it; `wp refs MT5` lists the entries citing a decision.
- Append only. Entries are numbered in order and never renumbered or rewritten; a later finding adds a dated
  **Later** line to the entry, or a new entry that supersedes it.
- One entry per finding, a few lines: what was seen, what follows, what was ruled out, and the next step if any.
- **Labels**, as the research notes use them: **FACT** (read in a named source, or seen on the owner's PC),
  **LIKELY** (strong inference, not yet checked), **SPECULATION** (a guess worth recording), **METHOD** (how
  something is done, and why), **DECIDED** (a pointer to the decision that settled it).
- **Tags:** `#procedure` (the manual master removal), `#xedit`, `#mo2`, `#vfs` (MO2's virtual file system and what
  a write does), `#safety` (backups, Revert, nothing lost), `#tools` (the modlist's tools and their versions), `#server`, `#page`, `#datapiler`, `#process`.
- The privacy rules bind it as every file: nothing personal, no paths from the owner's PC, nothing taken from a
  real mod. No model identifiers.

## Index

| # | Date | Entry | Label | Tags |
|---|---|---|---|---|
| 1 | 2026-11-20 | Why this log exists, and its form | METHOD | #process |
| 2 | 2026-11-20 | The manual procedure that defines "demaster" | FACT | #procedure |
| 3 | 2026-11-20 | xEdit can do the procedure unattended, from our own script | FACT | #xedit |
| 4 | 2026-11-20 | Write the changed plugin elsewhere and keep xEdit from saving the original | LIKELY | #xedit #vfs #safety |
| 5 | 2026-11-20 | Progress for the page comes from a file the script writes | LIKELY | #xedit #page |
| 6 | 2026-11-20 | What cannot be proven here is proven by a probe on invented plugins | METHOD | #xedit #mo2 #safety |
| 7 | 2026-11-20 | MO2 starts a tool from the command line, open or closed | FACT | #mo2 |
| 8 | 2026-11-20 | A save through MO2 lands in the original mod's folder | LIKELY | #vfs #safety |
| 9 | 2026-11-20 | What ModTrap takes from DataPiler | FACT | #datapiler #server #page |
| 10 | 2026-11-20 | Rejected: editing plugins with our own code | METHOD | #safety #xedit |
| 11 | 2026-11-20 | Rejected: driving xEdit's window, and a script generated per job | METHOD | #xedit |
| 12 | 2026-11-20 | The session link is left out of commits | FACT | #process |
| 13 | 2026-11-20 | The owner's reference system adopted | METHOD | #process |
| 14 | 2026-11-20 | The owner's xEdit is 4.1.5f, in a tools folder inside the modlist folder | FACT | #xedit #tools |
| 15 | 2026-11-20 | Compatibility is decided by the probe, not by a list of versions | METHOD | #xedit #tools |
| 16 | 2026-11-20 | Auto disable means writing modlist.txt, and only with MO2 closed | METHOD | #mo2 #safety |
| 17 | 2026-11-20 | The safe folder is taken after the dry run, and Revert checks before it writes | METHOD | #safety |
| 18 | 2026-11-20 | Replace the originals, or a ModTrap mod above them | METHOD | #vfs #safety |
| 19 | 2026-11-20 | "Nothing gets removed" was about the mod, not about records | METHOD | #procedure #process |
| 20 | 2026-11-20 | The method is ModTrap's to choose: what was chosen for MT4 and MT5 | DECIDED | #procedure #safety |
| 21 | 2026-11-20 | What "clean" can and cannot be checked by a tool | METHOD | #safety #procedure |
| 22 | 2026-11-20 | Telling which tool made a patch: evidence, and marks kept as data | METHOD | #tools #mo2 |
| 23 | 2026-11-20 | MO2's plugin lists and the plugin header are read from their sources | FACT | #mo2 #xedit |
| 24 | 2026-11-20 | Version 0.1's reader exists, and what it has not yet met | METHOD | #mo2 #process |
| 25 | 2026-11-20 | The first scan of the owner's modlist agrees with MO2 | FACT | #mo2 #process |
| 26 | 2026-11-20 | A patch is often one plugin in a collection: disable the plugin, not the mod | METHOD | #procedure #mo2 |
| 27 | 2026-11-20 | The real list shows generated outputs and loose files, as the design assumed | FACT | #tools #procedure |
| 28 | 2026-11-20 | The second scan: a patch with no master, MO2's output setting, and its limits | FACT | #tools #mo2 #procedure |
| 29 | 2026-11-20 | Version 0.1's page: what was built, how it was tested, what was not | METHOD | #server #page #process |
| 30 | 2026-11-20 | A dropped folder has no path: ModTrap finds it from its ModOrganizer.ini | METHOD | #page #mo2 #safety |
| 31 | 2026-11-20 | The dry run is built; what its first run on the owner's PC has to show | METHOD | #xedit #mo2 #safety #process |
| 32 | 2026-11-20 | A friendlier page: what was changed and why | METHOD | #page |
| 33 | 2026-11-20 | Sessions and Quit: how the state is kept, and what "safe to finish" means for now | METHOD | #page #safety #process |
| 34 | 2026-11-20 | The script checked against the script engine's source, without running it | METHOD | #xedit #process |
| 35 | 2026-11-20 | The Steps tab: a checklist the modlist's own files tick off | METHOD | #page #procedure #tools |
| 36 | 2026-11-20 | Groundwork for the demaster, built ahead and switched off | METHOD | #safety #mo2 #process |
| 37 | 2026-11-20 | Which tool made a plugin: read in the tools' own sources, kept as data | FACT | #tools |
| 38 | 2026-11-20 | A Browse button: an in-page folder picker | METHOD | #page |
| 39 | 2026-11-20 | The demaster built end to end against a stand-in, and kept switched off | METHOD | #xedit #mo2 #safety #process |
| 40 | 2026-11-21 | Adding mods: what is built, the placing rule, and what was ruled out | METHOD | #adding #mo2 #page #tools |
| 41 | 2026-11-21 | A dropped archive is unpacked by ModTrap itself, in its own folder | METHOD | #adding #mo2 #safety #licence |
| 42 | 2026-11-21 | Carrying out an add: written and tested against invented lists, switched off | METHOD | #adding #mo2 #safety #process |
| 43 | 2026-11-21 | An installer's questions are asked on ModTrap's own page | METHOD | #adding #page #safety #licence |
| 44 | 2026-11-21 | "Add it for me" and Revert on the page, behind a switch that is off | DECIDED | #adding #safety #process #page |
| 45 | 2026-11-21 | The record check and starting the tools: built, and not behind the switch | METHOD | #adding #xedit #tools #process |
| 46 | 2026-11-21 | "Demaster Selected" on the page behind the same switch, and a History tab | METHOD | #xedit #mo2 #safety #page #process |
| 47 | 2026-11-21 | The probe is built and gates real work; Revert goes line by line once MO2 has run | METHOD | #safety #mo2 #xedit #process |
| 48 | 2026-11-21 | "Save this session": the logs cleaned and packed into one .7z, written with Python alone | METHOD | #page #safety #licence #process |
| 49 | 2026-11-21 | The first real run of the probe: what passed, what failed, and what was changed for it | FACT | #xedit #mo2 #adding #process |
| 50 | 2026-11-21 | The probe passes on the owner's PC: what that proves, what it does not, and a message of MO2's | FACT | #xedit #mo2 #safety #process |
| 51 | 2026-11-21 | xEdit's "Module Selection" window: always shown in script mode, nothing to choose, ModTrap presses OK | FACT | #xedit #page #process |
| 52 | 2026-11-21 | The first real dry run against the guide: the same plugins, a different split; what was changed for it | FACT | #procedure #xedit #safety #process |
| 53 | 2026-11-21 | The second real dry run stopped at a file held by another program; the scripts now bear it, and a probe pass counts only for the scripts it ran | FACT | #xedit #mo2 #safety #process |
| 54 | 2026-11-21 | The probe and the dry run pass again with the changed scripts; MO2's message is closed the moment it shows | FACT | #xedit #mo2 #process |
| 55 | 2026-11-21 | What the big patch files carry on from the mod, as the evidence run showed it; MT4's case C becomes automatic, and the probe proves it first | DECIDED | #procedure #xedit #safety #process |
| 56 | 2026-11-21 | The probe proves the put-back on the owner's xEdit; all five big files read as demasterable; a copy that hides a remade original is called out | FACT | #xedit #mo2 #tools #safety #process |
| 57 | 2026-11-21 | The Steps tab still gave ModTrap's own steps to the owner; they are ModTrap's now, with the button | METHOD | #page #steps #process |
| 58 | 2026-11-21 | ModTrap knows whether this modlist's MO2 is open, and asks before closing it; every step says truly who does it | METHOD | #mo2 #page #steps #safety #process |
| 59 | 2026-11-21 | The first real demaster: four big files done, one left; "Demaster Selected" now goes in one go; a row click shows a mod and what is tied to it | FACT | #xedit #page #safety #process |
| 60 | 2026-11-21 | A button that waits for the probe says so in plain sight and runs it; "Demaster Selected" takes the probe into its one go | METHOD | #page #safety #process |
| 61 | 2026-11-21 | Why one big file was kept back: a topic's group outlives the topic; and the page's own question box, steps that follow the work, a dry run that says when it is out of date | FACT | #xedit #page #steps #safety #process |
| 62 | 2026-11-21 | New plugins that wait to be put in place are dropped once the modlist has moved on; Revert clears what the page still showed | METHOD | #page #safety #process |
| 63 | 2026-11-21 | The first whole demaster of a real mod is in place; which tools must run again is now decided by what their output holds | FACT | #xedit #tools #steps #process |
| 64 | 2026-11-21 | Sharing a record is not carrying the mod's change: one verdict for each tool, from what the mod really changes, with the evidence to unfold | METHOD | #tools #steps #page #process |
| 65 | 2026-11-21 | The demaster is in place a second time; the tool evidence compared bytes where plugins number their masters differently, and raised a false alarm | FACT | #tools #steps #xedit #process |
| 66 | 2026-11-21 | Reading bytes cannot say what a mod changes: xEdit says it in the dry run, and tools are judged from that or not at all | DECIDED | #tools #steps #xedit #process |
| 67 | 2026-11-21 | "No change" was an update without a restart: ModTrap now notices it; MO2 is closed without a question inside a confirmed demaster; finished jobs go to the History tab and can be cleared | DECIDED | #process #page #mo2 #history |
| 68 | 2026-11-21 | A version that rises with every change, a mark of contents, and one ModTrap at a time: a new start takes over from one still running | DECIDED | #process #version #server #page |
| 69 | 2026-11-21 | The other tools checked: a change is not a stake (the patcher was asked for a value many plugins share), and a behaviour tool reads lists and patch folders, not animation files | DECIDED | #tools #steps #xedit #process |
| 70 | 2026-11-21 | A Process tab: the demaster as linked boxes with their tasks, coloured as they are carried out, told by the jobs themselves | DECIDED | #page #process #steps |
| 71 | 2026-11-21 | The one go stopped where it should have waited (the modlist was being read after the probe); and the owner's buttons go into the process boxes | DECIDED | #page #process #steps |
| 72 | 2026-11-21 | The demaster went through on 0.3.4; xEdit's "Access violation" box came with ModTrap's early press of OK; the patcher is cleared by stakes; the behaviour tool wants the graph file with the list | FACT | #xedit #tools #steps #process |
| 73 | 2026-11-21 | "Are you 100% sure?" No: the patcher was cleared by comparing bytes it writes in its own form. A patcher is now cleared only where it can be ruled out | DECIDED | #tools #steps #process |
| 74 | 2026-11-22 | What each tool made, from its own files: the patchers behind each output, what was left out, and every tool-made plugin's records by kind | DECIDED | #tools #steps #page |
| 75 | 2026-11-22 | The demaster ran clean on 0.3.7; what is proven on one mod only, and what "any mod" still needs | FACT | #process #method |
| 76 | 2026-11-22 | A second mod: the tool check looked at part of the load order, the Process tab hid what was left to the owner, and a script property is the first new shape | DECIDED | #tools #steps #page #xedit #process |
| 77 | 2026-11-22 | Another modlist's MO2, settings, tabs in sections; and the cell stakes were three unused bytes: every stake a tool holds is now checked against the whole load order | DECIDED | #mo2 #page #tools #steps #process |
| 78 | 2026-11-22 | The generator asked for once more: my own slip in WHY§77's check; the evidence now shows the values; and a leftover could be put right by ModTrap instead of a run | FACT | #tools #steps #process |
| 79 | 2026-11-22 | Where the false alarms came from (ModTrap, not the files), the fix at the source, and how ModTrap would put a leftover right itself | FACT | #tools #xedit #process |
| 80 | 2026-11-22 | The demaster ran clean on 0.3.12; ModTrap retires its own copy once a tool has made the plugin anew; every tool can be started from the Tools tab | DECIDED | #tools #process #page #safety |
| 81 | 2026-11-22 | The tools in a row, and a Revert that always ends where the demaster began: remade plugins and kept tool output come back, and a job in place is never cleared | DECIDED | #safety #tools #process #page |
| 82 | 2026-11-22 | The row of tools could only begin at the moment of putting in place: a button starts it whenever a demaster is in place | DECIDED | #page #tools #process |
| 83 | 2026-11-22 | A Revert after MO2 had run enabled the mods but left their plugins out of the load order: Revert now puts the lines back where they stood, and an earlier such Revert can be finished | FACT | #safety #revert #mo2 |
| 84 | 2026-11-22 | A tool's run ends when the tool has gone: MO2's leftover message is closed; a tool with switches of its own runs and closes by itself; the patcher framework's compiler crash is its own, under MO2 | DECIDED | #tools #mo2 #process |
| 85 | 2026-11-22 | The log panes keep to the latest line until the owner scrolls away, and take it up again at the bottom | DECIDED | #page |
| 86 | 2026-11-22 | The steps foretell nothing: before the dry run they say only that it comes first; a tool-made plugin that names the mod is proof for its tool before the demaster as after | DECIDED | #steps #tools |
| 87 | 2026-11-22 | 0.3.16 on the owner's PC: both Reverts ended clean; ticks go with the demaster they were made for; the panes take their place whenever they come into view; what the patcher framework's profile is, and what is known when it writes nothing | FACT | #revert #page #tools |
| 88 | 2026-11-22 | A tool's own log is read after the run ModTrap started and kept with the session; the patcher framework's failures on the owner's PC were two things, neither ModTrap's | DECIDED | #tools #page #session |
| 89 | 2026-11-22 | Before the patcher framework starts, library versions its own log proves unfit are set to the pair the program was built with; nothing is set without that proof | DECIDED | #tools #safety #settings |
| 90 | 2026-11-22 | The patcher framework's patchers are built outside MO2 before it is started through MO2, when its log shows them unbuilt; what makes that safe | DECIDED | #tools #safety #mo2 |
| 91 | 2026-11-22 | A tool's step is done by ModTrap's own record of the tool's run since the demaster in place, not by a tick; ticks stay only where no record can exist | DECIDED | #steps #tools #page |
| 92 | 2026-11-22 | ModTrap tells its own reading and scanning; while any of it goes, nothing is started: greyed on the page, refused by the server, waited for by the one go | DECIDED | #page #process #safety |
| 93 | 2026-11-22 | 0.3.21 on the owner's PC: versions set, patchers built outside MO2 and taken as built inside; the framework then waited for its run button, which ModTrap now presses, closing it on its log's word | DECIDED | #tools #mo2 #process |
| 94 | 2026-11-22 | The press worked on the owner's PC; the framework's run compiles again and its compiler crashes inside MO2: the compiler goes on MO2's own list of programs it leaves alone, and a tool is started once more for a stated reason | DECIDED | #tools #mo2 #safety |
| 95 | 2026-11-22 | The whole demaster went through on the owner's PC; ModTrap reads the settings files that name the plugin line by line, and gives one account of its checks after the demaster | DECIDED | #steps #process #revert |
| 96 | 2026-11-22 | A Revert made before 0.3.25 left ModTrap's own mod folder behind with a plugin a tool had rewritten: harmless, said on the job, tidied with one press | FACT | #revert #page |
| 97 | 2026-11-22 | Steps say who really does them; what is left to the owner in a settings file is said with file, line and what to do; a third framework read; Revert with MO2 open | DECIDED | #steps #page #tools |
| 98 | 2026-11-22 | A scanner of every settings file in force in the modlist: the winner of each path, read to its end, no time limit; what it could not read is named; the frameworks installed are listed | DECIDED | #steps #tools #page |
| 99 | 2026-11-22 | The scanner walks all of meshes for the folders of animation replacers and reads which condition each mention belongs to; two conditions can hold once the mod is gone and stay the owner's; every look is written to the log with each failure | DECIDED | #steps #tools #log |
| 100 | 2026-11-22 | On the owner's list the scanner is whole in 20 s, then 3 s; the demaster of 0.3.29 went through clean; the Process tab's own Demaster button was not greyed while ModTrap scanned | FACT | #page #steps #process |
| 101 | 2026-11-22 | An update check: sources read from MO2's records and a Wabbajack file; Nexus and GitHub asked as MO2 asks; the owner's key kept under Windows' protection; not yet run against the real services | DECIDED | #updates #network #page |
| 102 | 2026-11-22 | The bar of ticked mods sits at the free end of the row of sections instead of over the page; ModTrap's own mod shows under the modlist's last separator only because it is placed above everything | DECIDED | #page |
| 103 | 2026-11-22 | A menu on a mod by the right mouse button; a source link of the owner's own, kept outside the mod; a drop zone for a Wabbajack file, downloads' meta files and mods' folders; of a Wabbajack file the page sends only the list | DECIDED | #updates #page |
| 104 | 2026-11-22 | The Updates tab is laid out as the modlist: priority, separators, MO2's notes; an Update column whose button opens the newer file's own page for a download through MO2; ModTrap still downloads nothing | DECIDED | #updates #page |
| 105 | 2026-11-22 | The update button fetches the newer file where the host gives one to a program (Nexus for a paying account's key, GitHub), else opens its page; the file goes to Add mods as a newer version: right above the old mod, which is disabled; LoversLab only through the owner's browser | DECIDED | #updates #add #network |
| 106 | 2026-11-22 | ModTrap watches MO2's and the browser's Downloads folders for a file the owner fetched on a site, and a setting lets a newer file be added without asking: one press where the host lets a program fetch, one more on the site where it does not | DECIDED | #updates #add #page |
| 107 | 2026-11-22 | On the owner's list a scan without a key asks nothing and ends at once, which looked like a dead button; the button now says so and leads to the key, with where the key is made | FACT | #updates #page |
| 108 | 2026-11-22 | The owner was right that a scan needs no key: Nexus's newer public service answers without one; the scan is rebuilt on it, the key kept only for fetching and as a fallback | DECIDED | #updates #network |
| 109 | 2026-11-22 | A source without typing: the mark a browser leaves on a downloaded file names its address; and a mod ModTrap adds had no source in its record, so an updated mod could no longer be asked about | DECIDED | #updates #add |
| 110 | 2026-11-22 | A download from Nexus's page was not taken: the public service gave a storage code where a file's name was expected; a download is now known by the browser's mark, or by the mod's number and the upload's time in its name | FACT | #updates #network |
| 111 | 2026-11-22 | A site's page in a small window of its own: a window ModTrap can close stays tied to ModTrap's tab, which the site's page could then send elsewhere; cut loose by default, tied only by the owner's setting | DECIDED | #updates #page #safety |
| 112 | 2026-11-23 | The download was still not taken, and a window was not what the owner asked for: the page handed the file to a mod manager instead of the browser; the watch looked only while ModTrap's tab was asked; a download is now known by its size, and the site's page is a tab again | DECIDED | #updates #page #network |
| 113 | 2026-11-23 | Still a window in the owner's browser, and nothing told of a download in progress: Firefox answers window.open with “noopener” among its features with a window; a folder's listing on Windows gives a file being written no size | LIKELY | #updates #page #windows |
| 114 | 2026-11-23 | The download works on the owner's PC; an update was judged as a new mod, with eight steps of tools and judgements, and the Updates tab still asked for it: an update now has its own few steps, and an older version replaced is shown as such | DECIDED | #updates #add |
| 115 | 2026-11-23 | The add did not go by itself because an entry left on Install mods' list stood in its way; the update is now carried through on the server, in an Updater of its own, with ModTrap's downloads folder and nothing downloaded twice | DECIDED | #updates #add #page |
| 116 | 2026-11-23 | A package for Windows: CPython from NuGet, a launcher of our own built with MinGW-w64, the path set by a ._pth file; built here, and not run here, since Wine does not start in this container | METHOD | #release #windows |
| 117 | 2026-11-23 | The update never began because the owner started the look-only program; the browser can be taken back to ModTrap's tab by ModTrap's program, not by its page; the press at Nexus goes only with a Premium account's key, and is not pressed by a program | DECIDED | #updates #page #release #windows |
| 118 | 2026-11-23 | The whole update works on the owner's PC, the tab return too; the first press took half a minute and a second press began a second update; a new mod's steps named tools that had nothing to do with it: tools are now judged by the kinds of records, and a new mod is installed with one press | DECIDED | #add #updates #page #release |
| 119 | 2026-11-23 | The owner dropped a mod and waited: the install waited for a button further up the page, under a list that read like tasks for the owner; a dropped mod now installs by itself, and ModTrap's own steps are named as ModTrap's | DECIDED | #add #page |
| 120 | 2026-11-23 | Install and placement by hand work on the owner's list; a separator is added through the add job; lists sort by their columns' titles; the launcher is a windowless program that starts ModTrap's console minimised | DECIDED | #add #page #release #windows |
| 121 | 2026-11-23 | The Modlist page changes MO2's lists as MO2 does: one job per change, MO2's own rule for plugins, a disabled mod's plugin keeps its line, a scanner that reads record headers | DECIDED | #page #mo2 #safety |
| 122 | 2026-11-23 | A hidden list forgets its place, so each list's place is noted while it is shown; a file dropped on the list is installed at that place by a run of the page's own, apart from the Installer tool's list | DECIDED | #page #add |
| 123 | 2026-11-23 | ModTrap reads .7z itself; what its reader does not read goes to 7-Zip or to Windows' own unpacker | METHOD | #adding #safety #licence |
| 124 | 2026-11-23 | The Plugins tab changes the load order within MO2's limits and marks rows instead of asking; ModTrap replaces its own files from a release package and starts again | DECIDED | #page #mo2 #release #safety |
| 125 | 2026-11-23 | The split view shows the two sections that exist, side by side, and builds nothing twice | METHOD | #page |
| 126 | 2026-11-23 | A star-number is a place to go to, not a filter; a found row is brought into view once per number; each search box waits on its own | METHOD | #page |
| 127 | 2026-11-23 | Column widths are kept by the kind of table and put on every table as it is drawn; the last shown column takes the rest | METHOD | #page |
| 128 | 2026-11-23 | Every column has its own width and the table is their sum; a mod's web is one box for each mod, read in two passes; a conflict is told by masters, not by what is inside a record; the picture goes through the server | METHOD | #page #model #updates #safety |
| 129 | 2026-11-23 | The console is hidden, not done without; only a console of ModTrap's own is hidden | METHOD | #launcher #safety |
| 130 | 2026-11-23 | An evaluation compares files and reads formats' marks, and says what it cannot tell; a double is told by its page and its file's name, not by its page alone; the list is scanned in one pass from the top | METHOD | #adding #model #page |
| 131 | 2026-11-23 | A closed tab is told by the page's goodbye, not guessed; a worker in the browser and a link of ModTrap's own kind bring it back; the link carries nothing | DECIDED | #page #launcher #safety |
| 132 | 2026-11-23 | An uninstall is a move on the same drive; every list change is a job with its own Revert, shown for good; a mod is renamed as MO2 renames it | METHOD | #page #safety #model |
| 133 | 2026-11-23 | A name is a title and a version from the most trustworthy source that has one; it is asked while the archive unpacks; a side of the web grows the sheet, not the boxes | METHOD | #adding #page #updates |
| 134 | 2026-11-23 | On the owner's list nearly every "same plugin twice" was a patch; a double is a title, and what is said of it depends on whether it is in the game | FACT | #model #page |
| 135 | 2026-11-23 | What fits is reckoned on the sheet before it is drawn, at the smallest size a box can be read at | METHOD | #page |
| 136 | 2026-11-23 | MO2's Conflicts column is a property of the whole list, so the whole list is listed once and kept; a new plugin goes before the tools' outputs whatever it changes | METHOD | #model #page #adding |
| 137 | 2026-11-23 | The page greys what the server already refuses; a re-read keeps the page; a run of the load order is not a separator's group; two saves at once shared one temporary file | METHOD | #page #safety #sessions |
| 138 | 2026-11-23 | A progress symbol is not decoration: it moves even where the PC asks for less motion | FACT | #page |
| 139 | 2026-11-23 | MO2's plugin groups are an extension's file; a group is a run, so a new plugin's group follows from where it stands | FACT | #model #page #safety |
| 140 | 2026-11-23 | A demastered copy inherits its plugin's place among the others; the rule of MT73 looked at who made the plugin, not at what the demaster changed | METHOD | #model #page #safety |
| 141 | 2026-11-23 | Which records two plugins both change predicts no fault, so it is told as none | DECIDED | #model #page |
| 142 | 2026-11-24 | xEdit settles what bytes could not, when asked; a leftover in a tool's plugin is the owner's to leave | DECIDED | #tools #steps #xedit #page |
| 143 | 2026-11-24 | A greyed control must say why where it is pressed; a group is made of picked plugins, and a drop on its line is the one way to join at its edge | METHOD | #page #model |
| 144 | 2026-11-24 | A bulk list is a queue and a run of small jobs, not one big analysis; a drag's aim must follow the list as well as the pointer | METHOD | #page #model #safety |
| 145 | 2026-11-24 | A record of something done is not a claim on its name; where "refresh" ends and a change begins | FACT | #model #page |
| 146 | 2026-11-27 | A plugin the game does not load is a fault as far as something calls it; the scripts say | METHOD | #model #safety |
| 147 | 2026-11-27 | "Not asked yet" beside a link just given reads as a link not understood; a name's version; pre-releases | FACT | #updates #page |
| 148 | 2026-11-27 | Versions are put in order only where both are understood; a page with one file says more than was taken from it | METHOD | #updates |
| 149 | 2026-11-27 | Two installers were one installer with two front ends; what "stops" were; a list that only grew | FACT | #page #add #safety |
| 150 | 2026-11-28 | "Remove" after an update is the uninstall that exists, run on the modlist as the update left it | METHOD | #add #updates #safety |
| 151 | 2026-11-28 | The version in a download's name is not always the file's; the code at its end is the file | FACT | #updates #add |
| 152 | 2026-11-28 | A run that hands its work over must look again; better that it does not hand it over | FACT | #updates #add #page |

## Entries

### 1. Why this log exists, and its form

`2026-11-20` · METHOD · `#process` · refs: MT3

- METHOD: the form is that of the owner's other projects (EldenNet's log): an index, numbered entries, labels,
  tags, append-only. Facts read in MO2's and xEdit's sources live in the research notes (MO01, XE01) with their
  file and line; this log holds what follows from them.
- METHOD: before the first push the log was briefly a flat list (R1 to R33). Nothing had left the session, so it
  was recast in this form once; from here on it is append-only.

### 2. The manual procedure that defines "demaster"

`2026-11-20` · FACT (screenshots of a modlist community's guide, supplied by the owner) · `#procedure` · refs: MT1, MT6

- FACT: for each plugin that depends on the unwanted mod, the guide has the user keep the unwanted mod enabled, load
  the dependant in xEdit through MO2, run xEdit's "Report masters" script on it for the unwanted plugin, and for
  each record or element listed either remove the whole record from the dependant or remove just the element that
  refers to the unwanted plugin (its example removes one entry of a FormID list); then Clean Masters; then the
  report again until it is empty; then save.
- FACT: the guide does not demaster every dependant. Patches that exist only for the unwanted mod are disabled;
  only plugins that do other things too are demastered.
- DECIDED: this is ModTrap's meaning of the word (MT1). The second point is MT6.
- The guide is described here in our own words. Nothing of it, and no name from it, is copied into the repository.

### 3. xEdit can do the procedure unattended, from our own script

`2026-11-20` · FACT (xEdit 4.1.5f's source) · `#xedit` · refs: XE01§2, XE01§3, XE01§4, XE01§7, XE01§8, DESIGN§7

- FACT: one command line starts xEdit with a script of ours, a plugins file of ours, no selection window, and an
  exit when the script ends (XE01§2 to XE01§4).
- FACT: every step of WHY§2 has a scripting function: the report, removing a record or an entry, Clean Masters
  (XE01§7). xEdit's own report script is a short loop over one of them (XE01§8).
- LIKELY: handing xEdit a short plugins file loads only the dependants and their masters, not a whole load order of
  a thousand plugins (XE01§3). This is what makes a run take minutes, not most of an hour.
- FACT of a kind: xEdit's window will show (XE01§4). "Watch it do its work" is the page's terminal plus xEdit's
  own window.

### 4. Write the changed plugin elsewhere and keep xEdit from saving the original

`2026-11-20` · LIKELY · `#xedit #vfs #safety` · refs: XE01§5, XE01§7, XE01§9, WHY§8, MT5, DESIGN§6.3

- FACT: in script mode xEdit saves every changed plugin on close, without asking (XE01§5).
- FACT: a script can write a loaded plugin to a stream of its own, and can clear a file's "unsaved" state (XE01§7).
- LIKELY: so the script can change a dependant in memory, write the result into ModTrap's output mod, and clear
  the state so that the original is never saved over. Not proven (XE01§9).
- Fallback if it fails: copy the dependants into the output mod first, enabled above the originals, and let xEdit
  save those copies in place (DESIGN§6.3). Either way no original is changed, and ModTrap hashes them before and
  after to be sure.

### 5. Progress for the page comes from a file the script writes

`2026-11-20` · LIKELY · `#xedit #page` · refs: XE01§6, XE01§7, DESIGN§4

- FACT: xEdit writes its log only on close, and it is a window program with nothing to read from its output
  (XE01§6).
- LIKELY: the script can append a line to a text file after each step, and ModTrap can follow that file. Not
  proven: whether the script host can append without rewriting the file each time; rewriting a small file would
  also do.

### 6. What cannot be proven here is proven by a probe on invented plugins

`2026-11-20` · METHOD · `#xedit #mo2 #safety` · refs: WHY§4, WHY§5, WHY§7, WHY§8, XE01§9, MO01§6, DESIGN§9

- METHOD: xEdit and MO2 are Windows programs, and nothing cloned is built or run in a session. So the open points
  are settled on the owner's PC, by ModTrap itself, before any real mod is touched: it writes three tiny invented
  plugins into a test mod of its own and runs the whole job on them.
- METHOD: the page allows a real job only after the probe passes, and says which point failed if it does not.

### 7. MO2 starts a tool from the command line, open or closed

`2026-11-20` · FACT (MO2's source) · `#mo2` · refs: MO01§3, MO01§4, DESIGN§7

- FACT: `run -e` starts a configured executable in the virtual file system with arguments of ours, and an open MO2
  takes the command over (MO01§3, MO01§4). The owner need not close MO2.
- LIKELY: with MO2 open, the command returns at once, so ModTrap watches for xEdit's own end (the script's last
  line, and the process), with a time limit and a Stop button.
- FACT: ModTrap never starts a second MO2 on the instance (MO01§4).

### 8. A save through MO2 lands in the original mod's folder

`2026-11-20` · LIKELY · `#vfs #safety` · refs: MO01§5, WHY§4, MT5

- LIKELY: this is why the guide's procedure alters the original plugins, and the reason for WHY§4.
- The session that started ModTrap expects the same, and adds: check the per-executable setting in MO2 that sends
  newly created files to a chosen mod. Both go to the probe (WHY§6).

### 9. What ModTrap takes from DataPiler

`2026-11-20` · FACT (DataPiler at its branch `feat/v0.2.41`, commit `75cea6f`) · `#datapiler #server #page` · refs: MT3, DESIGN§2, DESIGN§8

- FACT: the page server, whole: 127.0.0.1 only, Host and Origin checks, a per-start token on every API call, a
  strict content policy with nonces, size caps, refusals logged by reason only (`datapiler/server.py`).
- FACT: a job's lines reach the page by polling "lines after N" from a numbered ring, no SSE or WebSocket
  (`logbook.py`, `api.py`, `events.py`). It works under the strict policy and survives a reload.
- FACT: watching an outside program by its executable from a thread that fails closed (`smithbox.py`,
  `gamewatch.py`); one Windows adapter module, faked in tests (`winapi.py`); jobs as a closed set of operations
  with a schema version (`jobs.py`); atomic writes and bounded reads (`fileio.py`).
- FACT: DataPiler never starts an outside program from Python, so starting xEdit is new code: an argument list,
  never a shell, a time limit, Stop, the exit code read.
- METHOD: lessons carried over: logs mask the owner's paths so that a log can be shared; the first log lines state
  versions and environment; ask before Stop; every folder check says what it found in plain words.
- Not this: DataPiler's `guard.py` checks what may leave the PC. ModTrap's guard is about where a job may write
  (DESIGN§8).

### 10. Rejected: editing plugins with our own code

`2026-11-20` · METHOD · `#safety #xedit` · refs: DESIGN§3

- ModTrap could parse and rewrite plugins itself and never start xEdit. Rejected: the owner asked for xEdit inside
  MO2; xEdit's knowledge of every record type is years of work; and a wrong rewrite of someone's plugin is the
  worst failure this tool could have.
- METHOD: our own code reads only a plugin's header (its masters and flags), to build the lists and to check the
  result.

### 11. Rejected: driving xEdit's window, and a script generated per job

`2026-11-20` · METHOD · `#xedit` · refs: WHY§3, XE01§2, DESIGN§2

- Sending clicks and keys to xEdit to do the guide's steps: fragile, and unnecessary given WHY§3.
- Writing a new script for each job: rejected. The script is one fixed file of ours; a job reaches it as a small
  data file beside it (XE01§2). Jobs stay data, never code.

### 12. The session link is left out of commits

`2026-11-20` · FACT (DataPiler's `CLAUDE.md` at `75cea6f`) · `#process` · refs: MT12

- FACT: the owner's rule of 2026-11-16 for their other projects: no `Claude-Session` link in commit messages or
  pull requests, because it points to a private transcript and tells a reader nothing; the `Co-Authored-By` line
  stays. ModTrap follows it.

### 13. The owner's reference system adopted

`2026-11-20` · METHOD · `#process` · refs: MT3

- METHOD: `tools/workplan` (`wp`) is taken from the owner's EldenNet (MIT), with ModTrap's documents and codes:
  `DESIGN§n`, `WHY§n`, `MT1` onwards, `MO01` and `XE01` for the research notes, `RES` for their index. Documents
  are read by section, never whole. The index it builds is generated and not committed.
- Not taken yet: the roadmap with stage and step ids. Design 0001's build order (DESIGN§10) is short enough; a
  roadmap comes when there is more work to plan than that.

### 14. The owner's xEdit is 4.1.5f, in a tools folder inside the modlist folder

`2026-11-20` · FACT (the owner's screenshots of the folder and of the program file's details) · `#xedit #tools` · refs: MT8, XE01§1, XE01§6, DESIGN§13

- FACT: the modlist folder has a `tools` folder holding xEdit and the list's other tools (LOD generators, an INI
  editor, a patcher, mesh and texture tools). xEdit's folder holds a 32-bit and a 64-bit program, and its own
  `Edit Scripts` folder.
- FACT: the program file's details give version 4.1.5.0 and a date of 2024-04-27, the date of tag `xedit-4.1.5f`
  (XE01§1). The letter is not in the version details: the version and the date together identify the release.
- FACT: a script-mode log already sits in that folder, so script mode has run on this setup before (XE01§6).
- The research of XE01 was done at exactly this release.

### 15. Compatibility is decided by the probe, not by a list of versions

`2026-11-20` · METHOD · `#xedit #tools` · refs: MT8, WHY§6, WHY§14, DESIGN§9, DESIGN§13

- The owner asked that ModTrap detect the version and work with the popular ones. A list of approved versions
  would always lag, and the letter cannot be read from the file (WHY§14).
- METHOD: ModTrap detects and shows the version, refuses only what is known not to work (versions before the
  switches of XE01§2 to XE01§4 existed; to be researched per release), and lets the probe on invented plugins decide
  for everything else. A version that passes the probe is one ModTrap works with, and the history records it.
- Next step: read xEdit's release notes for when `-script`, `-autoload`, `-autoexit` and `-P:` arrived, and check
  the newest release's scripting functions against XE01§7.

### 16. Auto disable means writing modlist.txt, and only with MO2 closed

`2026-11-20` · METHOD · `#mo2 #safety` · refs: MT9, MO01§2, MO01§6, DESIGN§6.5, DESIGN§7, DESIGN§12

- FACT: the file's form is simple and known (MO01§2): disabling a mod is changing its line's `+` to `-`; its place
  in the file, and so its priority, does not change.
- FACT: an open MO2 writes the file from memory (MO01§2), so ModTrap writes it only while MO2 is closed, and asks
  the owner to close it for that step.
- LIKELY: ModTrap need not write the plugin files to disable a mod; MO2 drops the plugins itself (MO01§2). Putting
  plugins back at their old positions on Re-enable does need them, which is why the history keeps each plugin's
  position and why MO01§6's research comes before that feature.
- Rejected: asking MO2 to do it. Its command line has no command to enable or disable a mod (MO01§3).

### 17. The safe folder is taken after the dry run, and Revert checks before it writes

`2026-11-20` · METHOD · `#safety` · refs: MT14, DESIGN§6.2, DESIGN§11

- The owner's point: only after the dry run is it known exactly which files a job touches, so that is when the
  copies are taken, automatically, with no way to skip it.
- METHOD: the safe folder also holds the profile's three files, since Auto changes one of them and MO2 rewrites the
  others.
- METHOD: Revert compares each file with what ModTrap left there before overwriting it. If the owner or another
  tool changed it since, a blind copy-back would lose that work, so ModTrap shows it and asks.

### 18. Replace the originals, or a ModTrap mod above them

`2026-11-20` · METHOD · `#vfs #safety` · refs: MT5, WHY§4, WHY§8, DESIGN§6.5

- The owner proposed: work on copies, verify, then put them into the modlist in place of the originals, and verify
  again. The first, second and last steps are in the design either way (DESIGN§6.3 to DESIGN§6.5).
- For the third step there are two ways with the same result in the game. Replacing: the modlist's folders stay as
  they were in number and order, but files of a list installed by an installer now differ from what it installed,
  so an update or repair of the list may flag or restore them. A ModTrap mod above the originals: one more mod in
  the list, originals untouched, Revert is one disabled mod; with Auto (MT9) it costs the owner no extra step.
- Recommended: the ModTrap mod. The owner decides (MT5).

### 19. "Nothing gets removed" was about the mod, not about records

`2026-11-20` · METHOD · `#procedure #process` · refs: MT4, MT9, WHY§2

- The owner's answer to MT4 was that the mod is disabled and stays in place. That is now MT9's rule: ModTrap never
  deletes a mod or a plugin.
- MT4 asks something else: demastering a dependant means taking out of that dependant the records and entries
  that point at the unwanted mod, as the guide does by hand (WHY§2). Without that, Clean Masters cannot drop the
  master. The question was worded badly ("what gets removed") and is put again in plain words.

### 20. The method is ModTrap's to choose: what was chosen for MT4 and MT5

`2026-11-20` · DECIDED · `#procedure #safety` · refs: MT17, MT4, MT5, WHY§18, DESIGN§5, DESIGN§6.5

- DECIDED: the owner named the result that counts and left the method to ModTrap (MT17).
- MT4: cases A and B automatic, C and D reported as steps for the owner. A forced edit that leaves a record
  pointing nowhere is exactly the kind of in-game issue MT17 rules out; a reported one costs a manual step.
- MT5: a ModTrap mod above the originals (WHY§18), since ModTrap places it itself under Auto and an installed
  list's own files stay verifiable.

### 21. What "clean" can and cannot be checked by a tool

`2026-11-20` · METHOD · `#safety #procedure` · refs: MT17, DESIGN§3, DESIGN§6.5, DESIGN§14

- METHOD: checkable from files: no active plugin lists a missing or inactive master; no demastered plugin still
  needs a trapped plugin (xEdit's own report, run again); every generated patch that listed a trapped plugin has
  been rebuilt without it; the load order is otherwise unchanged; nothing was changed outside the plan.
- Not checkable from files: that a script, a mesh or a setting of another mod quietly relied on the trapped mod's
  loose files, or that the game plays well. ModTrap says so, lists the kinds of loose files the trapped mod
  contained (DESIGN§13), and leaves "play, and report anything odd" as the owner's last step.
- SPECULATION: a later version could list which loose files of the trapped mod were winning file conflicts, the
  nearest thing to "who else relied on it" that the instance's files can show.

### 22. Telling which tool made a patch: evidence, and marks kept as data

`2026-11-20` · METHOD · `#tools #mo2` · refs: MT18, MO01§2, XE02§4, DESIGN§13

- FACT: MO2 records, per executable, the mod that receives the files the program creates (MO01§2). A plugin found
  in that mod is tied to that tool by MO2's own settings: the strongest evidence, and it needs no knowledge of the
  tool.
- LIKELY: patching tools mark their output in the plugin header's author or description, and use well-known file
  names. From general knowledge of these tools, not yet read in their documentation.
- METHOD: so the marks and names go in a shipped data file, one entry a tool, each with its source and a label,
  and the page shows which evidence led to each "made by". Next step: read each tool's own documentation
  (Synthesis, Wrye Bash, the LOD generators) before an entry is trusted.
- Rejected: reading a tool's own settings files to learn its output. Each tool's format differs and changes; MO2's
  setting and the plugin's header cover it.

### 23. MO2's plugin lists and the plugin header are read from their sources

`2026-11-20` · FACT · `#mo2 #xedit` · refs: MO01§2, XE02§2, XE02§3, XE02§4, DESIGN§3

- FACT: the forms of `plugins.txt` and `loadorder.txt` are now read in MO2's game plugins (MO01§2): different
  text encodings, the newer file gives the order, the game's primary plugins are not listed.
- FACT: the plugin header's flags and fields are read in xEdit's definitions (XE02). ModTrap's reader is written
  from that description and stops at the end of the header.
- METHOD: the reader and the instance model are built first (version 0.1), with invented plugins written by the
  test code, since everything else stands on them.

### 24. Version 0.1's reader exists, and what it has not yet met

`2026-11-20` · METHOD · `#mo2 #process` · refs: DESIGN§3, DESIGN§10, MO01§2, XE02§5, MT17

- METHOD: `modtrap/plugin.py` reads a plugin's header and nothing more; `modtrap/instance.py` reads the instance's
  ini and the profile's three lists; `modtrap/model.py` works out who provides each plugin, its masters, its
  dependants, and the health check. `python -m modtrap scan FOLDER` prints the result and writes nothing.
- METHOD: tested on an invented instance written by the test code. Not yet met: a real instance. The ini's
  escaping rules are written from how such files look, not read in Qt's source (LIKELY), so the first scan of the
  owner's modlist is the real test, and its summary (counts, notes, health) is what to compare with MO2's own view.
- Left out on purpose until needed: plugins inside a mod's subfolders (MO2 ignores them), the VR and LE games
  (MT7), and anything that writes.

### 25. The first scan of the owner's modlist agrees with MO2

`2026-11-20` · FACT (the scan's output and a screenshot of MO2 2.5.2, both from the owner) · `#mo2 #process` · refs: WHY§24, MO01§2, XE02, DESIGN§3

- FACT: on the owner's list (about 3,600 mods, 135 separators, 3,751 plugins, all active) the scan read every
  plugin's header with none unreadable, and the health check was clean, as MO2 shows it.
- FACT: for the mod the owner picked, the scan's priority and its plugin's load-order position are the numbers
  MO2 shows for them. The ini's escaping (LIKELY in WHY§24), the modlist order and the plugin lists therefore
  hold on a real instance of this size.
- FACT: the scan found 17 dependants in 9 mods. Every plugin the community guide names for this mod is among
  them, under the names this version of the list gives them, and two more that the guide does not name. The guide
  is older than the list; reading the masters is not.
- Open: one plugin that sits among the mod's patches in MO2's list, and by its name should depend on it, is not
  among the 17. Either it does not list the mod as a master or the reader missed it; the owner is asked to run
  `scan --plugin` on it.
- FACT: the executable to start is titled as the 64-bit xEdit in this MO2, one of 24 configured.
- **Later (2026-11-20):** the open point is closed. `scan --plugin` shows that plugin's masters are two of the
  game's own and one Creation Club plugin: it does not list the trapped mod, and the reader was right (WHY§28).

### 26. A patch is often one plugin in a collection: disable the plugin, not the mod

`2026-11-20` · METHOD · `#procedure #mo2` · refs: MT6, MT9, MT17, WHY§25, MO01§2, DESIGN§5, DESIGN§6.5

- FACT: on the real list, five of the nine mods holding dependants are patch collections: each has one or two
  plugins for the trapped mod among many for other mods. The guide's "disable plugins" list is exactly these.
  Disabling such a mod would switch off patches the list still needs.
- METHOD: so the treatments are per plugin, and there are two ways to switch a patch off: **disable the mod** when
  every plugin it provides depends on the trapped mod, **deactivate the plugin** when it is one among others.
  `model.groups` gives this first reading from the headers alone ("whole mod", "some plugins", "output").
- METHOD: deactivating a plugin means writing `plugins.txt` (removing its star), in MO2's form and encoding, with
  MO2 closed and the file in the safe folder first. MO2 takes the order from the newer of its two list files
  (MO01§2), and a rewritten `plugins.txt` is the newer one, so ModTrap must write every line in the same order and
  check, after MO2's next start, that the order is unchanged. This goes to the probe.
- Design 0001's "patch-only mod" becomes "patch-only plugin or mod" (DESIGN§5).

### 27. The real list shows generated outputs and loose files, as the design assumed

`2026-11-20` · FACT (the same scan and screenshot) · `#tools #procedure` · refs: MT18, WHY§22, DESIGN§13, DESIGN§14

- FACT: two of the 17 dependants live in mods named as tools' outputs, one of them the output of a tool whose
  work is textures and meshes, which nonetheless writes a plugin. Whether MO2's per-executable output setting
  (MO01§2) names those mods on this list is not yet known: the scan now reads it and says so.
- FACT: the trapped mod holds, beside its plugin and an archive, loose animation and behaviour files and settings
  files for a script-extender plugin. The guide's step to re-run the animation tool matches the first; nothing in
  any plugin's masters would have shown it. This is DESIGN§13's "what masters cannot show", met in practice.
- FACT: the guide also disables a mod that holds no plugin, a hotfix for the trapped mod. No master points to
  it. LIKELY: a mod whose files do nothing but replace the trapped mod's files can be found by comparing file
  names between the two folders; that is the file-conflict idea of WHY§21, now with a concrete case.

### 28. The second scan: a patch with no master, MO2's output setting, and its limits

`2026-11-20` · FACT (the scan's output, from the owner) · `#tools #mo2 #procedure` · refs: WHY§25, WHY§26, WHY§22, MO01§2, DESIGN§5, DESIGN§13

- FACT: a patch hub for the trapped mod holds eight plugins; seven list the trapped mod as a master and one does
  not, though it is a patch for it by its name and its place. The guide disables that mod whole. Masters alone
  would leave the eighth plugin active.
- METHOD: a new reading, "most of the mod": more of a mod's plugins depend on the trapped mod than not, and nothing
  outside the mod needs the rest. ModTrap then proposes disabling the mod whole and names the leftover plugins, for
  the owner to judge. A patch collection (one plugin in 167) never reads this way.
- FACT: MO2's per-executable output setting works as evidence (WHY§22): the scan tied one output mod to the four
  xEdit entries of this MO2, from the profile's settings alone.
- FACT: it is not enough by itself. Another tool's output mod on the same list carries no such setting (that tool
  chooses its own output folder), so the scan read it as an ordinary mod. Names and header marks, kept as data
  (DESIGN§13), are needed beside it.
- METHOD: "made by xEdit" does not mean "run the tool again": xEdit is an editor, and what it wrote there came
  from a script or from hand edits that ModTrap cannot repeat. For an editor's output the proposed treatment is
  demaster; "run the tool again" is for patchers and generators. The tool data file needs a field for this.
- FACT: xEdit's new files go to that output mod on this list. ModTrap's script writes its results to a folder
  outside the instance (DESIGN§6.3), so they do not land there; in the fallback route they would, and so would
  xEdit's own backups unless `-B:` points elsewhere (XE01§5).
- FACT: the dependants' master lists run from 4 to 200 plugins; the largest are the list's merged and generated
  patches. Loading "the dependants and their masters" (XE01§3) is still far less than the whole load order for the
  small patches, but close to all of it for the largest; the dry run's time will be set by those.

### 29. Version 0.1's page: what was built, how it was tested, what was not

`2026-11-20` · METHOD · `#server #page #process` · refs: DESIGN§2, DESIGN§4, DESIGN§10, WHY§9, MT11

- METHOD: `python -m modtrap` (or `ModTrap.cmd`) starts the server on 127.0.0.1 and opens the page. The server is
  DataPiler's, taken whole (NOTICE); the log is a small one of our own on DataPiler's pattern; the API reads only.
  The chosen folder is kept in ModTrap's own folder under the user's local application data, never in the instance.
- METHOD: an instance is read on a thread of its own, and plugin headers are cached by path, size and time, so a
  rescan re-reads only what changed.
- FACT: tested here with the standard library's test runner (server guards, API, masking, nothing written to the
  instance) and in a real browser against two invented instances, one the size of the owner's (about 3,600 mods and
  3,900 plugins): read and modelled in well under a second, first rows on the page in under a second, filtering
  instant, no errors in the browser's console under the strict content policy.
- Not tested: on Windows at all, the `.cmd` starter included; the page against the owner's real modlist. Timings on
  the owner's PC will be set by the disk (3,751 plugin files opened), not by this code.
- Not built yet from DESIGN§4: the tools' versions in the instance bar (DESIGN§13), the Steps and History tabs, a
  folder picker (the folder is typed or pasted), and the built launcher and updater (MT11).

### 30. A dropped folder has no path: ModTrap finds it from its ModOrganizer.ini

`2026-11-20` · METHOD · `#page #mo2 #safety` · refs: MT19, WHY§29, MO01§2, DESIGN§4

- FACT (the owner's report): the first page's Open button "did nothing". With an empty box the server's refusal
  was shown and at once painted over by the next refresh, and the grey example path in the box read as a real
  value. Fixed: an empty box is answered on the page, a refusal stays until a modlist is being read, and the box's
  hint no longer looks like a path. The form had only ever been tested through the start-up option, never through
  the button: the browser test now presses it.
- FACT: a browser gives a page a dropped folder's name and lets it read files inside, but never its path. So the
  page reads one file from the dropped folder, `ModOrganizer.ini`, and sends its bytes and the folder's name; it
  never walks the folder.
- METHOD: the server finds the folder (`modtrap/locate.py`): folders opened before; then every ancestor of every
  absolute path in that ini (MO2's executables and the game usually sit inside the instance, MO01§2); then a
  bounded search for a folder of that name. A candidate is accepted when its own ini has the same sha256.
- From the session that started ModTrap, whose DataPiler has a folder picker and detection but never met a
  dropped folder: handle the drag for the whole page, or a near miss makes the browser open the dropped thing;
  never log, store or echo the ini (it holds the owner's paths); the search only on fixed drives, never through a
  link or junction, never opening a cloud drive's placeholder; and MO2 rewrites its ini, so fall back from the
  byte match to identity (the one folder of that name that is an instance of the same game). All taken.
- Not taken, and why: asking "Use this folder?" before registering it. ModTrap at this stage only reads, the owner
  asked that the drop register the path, and the page shows at once what was found. A confirmation belongs before
  the first job that writes, where the plan already is (DESIGN§6.1).
- Next, from the same advice: detection (a running MO2's folder; MO2's own records of its instances), and
  DataPiler's in-page folder picker as a Browse button. A native folder dialog was ruled out there: it opens
  behind the browser.
- Tested here in a browser with a simulated drop (a real drag from Explorer cannot be driven from a test), and on
  Linux only. The drive search and the Windows file attributes are untested until the owner's PC.

### 31. The dry run is built; what its first run on the owner's PC has to show

`2026-11-20` · METHOD · `#xedit #mo2 #safety #process` · refs: DESIGN§6.1, DESIGN§6.2, DESIGN§9, WHY§3, WHY§5, WHY§6, WHY§7, XE01§3, XE01§7, MO01§3, MT4

- FACT (the owner): the page and the drop box work on the real modlist. The owner asked for the dry run.
- METHOD: the dry run on real plugins comes before the probe on invented ones, because report mode only reads:
  `modtrap/xedit/ModTrap.pas` changes nothing in memory, so xEdit has nothing to save. The probe (DESIGN§9) is for
  the mode that writes. All the same, before xEdit starts ModTrap copies and hashes every dependant in the job's
  folder, and afterwards checks each is still that file; and the script clears any "unsaved" mark xEdit holds on a
  plugin it did not change, and reports it.
- METHOD: the script asks, per record, which plugins it needs (one call, XE01§7), and only for a record that needs
  a trapped plugin goes down to the lowest elements. For each it reports whether the record is the trapped
  plugin's own, and for an element whether it sits in an array (and which, and how long) or is a single field. It
  judges nothing: which arrays are safe to shorten is ModTrap's list (`dryrun.SAFE_ARRAYS`), not the script's.
- METHOD: xEdit is given a plugin list of the dependants and every master under them, and is told not to build
  references, which the report does not need. On the owner's list the largest dependants have up to 200 masters,
  so several hundred plugins load.
- METHOD: the page follows a progress file the script rewrites after each step, and takes the end from the
  report's last line. If xEdit closes without one, ModTrap prints the tail of xEdit's own log from the job's
  folder into the terminal, masked: the script cannot be run here, so that tail is how a script error will be read.
- Tested here: everything around xEdit, with a stand-in that reads the same job file and writes the same report
  (the plan, the job's files, the command, following progress, the checks, a closed xEdit, a changed dependant,
  the page in a browser).
- Not tested, and what the first run shows, in the order it would fail:
  1. LIKELY: MO2 accepts the command as built, with quoted paths inside `-a`, open or closed (MO01§3, WHY§7).
  2. LIKELY: xEdit takes `-P:` and loads exactly those plugins and their masters (XE01§3).
  3. LIKELY: the script compiles and runs in xEdit's script host. It is written only with functions and idioms
     found in xEdit's own scripts, but has never run.
  4. LIKELY: a script can rewrite a text file while it works (WHY§5).
  5. LIKELY: xEdit's names for arrays match `SAFE_ARRAYS` ("FormIDs", "Leveled List Entries", "KWDA - Keywords").
     The first real report shows the names; until then an entry of an unknown array reads "needs you", which is the
     safe side.
  6. How long it takes, and whether xEdit closes by itself at the end.

### 32. A friendlier page: what was changed and why

`2026-11-20` · METHOD · `#page` · refs: DESIGN§4, WHY§29, WHY§30, MT2

- The owner, away from the PC with the dry run still to try, asked for the page to be made friendlier meanwhile.
- FACT (the owner's screenshot of the real list): with the highest priority first, each separator sat above
  mods that belong to the separator before it, so the groups read wrongly; and ticking meant hitting a small box
  in a list of 3,580 rows, most of which cannot be ticked.
- METHOD: the mods are now shown as MO2 shows them, lowest priority first, each separator heading its own mods,
  with groups that fold (one, or all), a choice of order (as in MO2, reversed, most dependants first), a click
  anywhere on a row to tick it, and a "nothing matches" line with a way back.
- METHOD: a first-time visitor is told what to do: a welcome screen with the three steps, a large drop area, and
  the modlists opened before; a step guide in the header that follows the owner's progress (the fourth step,
  the demaster itself, is shown as not yet built); and a bar at the foot of the page as soon as a mod is ticked,
  leading to what depends on it.
- METHOD: things are linked: a plugin's name anywhere opens it on the Plugins tab, a mod's name shows it on the
  Mods tab, the health and tools chips open their tabs. The tools set up in MO2 have a tab of their own, with the
  one ModTrap starts as xEdit marked and each tool's output mod.
- METHOD: the dry run's result opens with a count by outcome, and its lines and the whole log have a copy button;
  the log is already masked, so what is copied can be pasted when asking for help.
- METHOD: keyboard and assistive use: `/` goes to the search box, Escape clears it, folding and links are real
  buttons, counts and states have text beside their colour, movement stops under "reduce motion".
- FACT: checked in a browser on the invented lists, the large one included (folding 134 groups, re-ordering and
  searching 3,467 mods each take a fraction of a second; no error in the console). The list of mods is now worked
  out once for each reading, not at every request. A test checks that every element the script asks for is on the
  page, and that the page loads nothing from outside and has nothing inline.
- Not done: a folder picker with a Browse button and detection of a running MO2 (WHY§30); a light theme.

### 33. Sessions and Quit: how the state is kept, and what "safe to finish" means for now

`2026-11-20` · METHOD · `#page #safety #process` · refs: MT20, DESIGN§15, DESIGN§11, DESIGN§14, WHY§32

- METHOD: a session is a folder under ModTrap's own work folder with a `session.json` (name, modlist, profile,
  status, what the page looked like), its log, and its jobs. The page sends what it looks like half a second after
  each change; the server writes it at once and atomically. So closing the console window loses at most that half
  second, and Quit loses nothing.
- METHOD: "the exact same state" is built from two halves. What ModTrap decides (the session, its last job and
  result, its log) is read back from the session's folder. What comes from the modlist (the mods, plugins,
  masters) is read again from the modlist itself at start, never from a copy: a copy could be stale, and every
  later step must stand on what is on disk now. Plugin headers are cached by path, size and time, so a start reads
  only plugins that changed.
- METHOD: the lock is by modlist folder, not by profile: profiles of one MO2 share the mod folders that a
  demaster's output goes to, so two sessions on two profiles of one modlist could still trip over each other.
- METHOD: "verified finished and safe" is today one check (nothing of the session is still going), because
  nothing ModTrap does yet changes a modlist. The place for the real check exists (`Api.session_finish`); the
  steps of a demaster and the health check plug into it when they are built (DESIGN§14, DESIGN§15).
- FACT: a page can close its own tab only if a script opened it; ModTrap's tab is opened by the operating system's
  browser launch, so `window.close()` is refused. The page therefore says "ModTrap has closed, you can close this
  tab", and tries to close itself all the same.
- FACT: tested here: the store and the lock; through the API a quit and a fresh start that give back the same
  session, page state, dry-run result and log without reading a single plugin again; and in a browser, where the
  page's state before Quit and after the restart compared equal, and a second session on the same modlist was
  locked until the first was finished. Not tested on Windows.
- Not built: deleting a session (it will hold safe folders, so deleting needs the same care as Revert), and what a
  demaster cut short by Quit should do.

### 34. The script checked against the script engine's source, without running it

`2026-11-20` · METHOD · `#xedit #process` · refs: WHY§31, XE01§7, XE01§9, MT4

- METHOD: xEdit's scripts run in JVCL's interpreter, whose source is not in xEdit's repository. It was read at
  `github.com/project-jedi/jvcl`, commit `b045b99` (2026-05-29; MPL 1.1 by its file headers; only
  `jvcl/run/JvInterpreter*.pas`, read only), together with xEdit's own adapter units at the 4.1.5f tag.
- FACT: every keyword and form the script uses is in the interpreter's parser: `unit`, `while`, `mod`, `try` with
  `except on E: Exception`, a bare `raise` to pass an error on, `exit`, character constants such as `#9`
  (`JvInterpreterParser.pas:104-150`, `:336-381`, `:740-748`; `JvInterpreter.pas:7640-7648`).
- FACT (a real find): the interpreter looks names up without regard to case, across everything registered. Four
  of the script's own variable names were names xEdit registers: `formId` (xEdit's `FormID` function), `tFile` and
  `tForm` (the classes `TFile` and `TForm`) and `fileName`. They are renamed. Every name the script declares was
  then compared by a small program with all 3,741 names the two sources register; what is left in common are the
  entry point `Initialize` and the one-letter names xEdit's own scripts use.
- FACT: xEdit catches an error a script lets through and writes it with its place in the script
  (`xEdit/xeMainForm.pas:8469-8474`). So the script now records its failure and passes the error on: xEdit's log
  names the line, and ModTrap prints that log's tail (WHY§31).
- METHOD: the script no longer decides what an element is. For each element that points at a trapped plugin it
  writes the chain of elements up to the record: each one's name, kind of element, kind of value, size and place.
  ModTrap's own code reads the chain (`dryrun.read_chain`): an entry of a list is an element whose parent is a list
  by either kind. A keyword list is a list by its value, not by its element kind, which the first version of the
  script would have missed. A wrong reading can now be put right in ModTrap without the owner running xEdit again
  on a new script.
- METHOD: the job file is written as UTF-8 with a byte-order mark, which the script's string list honours, so a
  folder name with letters outside the PC's own text encoding still arrives whole. The script's own files come back
  in the PC's encoding; ModTrap reads them as UTF-8 if valid, else as that.
- Still unproven, as WHY§31 lists: only a run can show the rest.

### 35. The Steps tab: a checklist the modlist's own files tick off

`2026-11-20` · METHOD · `#page #procedure #tools` · refs: MT18, MT17, DESIGN§14, DESIGN§13, WHY§21, WHY§27, WHY§28

- METHOD: until ModTrap can change a modlist, the steps of a demaster are a checklist for doing it by hand, made
  for whichever mods are ticked: the dry run; the patches to switch off; the plugins to demaster; the tool outputs
  to rebuild; the mods to disable; the tools to run again; the settings files to look at; the health check; play.
  It replaces a guide written for one mod with one worked out from the modlist.
- METHOD: a step is "done" when the modlist's files show it, at every reading: a plugin no longer lists the mod as
  a master, a plugin is inactive, a mod is disabled, the health check is clean. Only what no file can show (a tool
  was run again, a settings file was looked at, the game plays) is ticked off by the owner, and kept in the session.
- METHOD: three things no master list shows are now found (WHY§27). What the ticked mod carries besides plugins,
  by file name: animations and behaviours lead to the behaviour tool set up in MO2, LOD files to the LOD tools.
  Mods that only replace the ticked mod's files (a hotfix): a mod at least four fifths made of files the ticked mod
  also has. And small settings files of other mods that name a ticked plugin: lines for something that works while
  the game runs. The last reads the content of other mods' settings files, and nothing else of them.
- LIKELY: the file-name patterns for each kind (`steps.KINDS`) are from general knowledge of how Skyrim mods lay
  out their files, not from a source; the page says "for example" and shows the files it went by.
- FACT: a mod that also provides a ticked plugin (a second copy of it, higher or lower in priority) is listed with
  the mods to disable: the plugin stays in the game while any of them is enabled.
- Limits: files inside a mod's archive are not seen (the archive's table is not read); the search of settings files
  stops after a time and a count, and says so; the caution about saves and compiled scripts is general modding
  knowledge, worded as such.

### 36. Groundwork for the demaster, built ahead and switched off

`2026-11-20` · METHOD · `#safety #mo2 #process` · refs: MT9, MT14, MT15, WHY§16, WHY§26, WHY§6, DESIGN§8, DESIGN§9, DESIGN§11, DESIGN§12, MO01§2, XE02

- METHOD: four parts of the demaster step can be written and tested without xEdit, so they were, while the dry run
  waits for its first real run. None is called by anything the page can reach; a test checks that the module
  behind the page imports none of them.
- `modtrap/profile.py`: enabling and disabling mods in `modlist.txt`, activating and deactivating plugins in
  `plugins.txt`, adding a mod on top. It works on the file's bytes line by line: only the changed lines differ, and
  disabling then enabling gives the original file back byte for byte (order, line ends, comment, encoding). It
  refuses, writing nothing, a name that is not listed, a mod MO2 does not manage, and a file that is not the one
  the change was planned against or that changed meanwhile. It answers with each line changed and the mod's
  priority as MO2 numbers it, for the history.
- `modtrap/safe.py`: the safe folder. A file may be changed only if its copy is there and matches; what ModTrap
  writes is noted; Revert first checks every file and writes nothing at all if one was changed since by something
  else, unless told to go ahead; files ModTrap made are removed only if still as made. The record is written after
  every step, so a new start of ModTrap can still revert.
- `modtrap/history.py`: the append-only record, one event a line, flushed to disk as written; a line cut short by
  a crash is passed over. It answers which mods and plugins ModTrap switched off and not on again, with where they
  were: what Re-enable needs.
- `modtrap/probe.py`: three invented plugins with real records for the probe: a mod to take out, a plugin that
  overrides one of its records and holds a list with one entry pointing at it, and a patch made only for it; and
  what a dry run and a demaster of them must give. LIKELY: the layout of records and groups is the format as widely
  documented, not read in a source; ModTrap's own tests read the files back, and whether xEdit loads them is the
  first thing the probe will show.
- Not written: the script's mode that changes plugins. It waits for the first real report, which shows xEdit's
  names and behaviour; and it must not share a file with the report mode until that mode is proven, since an error
  in it could stop the script from loading at all.
- Still open before any of this is switched on: what MO2 does with a re-enabled mod's plugins (MO01§6), whether a
  rewritten `plugins.txt` keeps the load order through MO2's next start (WHY§26), and detecting that MO2 is closed.

### 37. Which tool made a plugin: read in the tools' own sources, kept as data

`2026-11-20` · FACT (the tools' repositories at named commits, TL01) · `#tools` · refs: MT18, WHY§22, WHY§28, TL01§2, TL01§3, TL01§4, TL01§5, TL01§7, DESIGN§13

- FACT: Wrye Bash marks its patch in the header's author field and names it by a fixed pattern (TL01§2);
  ParallaxGen names its split outputs by a fixed pattern and chooses its own output folder, which is why MO2's
  setting missed it on the owner's list (TL01§4, WHY§28); Synthesis has a default name, but a group's output is
  named by the modlist's maker and carries no mark of the tool (TL01§3).
- METHOD: `modtrap/data/tools.json` holds one entry a tool with its marks, names, kind and source; `modtrap/tools.py`
  applies it. Evidence in order: MO2's own record of where a tool's new files go, the author field, a known file
  name, and last a name that only begins like a tool's (weak: shown as "probably"). The page shows the evidence.
- METHOD: what follows from the kind. A patcher's or generator's output is proposed for "run the tool again". An
  editor's output (xEdit, zEdit) cannot be made again by ModTrap and is demastered. A tool ModTrap does not know,
  but whose output mod MO2 records, is taken for a tool, not an editor.
- LIKELY: DynDOLOD's names (TL01§5); its source is not public and its documentation is still to be read.
- On the owner's list this now recognises the texture tool's output plugin by its name, where MO2's setting alone
  had read it as an ordinary mod.

### 38. A Browse button: an in-page folder picker

`2026-11-20` · METHOD · `#page` · refs: MT19, WHY§30, DESIGN§4

- METHOD: a third way to open a modlist, beside dropping its folder and pasting its path: a picker over the page
  that walks this PC's folders (`modtrap/browse.py`). It lists folder names only, never files, marks each folder
  that holds a `ModOrganizer.ini`, and lets a folder be opened only if it is such a folder. It starts at the fixed
  drives, shows no link, junction or system folder, and refuses network and device paths.
- In-page and not a native dialog, on the advice from the owner's DataPiler (WHY§30): a dialog opened by ModTrap's
  own process tends to open behind the browser.
- FACT: tested here with the test runner and in a browser on Linux, where the start is the root folder. The list
  of drives on Windows comes from the same code as the drop's search and is untested until the owner's PC.
- Not done from the same advice: detecting a running MO2 and offering its folder, and showing each tool's version;
  both need Windows calls that cannot be tried here, and are better written when the owner can run them.

### 39. The demaster built end to end against a stand-in, and kept switched off

`2026-11-20` · METHOD · `#xedit #mo2 #safety #process` · refs: MT4, MT5, MT9, MT14, MT15, MT17, WHY§4, WHY§31, WHY§34, WHY§36, DESIGN§6.3, DESIGN§6.4, DESIGN§6.5, DESIGN§8, DESIGN§9, DESIGN§11, DESIGN§12, XE01§7, MO01§2

- The owner asked what could be finished before the first real dry run. The two missing parts could: the script
  that changes plugins, and the code that drives a demaster. Both are written; neither is reachable from the page,
  and a test checks that.
- METHOD (`modtrap/xedit/ModTrapApply.pas`): a second script, in a file of its own so that an error in it cannot
  stop the read-only script from loading. It takes out exactly what its job lists and nothing it cannot confirm: a
  record only if it belongs to a trapped plugin; an element only if it is where the dry run found it, is called
  what the dry run called it, and itself needs a trapped plugin. One refusal and that dependant is not written.
  After Clean Masters it counts again what still needs a trapped plugin; only at zero does it write the plugin, to
  a new file in ModTrap's own folder. Last, whatever happened, it takes the "changed" mark off every loaded plugin,
  so that xEdit saves nothing over an original (WHY§4). Its names were checked against the script engine's like
  the first script's (WHY§34); it has never run.
- METHOD (`modtrap/demaster.py`): plan from the dry run; safe folder; xEdit; verify each new plugin with ModTrap's
  own reader (the trapped plugins gone, no master missing or newly added, the script's own recount at zero) and
  every original by checksum; install with MO2 closed (ModTrap's mod on top with the new plugins, the patch-only
  plugins deactivated, the ticked mods disabled only if no dependant is left needing them); read the modlist again
  and run the health check; Revert. An entry is reached by the route the dry run recorded, and entries of one list
  are taken highest place first so that none moves. Every change goes into the history with priorities and
  positions.
- FACT: tested here end to end against a stand-in for xEdit that writes new plugins with ModTrap's own writer:
  after a demaster the modlist reads as intended (ModTrap's mod on top providing the demastered plugins at their
  old positions, the mod disabled, the patch inactive, the health check clean, every original byte for byte as it
  was), and after Revert the whole modlist folder is file for file what it was before. Also tested: MO2 open, or
  not known to be closed, refuses before anything is written; a new plugin that still lists the mod is not
  installed and the mod stays enabled; a refused action keeps that dependant out; an original changed during the
  run stops everything; an install that fails part way puts everything back.
- A slip the tests caught: a write to the mod list was noted in the safe folder only at the end of the install, so
  a failure in between left Revert seeing ModTrap's own change as someone else's. Each write is now noted at once.
- What the stand-in cannot show, and the owner's PC must (in order): the read-only script runs (WHY§31); the
  probe's invented plugins load in xEdit (WHY§36); the changing script runs, and taking the "changed" mark off
  really keeps xEdit from saving (WHY§4); a file written through `FileWriteToStream` is a sound plugin; MO2 keeps
  the load order after its lists were rewritten (WHY§26); and MO2 is reliably found open or closed.
- Not built: the page for it, the probe's own run, Re-enable, and Revert on the page. They come when the first
  real dry run has shown that the foundation holds.

### 40. Adding mods: what is built, the placing rule, and what was ruled out

`2026-11-21` · METHOD · `#adding #mo2 #page #tools` · refs: MT21, MT9, MT17, DESIGN§16, DESIGN§13, DESIGN§14, MO01§7, XE02§6, XE01§10, TL01§6, WHY§27, WHY§30, WHY§36, WHY§39

- The owner asked for a way to add extra mods safely, in place of "add it last, and its plugin last" (MT21), and
  left the how open. Built now, read-only: `modtrap/adding.py`, an Add mods tab, and `python -m modtrap add`.
- DECIDED (under MT21's freedom): **MO2 installs.** Ruled out: ModTrap unpacking archives itself. Most archives are
  7z or rar, which Python cannot read without third-party code; many mods come with an installer that asks which
  options to take; and MO2 already does both. So ModTrap starts from a mod that is installed and disabled, and a
  dropped archive is only a name to find that mod by (as WHY§30 found for folders: a page gets no path).
- METHOD: **the placing rule.** "Last" is right for what the owner wants (the new mod wins) and wrong only where
  something was meant to stay last: what the tools made. So the proposal is: after everything made by hand, before
  the tools' output. For plugins that is the run of tool-made plugins at the end of the load order, found by the
  same marks as DESIGN§13; for mods, the output mods at the end of the list. An editor's output does not count as
  tool-made (TL01§6): it is the modlist's hand-made patches, and the new plugin goes after them, as it does today.
- LIKELY, and the limit of that rule: going after the hand-made patches means the new plugin takes back every
  record it shares with them. That is what happens today too, unseen. Seeing it needs xEdit (DESIGN§16.5); until
  that is built, a step says how to look by hand. ModTrap does not pretend to settle record conflicts from headers.
- SPECULATION: an output mod with no plugin and no entry in MO2's settings (a behaviour or texture generator's
  folder) is recognised only by "output" in its name. On a list that names such mods otherwise, the new mod would
  be proposed after them; the report lists what it takes as outputs, so the owner can see when that is wrong.
- METHOD: shared files are found by entering, in each other mod, only the folders the new mod also has. Listing
  every file of a few thousand mods would take minutes; this takes one folder listing for a mod that shares
  nothing. It has a time limit and says when it was cut short. Not yet run on a real list.
- Not compared, and said on the page: files inside archives. Not known: the game's version (so the newer header
  format is only pointed out, XE02§6).
- FACT: tested on an invented list only (21 tests): the place among mods and plugins, masters in each state, the
  room in the load order, files won and lost, the tool to run again, the steps in order, and that nothing is
  written. The page was driven in a browser on that list.
- Next, on the owner's PC: `python -m modtrap add` on a real mod, to see the timing of the shared-files search and
  whether the outputs it recognises are the real ones.

### 41. A dropped archive is unpacked by ModTrap itself, in its own folder

`2026-11-21` · METHOD · `#adding #mo2 #safety #licence` · refs: MT21, MT9, MT14, DESIGN§16.1, DESIGN§16.8, DESIGN§8, MO01§8, MO01§7, WHY§30, WHY§36, WHY§40

- The owner corrected WHY§40's first choice the same day: the mod is to be dropped on ModTrap, which then does the
  rest (MT21's note). WHY§40 had "MO2 installs"; that entry stands as written, and this one replaces that point.
- FACT: MO2 cannot be asked from outside to install an archive (MO01§8). So "drop it and ModTrap does the rest"
  means ModTrap unpacks.
- METHOD: a page does get a dropped file's bytes, though not its path (WHY§30). They are sent to ModTrap's own
  server on this PC and written straight to the session's folder, never held in memory; an archive that already
  lies in MO2's Downloads is read there instead, without a copy.
- METHOD: `.zip` with Python's own reader. `.7z` and `.rar`, which most mods come as, through the owner's installed
  7-Zip: called, not contained, as MO2 and xEdit are. Ruled out for now: taking third-party unpacking code into
  ModTrap (a dependency to vet and list, and it would still not read `.rar`). SPECULATION: Windows' own `tar` may
  serve where 7-Zip is not installed; not tried.
- METHOD (safety): an archive is untrusted. Its kind is read from its first bytes; every name is checked before
  anything is written (no absolute path, no drive, no step upwards, no name Windows cannot hold); links and
  password-protected archives are refused; the unpacked size and file count are capped and the disk's free room
  is checked; after 7-Zip has run, the result is walked again for links. A refusal leaves nothing behind.
- METHOD: nothing of this touches the modlist. The unpacked mod lies in the session's folder and is analysed
  there, as a mod MO2 does not have yet. Copying it into MO2's mods folder is a write to the instance and belongs
  to the part that is switched off (WHY§36, DESIGN§16.8), even though it only adds.
- An installer that asks questions (a `fomod` folder, or several folders to choose from) is recognised and handed
  to MO2 for now. LIKELY: the installer's description file is plain XML naming the choices and the files each
  installs, so ModTrap can ask them on its own page; that is the next piece, and needs reading that format first.
- FACT: tested here with zips for real and with a stand-in for 7-Zip; the page was driven in a browser with a real
  upload. Not proven: the call to the real 7-Zip (its switches and the shape of its listing are from memory of its
  documentation, not from a run), and large archives on the owner's PC.
- Later, 2026-11-21: the call was run against 7-Zip 23.01 here (WHY§48): a .7z made by 7-Zip unpacks; one with a
  password, with or without its names hidden, is refused in words; one holding a link is refused. Its listing
  shows a link as a mode starting with "l", which the reader now looks for. Still not run: 7-Zip on Windows, whose
  listing gives attribute letters instead of a mode.
- **Later (2026-11-23).** ModTrap now reads .7z itself, and Windows' `tar` is the last resort for what it does
  not read: WHY§123.

### 42. Carrying out an add: written and tested against invented lists, switched off

`2026-11-21` · METHOD · `#adding #mo2 #safety #process` · refs: MT21, MT9, MT14, MT15, DESIGN§16.8, DESIGN§8, DESIGN§11, DESIGN§12, MO01§2, MO01§7, WHY§16, WHY§26, WHY§36, WHY§39, WHY§41

- The owner said to carry on. Written: `modtrap/addjob.py`, and two more list edits in `modtrap/profile.py`
  (`place_mod`, `place_plugins`). As with the demaster (WHY§39), nothing the page can call reaches them, and a
  test checks that.
- METHOD (`place_mod`): `modlist.txt` lists the highest priority first, so "directly before X as MO2 shows the
  list" is the line after X's. A listed mod's line is moved, an unlisted one's is added; every other line is
  written back byte for byte.
- METHOD (`place_plugins`): both lists are written, in agreement, because MO2 takes the order from the newer one
  (MO01§2). `loadorder.txt` gets the name before the named plugin; in `plugins.txt`, which leaves the game's own
  plugins out, it goes before the first later plugin that file names, with the star.
- METHOD (`addjob`): refuse unless MO2 is known to be closed and the three lists are still as planned; the lists
  into the safe folder; each unpacked mod copied into MO2's mods folder, never over an existing one, with a
  `meta.ini` naming its archive; each mod placed and enabled, each plugin placed and activated; then the modlist
  is read again from disk and must show every mod enabled in place, every plugin active after its masters, used
  from its own mod, and no new problem. Anything else, or any error, puts everything back.
- DECIDED (under MT9 and MT14, which pull apart here): Revert removes the copy of a mod that ModTrap itself made
  in that job, but only while that folder is file for file as copied; if anything in it has changed since, it is
  left and named. The unpacked original stays in the session's folder either way. No other mod is ever removed.
- FACT: tested on invented lists: an unpacked mod and an installed, disabled one added together land in place
  with a clean health check; Revert leaves the whole modlist folder byte for byte as before; MO2 open or unknown,
  a list changed since the plan, a missing master, a name already taken, and a failure part way each refuse or
  put everything back.
- Not proven, and why it stays switched off: whether MO2 keeps the mod order and the load order exactly as
  written when it next starts (WHY§26), and whether it takes a mod folder with only that one line in `meta.ini`
  as an installed mod (LIKELY, MO01§7). Both are for the probe on the owner's PC.

### 43. An installer's questions are asked on ModTrap's own page

`2026-11-21` · METHOD · `#adding #page #safety #licence` · refs: MT21, DESIGN§16.1, MO02§2, MO02§3, MO02§4, MO02§5, MO02§6, WHY§41

- WHY§41 handed a mod with an installer to MO2 and named this as the next piece. Built: `modtrap/fomod.py`, the
  questions on the Add mods tab, and the build of the mod's folder from the answers.
- METHOD: the format's meaning was read in MO2's own installer (MO02), which has no licence file, so nothing of it
  is copied: ModTrap's reader is its own code over Python's XML reader. Where the format leaves a choice, ModTrap
  does what MO2 does, so that a mod built by ModTrap is the mod MO2 would have installed for the same answers:
  the fallback encodings, the order of options, what is chosen to begin with, the order files are copied in.
- METHOD: all steps that apply are shown on one card, not as pages. The answers are sent as a whole each time and
  the card is worked out afresh, so a step that depends on an earlier answer appears or goes as that answer
  changes. A group the owner has not touched keeps what the installer recommends.
- METHOD (safety): the file is another person's. It is size-capped; a file that declares its own document rules
  (the way such a file can be made to swell without end) is refused, in any encoding; every source must lie in
  the archive and every destination in the mod being built, by the same name check as unpacking (WHY§41).
- METHOD: an archive that only holds several folders to choose from gets one question made for it: which of the
  folders, a later one winning a shared file.
- Left out, and said: images; the game's version (a version condition is taken as met); `alwaysInstall` and
  `installIfUsable`, which MO2 does not act on either (MO02§4); and the older script-based installers.
- FACT: tested with an invented installer (steps that depend on a flag, an option that depends on the load order,
  priorities, a conditional file), and driven in a browser from the drop to the analysed mod. Not proven: real
  mods' installers, which are often untidy; the first few on the owner's PC will show what is missing.

### 44. "Add it for me" and Revert on the page, behind a switch that is off

`2026-11-21` · DECIDED · `#adding #safety #process #page` · refs: MT21, MT14, DESIGN§8, DESIGN§9, DESIGN§16.8, WHY§36, WHY§39, WHY§42

- The owner asked for the rest to be built. The job of WHY§42 is now reachable from the page: `modtrap/changes.py`
  holds the three endpoints (the plan, carrying it out, Revert), and the Add mods tab has "Add it for me", the
  plan with its go-ahead, and "Take it out again" for each add the session carried out.
- DECIDED (mine, for the owner to overrule): it is switched off unless ModTrap is started with `--allow-changes`.
  Without the flag the module is never imported, its paths do not exist, and the button is greyed out with the
  reason. WHY§36's rule stands: nothing changes a modlist until the owner's PC has shown that MO2 keeps what
  ModTrap writes. The flag is how that is shown: the owner starts ModTrap with it for the probe, on purpose.
- METHOD: the plan is made twice, once to show and once more at the go-ahead, and the job refuses if the lists
  changed in between. The plan card says whether MO2 is closed; open or not known, the go-ahead is greyed out and
  the job would refuse anyway (WHY§42). After an add or a Revert the modlist is read again from disk.
- METHOD: a dropped mod that was added becomes one of MO2's mods on the page; after Revert it is again the
  unpacked mod in ModTrap's folder, so it can be added again.
- FACT: tested through the same calls the page makes, and driven in a browser on an invented list from the drop
  to the added mods and back: after Revert the modlist's folder is as before. Tests also check that without the
  flag a fresh start loads none of the writing modules.
- Not proven: all of WHY§42's open points, and telling whether MO2 is open on a real PC.

### 45. The record check and starting the tools: built, and not behind the switch

`2026-11-21` · METHOD · `#adding #xedit #tools #process` · refs: MT18, MT21, DESIGN§16.5, DESIGN§16.6, DESIGN§16.8, DESIGN§7, XE01§10, MO01§3, WHY§31, WHY§34, WHY§40, WHY§44

- The last two pieces of DESIGN§16.8. Neither changes a modlist by ModTrap's own hand, so neither is behind
  WHY§44's switch: the record check is a read-only xEdit run like the dry run (WHY§31), and starting a tool is
  what MO2's own Run button does.
- METHOD (record check): a third script in its own file, `ModTrapRecords.pas`, report-only, with the same job
  file, progress file and end line as the first. For each record of the new plugin that is not its own it writes
  xEdit's two conflict levels and the plugins that hold the record. Its names were checked against the script
  engine's (WHY§34). ModTrap loads the whole active load order for it, not a cut-down list: who else changes a
  record cannot be known from the new plugin's masters. On a large list that is a long load, and the page says so.
- METHOD (reading it): "takes" needs both another overriding plugin before it and xEdit's level "conflict" or
  higher; where plugins override the same record without a conflict, nothing is lost. Whether the plugin taken
  from or lost to was made by a tool is told by the same marks as DESIGN§13. ModTrap lists and explains; it does
  not write a patch. Ruled out for now: merging records automatically, which is what the patchers exist for and
  goes wrong quietly when done blindly.
- METHOD (tools): before the start ModTrap notes size and time of the files in the tool's output mod, in
  `overwrite`, and of the plugins that tool made; after the tool has closed it says which were written, and reads
  the modlist again. "None changed" is said plainly: the tool may have been closed without running.
- LIKELY: MO2's command waits for the tool (MO01§3), and where ModTrap can see running programs it also waits for
  the tool's own program to be gone. Not proven on a real PC, like every start through MO2 so far.
- FACT: tested with the stand-ins (the record report read and sorted; a run through the stand-in xEdit with the
  plugin unchanged; a tool that writes, one that does not, one at a time, stopping), and the whole flow driven in
  a browser on an invented list: drop, add, record check, start the tool.

### 46. "Demaster Selected" on the page behind the same switch, and a History tab

`2026-11-21` · METHOD · `#xedit #mo2 #safety #page #process` · refs: MT1, MT2, MT9, MT14, MT15, DESIGN§6.3, DESIGN§6.4, DESIGN§6.5, DESIGN§8, DESIGN§11, DESIGN§12, WHY§36, WHY§39, WHY§44

- The owner said to carry on. WHY§39's demaster is now reachable from the page, through `modtrap/changes.py` and so
  only with `--allow-changes` (WHY§44). Without the flag the button is greyed out and says why.
- METHOD: the page takes it in two go-aheads, because the two halves need opposite things of MO2. First
  "Demaster Selected" shows the plan from the finished dry run; "Go ahead" makes the safe folder, runs xEdit
  through MO2 with the changing script, and verifies the new plugins: MO2 is in use, and nothing in the modlist
  has changed. Then "Put them in place" asks again and needs MO2 closed: ModTrap's mod with the new plugins, the
  patch-only plugins deactivated, the ticked mods disabled, the health check. A failure in either half says why;
  the first changes nothing, the second puts everything back (WHY§39).
- METHOD: the plan is only made from a dry run of the modlist as it was last read, by this start of ModTrap; after
  a restart or a rescan the dry run is run again first. The demaster does exactly what that dry run listed.
- METHOD: each demaster the session put in place is listed with "Revert", which works from the job's safe folder
  alone, so also after ModTrap was closed and started again.
- METHOD: a History tab shows the session's history file (MT15), newest first: what, when, priorities and
  positions. Reading it needs no switch; the page's own code only reads the file.
- FACT: tested through the page's calls with the stand-in xEdit (plan, run, verified with the modlist untouched,
  refused while MO2 is open, put in place, the history, Revert back to byte for byte; a run that alters an
  original stops with nothing changed), and driven in a browser on an invented list.
- Not proven, unchanged from WHY§39: the changing script in a real xEdit, a plugin written by it, MO2 keeping the
  lists, and telling whether MO2 is open. The order to prove them in on the owner's PC: the dry run; the record
  check; one small add with the switch; then a demaster of a small mod, with Revert at hand.

### 47. The probe is built and gates real work; Revert goes line by line once MO2 has run

`2026-11-21` · METHOD · `#safety #mo2 #xedit #process` · refs: DESIGN§9, DESIGN§11, MT8, MT14, WHY§4, WHY§5, WHY§7, WHY§8, WHY§15, WHY§26, WHY§36, WHY§39, WHY§42, WHY§44, WHY§46, MO01§2

- With everything else built, what stood between the code and the owner's PC was a list of unproven things spread
  over WHY§39, WHY§42 and WHY§46, to be tried by hand in a set order. DESIGN§9 had named the answer from the start:
  a probe. It is built (`modtrap/probejob.py`, a card on the Tools tab).
- METHOD: the probe has no code of its own for changing anything. It calls the add job, the dry run, the demaster
  and Revert exactly as real work does, on `modtrap/probe.py`'s invented plugins, so each of its seven steps
  stands for one unproven thing (DESIGN§9). The plugins are in two mods, because a dry run needs a mod to take out
  and something outside it that depends on it.
- DECIDED (DESIGN§9's rule, now enforced): `--allow-changes` alone no longer lets a real job run. The probe must
  have passed in this session's modlist with the xEdit now set up in MO2; the outcome is kept with the session.
  The two buttons say what is missing. Tests that try the jobs themselves switch the rule off by name.
- METHOD: a failed step names what differed, as far as it can be told: for the dry run, the value that was not
  as expected and the name xEdit gave the list (the likeliest first failure: WHY§31's list of safe arrays holds
  names read in xEdit's definitions, not seen in a report yet).
- FACT, found by the probe's own test: after MO2 has rewritten a list, the safe folder's Revert refuses, rightly
  (the file is no longer what ModTrap left), and so the probe could not clean up after "MO2 changed the order".
  The same would meet the owner in real use: add or demaster, open MO2, later ask for Revert.
- METHOD (DESIGN§11, added): when the whole files cannot be put back, Revert takes back ModTrap's own changes line
  by line and leaves the rest of the lists alone. Ruled out: overwriting with the old files after a warning, which
  would silently undo whatever the owner did in MO2 since.
- FACT: tested with the stand-ins: the probe passes and leaves the modlist's folder file for file as before; a
  different list name fails the dry-run step and says the name; a reordered list fails "kept" and ModTrap's lines
  and mods are taken out while the reordering stays; MO2 open or unknown, the probe does not begin; an earlier
  probe's mod is named, not overwritten; real work is refused before the probe and allowed after; Revert of an
  add and of a demaster after the lists changed keeps the change and takes ModTrap's part out. Driven in a
  browser on an invented list.
- Not proven: the probe itself is the proof still to come. Its first real run is expected to fail somewhere, and
  to say where.

### 48. "Save this session": the logs cleaned and packed into one .7z, written with Python alone

`2026-11-21` · METHOD · `#page #safety #licence #process` · refs: MT20, DESIGN§15, DESIGN§4, WHY§9, WHY§33, WHY§41, WHY§47

- The owner asked for one button that packs what is needed to diagnose a run into a single .7z to download from
  the page, and gave the design of the same feature in another of their tools, including the archive's layout and
  the pitfalls found in its review. Built to that design: `modtrap/sevenz.py`, `modtrap/savelog.py`, a button on
  the Log tab.
- METHOD (what goes in), fitted to ModTrap, whose sessions are folders, not stamped files: the session's log as it
  stands; its `session.json`, history and probe outcome; the text records of its newest jobs (plans, reports,
  xEdit's own log, the lists handed to xEdit, each safe folder's record but not its copies); what was noted of
  dropped archives; the open profile's three list files; ModTrap's settings; and a short description of the setup.
  Never: a plugin, an archive, an unpacked mod, a safe folder's copies, or another session. Only files with a
  text ending are taken, and folders that hold mods' content are not entered.
- METHOD (cleaning): each text is cleaned as it is packed. Known folders become the same placeholders as in the
  log; the user name is replaced only where it is a part of a path; any other absolute path keeps only its last
  part; a web address is not a path. A `.json` is parsed, every string and key cleaned, and written again, so it
  stays valid; a `.jsonl` goes line by line, a torn last line as text. A text that cannot be cleaned is replaced
  by a note, never passed through.
- METHOD (packing): off the request, one at a time; a second press while packing does nothing. Each file's size
  is noted when it is opened and no more is read, in blocks cut at a line end. The archive is written in the
  system's temporary folder, handed out once through the page's own token, and removed after that or at the next
  press. With nothing to pack, no archive is made and the page says so.
- METHOD (the .7z): one solid LZMA2 stream with Python's `lzma`, and the header written by hand from the
  format's description: no dependency, nothing bundled.
- FACT: read back three ways: by a reader written in the tests from the same description, by an independent
  library where it is installed, and by 7-Zip 23.01 itself ("Everything is Ok"), each checking every file. The
  library and the program are only used by the tests, which pass over them where they are not installed; neither
  is a dependency of ModTrap. The download was driven in a real browser.
- A side gain: with 7-Zip installed here, WHY§41's untested call to it could be run (its Later line).
- Not proven: 7-Zip on Windows opening the archive, though the format is the same; and what a real session's
  files hold that the cleaning does not expect. The first archive from the owner's PC should be looked through
  by the owner before it is sent.

### 49. The first real run of the probe: what passed, what failed, and what was changed for it

`2026-11-21` · FACT · `#xedit #mo2 #adding #process` · refs: DESIGN§7, DESIGN§9, DESIGN§16.3, XE01§11, MO01§3, WHY§7, WHY§31, WHY§34, WHY§40, WHY§42, WHY§47, WHY§48

- The owner ran the probe on the real modlist (about 3,600 mods and 3,750 plugins; xEdit 4.1.5f; Windows 11) and
  sent the saved session (WHY§48). It is the first time any of ModTrap's work met MO2 and xEdit.
- FACT, passed: step 1. ModTrap's two test mods were copied into MO2's mods folder, listed, enabled, and their
  three plugins placed and activated in both plugin lists; ModTrap's re-reading of the lists agreed. In the first
  of two runs the lists were then put back whole: about a minute after MO2 had been started on them they were
  still byte for byte what ModTrap had written. LIKELY, not shown: that MO2 had already closed by then; the
  saved session does not say whether MO2 was found closed or could not be found at all, and the log now says
  which.
- FACT, passed: MO2's command started xEdit; the quoting of the arguments held; xEdit took the plugins file, the
  backup folder and the log file from them; the script compiled and ran in xEdit's interpreter, read its job file,
  wrote its progress and its report, and ModTrap read the report (WHY§31 and WHY§34's open points, for the
  reading script).
- FACT, failed: step 2, for two reasons, both ModTrap's (XE01§11). xEdit read another installation's Data folder,
  because MO2's `-a` replaces the arguments the modlist had set for its xEdit; and xEdit does not close after a
  script, whatever `-autoexit` says, so MO2 stayed open, waiting, and the probe could not clean up after itself.
  XE01's earlier reading of `-autoexit` was wrong and is corrected there.
- METHOD, changed: the executable's own arguments are carried over and the game folder MO2 manages is named to
  xEdit; ModTrap closes the xEdit it started; the script reports where xEdit looks; a run that loads nothing fails
  and says so (before, it "finished" with nothing read); the probe's clean-up waits for MO2 to go.
- FACT, also seen in the saved lists: the placing rule of WHY§40 did not fit this list. Its outputs are under an
  "Outputs" separator in the middle of the list, with sections of options after it, so ModTrap found no output at
  the end and put the test mods last, in a section for mods not yet installed; and one plugin of unknown making
  among the outputs ended the run of tool-made plugins early, so the test plugins landed after the patcher's
  output instead of before it. METHOD: a separator named for outputs now decides both (DESIGN§16.3), and a
  couple of unknown plugins among the outputs no longer end the run.
- FACT: the saved session was clean: the owner's folders came as placeholders, and no file of a mod was in it.
  xEdit's own log was in it, which is what showed the wrong Data folder.
- Not proven still: everything from step 2's reading onward (whether xEdit loads the invented plugins at all, the
  names it gives the list, MO2 keeping the lists, the changing script, Revert on the real list).

### 50. The probe passes on the owner's PC: what that proves, what it does not, and a message of MO2's

`2026-11-21` · FACT · `#xedit #mo2 #safety #process` · refs: DESIGN§9, DESIGN§7, DESIGN§11, DESIGN§16.3, XE01§11, XE01§12, MO01§9, WHY§4, WHY§5, WHY§7, WHY§8, WHY§26, WHY§31, WHY§34, WHY§39, WHY§42, WHY§47, WHY§49

- FACT: after WHY§49's changes the owner ran the probe again and all seven steps passed, on the real modlist with
  xEdit 4.1.5f, in about four minutes. The saved session shows each step (XE01§12, MO01§9).
- What that settles, each an open point until now: MO2 takes a mod folder ModTrap made; MO2's command starts xEdit
  with ModTrap's arguments, the modlist's own carried over; both scripts compile and run in xEdit; xEdit loads
  invented plugins and names the form list as ModTrap expects (WHY§31, WHY§34); the changing script writes a
  sound plugin and leaves xEdit nothing to save (WHY§4, WHY§39); a MO2 started by `run` keeps the lists ModTrap
  wrote (WHY§26, for that case); ModTrap tells whether MO2 is running; closing xEdit by asking works; Revert puts
  the real lists back whole. The placing rule of WHY§49 put the test mods right before the list's "Outputs"
  heading and the test plugins before everything under it.
- What it does not settle. The probe's plugins are three, tiny and tidy. A real dependant has thousands of
  records and kinds of list the probe has none of; a real job loads far more plugins and takes far longer; what a
  MO2 opened as a window does to the lists was not tried; nor Revert after the owner has gone on working in MO2
  (the line-by-line path, WHY§47, tested only here). The first real dry run and the first real demaster are still
  firsts, and their safeguards are the ones built for them: the dry run only reads, the demaster checks every new
  plugin and every original, and Revert is at hand.
- FACT: each time MO2 had finished a run it showed a message, "Failed to run 'xEdit64'", with an error raised by
  one of the modlist's own MO2 plugins, and stayed open until the owner pressed OK. xEdit had run; the error comes
  from that plugin's code for "a run has finished" (MO01§9). ModTrap waited, as built, and went on when MO2 had
  closed.
- METHOD: a MO2 that ModTrap's own command started, and that has not closed some seconds after xEdit has gone, is
  now asked to close, as a click on a window's X does, with a line in the log saying so. It is never ended by
  force, and a MO2 the owner had open before the run is never touched. LIKELY, to be seen on the owner's PC: that
  the request dismisses the message. Ruled out: ending MO2 by force (it may be writing its settings), and
  starting MO2's window first so that its plugins are set up (slow on a large list, and more to go wrong).

### 51. xEdit's "Module Selection" window: always shown in script mode, nothing to choose, ModTrap presses OK

`2026-11-21` · FACT · `#xedit #page #process` · refs: XE01§11, XE01§13, XE01§2, DESIGN§7, WHY§49, WHY§50

- The owner, with a picture of the window: "it seems the user also has to click ok inside xedit for module
  selection, can that be done by ModTrap as well? Is the user supposed to select specific mods here?"
- FACT: WHY§49 took `-autoload` out on the reading that script mode loads without asking. That reading was wrong:
  the source shows the window always opens in script mode (XE01§13), and the owner had been pressing OK on every
  run. Taking `-autoload` out was still right (it is never read in script mode); the claim beside it was not, and
  XE01§11 is corrected.
- FACT: nothing is to be chosen. The window comes preset to the plugins of the plugins file, and for ModTrap's
  runs that file is ModTrap's own list for the job.
- METHOD: ModTrap presses OK itself, through Windows' own window calls from Python's standard library, with no
  new dependency. It presses only xEdit's own window of that class and caption, only its OK, only while the
  script has not started, and a failure there never stops a run. Unproven until the owner's next run; the log
  and the page tell the owner to press OK if the window stays.
- Ruled out: starting xEdit in edit mode with `-autoload` and running the script another way (edit mode has no
  switch that runs a script); a plugin mode (they load one plugin and do their own work).

### 52. The first real dry run against the guide: the same plugins, a different split; what was changed for it

`2026-11-21` · FACT · `#procedure #xedit #safety #process` · refs: MT4, MT6, MT17, DESIGN§5, XE01§14, WHY§2, WHY§26, WHY§28, WHY§50, WHY§51

- The owner ran the first real dry run (17 dependants of one mod, read in under three minutes, every file
  unchanged) and said: "you can compare that to what the JoJ guide asks for (keep in mind that guide can miss
  some things, as it's few months old", and "basically it's about finding what xedit find registered for the big
  patch files the modlist features".
- FACT: the guide's own steps for that mod (the owner's pictures of 2026-11-20, WHY§2) name 15 plugins: one patch
  mod to disable whole (7 plugins), 5 single patches to deactivate in other mods' collections, and 3 big patch
  files of the list to demaster by hand. ModTrap's dry run found those 15 and two more big files, which are
  newer than the guide. Nothing the guide names was missed.
- FACT: the split was not the guide's. ModTrap read a dependant as a patch only when nothing of it would remain,
  so it would have demastered the 5 single patches and left 6 of the patch mod's 7 as "needs you". The guide
  switches all 12 off without looking inside: they are patches for the mod, and have no purpose without it.
- DECIDED (the method is ModTrap's, MT6 and MT17): a dependant is a patch for the mod, and is switched off
  whatever it holds, when it has at most two masters besides the game's own files and the trapped plugins, and
  its name holds the mod's or the plugin's whole name, or their initials as a word of its own. On the real
  report this gives exactly the guide's split: the 12 switched off, the 5 big files kept for demastering. A mod
  all (or nearly all) of whose plugins are switched off this way is disabled whole, as the guide does, so that
  its loose files go too (DESIGN§5, WHY§28); a patch among others in a collection is only deactivated. Both are
  undone by Revert, and nothing in those plugins is changed.
- Ruled out: few masters alone (a mod that merely builds on the trapped mod would be switched off, and the
  probe's own plugin that must go on working has one master); the name alone (a big patch may carry a like
  name); "every plugin of its mod depends on the trapped mod" as a reason by itself (true of the probe's mod
  too). The name and the masters together are a proposal, not a proof; changing a single proposal on the page
  (MT6) is not built yet.
- FACT: in the five big files, what needs the mod is: list entries (one file; already automatic, case B), the
  files' copies of the mod's own records (already automatic, case A), and, in every "needs you" record, a part
  of a record of the game or of another mod: a condition of a dialogue line that names something of the mod, a
  script's property pointing into the mod, a "previous line" field pointing at one of the mod's lines. Seven
  such records are the same in two of the files. This is what the guide means by a record "forwarding" the
  mod's data: the big patch carries on what the mod, or a patch for the mod, put into that record.
- LIKELY, and what the next dry run is to show: for each such part, some plugin loaded before the big patch (the
  mod itself or one of its patches) has the very same part, and the big patch's remaining masters have that part
  without the mod. Putting it back as it is there is MT4's case C, and is what a person following the guide's
  "more surgical edit" does. MT4 makes C automatic only once real dry runs show it reliable.
- METHOD: the reading script now reports, for every such part, where it comes from and what it would be without
  the mod (XE01§14), and the dry run shows it beside each "needs you" record: "carried on from …; without the mod
  this part is as in …", or "added on top of what … has". It is reported only. The applying half is built when
  the owner's next dry run shows what share of the parts it covers.
- The guide and the list are named here only in the owner's own words; no plugin name, record or id of the real
  list is in the repository.

### 53. The second real dry run stopped at a file held by another program; the scripts now bear it, and a probe pass counts only for the scripts it ran

`2026-11-21` · FACT · `#xedit #mo2 #safety #process` · refs: XE01§13, XE01§15, DESIGN§7, DESIGN§9, MO01§9, WHY§47, WHY§50, WHY§51, WHY§52

- The owner: "the dry run couldn't complete this time, MO2 came up with the same error at one point", with the
  saved session.
- FACT: ModTrap's press of OK in xEdit's module selection worked on the owner's PC (the log line of WHY§51, 24
  seconds after the start, and the script began without the owner). XE01§13's LIKELY holds.
- FACT: the run then stopped in the script, at the write of the progress file, which another program held open
  at that instant (XE01§15). It is not MO2's message: that message comes after every run that MO2 starts from
  the command line (WHY§50) and is unrelated. Every dependant was unchanged.
- METHOD: the scripts let a missed progress write go and try the report's write again (XE01§15). Not provable
  here: the stand-in for xEdit does not run the scripts; the owner's next run shows it.
- METHOD: a passed probe is now remembered together with a mark of ModTrap's three scripts, and counts only while
  they are the same. The scripts changed twice today after the probe had passed; a real demaster must not rest on
  a pass earned by other code. The dry run itself needs no probe (it only reads).
- METHOD: after asking a MO2 that stopped at a message to close, ModTrap now waits and says in the log whether it
  closed, so the next session file answers whether the request dismisses the message (WHY§50's open point). The
  wait before asking is four seconds, not eight.

### 54. The probe and the dry run pass again with the changed scripts; MO2's message is closed the moment it shows

`2026-11-21` · FACT · `#xedit #mo2 #process` · refs: XE01§13, XE01§14, XE01§15, MO01§9, DESIGN§7, WHY§50, WHY§51, WHY§52, WHY§53

- The owner, with the saved session: "that MO2 still keeps coming up though it seems ModTrap completes its tasks."
- FACT: with the scripts of WHY§52 and WHY§53 the probe passed all seven steps and the dry run read all 17
  dependants in 90 seconds, every file unchanged. The new script code runs on the owner's xEdit; no write failed.
  The split is the guide's: 12 patches switched off, 5 big files for demastering.
- FACT: each of the three runs ended with MO2 at its message; ModTrap asked MO2 to close after four seconds and
  MO2 was gone within three more ("MO2 closed when asked"). WHY§50's open point is settled: the request does
  dismiss the message. But the message stood on the screen for some seconds every time.
- FACT: the message cannot be prevented from ModTrap's side. It is raised inside MO2 by one of the modlist's own
  MO2 plugins when a run that MO2 started from the command line ends (MO01§9).
- METHOD: ModTrap now looks, several times a second once xEdit has gone, for a visible window of the MO2 it
  started whose caption is exactly MO2's message caption, and asks that window to close. MO2's main window has
  a longer caption and is never touched, nor is a MO2 the owner had open. The earlier request to MO2 as a whole
  stays as the fallback. Unproven until the owner's next run.

### 55. What the big patch files carry on from the mod, as the evidence run showed it; MT4's case C becomes automatic, and the probe proves it first

`2026-11-21` · DECIDED · `#procedure #xedit #safety #process` · refs: MT4, MT6, MT17, DESIGN§5, DESIGN§6.3, DESIGN§9, XE01§14, XE01§16, WHY§2, WHY§47, WHY§52, WHY§53, WHY§54

- FACT (the dry run of WHY§54, with WHY§52's evidence lines): in the five big files, 32 records needed the owner, in 33 parts.
  - In 17 of the parts, the part that needs the mod is the very same as in an earlier plugin that goes: the mod itself
    (five script attachments in one generated file, three "previous line" fields in another) or a patch for the
    mod that is switched off (nine condition lists). In each case the big file's last master without the mod
    has the part, and nothing it points at is missing from the big file's masters.
  - In 7 the part is the same as in another big file that loads earlier and is itself to be demastered.
  - In 9 (seven of them those same records in that earlier file) the part is a list of conditions that no
    earlier plugin has in that form: the big file merged it, and one entry of it needs the mod.
- DECIDED (MT4 left "when C becomes automatic" to the evidence; MT17 leaves the method to ModTrap):
  1. A part that is the same as a trapped plugin's, or as that of a patch that is switched off, is **put back**
     as the dependant's last master without the mod has it, or **taken out** if that master has none.
  2. A list in which each entry that needs the mod is also an entry of an earlier plugin's version of the list
     (the dependant did not write it) loses **those entries**, except an entry of conditions whose removal would
     join the conditions around it differently (XE01§16).
  3. A part that is the same as an earlier dependant's which is itself demastered gets what that one gets, if
     that is the same plugin's version; else rule 2 is tried on its own evidence.
  4. Anything else still needs the owner: a part no earlier plugin has in that form and that is not such a list,
     a source that would need a master the dependant lacks, an older report without the evidence.
- Why not always "put back the last master's version": where the big file merged the list itself (the 9), the
  last master's list is not what the big file would hold without the mod; taking out the mod's entry keeps the
  rest of the merge. Why not always "take out the entry": a changed single field or a script attachment has no
  entry to take out, and for a part that is wholly the mod's version, the master's version is the exact answer.
- METHOD (safety): the changing script puts a part back only from a plugin that is not trapped, whose version
  needs no trapped plugin, and then checks that the part reads exactly as that version; one refusal and the
  dependant is not written (XE01§16). Entries go before parts and later lists before earlier ones, so that no
  place found by the dry run has moved. ModTrap's own checks of every new plugin and every original stand as
  before, and Revert undoes the lot.
- METHOD (the probe): the probe has a fourth invented plugin, a base that stays, and the plugin that must go on
  working now carries on the test mod's change to one of the base's records. The probe passes only if the dry run
  reads that as "put back", and the new plugin holds the base's value and not the test mod's. The scripts
  changed, so the probe must pass again before real work (WHY§53).
- Unproven: the put-back of a script attachment and the removal of a condition, on real plugins. Both are
  guarded by the checks above; the first real demaster shows them.

### 56. The probe proves the put-back on the owner's xEdit; all five big files read as demasterable; a copy that hides a remade original is called out

`2026-11-21` · FACT · `#xedit #mo2 #tools #safety #process` · refs: MT4, MT5, MT14, DESIGN§5, DESIGN§9, DESIGN§13, XE01§16, MO01§9, WHY§28, WHY§54, WHY§55

- FACT (the owner's session): with WHY§55's scripts the probe passed every step. xEdit read the carried-on part
  of the invented plugin as "put back", the changing script put it back, and the new plugin holds the base's
  value. XE01§16's LIKELY holds for a single link.
- FACT: the real dry run then read all five big files as "can be demastered", with nothing left for the owner:
  7 keyword entries; 7 + 7 + 2 condition entries, each also found in a patch for the mod or in the mod itself,
  none ending a run of "or"; 9 condition lists and 3 single fields put back from the files' own masters; 5
  script attachments put back from the game's own file; 45 copies of the mod's own records taken out. The
  twelve patches are switched off. This is the guide's whole list, and the two files the guide does not name.
- FACT: closing MO2's message worked, but MO2 then took some seconds to leave, and ModTrap's fallback asked it
  again with a warning in the log. METHOD: once the message is closed MO2 gets twelve seconds before that.
- METHOD: ModTrap's demastered copy lies in ModTrap's own mod, above the original (MT5). If a tool later makes
  the original again (one of the five is a generator's output, WHY§28), the copy would hide the newer file and
  nothing would say so. An installed job now compares each original with what the safe folder knows of it, and
  the job's card names any that changed since, with what to do. Hashing is done again only when a file's size
  or time changed.
- Still a first: the demaster of real plugins. The put-back of a script attachment and the removal of a
  condition run there for the first time, each checked by the script against its source (XE01§16).

### 57. The Steps tab still gave ModTrap's own steps to the owner; they are ModTrap's now, with the button

`2026-11-21` · METHOD · `#page #steps #process` · refs: MT18, MT21, DESIGN§14, WHY§46, WHY§52, WHY§55

- The owner, with a picture of the step "Switch off the patches made only for the mod", marked "You": "can this
  not be done by ModTrap?"
- FACT: it can, and "Demaster Selected" does it (WHY§46, WHY§52). The Steps tab was written before that was built
  and still gave switching off, demastering and disabling the mod to the owner, with words to match.
- METHOD: when ModTrap is started with the switch, those three steps are ModTrap's; the first two carry a
  "Demaster Selected…" button that shows the plan and asks, as the Selection tab's does. Without the switch
  they stay the owner's, and say that ModTrap does them when started with it.
- METHOD: the tab now sorts the dependants as the demaster itself does, by the dry run's reading first: a tool's
  output that the dry run found demasterable is listed under demastering, not under "run the tool again", and
  the demaster step says how many of its plugins need the owner.

### 58. ModTrap knows whether this modlist's MO2 is open, and asks before closing it; every step says truly who does it

`2026-11-21` · METHOD · `#mo2 #page #steps #safety #process` · refs: MT18, DESIGN§7, DESIGN§14, DESIGN§16.7, MO01§2, WHY§50, WHY§54, WHY§57

- The owner: "make sure ModTrap knows if MO2 is open for the modlist, so it geyes out functions that require it
  closed (same vice versa, grey out features the need MO2 open if not already open, or perhaps it could auto start
  or close MO2 with prompt 'Close/open MO2?' with Yes or No)", and "most of these steps indicate 'You', including
  the one you said ModTrap can do, can you double check which steps can be done by ModTrap".
- FACT: ModTrap knew only whether any program called ModOrganizer.exe ran, by asking Windows' task list each
  time; the buttons that need MO2 closed were greyed out with a line of text, and the owner had to close MO2 and
  press "Check again".
- METHOD: ModTrap now lists the running programs of that name with their full paths, through Windows' own calls,
  and counts MO2 as open only if one of them is this modlist's own ModOrganizer.exe (the same file, however the
  path is written). A MO2 of another modlist has its own lists and does not count. Where the list cannot be had,
  the old answer stands; where nothing can be told, nothing that needs MO2 closed is done.
- METHOD: the page shows "MO2 is open" or "MO2 is closed" beside the modlist's other facts. A step that changes
  MO2's lists (adding and taking out again, putting a demaster in place, Revert, the probe) asks, when MO2 is
  open, "Close MO2 now?"; on yes ModTrap asks that MO2's windows to close, as a click on the X does, waits until
  it has gone, and goes on. It never ends MO2 and never closes it unasked (WHY§50's rule stands: the yes is the
  owner's). The same place starts MO2 when it is closed, to look at a result.
- FACT: nothing ModTrap does needs MO2 open beforehand: for xEdit and the tools it starts MO2's command itself,
  and a MO2 that is open takes the command over (MO01§4). So nothing is greyed out for a closed MO2.
- METHOD (the labels): each step now says who does it, for demastering and for adding mods alike. "ModTrap":
  the dry run, switching off, demastering, disabling, enabling and activating an added mod, the record check,
  the health check. "ModTrap starts it, you run it": a tool that is in MO2's list, with its start button, also
  for a generated plugin whose tool MO2 names. "You": getting what a mod needs, judging shared files, settings
  files of other mods that name the plugin, a tool that is not in MO2's list, and playing. Without the switch
  the steps ModTrap would carry out stay the owner's, and say so.
- Shown in a browser on the invented list: the labels, the indicator turning to "open", and a demaster put in
  place through the question, with MO2 "closed" by it. On the owner's PC the listing of programs and the
  request to close are unproven until the next session.

### 59. The first real demaster: four big files done, one left; "Demaster Selected" now goes in one go; a row click shows a mod and what is tied to it

`2026-11-21` · FACT · `#xedit #page #safety #process` · refs: MT4, MT17, MT18, DESIGN§6.3, DESIGN§6.5, DESIGN§8, XE01§16, WHY§46, WHY§53, WHY§55, WHY§56, WHY§58

- FACT (the owner's pictures; no session file came with them): the first demaster of real plugins went through.
  Four of the five big files were demastered into ModTrap's own mod, among them the generated file with its five
  script attachments put back and the two files with conditions taken out; the twelve patches were deactivated,
  the patch mod disabled, the load order clean, MO2 closed by ModTrap's question. XE01§16's open points (a script
  attachment, a condition) held on real plugins, as far as ModTrap's own checks of the new files tell.
- FACT: the fifth file was left as it was, so the mod stayed enabled; the page said only "still to do by you",
  with no reason, and the next step offered a second demaster that led to "a dry run is needed first".
- LIKELY (to be confirmed by the session file): that file holds 44 copies of the mod's own records, dialogue
  topics and their lines. Taking a topic out takes its lines with it; the action for a line that had already
  gone was then refused as "the record is not in this plugin", and one refusal keeps a dependant out (DESIGN§6.3).
  The other file with such a copy had a single one.
- METHOD: an action to take a whole record out, where the record is no longer there, now counts as done: the
  wanted end is reached. A record that was never there is still caught, by the check after the actions that no
  record needs a trapped plugin and by ModTrap's own check of the new file's masters. The scripts changed, so
  the probe must pass again (WHY§53).
- The owner: "Why doesn't ModTrap just completes the whole demaster process? why not just do it all in one go
  until the user needs to do something?" DECIDED (the method is ModTrap's, MT17): "Demaster Selected" now runs
  the dry run itself when there is none of the modlist as it is now, shows the plan, and after the one "Go
  ahead" does everything: the xEdit run, the checks, and putting the plugins in place (asking only if MO2 is
  open). The separate "Put them in place" stays for a run that was not carried through. MT4's "a dry run that
  lists every change, then a confirmation" stands: the plan is that confirmation. What is left afterwards says
  why, and has a button that takes it up again the same way.
- The owner: "allow mods to be clicked on for information without being selected … make only the tick square
  … select a mod for demaster. When clicking on a mod's row … highlight other mods that are related to it in
  demaster sense". METHOD: a click on a row shows the mod above the list (its plugins, how many plugins in which
  other mods need it, which mods it needs) and marks those mods' rows, with a switch to show only them; only the
  box ticks. The mod list the server sends names, for each mod, the mods that need it and the mods it needs.
- Shown in a browser on the invented list: the row click, the marks, the box, and a demaster from a bare tick to
  "in place" with one "Go ahead".
- Later, 2026-11-21: the session file showed the LIKELY above to be wrong. No action was refused; the topics'
  empty groups kept the master in use (XE01§17, WHY§61). The change made here stays, and is needed by the fix.

### 60. A button that waits for the probe says so in plain sight and runs it; "Demaster Selected" takes the probe into its one go

`2026-11-21` · METHOD · `#page #safety #process` · refs: DESIGN§9, MT17, WHY§47, WHY§53, WHY§57, WHY§59

- The owner, with pictures: "Demaster selected is greyed out, I had to click on demaster selected in steps page".
  The scripts had changed (WHY§59), so the probe had to pass again (WHY§53). The Selection tab's button was
  greyed out and said why only when the mouse rested on it; the Steps tab's button was not greyed out and showed
  a plan whose "Go ahead" the server would then have refused.
- METHOD: nothing waits for the probe in silence. "Demaster Selected", from either tab, is no longer greyed
  out for it: the line beside it says in words that the probe runs first and why, and a press asks once ("Run
  the probe now?"), runs it, and when it has passed goes on by itself to the dry run and the plan (WHY§59's one
  go, with the probe in front). A probe that fails stops the chain and says where; nothing real is touched.
  "Add it for me" keeps waiting for the probe, with the reason in plain sight and a "Run the probe now" button
  beside it.
- The gate itself is unchanged and stays on the server: no real change without a probe passed for this
  modlist, this xEdit and these scripts.
- Shown in a browser on the invented list with the gate on: one press, one question, the probe's seven steps,
  the dry run, the plan, "Go ahead", in place.

### 61. Why one big file was kept back: a topic's group outlives the topic; and the page's own question box, steps that follow the work, a dry run that says when it is out of date

`2026-11-21` · FACT · `#xedit #page #steps #safety #process` · refs: MT5, MT17, MT18, DESIGN§6.3, DESIGN§6.5, DESIGN§14, XE01§17, WHY§53, WHY§56, WHY§59, WHY§60

- FACT (the owner's session file): the whole chain of WHY§60 ran on the real list: the probe passed, the dry run
  ran by itself, four big files were demastered and put in place, the patches switched off. The fifth file was
  kept back again, and a second go on it alone ended with "0 plugins" and an offer to put nothing in place.
- FACT: the cause is in xEdit, not in a refusal (XE01§17): a dialogue topic's group of lines stays when the topic
  is taken out, and its label keeps the trapped plugin in use. WHY§59's reading was wrong and is marked so.
- METHOD: the changing script takes a record's group of children out before the record (XE01§17). The scripts
  changed, so the probe runs again first (WHY§53, WHY§60); the probe's own plugins hold no record with such a
  group, so this is first run on the real file, under the same checks as before: the plugin is written only if
  the master is gone, and ModTrap checks the new file itself.
- METHOD: a second demaster of the same mod no longer stumbles over the first one's mod: its own mod gets the
  next free name ("… (2)"); no mod is ever overwritten (MT5). A run in which nothing could be demastered and
  nothing is to be switched off stops with the reason, and offers nothing to put in place.
- The owner: "the pop up messages are just standard browser style, can you make them look same as the ModTrap
  UI?" METHOD: every question the page asks (closing MO2, running the probe, Revert, finishing or renaming a
  session, quitting, stopping) is ModTrap's own box in the page's look, with Yes and No, Enter and Escape.
- The owner: "double check the the steps and dry run get updated as the process completes its tasks". FACT, as
  found by driving the page: (1) once a demaster had disabled the mod, the page unticked it, because a disabled
  mod provides no plugin, and the Steps tab went blank just when its last steps mattered; (2) while a demaster
  ran, its steps still read "to do"; (3) after it, the Dry run tab showed the earlier dry run as if current;
  (4) the Dry run tab's pane of lines held every dry run of the day, the oldest on top.
  METHOD: (1) a ticked mod stays ticked when it is disabled; (2) the steps a demaster carries out read "going"
  while it runs, and "done" when the modlist has been read again; (3) a dry run made before the modlist was last
  read says so, and "Demaster Selected" makes a fresh one by itself; (4) the pane holds the lines of the latest
  run and opens at their end.
- Shown in a browser on the invented list: the question box, the steps going and then done with the mod still
  ticked, and the out-of-date note.

### 62. New plugins that wait to be put in place are dropped once the modlist has moved on; Revert clears what the page still showed

`2026-11-21` · METHOD · `#page #safety #process` · refs: DESIGN§6.5, DESIGN§8, MT14, WHY§46, WHY§59, WHY§61

- The owner, with a picture: "when I press revert for a demaster, the ModTrap won't update right away, it will
  keep showing the next step to 'put them in place'."
- FACT: the card belonged to a later demaster that was still waiting to be put in place (the one with nothing to
  put, WHY§61). Revert took back the earlier one and cleared only that one's card; the waiting one stayed, and
  offered plugins made for a modlist that no longer was.
- METHOD: new plugins that wait were made for the modlist as it was read then. They are dropped, with a line in
  the log, when the modlist is read again for any reason (a Revert, an add, a Rescan, a change in MO2), and on
  "Not now", which the waiting card now has. Nothing of them was ever in the modlist; their files stay in the
  job's folder. A stopped demaster's card can be closed. In the one go of WHY§59 nothing waits: it is put in
  place at once.
- Shown in a browser on the invented list: after Revert the page shows "reverted" and nothing else within a
  quarter of a second.

### 63. The first whole demaster of a real mod is in place; which tools must run again is now decided by what their output holds

`2026-11-21` · FACT · `#xedit #tools #steps #process` · refs: MT17, MT18, DESIGN§13, DESIGN§14, TL01§7, TL01§8, XE01§17, WHY§2, WHY§52, WHY§55, WHY§61

- FACT (the owner's session file): one press, the probe, the dry run, the plan, "Go ahead": all five big files
  were demastered and verified, among them the one kept back before (its six topics' groups went with them,
  XE01§17, and sixteen lines had gone with their topics), the twelve patches deactivated, the patch mod and the
  mod itself disabled, the load order clean. MT17's first part holds for this mod; whether the game plays well
  is the owner's to see.
- The owner: "is it now supposed to suggest to run synthesis as well? what logic determines that? can you check
  if all tools are considered (is pandora run suggestion just a placeholder to run it regerdless of good
  practice?)".
- FACT: the behaviour tool was listed for a reason the step states: the mod carries four animation and
  behaviour files, which that tool builds from. The patcher was not listed, although the guide runs it (WHY§2),
  because its three plugins do not name the mod as a master and ModTrap looked no further. That was a gap.
- METHOD (TL01§8): tools are now judged by evidence, in three ways: the records a tool's plugin shares with the
  mod and its patches; the files a tool's output mod holds at the mod's own paths; the kinds of file the mod
  carries that a tool feeds on. A tool that must run is a step with the reason and the counts; the tools that
  need no run are named in a step of their own with why. Nothing is suggested from habit, and nothing is left
  out in silence.
- Ruled out: suggesting every patcher after every demaster (true to the guide's habit, but it costs the owner
  long runs that the evidence can spare); loading the tools' plugins into the dry run's xEdit to compare records
  there (their masters would pull most of a large list in; reading record headers with ModTrap's own reader
  takes about half a second for a million records).
- Unproven: the counts on the owner's list; they show at the owner's next look at the Steps tab.
- Later, 2026-11-21: counting shared records proved too coarse on the owner's list, and showing two verdicts for
  one tool was wrong. Both are replaced in WHY§64 (TL01§9).

### 64. Sharing a record is not carrying the mod's change: one verdict for each tool, from what the mod really changes, with the evidence to unfold

`2026-11-21` · METHOD · `#tools #steps #page #process` · refs: MT17, MT18, DESIGN§13, DESIGN§14, TL01§8, TL01§9, WHY§52, WHY§63

- The owner, with a picture of WHY§63's steps on the real list: three tools told to run again and the same three
  named as needing no run; "So which one is it? also, what is the logic for suggesting those tools in the first
  place? Does ModTrap know what each tool actually is for and what they need to do? How does it know they are
  really needed for demastering a mod? when evidence is shown, I would like to see details (could be a
  fold/unfold type field within each step)".
- FACT: both faults were ModTrap's. The two lists came from judging a tool by records and by files apart and
  showing both. And the record count of WHY§63 took "holds the same record" for "was built from the mod", which
  on a dialogue mod sent the owner towards running the distant-view generator.
- METHOD (TL01§9): a record counts only if the mod changes it, by comparing its fields with what the mod's
  author had before them; a tool's plugin counts only if it holds one of those changed fields. Each tool gets
  one verdict from all the evidence, with a sentence on what the tool is for, the reasons for, the reasons
  against, and the records and files themselves in a fold.
- Ruled out: knowing each tool by a list of record types it "cares about" (the tools change, and a list is a
  guess the owner cannot check); comparing in xEdit, which knows what every field means (its load of the tools'
  plugins and all their masters would turn a three-minute dry run into a long one); always advising a run "to be
  safe" (it costs the owner hours and teaches them to ignore the step).
- The limit is said where it applies: the comparison is of bytes, and can miss a change in a field that points
  at another record when the two plugins' master lists differ (TL01§9). A tool whose plugin could not be read to
  the end is still advised, and says that this is why.
- Shown in a browser on invented plugins: a tool whose plugin carries the mod's value is to run, one that holds
  the record with another value is named beside it as speaking against, one that holds only what the mod does
  not change is cleared; the folds open to the records. The owner's list shows what it gives there.
- Later, 2026-11-21: the comparison of bytes in this entry raised a false alarm on the owner's list, and the
  limit as worded here was wrong. Corrected in WHY§65 (TL01§10).

### 65. The demaster is in place a second time; the tool evidence compared bytes where plugins number their masters differently, and raised a false alarm

`2026-11-21` · FACT · `#tools #steps #xedit #process` · refs: MT17, DESIGN§6.3, DESIGN§14, XE02, TL01§9, TL01§10, WHY§61, WHY§63, WHY§64

- FACT (the owner's session file): the whole demaster went through again from a clean start, in one go: five
  plugins demastered and verified, twelve patches deactivated, two mods disabled, the check clean. Four of the
  five lost exactly the one master. The fifth, the editor-made one, went from 113 masters to 54: xEdit's Clean
  Masters takes off every master the plugin does not use, not only the trapped one (the guide's own step does
  the same). A master nothing in the plugin uses does nothing in the game; the owner is told.
- The owner, with a picture of the tool steps: "dyndolod is still there with evidence, I am surpised SDA has
  anything to do with occulsions and the like. can you double check the logic?"
- FACT: the logic was wrong, in the way TL01§10 describes. Comparing bytes across plugins that number their
  masters differently made untouched fields look changed and unrelated copies look carried. WHY§64's stated
  limit ("can miss, does not invent") was false.
- METHOD: fields are compared with each plugin's numbering in mind (TL01§10), with tests that rebuild the false
  alarm on invented plugins: an untouched patch no longer counts, a real change written in other bytes is found,
  and the mod's own bytes pointing elsewhere are not taken for it. What each verdict rests on is also written
  into the log, so a saved session shows it. For a tool whose need depends on what kind of thing changed (the
  distant-view generator: only what is seen from afar), the step now says that.
- Not claimed: that the comparison is exact. It is made without knowing what each field means (TL01§10's limit).
  If a verdict still looks wrong to the owner, the log now holds the records to settle it with.
- Later, 2026-11-21: the false alarm stayed. Its cause lay deeper than the numbering of masters: see WHY§66.

### 66. Reading bytes cannot say what a mod changes: xEdit says it in the dry run, and tools are judged from that or not at all

`2026-11-21` · DECIDED · `#tools #steps #xedit #process` · refs: MT17, DESIGN§6.2, DESIGN§14, XE01§14, XE01§18, TL01§9, TL01§10, TL01§11, WHY§63, WHY§64, WHY§65

- The owner, with the evidence unfolded: "no changes, dyndolod is still required in steps".
- FACT: the evidence named, for worldspaces, the field that holds the name, and for a cell its list of regions.
  The mod changes neither. The game's files keep names in strings files and the mod as text; the list is the
  same list in another order (XE01§18). Three attempts at reading bytes (WHY§63, WHY§64, WHY§65) each met
  another way in which the same value is written differently. There will be more.
- DECIDED (the method is ModTrap's, MT17): ModTrap's own reader no longer says what a mod changes. xEdit says it,
  in the dry run that is made anyway, for the mod's plugins and the patches made for it (XE01§18). ModTrap then
  only looks for those changed fields in the plugins that tools made (TL01§11). A tool for which no dry run has
  told this is not judged by records at all, and the page says so and how to get it judged; it is never told to
  run on a guess.
- Ruled out: teaching ModTrap's reader the meaning of each field (xEdit's definitions are its own work and under
  its own licence, and are thousands of lines); loading the tools' plugins into xEdit as well, to ask both
  questions there (their masters are most of a large list).
- The scripts changed, so the probe runs again before real work; its dry run exercises the new lines.
- For the owner's list as it stands (the mod demastered before this version): the tools wait. The page tells
  the owner so, and that the modlist's own guide for this mod says to run the behaviour tool and the patcher, and
  not the distant-view generator.
- Later, 2026-11-21: the owner's next try showed the same step. The new script had run, but under the old
  program: see WHY§67. This entry's method is still unproven on the owner's list.

### 67. "No change" was an update without a restart: ModTrap now notices it; MO2 is closed without a question inside a confirmed demaster; finished jobs go to the History tab and can be cleared

`2026-11-21` · DECIDED · `#process #page #mo2 #history` · refs: MT9, MT15, MT17, DESIGN§5, DESIGN§7, DESIGN§12, WHY§58, WHY§60, WHY§66

- The owner: "can you add job history tab to history page? these jobs that are done should be archived in a
  separate page, and also add a button to clear session job history. currently the selection page just keeps
  stacking jobs, including reverted ones, forever. No change, still wants dyndolod to run in steps. I also noticed
  that at some point ModTrap keeps asking MO2 to be closed down, if it's part of demaster process, then let it
  close or open MO2 automatically."
- FACT (the owner's session file): the dry run's report carries the new script's header, yet its job file has none
  of the lines the new program writes for the script, and the log has the earlier version's wording for tools.
  The files had been replaced while ModTrap was running: the scripts and the page are read from disk at each use,
  the program once, at the start. So a new script ran under an old program, and WHY§66 was not tried at all.
- DECIDED: ModTrap takes a mark of its own files (names, sizes, times) when it starts and compares it when asked
  to start a run, a demaster, an add, a revert or a tool. If the files have changed it starts nothing, and the
  page says so at the top with a Quit button. Reading goes on. A mismatch of versions is worse than a pause.
- FACT: a run through MO2 starts a MO2 of ModTrap's own, which takes some seconds to leave after xEdit is closed
  (WHY§58). The page saw it open and asked the owner whether to close it, each time.
- DECIDED: ModTrap remembers that the open MO2 is the one it started. The page then asks nothing, and the server
  waits for it to go: it closes MO2's end-of-run message, and after five seconds asks it to close as a click on
  its X does. Never by force.
- DECIDED: in the one go (WHY§60) the plan the owner confirms now says that MO2 is closed for the last step if
  it is open. So that step closes an open MO2 of this modlist without a second question, the same gentle way.
  Outside the one go (Revert, an add, "Put them in place" pressed by hand) the question stays: there no plan
  said so. ModTrap does not open MO2 again by itself: nothing it does needs MO2 open, and the page has the button.
- DECIDED: the History tab lists the jobs of the session, demasters and adds, newest first, each with its state;
  one still in place has its Revert there. The Selection tab and the Add mods tab show only what is in hand and
  the jobs still in place, with a line that leads to the History tab for the rest.
- DECIDED: "Clear job history" takes the jobs that no longer stand (reverted, or stopped) off the list. A job in
  place is never cleared, since its Revert needs it. Nothing is deleted: the job folders, their safe folders and
  the record of every change (MT15) stay on disk; a list of hidden names is all that is written.
- Checked: tests for the mark, the waiting, and the clearing; in a browser on an invented list, with MO2 shown as
  open: the one go asked nothing, the job was listed, reverted from the History tab and cleared.
- Not checked: any of it on the owner's PC.
- Later, 2026-11-21: the mark of names, sizes and times is replaced by a mark of contents, and the notice names
  the versions: see WHY§68.

### 68. A version that rises with every change, a mark of contents, and one ModTrap at a time: a new start takes over from one still running

`2026-11-21` · DECIDED · `#process #version #server #page` · refs: MT22, MT11, MT17, MT20, DESIGN§2, DESIGN§17, WHY§9, WHY§67

- The owner, on the update that ran without a restart (WHY§67): "that's an issue, we need to start involving
  version updates to prevent that error".
- FACT: the version had stood at one placeholder since the first day. A session file therefore could not tell
  which ModTrap had made it, and neither the owner nor the page could tell an old ModTrap from a new one.
- FACT (read in ModTrap's own start-up code): a ModTrap started while another still runs found its port taken
  and quietly took another. Two pages were then open, of two versions, and nothing said which was which. The
  mark of WHY§67 does not catch this when the update was unpacked into a new folder: the older one's files do
  not change.
- FACT: the mark of WHY§67 used the files' dates. Unpacking the same version again changes the dates, and would
  have raised the notice for nothing.
- DECIDED (MT22): the version is `0.3.n`, in `modtrap/version.json`, with a mark of the contents of ModTrap's
  files (line endings left out; the record itself and Python's own caches left out). `tools/bump.py` raises the
  number once for each commit and writes the mark; a test fails while the files and the mark disagree. So every
  state of the files that is pushed has a number of its own, and the owner is told that number with each change.
- DECIDED: the version is shown on the page, in the window ModTrap runs in, at the start of its log, in every
  saved session file, and in the log line of each job that is started.
- DECIDED: the notice of WHY§67 now compares contents, and names both versions: the one running and the one on
  disk. Where the files a ModTrap started from are not those its version was written for (an update unpacked
  over an older folder leaves the older one's files; a copy cut short; a file edited), the page says "files
  differ" beside the version and the log says why. It is a warning, not a refusal: the tests cannot know which
  file is at fault.
- DECIDED: one ModTrap at a time. A running ModTrap leaves a note in its own work folder: its port, its version
  and a key made for that start. A new start asks the running one, with that key, to save its session and
  close, waits for its port, and takes its place; the owner's session comes back as after any Quit (MT20). One
  that is in the middle of a job is left alone: the new start says so, opens the running one's page and ends.
- METHOD: the key is not the page's token, and the request is not open to a page. It must carry the key, the
  right Host, no Origin and no body; a browser cannot send it without the key, and the key is in a folder no
  web page can read. It opens that one request only. A program of the same user on the same PC could read it,
  as it could already end ModTrap's process.
- METHOD: a page left open from the ModTrap that closed is refused by the new one (its token is of another
  start). It now loads itself again, once, and is then the new one's page.
- REJECTED for now: ModTrap fetching its own updates. It would be the first time ModTrap reaches the network,
  and the first time it runs code it has just downloaded. MT11 leaves an updater for later; it is the owner's
  to ask for.
- LIMIT: a ModTrap older than 0.3.1 leaves no note and cannot be asked. Going from such a one to this version,
  it has to be quit by hand once.
- Checked: tests for the mark, the bump, the refusals of the request and the three outcomes of a take-over; two
  real starts one after the other on one port here: the first saved and ended, the second took the port.
- Not checked: on the owner's PC, where a port is released under Windows' rules.

### 69. The other tools checked: a change is not a stake, and a behaviour tool reads lists and patch folders, not animation files

`2026-11-21` · DECIDED · `#tools #steps #xedit #process` · refs: MT17, DESIGN§13, DESIGN§14, XE01§18, XE01§19, TL01§8, TL01§11, TL01§12, WHY§66, WHY§67

- The owner, on version 0.3.1 with a new dry run: "dyndolod isn't requested anymore. Can you double check other
  tools are properly requested by reliable logic?"
- FACT (the session file): WHY§66's method worked on the owner's list. The distant-view generator is cleared,
  with its evidence: six records the mod changes, none with the mod's values.
- FACT: the patcher was asked to run for one record: a worldspace's table of heights, which the mod "changes"
  and one of the patcher's plugins holds the same. xEdit also reported cells changed in their place on the
  grid. A dialogue mod has no business with either. LIKELY these are what the game's editor writes into every
  plugin it saves that holds such a record (XE01§19); then many plugins say the same, and the patcher's copy
  proves nothing about this mod.
- FACT: the behaviour tool was asked because the mod carries four files that ModTrap files under animations.
  Read in that tool's source (TL01§12): it takes a mod's animations in through a list or a patch folder only.
  Whether those four files include a list, the session file does not say.
- DECIDED (the method is ModTrap's, MT17): tools are judged by records from **stakes**, told by xEdit
  (XE01§19): parts where the leaving plugins have the last word and the next in line says something else, or
  where they say what no plugin that stays says. A dry run made before this version tells no stakes; its
  tools wait for a new one, as in WHY§66.
- DECIDED: a behaviour tool is asked for a list or a patch folder it reads, or where its output names one of
  the mod's animation folders; plain animation files clear it, with the files shown.
- LOOKED AT, left as it is: the generators that work on files are judged by files of their output at the mod's
  paths, and by the mod carrying files for distant view (TL01§8). The second is a wide net (it also catches
  ready-made files that are nobody's input); nothing on the owner's list speaks against it yet, and the source
  of that tool is not open to read.
- Not judged, as before: what is packed in archives; tools MO2 has no output mod for.
- For the owner's mod the modlist's guide says: behaviour tool and patcher. ModTrap now decides both by
  evidence and shows it; where it differs from the guide, the evidence is there to judge.
- Checked: tests on invented plugins and folders. Not checked: the new lines on a real xEdit (the probe runs
  them first), and the search of a real behaviour output.

### 70. A Process tab: the demaster as linked boxes with their tasks, coloured as they are carried out, told by the jobs themselves

`2026-11-21` · DECIDED · `#page #process #steps` · refs: MT17, DESIGN§4, DESIGN§14, DESIGN§18, WHY§60, WHY§61

- The owner: "can you add job process tab that would show the steps as smaller boxes interlinked and within each
  step box show list of tasks to complete to finish. This new page will show the process in real time (also add
  text colors, white normally, amber ongoing, green complete, red error, etc.)."
- FACT: until now the page knew a job only as a word (working, verified, installed) and the log's lines. What a
  job was doing at a given moment was in the log alone.
- DECIDED: each job tells a board what its tasks are when it starts, and marks each as it goes: waiting, going,
  done, failed, skipped, or waiting for the owner. For the part xEdit does, the marks come from the lines
  ModTrap's own scripts write while they work (which dependant is read, which plugin is written), so the page
  follows xEdit without asking it anything. The board decides nothing; a job that never marks it works as before.
- DECIDED: the stages are the ones the one go runs (WHY§60): probe, dry run, plan, demaster on copies, put in
  place; and one more box made from the Steps tab for what follows (tools, the owner's checks). Colours as the
  owner asked, with purple for what waits for the owner and grey for what is not needed.
- DECIDED: the probe's inner dry run and change write to a board of their own: on the page the probe is one box
  with its seven steps, and the real dry run's box is not painted by a test on invented plugins.
- REJECTED: working the stages out on the page from the log's text. The log's wording is for reading and
  changes; a mark is a contract.
- Checked: tests for the board and for the stages through a whole demaster on the stand-in; in a browser, the
  one go from probe to in place, the box going amber while xEdit runs, and all green at the end.
- Not checked: on the owner's PC; a failed run's red box was checked by test only, not by eye.

### 71. The one go stopped where it should have waited (the modlist was being read after the probe); and the owner's buttons go into the process boxes

`2026-11-21` · DECIDED · `#page #process #steps` · refs: MT17, DESIGN§18, WHY§60, WHY§61, WHY§70

- The owner, on version 0.3.3: "it gut stuck at this point, there is no go ahead button anywhere. Can you also
  add pop up buttons to process boxes? when something needs to be pressed by user, make it appear on the step box
  at the right task (and also add navigation button to the button's origin page so the user can check)."
- FACT (the session file's log): the probe passed; ModTrap began reading the modlist again, as it does after
  every probe; one second later the page asked for the dry run and was told "the modlist is being read; try
  again in a moment". The one go took that as a failure and ended. No dry run was made, so no plan and no
  "Go ahead". On an invented list the reading takes no time, which is why the stand-in never showed it; on
  3,751 plugins it takes long enough.
- FACT: the Process tab showed the dry run as done and the plan as waiting for the owner, from a dry run kept
  from before the modlist was read again. That dry run does not count for a demaster (WHY§61); the box said
  what was not so, and pointed at a button that could not come.
- DECIDED: the one go waits. After the probe, and wherever the server says the modlist is being read, it holds
  its place and goes on by itself once the modlist is read. It gives up only on a real refusal.
- DECIDED: a dry run of the modlist as it was is shown as to come, with a line saying that an earlier one is
  kept and a new one is made. A demaster in hand or in place keeps its own dry run shown as done; Revert and
  "Not now" set the later boxes back.
- DECIDED: what the owner can press appears in the box, at its task: start, the plan's "Go ahead" with what the
  plan amounts to, "Put them in place", a tool's start, the tick for what only the owner can judge. Each has a
  way to its own tab beside it. The buttons call the same functions as the ones on those tabs: one behaviour,
  two places. "Demaster Selected" is also at the top of the tab. Started from here, the one go no longer jumps
  to other tabs.
- Checked: in a browser on the stand-in with reading slowed to two and a half seconds: the whole demaster
  driven from the boxes alone, the wait after the probe, Revert setting the boxes back. Tests for the stages
  after a Revert and with an earlier dry run.
- Not checked: on the owner's PC.

### 72. The demaster went through on 0.3.4; xEdit's "Access violation" box came with ModTrap's early press of OK; the patcher is cleared by stakes; the behaviour tool wants the graph file with the list

`2026-11-21` · FACT · `#xedit #tools #steps #process` · refs: MT17, XE01§13, XE01§19, XE01§20, TL01§12, WHY§69, WHY§71

- The owner, on version 0.3.4: "ended up with an error, seems memory related? And it doesn't need synthesis
  anymore?"
- FACT (the session file): the one go ran from the Process tab to the end. Dry run, plan, five plugins changed
  and verified, put in place, the modlist clean. WHY§71's waiting worked.
- FACT: the error box was xEdit's own, at its start, and the run went on after it (XE01§20). It is a fault
  inside the program, not a lack of memory. LIKELY cause: ModTrap's press of OK arrived while the window was
  still being set up. DECIDED: the press waits until the window has stood ready for two and a half seconds.
- FACT: the stakes of XE01§19 worked on a real xEdit. Of 528 records the mod and its patches change, they have
  a stake in 502. The worldspace's table of heights is no longer among them, as WHY§69 expected: other plugins
  say the same. The patcher's three plugins hold two records with a stake and none of the mod's values. So the
  patcher is cleared by evidence. The modlist's guide says to run it; ModTrap shows why it sees no need, and the
  owner may run it all the same: a patcher run does no harm.
- FACT: the behaviour tool is still asked, for one animation list; against it, no file of its output names the
  mod's animation folder. By its source the tool takes a list in only with its graph file (TL01§12). DECIDED:
  a list counts for this tool only where that file is in the modlist; otherwise the tool is cleared with both
  findings shown.
- Not checked: the new press on the owner's PC; whether the search of the behaviour output finds names in a
  real output that has them (it has found none so far, in an output that may well have none).

### 73. "Are you 100% sure?" No: the patcher was cleared by comparing bytes it writes in its own form. A patcher is now cleared only where it can be ruled out

`2026-11-21` · DECIDED · `#tools #steps #process` · refs: MT17, DESIGN§13, DESIGN§14, XE01§19, TL01§11, TL01§13, WHY§69, WHY§72

- The owner, on version 0.3.5: "again, still no synthesis to run post demaster, are you 100% sure that's not
  needed?"
- The answer is no, and WHY§72 said more than the evidence held. TL01§11 already named the limit ("a tool whose
  plugin writes it otherwise would be missed"); I cleared the patcher across that limit.
- FACT: one of the patcher's plugins holds two records in which the mod has a stake. ModTrap found "none of the
  mod's values" there by bytes. The patcher writes records through a library of its own, in its own form, and
  works values out from the winning version (TL01§13). Neither fact lets other bytes mean "not from the mod".
- DECIDED: three kinds of finding, said as such. Proof: the mod's value is in the tool's plugin: run again.
  Cannot be ruled out: a patcher with its own writer holds a record the mod has a stake in: "run again, to be
  sure", with the reason; a patcher's run is short and changes only its own output. Cleared: no record with a
  stake, or, for a tool built on xEdit, such records without the mod's values.
- DECIDED: the step that lists cleared tools says that it is evidence and not proof, and why: only a run of the
  tool shows for certain what it would make without the mod.
- For the owner's mod this gives: patcher, to be sure; behaviour tool, by its list and graph file. That is what
  the modlist's guide says too. The distant-view generator stays cleared: it is built on xEdit, and its copies
  hold none of the mod's values.
- REJECTED: asking for every tool whenever any doubt is left. For a generator that takes hours that would make
  the steps useless; its evidence is of the kind that can be compared.
- Not built: xEdit comparing the tools' copies by meaning (TL01§13), which could clear a patcher with evidence.

### 74. What each tool made, from its own files: the patchers behind each output, what was left out, and every tool-made plugin's records by kind

`2026-11-22` · DECIDED · `#tools #steps #page` · refs: MT17, MT23, DESIGN§13, DESIGN§14, TL01§13, TL01§14, WHY§73

- The owner: "but synthesis is not just about terrain, it also patches other things. and other patch files
  result from it. is there a better way we can implement to check what exactly synthesis and each tool patches
  for the modlist?"
- FACT: until now ModTrap knew a tool's plugin only as "made by that tool", and looked in it for the mod's
  values. It did not know what the plugin is for. The framework's three outputs were three names.
- FACT (TL01§14): the framework writes down, beside its program, which patchers make each output, in order,
  which are on, and which plugins an output leaves out. And any plugin says what it works on by the kinds of
  record it holds, which ModTrap's own reader counts from headers.
- DECIDED: both are read. The Tools tab has a table of everything the modlist's tools made: plugin, tool, the
  patchers behind it, records by kind. A tool's step says for each of its plugins what it is made of, in how
  many records of its kinds the mod has a stake, and how many of those it holds.
- DECIDED: two new findings count. A plugin made with the mod's plugin left out is cleared, with the list as
  proof. A patcher's own settings that name the mod's plugin are a reason to run again.
- The verdict of WHY§73 stands: a patcher's plugin that holds a record in which the mod has a stake cannot be
  ruled out. This entry makes the reason visible; it does not make it certain.
- OPEN (MT23): the exact answer for records needs xEdit to compare, by meaning, each tool's copy with the mod's
  version and with the next in line, with the whole load order loaded: minutes on a large list. Asked of the
  owner as a separate check.
- Checked: tests on invented plugins and an invented settings file; the table in a browser. Not checked: the
  owner's real settings file.

### 75. The demaster ran clean on 0.3.7; what is proven on one mod only, and what "any mod" still needs

`2026-11-22` · FACT · `#process #method` · refs: MT4, MT17, MT21, DESIGN§5, DESIGN§9, WHY§72, WHY§74

- The owner: "does that look okay so far? I just wanted to ask that whether you have been tuning the tool to be
  able to demaster or add any mod (not just SDA)?"
- FACT (the session file, version 0.3.7): dry run of 17 dependants in five minutes, 12 patches switched off, 5
  plugins changed and verified, in place, the load order clean. No error box this time; OK was pressed half a
  minute after xEdit's start (WHY§72).
- FACT: the saved session's summary file was not valid JSON: a tool's own arguments hold a quoted path, and
  cleaning the written text took the backslash of the escaped quote for part of the path. It is now cleaned
  value by value.
- FACT, on "any mod": nothing in ModTrap names this mod. Its rules are about kinds of dependence (MT4), its
  tests use invented plugins, and the probe proves the machinery on any PC. But every fault found on a real
  modlist so far was found through this one mod and its 17 dependants. The record shapes they hold (dialogue,
  quests, cells, lists, conditions, a material's parent) are the shapes proven. Others are not yet met on a
  real list: a navmesh that leans on the mod, a required single field (a character's race, an outfit), script
  properties, a mod with several plugins, a mod that is a master of hundreds.
- FACT: what is not recognised is not changed. Such a part is "needs you", its plugin is left as it is, and the
  mod stays enabled (DESIGN§5). So an unmet shape costs a demaster that stops short, not a broken plugin.
- FACT: adding mods (MT21) is built and tested on stand-ins and has not been run on the owner's list.
- METHOD proposed to the owner: dry runs only, of a few mods of other kinds (they change nothing), and their
  session files; what falls under "needs you" there says what to build next.
- KNOWN GAP: a mod that others lean on without naming it as a master (a script that asks for its plugin by
  name) is found only in settings files today, not in compiled scripts.

### 76. A second mod: the tool check looked at part of the load order, the Process tab hid what was left to the owner, and a script property is the first new shape

`2026-11-22` · DECIDED · `#tools #steps #page #xedit #process` · refs: MT4, MT17, MT23, DESIGN§5, DESIGN§18, XE01§19, XE01§21, TL01§11, WHY§69, WHY§75

- The owner, demastering two mods at once on version 0.3.8: "It's asking for dyndolod in steps again, and the
  steps page doesn't keep up with the process anymore."
- FACT (the distant-view generator): its plugins hold one cell where the second mod "has a stake" in the cell's
  place on the grid, with the same bytes as the mod's. By WHY§69 that is proof. But the stake was told by an xEdit
  that had loaded 524 plugins of 3,751: the mods, what depends on them, and their masters. "The last word" and
  "no plugin that stays says the same" were true of those 524 only. Any plugin outside them may win that cell.
- DECIDED: before "the tool holds the mod's value" counts, ModTrap looks through the whole load order for that
  record with its own reader, quickly (only groups that can hold that kind of record): the leaving plugin must
  be the last of the plugins no tool made that holds it, and the last plugin that stays must say something else
  in that field. Otherwise the finding is dropped, with the plugin named. If the look is cut short, the finding
  stands.
- FACT: this narrows only. A stake that is not one can still be counted where bytes differ for the same value;
  the error is on the side of asking. The exact answer for every record is MT23's.
- FACT (the pages): the Steps tab was right and the Process tab was not saying it. One plugin could not be
  demastered, so the mods stayed enabled by design; the Process tab showed every box done.
- DECIDED: putting in place ends with a task "Left to you" when something still needs the mod; the box then
  waits for the owner, with ways to the Steps and Dry run tabs; the last box lists the open steps of ModTrap's
  own part too.
- FACT (the plugin left over): a settings plugin's own quest carries a script with two properties that are
  records of the mod. Nothing else of the mod is in it. This is the first shape not met with the first mod.
- DECIDED (MT4, dated note): a script property that points at the mod is an entry to take out, with the plan
  saying so (XE01§21). Not in the probe; the run's own checks hold it.
- FACT: one of the patcher's plugins now names the second mod as a master (it holds a copy of a record of the
  mod's own). ModTrap demastered it like any dependant; the patcher's run will make it anew, and ModTrap's copy,
  which has the higher priority, is then the stale one. ModTrap says so when it sees the original remade.
- Not checked: any of this on the owner's PC.

### 77. Another modlist's MO2, settings, tabs in sections; and the cell stakes were three unused bytes: every stake a tool holds is now checked against the whole load order

`2026-11-22` · DECIDED · `#mo2 #page #tools #steps #process` · refs: MT4, MT17, MT23, DESIGN§4, DESIGN§19, MO01§9, TL01§13, TL01§15, XE01§19, WHY§71, WHY§73, WHY§76

- The owner, on version 0.3.9, with both mods demastered and disabled (the script properties went through): "I
  already had an MO2 process open for another modlist … this caused ModTrap to fail. Instead of freaking out
  like this, it should recognize that there is another MO2 process ongoing and pause the process (redo the
  current task once resumed if that's safer), and ask the user to close down the MO2 process first"; "can you
  also add a setting to carry on with the demaster process after dry run segment if everything looks fine. Is
  there a setting page actually?"; "can the rows be made into categories"; "It's still asking for dyndolod
  run, is that right?"
- FACT (the owner's PC): with a MO2 of another modlist open, ModTrap's command went to that MO2, which said the
  command was for another profile. xEdit never started; the dry run failed half a minute later with "xEdit
  closed before the script finished". ModTrap already knew that another modlist's MO2 was running and did
  nothing with it.
- DECIDED: nothing is started through MO2 while another modlist's MO2 is open. The server refuses the start
  before anything is begun; the one go holds its place, says what it waits for on the Process and Selection
  tabs, and takes the same step again by itself once that MO2 is gone. A step refused before it began is safe
  to take again as it is.
- DECIDED: a Settings tab, with five switches (DESIGN§19). "Go ahead without asking" goes on only when the plan
  leaves nothing to the owner; anything left to them, and it asks as before. The safeguards are not settings.
- DECIDED: tabs in two rows, by section. Nothing was merged yet. Proposed to the owner: the Dry run tab into
  the Process tab (its report as the dry run box's detail), Health into Plugins (a filter), and Steps and
  Process to stay two views of one thing until one proves enough.
- FACT (the distant-view generator, again): no, it was not right. The stake was in a cell's grid field, whose
  last three bytes mean nothing and differ from plugin to plugin (TL01§15). WHY§76's look through the whole
  load order confirmed the finding because it compared those bytes too.
- DECIDED: that field is compared by what it means. And every record a tool's plugin holds in which the mod
  "has a stake" is now checked against the whole load order, not only those where the tool has the mod's value:
  the leaving plugin must have the last word among all plugins no tool made, and only fields in which the
  plugin next in line says something else remain its stake. What falls away is listed in the evidence with the
  reason.
- FACT: this takes the ground from under WHY§73's "to be sure" where the only stakes were such cells. And it
  adds a ground WHY§73 lacked: a plugin a tool made that named the mod as a master (ModTrap's demastered copy of
  it, in ModTrap's own mod) is proof that the tool worked from the mod's records: "run again", without "to be
  sure", and the step says that ModTrap's copy then hides the tool's new one.
- Not checked: any of it on the owner's PC. The reading script still counts unused bytes; changing it would ask
  for the probe again, and is left for the next change to the scripts.

### 78. The generator asked for once more: my own slip in WHY§77's check; the evidence now shows the values; and a leftover could be put right by ModTrap instead of a run

`2026-11-22` · FACT · `#tools #steps #process` · refs: MT17, MT24, DESIGN§14, TL01§15, WHY§77

- The owner, on version 0.3.10: "still asking for dyndolod. why is that? Should we implement something else?"
- FACT (the session file): WHY§77's look through the whole load order worked for five of six cells: each has a
  later plugin that stays and has the last word, named in the evidence. One cell stayed, in the grid field,
  "the same" in three of the generator's plugins.
- FACT (my slip): the look compared only the fields that differ, by bytes, from the mod's own master. With the
  unused bytes left out (TL01§15) that field no longer differed from the master, so it was not compared with
  the plugin next in line at all; and then it was counted from xEdit's telling all the same. The one case the
  change was made for was the one it passed over.
- DECIDED: the look compares every field xEdit named. A test holds the case: a field that differs in nothing
  that counts is no stake, whatever holds the same bytes.
- DECIDED: where a tool's plugin holds the mod's value, the evidence shows the three values side by side: the
  mod's, the tool's plugin's, and the next in line's with its plugin; a cell's grid field in words. They go into
  the log too. A finding can then be judged by eye, by the owner and from a saved session.
- OPEN (MT24): if such a finding is ever real, a run of a generator that takes hours is a heavy answer to one
  field in one record. ModTrap could put the field right itself, in a copy of the tool's plugin, as it does for
  a patch (MT4, case C). Asked of the owner.
- Not checked: on the owner's PC. Whether the last cell falls away depends on its flags byte, which the next
  session file will show.

### 79. Where the false alarms came from (ModTrap, not the files), the fix at the source, and how ModTrap would put a leftover right itself

`2026-11-22` · FACT · `#tools #xedit #process` · refs: MT4, MT24, XE01§19, XE01§22, TL01§13, TL01§15, WHY§66, WHY§69, WHY§76, WHY§77, WHY§78

- The owner: "so you are saying that ModTrap could do those fixes itself without having to run patching tools?
  How would that work in details? Would ModTrap alter existing patch files made by those tools or generate new
  ones? Either way, we have to ensure the ModTrap does not get any more false alarms in the first place (or do
  those actually comes from those bad fields themselves? are they false or badly written? are thug bugs?)"
- FACT: none of the false alarms came from a faulty mod or tool. In order: bytes read without knowing what a
  field means (WHY§63 to WHY§66); values many plugins share (WHY§69); unused bytes taken for content
  (TL01§15); a conclusion about the whole load order drawn from the part xEdit had loaded (WHY§76); and a slip
  of mine (WHY§78). Unused bytes are how the game's file format is: every plugin has them.
- DECIDED: the unused bytes are left out where the comparison is made, in the scripts (XE01§22), not only
  sorted out afterwards for one field.
- METHOD told to the owner (MT24, not built): ModTrap never alters a tool's file. It would copy the tool's
  plugin into its own mod, which has the highest priority, set the one field in the copy to what the plugin next
  in line says, check the copy, and put it in place with the rest of the demaster; Revert takes it out. It can
  do this for a value a tool copied into a plugin. It cannot for what a tool builds from the mod's files
  (models, textures, behaviour files), nor for what a patcher works out anew.
- KNOWN: the copy hides the tool's next output of that plugin until it is taken out of ModTrap's mod; ModTrap
  warns of it and does not yet retire its copy by itself.

### 80. The demaster ran clean on 0.3.12; ModTrap retires its own copy once a tool has made the plugin anew; every tool can be started from the Tools tab

`2026-11-22` · DECIDED · `#tools #process #page #safety` · refs: MT9, MT14, MT15, MT17, DESIGN§11, DESIGN§13, DESIGN§19, WHY§56, WHY§77, WHY§79

- The owner, on version 0.3.12: "no dyndolod asked this time, looks promising." And on ModTrap's copy hiding a
  plugin a tool makes anew: "Build that next. Could the user run tools as well from ModTrap? basically start up
  MO2 interface and run the tools from its environment. Can that be built?"
- FACT (the session file): the probe passed with the changed scripts; two mods demastered with seven plugins,
  one of them through script properties; the generator cleared, each of six cells with its reason, the last one
  "the plugin next in line says the same there as the mod". XE01§22 and WHY§77 hold on a real list.
- FACT: a demastered copy of a tool's plugin lies in ModTrap's mod, above the original. After the tool's next
  run the original is new and whole, and ModTrap's copy hides it. ModTrap said so (WHY§56) and left the rest to
  the owner.
- DECIDED: ModTrap retires its copy. Only when the original, as it is now, names no ticked plugin as a master
  and all its masters are active: a tool run while the mod was still enabled makes an original that still
  needs it, and then the copy must stay. The copy is moved into the job's folder (MT9: nothing of the owner's is
  deleted, and this is ModTrap's own file), the history says so (MT15), MO2 must be closed, and the plugin keeps
  its place in the load order under the mod that now provides it.
- DECIDED: after a tool's run that ModTrap started, this happens by itself (a setting, on). Otherwise the
  Selection tab says which copies can go and has the button; a copy that must stay says why.
- FACT (the owner's second question): starting a tool through MO2, with the modlist's files in place, was built
  (DESIGN§16.8) but only offered inside a step. DECIDED: the Tools tab has a start button for every executable of
  MO2's list, and one to open MO2 itself.
- Checked: tests on the stand-in (refused when nothing was made anew, when the new original still needs the mod,
  when MO2 is open; done otherwise). Not checked: on the owner's PC, with a real tool's run.

### 81. The tools in a row, and a Revert that always ends where the demaster began: remade plugins and kept tool output come back, and a job in place is never cleared

`2026-11-22` · DECIDED · `#safety #tools #process #page` · refs: MT9, MT14, MT15, MT17, DESIGN§11, DESIGN§12, DESIGN§19, TL01§12, WHY§60, WHY§67, WHY§80

- The owner: "can you also add setting for the tool process to carry on automatically, like the process after dry
  run? so the user could run the whole demaster process in one go. I would like to ensure that a strong and
  stable revert option always remains and can be used at any stage of the demaster. The user should always have
  the revert back to pre-demaster state option (never deleted from job history)."
- DECIDED (the setting, off by default): once the demaster is in place, each tool its steps name is started
  through MO2 as soon as the one before it has closed, and its step is ticked off when it has written output. A
  tool that closes without writing anything ends the row. The owner still works each tool: ModTrap starts a
  tool's program, it does not press the tool's own buttons.
- FACT (read in the behaviour tool's source, `Pandora.Skyrim/CLI/CommandLineParser.cs:24-30` at commit `1f26bbc`):
  that tool has switches to run and to close by itself. Not used yet: each tool would need its own, and a run
  nobody watches needs its outcome checked. A later step, on the owner's word.
- FACT (Revert as it was): it put the three lists back (whole, or line by line once MO2 had rewritten them) and
  removed ModTrap's own mod. It did not touch a plugin a tool had made anew since, nor anything else a tool had
  written after the demaster. After tools had run, "Revert" was not "as it was before".
- DECIDED: Revert ends where the demaster began. (1) Every plugin ModTrap copied into the safe folder that is no
  longer that original is put back from the copy. (2) Before ModTrap starts a tool while a demaster is in
  place, it keeps a copy of what the tool is about to write over: the files of its output mod and the plugins it
  made; once for each tool, so that the copy is of the state before the demaster's tools. Revert puts those
  back and takes out what the run added. (3) What is there at the time of the Revert is set aside in the job's
  folder first: nothing made since is lost either.
- LIMIT, said where it applies: an output of more than 5,000 files or one gibibyte is not kept (the
  distant-view generator's is of that size); the log says so before the tool starts, and Revert names the tool
  as one to run again. A tool the owner starts outside ModTrap is not seen, so nothing of it is kept.
- FACT: a job in place cannot be cleared from the job history (WHY§67): only jobs that no longer stand can. Its
  Revert is on the History tab and the Selection tab for as long as the session exists. A test holds it.
- Checked: a test in which a tool ran, a copy was retired and MO2 rewrote the lists, and every file ends as it
  began, dates included; in a browser, one press through the tool's run, then Revert from the History tab.
- Not checked: on the owner's PC.

### 82. The row of tools could only begin at the moment of putting in place: a button starts it whenever a demaster is in place

`2026-11-22` · DECIDED · `#page #tools #process` · refs: DESIGN§18, DESIGN§19, WHY§81

- The owner, with the session file of 0.3.14 and a picture of the settings: "yeah I ticked these on after the
  demaster process got to the tools."
- FACT (the session file): the demaster ran clean and was put in place; the settings were switched on two
  minutes later; no tool was started; the owner reverted, whole, to 3,575 mods and no problem. WHY§81's row of
  tools began only in the moment the demaster was put in place, with the setting already on. Switched on after
  that, it did nothing, and nothing said so.
- DECIDED: the last box of the Process tab offers "Start the tools one after another" at the first tool still to
  run, whenever a demaster is in place and a tool waits; while the row runs it says so and has
  "Stop the row". Switching the setting on with a demaster already in place says where that button is.
- FACT: with "go ahead without asking" on, 17 seconds lay between the dry run's end and the demaster's start,
  against one second the time before. The log cannot say whether the owner pressed. LIKELY otherwise: a browser
  slows the timers of a tab that is not in view, and the one go is driven by the page. Noted; if it shows again,
  the one go belongs on the server.

### 83. A Revert after MO2 had run enabled the mods but left their plugins out of the load order: Revert now puts the lines back where they stood, and an earlier such Revert can be finished

`2026-11-22` · FACT · `#safety #revert #mo2` · refs: DESIGN§11, MO01§10, WHY§47, WHY§81

- The owner, with the session file of 0.3.15: "Then I reverted the demaster job (did that work well?)". It did
  not, in one respect.
- FACT (the session file). After the demaster, two tools were started through MO2. After the first, the modlist
  read 3,741 plugins where it had read 3,751: MO2, run by its `run` command, had written its two plugin lists
  without the ten plugins of the three mods the demaster had disabled (MO01§10; MO01§9 had shown only that such a
  MO2 leaves lists alone when it has nothing to drop). The Revert then found the lists changed, went line by line
  (WHY§47), enabled the three mods, and could activate none of their plugins: they were in no list any more. The
  modlist read 3,575 mods, 3,751 plugins and 12 problems. MO2, opened next, would have added the ten at the end
  of the load order, after the plugins that need them.
- FACT (the same file). The files were right: ModTrap's seven copies removed, the first tool's output as kept
  before its run (of the 33 files it had written, 30 were byte for byte what they had been; three were put back
  or set aside), the second tool's untouched, since it had written nothing.
- DECIDED. The line-by-line Revert also puts back, in both plugin lists, the plugins of the mods the demaster
  had disabled and the ones it had deactivated: each directly before the plugin that followed it in the safe
  folder's copy of the load order, active or not as it was there (`demaster.lists_gap`, `lists_back`). The
  anchor is the next plugin that itself stays where it is. A plugin still in its place is only activated.
- DECIDED. A Revert already made without this can be finished: the newest reverted demaster says which plugins
  are not back at their places (not listed, or listed after the plugin they stood before, as MO2 adds them), stays
  on the job list whatever is cleared, and has "Put them back in place". Only the two plugin lists change; the
  history gets a "revert finished" line. A second whole Revert of the same demaster is refused.
- Checked: tests in which the lists lose the disabled mod's plugins as MO2 drops them, and the three lists end
  byte for byte as before the demaster, by Revert and by the finishing press (with the plugins unlisted, and added
  at the end); in a browser, both.
- Not checked: on the owner's PC.
- **Later (2026-11-22, the session file of 0.3.16).** Checked on the owner's PC: the finishing press put ten
  plugins back and the modlist read no problem where it had read 12; a new demaster and its Revert, with a tool
  run through MO2 in between, ended at 3,751 plugins and no problem, ten plugins back at their places (WHY§87).

### 84. A tool's run ends when the tool has gone: MO2's leftover message is closed; a tool with switches of its own runs and closes by itself; the patcher framework's compiler crash is its own, under MO2

`2026-11-22` · DECIDED · `#tools #mo2 #process` · refs: MT25, MO01§9, MO01§10, TL01§16, DESIGN§16.8, DESIGN§19, WHY§54

- The owner: "Would it be possible for Modtrap to not only start but close the tools after they confirm their
  part is done? After I ran Pandora and closed it manually (once it was done with its job), this error popped up
  again and kept ModTrap thinking that Pandora is still ongoing."
- FACT. The message is MO2's own "Failed to run", raised by one of the modlist's MO2 plugins after every run
  started by command (MO01§9). A dry run closes it (WHY§54); a tool's run waited for MO2 to end, and MO2 waited
  for the message.
- DECIDED. Once the tool was seen running and has been gone for the grace time while MO2 still stands, ModTrap
  closes a message of MO2's (a window of MO2's program whose caption is exactly MO2's message caption), as a
  click on its X does, and the run ends when MO2 has gone, or thirty seconds after the message was closed. With
  no such message to close, MO2 is waited for as before: it may be waiting for something of the tool's.
- DECIDED (MT25). A tool is closed by ModTrap never: what "done" looks like in a tool's window is not something
  ModTrap can know for every tool. A tool that has switches of its own for it is started with them, added to the
  arguments MO2 has for it (MO2's `-a` replaces those, MO01§10). The switches are data, tool by tool, each read in
  the tool's source: so far the behaviour engine, which then builds for the mods ticked in it when it was last
  used and closes (TL01§16). A setting, on by default, turns it off. The outcome is still told from the output
  files: a tool that wrote nothing ends the row of tools (WHY§81).
- FACT (TL01§16). The patcher framework's "Blocking Error", `csc.exe exited with code -1073741819`, on every
  patcher: the compiler crashed (an access violation) while the framework built its patchers inside MO2. The
  framework's own source names this exact failure and gives MO2's virtual file system and antivirus software as
  the usual causes; it has a mode for building the patchers outside MO2 first. ModTrap starts the framework as
  MO2's Run button does. LIKELY, then: the same happens from MO2's own Run button whenever the patchers have to
  be built anew; not established on the owner's PC.
- The framework's window takes no switch to run its patchers and close (only which profile to open, TL01§16);
  its separate command-line program does, and would have to be set up in MO2 as a tool of its own. Not done.
- Checked: tests (the switches added to a tool's own arguments, kept out when the setting is off or when they are
  already there; a MO2 that stays at a message until it is closed; a MO2 that waits with no message is waited
  for); in a browser, the row of tools with a tool started by its switches.
- Not checked: on the owner's PC.

### 85. The log panes keep to the latest line until the owner scrolls away, and take it up again at the bottom

`2026-11-22` · DECIDED · `#page` · refs: DESIGN§4

- The owner: "ensure that the logs show latest entry by default unless user has scrolled manually away (then once
  they scroll back to latest entry at the bottom, resume to keep showing latest entry, also after each launch show
  latest log entry at the bottom)".
- FACT. The page asked the pane whether it stood at its end each time lines came. A pane whose tab is not shown
  has no size and cannot be scrolled, so lines that came meanwhile left the Log tab at its top when it was opened.
- DECIDED. Whether a pane follows is kept by the page, changed only by the owner's own scrolling while the pane
  is shown: away from the end stops it, back at the end resumes it. When its tab opens, a pane that follows goes
  to its last line, and one that does not goes back to where it was left. A new dry run's pane follows again.
  Both panes: the log, and the dry run's lines.
- Checked in a browser: at the start, with lines coming, scrolled away, another tab and back, scrolled down
  again, and lines that came while the tab was not shown.
- **Later (2026-11-22).** The owner, on 0.3.16: the log "isn't showing automatically the latest entry at the
  bottom of terminal log after a ModTrap launch". Not reproduced in a browser here; made independent of the
  order in which things are shown (WHY§87).

### 86. The steps foretell nothing: before the dry run they say only that it comes first; a tool-made plugin that names the mod is proof for its tool before the demaster as after

`2026-11-22` · DECIDED · `#steps #tools` · refs: MT26, DESIGN§14, WHY§63, WHY§77, TL01§7

- The owner: "before I started the new demaster process, in the steps it was stated that Synthesis run is not
  required amongst other tools, but as the process went on, later it said it was needed. Can you implement a
  stronger and more deterministic tool that will not predict but only state facts that are actually true. if
  steps needs a dry run first then it should state that and only after show what the steps would look like."
- FACT (the session file of 0.3.15). One of the patcher framework's plugins named the mod as a master. Before the
  demaster the tool check passed over it ("a dependant: the demaster itself deals with it") and judged the tool
  by its other plugins: no new run. After the demaster the plugin was a copy in ModTrap's own mod, which is proof
  (WHY§77): run again. Two answers to one question, from the same facts.
- DECIDED. A plugin a tool made that names the mod as a master is proof for that tool at once: the tool made it
  from the mod's own records, and only the tool's run makes it as it is without the mod, whatever the demaster
  does with a copy meanwhile. Said before the demaster and after it in the same words' meaning.
- DECIDED (MT26). While a dry run is still to be made, or is going, the steps are two: the dry run, and a step
  that says the rest follows from it and names the plugins it will read. Nothing about patches, tools or the
  mod's own disabling is stated until xEdit has read the plugins. With ModTrap allowed to change the modlist, the
  dry run's step carries "Demaster Selected", which makes the dry run itself.
- What stays a judgement, and is worded as one: a tool cleared "by evidence, not proof" (WHY§73). That wording
  is kept; it states what was looked at and found.
- Checked: tests (the two steps before and during the dry run; the tool's step from the dry run on, with the
  plugin demastered in the plan or not); in a browser, before the dry run and after the demaster.

### 87. 0.3.16 on the owner's PC: both Reverts ended clean; ticks go with the demaster they were made for; the panes take their place whenever they come into view; what the patcher framework's profile is, and what is known when it writes nothing

`2026-11-22` · FACT · `#revert #page #tools` · refs: WHY§83, WHY§84, WHY§85, TL01§16, TL01§17, DESIGN§14, DESIGN§18

- FACT (the session file of 0.3.16). The Revert left unfinished by 0.3.15 was finished (WHY§83). A new one go ran
  clean to "in place"; the row of tools then started the patcher framework and not the behaviour engine; the
  framework wrote nothing; MO2's message after it was closed by ModTrap and the run ended; Revert ended clean.
- FACT. The behaviour engine was passed over because its step was still ticked "I have done this" from the
  demaster before, which had been reverted. A tick was kept by the ticked mods and the step alone.
- DECIDED. A tick on a tool's step or on the play test belongs to the demaster in place: when that demaster is
  reverted, or another is put in place, those ticks go. The page keeps the job the ticks were made for.
- The owner: the behaviour engine, started by ModTrap, did its work and closed by itself (WHY§84, on their PC).
- The log pane (WHY§85's Later line). DECIDED: a pane takes its place again whenever it comes into view or
  changes size, whatever made it so (its tab, the page shown after a start), and only a move up by the owner
  stops the following; a log read afresh follows again. LIKELY cause, not established: the Log tab was put back
  as the session's last tab before the page's body was in view, and no line came afterwards to move it.
- The owner: "Synthesis opens default JoJ profile, not the custom one I made to be modified. it seems it's not
  being seen by synthesis at all." FACT (TL01§14): the name shown there is a profile of the framework's own, kept
  in its settings file; it names the game's Data folder and holds the groups of patchers. Which mods and load
  order it reads is MO2's doing. FACT (the session file): ModTrap started it with MO2's profile of the session,
  and it was that profile's plugin lists MO2 wrote during the run (WHY§83).
- FACT (the owner's picture). This time the patchers failed earlier than before: "Access is denied" when the
  framework started the build program, where the time before the compiler had crashed (TL01§16). Both lie before
  any load order is read. FACT (TL01§17): MO2 hands a tool the same whether started by its Run button or by its
  `run` command, as far as handles go. Not established: whether the framework builds its patchers from MO2's own
  Run button on this PC; asked of the owner twice.
- DECIDED. What is known about a tool that closes without output is data and is said as a hint on the tool's card
  and in the log, for the framework: its own answer to a failed build inside MO2 (build outside MO2 once). The
  card also names the MO2 profile the tool was started with.
- Checked: tests (the hint and the profile); in a browser, the ticks gone after Revert, the panes with a long
  restored log, opened early, late, and put back as the last tab.

### 88. A tool's own log is read after the run ModTrap started and kept with the session; the patcher framework's failures on the owner's PC were two things, neither ModTrap's

`2026-11-22` · DECIDED · `#tools #page #session` · refs: TL01§16, TL01§17, TL01§18, WHY§84, WHY§87, DESIGN§16.8

- The owner, with four of the patcher framework's own logs: "does ModTrap check these? Does ModTrap check any tool
  logs? Does ModTrap collect any tool logs for sessions?" and: the framework shows its blocking errors when
  started from MO2 itself, and when started from its own folder.
- FACT. It did none of the three. A tool's run was judged by its output files alone; a session file held ModTrap's
  log and xEdit's logs of ModTrap's own runs.
- FACT (the four logs, TL01§18). Two different failures. Inside MO2, with the library versions the profile had
  at first: the compiler crashing, and Windows refusing to start the build program. Then, in the framework's
  second session of the day, the profile's library versions were raised to the newest; from then on every
  patcher failed in every kind of start, MO2 or not, because this framework builds for a .NET version those
  libraries no longer support. Started outside MO2, that was the only failure left: no crash, no refusal.
- So: started by MO2's own Run button it fails as it does from ModTrap (WHY§87's open point, settled), and the
  failure outside MO2 is the versions, not the building. LIKELY: with the first versions back, the patchers build
  outside MO2. Not established: that a start inside MO2 then finds them built and does not build again.
- DECIDED. Where a tool keeps a log of its own, ModTrap reads the one written during the run it started, after
  the tool has closed. Which tools, where, and which lines mean what is data (`tools.json`, "log"): a pattern
  and the sentence said when it shows, counted or listed, nothing inferred (`toollog`). What it finds is on the
  tool's card and in ModTrap's log. A copy of the tool's log goes into the session's folder and from there into
  a saved session file (the newest six of each tool), cleaned there like every text.
- So far only the patcher framework has signs: its version, the library versions of its profile and a change of
  them, the .NET version it built for, a library that does not fit, the compiler's crash, a refused start, a
  blocking error. Other tools' logs are not read: their lines have not been looked up, and none is guessed.
- Checked: the reader on the owner's four logs (each read as told above); a test with an invented log (the one
  of this run read and kept, an older one left alone, the session file holding it); the card in a browser.
- Not checked: on the owner's PC.

### 89. Before the patcher framework starts, library versions its own log proves unfit are set to the pair the program was built with; nothing is set without that proof

`2026-11-22` · DECIDED · `#tools #safety #settings` · refs: MT27, TL01§18, TL01§19, WHY§88, DESIGN§19, MT14, MT15

- The owner: "can you make ModTrap to check the patches what versions are required and automatically set them to
  that version?"
- What "required" can mean, as facts: a patcher's own project names the library versions it was written
  against (old ones, for most); the framework's profile overrides them all with one pair, by the modlist's
  choice; and the program can only build for versions it knows a .NET version for (TL01§18). The last is the
  one that failed, and the only one with a certain answer: the pair of versions the program itself was built
  with, which every log of it states at its top (TL01§19).
- REJECTED: comparing version numbers ("newer than the program's own means unfit"). A later patch version of a
  library may well fit; ModTrap would be setting things right that were not wrong.
- DECIDED. Three facts must agree before anything is set: the program's newest log names a library version as
  not fitting (its build error for that); the profile in the settings file is still set to exactly that
  version, or to "Latest"; and the same log states the program's own pair. Then, before ModTrap starts the
  program, the profile is set to that pair, chosen by hand, in the settings file: four fields of that profile,
  nothing else. A profile set to follow each patcher's own versions is left alone, and so are a patcher's own
  overrides.
- Safety (MT14, MT15): the program must not be running; a copy of the settings file as it was goes into the
  session's folder first and is compared with what was read; the file is written whole and swapped in, with its
  byte order mark and line ends as before; the change is in the History with what was and what is. A setting,
  on by default at the owner's word, turns the setting-right off; ModTrap then only says what it found.
- Not part of a demaster, so Revert does not undo it: it puts right the tool's own setup. The kept copy is the
  way back.
- What this does not solve: building inside MO2 (the compiler's crash, TL01§16), which showed with the fitting
  versions too.
- Checked: the reading on the owner's four logs (own pair and unfit pair as told in TL01§18); tests (set once
  and not again; only the four fields change; left alone when the log's errors name other versions, when there
  is no such error, when the log does not state the program's pair, when the setting is off; "Latest"; a number
  kept a number).
- Not checked: on the owner's PC; against a settings file of the owner's (none was at hand: the field names are
  from the source).
- **Later (2026-11-22, the session file of 0.3.21).** Checked on the owner's PC: the profile was set from
  0.54.4 and 0.36.6 to 0.53.1 and 0.35.5 before the start, with the copy kept (WHY§93).

### 90. The patcher framework's patchers are built outside MO2 before it is started through MO2, when its log shows them unbuilt; what makes that safe

`2026-11-22` · DECIDED · `#tools #safety #mo2` · refs: MT28, TL01§16, TL01§18, TL01§20, WHY§88, WHY§89, MT25, DESIGN§19

- The owner: "can ModTrap also build the patchers outside MO2 automatically? is that safe?"
- FACT (TL01§20). The framework builds a patcher when it is opened, in a folder of its own under the user's
  temporary folder, not in the modlist. A build that succeeds leaves a record file beside it; a build about to be
  made anew has its record deleted first. Asked again, the framework takes the build as done when the record
  matches (the patcher's commit, the two library versions, the program's version, the built program still
  there). MO2 plays no part in that. Its log names each patcher's record file when it sets out to build.
- FACT (TL01§18). On the owner's PC building failed inside MO2 and, outside MO2, failed only for the versions.
- DECIDED. Before ModTrap starts the framework through MO2: if the framework's newest log names patcher builds
  whose record file is not there, ModTrap opens the program by itself (its program file, no arguments, no MO2),
  and waits. Done: the new log names builds, every record named is there, the log has stood still for ten
  seconds, and as many are named as the settings file has patchers switched on (or two minutes have passed
  without more). Failed: build errors in the log and thirty seconds of stillness; or the window closed early;
  or forty-five minutes. Then the window is asked to close, as a click on its X does, and only when the program
  has gone and every patcher is built is it started through MO2. If the build failed outside MO2 too, no start
  through MO2 is made: it would fail the same way, and the tool's card says what the log holds.
- What makes it safe. Nothing in the program is pressed: no patcher runs, so nothing is written to the game's
  folder or to the modlist. What the open program writes is its own: its log, the builds in the temporary
  folder, and its settings file when it closes. The settings file is compared, by content, with how it was
  before; if it says anything else, the file as it was is put back. The program is never ended, only asked to
  close; one that stays is left to the owner. The one thing ModTrap cannot keep from happening is the owner
  pressing Run in that window: the card says to leave it alone.
- This is the one tool ModTrap closes (MT25 said none): here "done" is a fact on disk, and a window in which
  nothing was run has no work to lose.
- A setting, on by default, turns it off.
- Not established: that the builds succeed outside MO2 on the owner's PC with the fitting versions (LIKELY,
  WHY§88), and that version 0.35.5 words its log and keeps its records as the source read here does (its logs
  show the record's name and its deletion, as the source has them).
- Checked: the reading of the owner's four logs (13 records named in each, the errors of each); tests (built
  outside, then started through MO2, the settings file put back after the program had changed it, nothing
  opened the next time; a build that fails outside ends there with no start through MO2; the setting off).
- Not checked: on the owner's PC.
- **Later (2026-11-22, the session file of 0.3.21).** Checked on the owner's PC: 12 of 13 patchers were not
  built; opened outside MO2, the program built all 13 in 37 seconds and closed when asked; started through MO2 it
  took every one as built ("Short circuiting … because meta matched", thirteen times) (WHY§93).

### 91. A tool's step is done by ModTrap's own record of the tool's run since the demaster in place, not by a tick; ticks stay only where no record can exist

`2026-11-22` · DECIDED · `#steps #tools #page` · refs: MT29, WHY§87, WHY§86, DESIGN§14, DESIGN§18

- The owner, with a picture of 0.3.20 before a new demaster, the behaviour engine's step ticked "I have done
  this": "it still says that pandora run is complete from previous session, that should be rerun after each
  demaster. since we already made these tool processes automatic, maybe we should remove the manual override, it
  just introduces more error."
- FACT. WHY§87 took ticks away on a Revert or a new demaster, but only from the moment the page first kept which
  demaster its ticks were for: a tick from before stayed until the next demaster was put in place. More to the
  point, a tick is the owner's word, and the steps are to state facts (MT26).
- DECIDED. When a tool that ModTrap started has closed with its output written, ModTrap notes the run with the
  demaster that is in place (`tools-run.json` in that demaster's folder) and in the History. A tool's step is
  done exactly when such a note exists for one of the tool's entries in MO2's list. No demaster in place: no
  note. A Revert, or a new demaster, therefore asks for every tool again, by construction. The step has no tick
  box, and the row of tools goes by the steps' own state.
- Ticks stay only where no record of ModTrap's can exist: the play test, the settings files to look at, a tool
  that is not in MO2's list (ModTrap cannot start it), and every tool when ModTrap was started without leave to
  change anything (it starts none then). The page drops play-test and tool ticks whenever the demaster in place
  is another than the one they were made for, also when it never kept which that was.
- Not counted: a run the owner makes from MO2 itself. ModTrap does not see it; the step stays to do until the
  tool is started from ModTrap. Telling such a run from the tool's output files (written after the demaster was
  put in place) would be a fact too; not built.
- Checked: tests (the note kept only with a demaster in place and gone with its Revert; the step done from the
  note and each tool by its own; no tick for a tool ModTrap starts, a tick where it starts none); in a browser,
  one go with the row of tools, the step done without a tick, to do again after Revert.
- **Later (2026-11-22).** The owner on runs made outside ModTrap: not ModTrap's business (MT29's note). The
  "not built" above stays not built, by decision.

### 92. ModTrap tells its own reading and scanning; while any of it goes, nothing is started: greyed on the page, refused by the server, waited for by the one go

`2026-11-22` · DECIDED · `#page #process #safety` · refs: MT30, WHY§71, DESIGN§18, DESIGN§4

- The owner: "can you also make ModTrap monitor its own loading, checking, scanning processes so the tools and
  features are greyed until those are done? I noticed that after launch I can launch a demaster even though scans
  are still ongoing."
- FACT. Only the reading of the modlist held a start back. ModTrap's other work of its own went on unseen: the
  look into the ticked mods' folders and the tools' plugins for the steps (up to a minute or two on a large
  list), the reading of what the tools made, the reading of mods to add, the unpacking of a dropped archive.
  A demaster or a tool could be started in the middle of it.
- Why it matters beyond tidiness: those scans hold plugin files open for reading; a tool that makes such a
  plugin anew, or a Revert that puts one back, can be refused the file by Windows while it is held.
- DECIDED. The server tells what it is at (`working` in its state, each with words). While the list is not empty,
  or the modlist is being read: every start that changes the modlist or starts a program is refused, in words
  the one go waits on ("still at work"; "being read" as before): the dry run, the demaster's start and its
  putting in place, a tool, the probe, the record check, an add and its taking out, Revert and its finishing,
  retiring a copy by hand. ModTrap's own retiring after a tool's run is not held back.
- On the page: a chip in the header says "ModTrap is …" with what, or "ModTrap is ready"; the buttons that
  would start any of the above are greyed and do nothing but say why; they open again by themselves. The one go
  holds its place at each of its steps (before the dry run, at "Go ahead", before putting in place, before each
  tool) and takes the step again when ModTrap is ready.
- Which buttons: told by what they say, where the page makes its buttons, so that one made later is covered too.
- Checked: a test (a scan held open: told in the state, four kinds of start refused in those words, the same
  start accepted once it has finished); in a browser, with a scan slowed to five seconds: the chip, the greyed
  button, a press meanwhile doing nothing, and the whole one go through the tool with scans in between.

### 93. 0.3.21 on the owner's PC: versions set, patchers built outside MO2 and taken as built inside; the framework then waited for its run button, which ModTrap now presses, closing it on its log's word

`2026-11-22` · DECIDED · `#tools #mo2 #process` · refs: MT31, MT25, TL01§21, WHY§84, WHY§89, WHY§90, DESIGN§19

- The owner, with the session file of 0.3.21 and a picture of the framework's window without an error: "it done
  everything until synthesis needed to run (even started, ran and closed Pandora), but it did not start synthesis.
  It seems Synthesis was ready to run (no errors this time)."
- FACT (the session file; the framework's own log is in it now). The behaviour engine ran by its switches and
  closed. The framework's library versions were set right (WHY§89), its patchers built outside MO2 (WHY§90), and
  inside MO2 it passed over every build. One check of a patcher was refused by Windows at first ("Access is
  denied") and went through seconds later; the log then says "State returned success!" thirteen times and "No
  global error". From there it stood open for six and a half minutes, ready, until the owner closed it. Nothing
  was run, because nothing pressed its run button: ModTrap's words were "it is yours to work".
- FACT (TL01§21). The framework's window has no switch that runs the patchers; its separate command-line program
  has one, and is not part of what the framework's releases hand out. The run button has a name of its own in
  the window; the log says when a run begins and when it has come to its end.
- DECIDED (MT31). For a tool with no switch but a button, named as data: once the tool is open, ModTrap looks
  for that button every few seconds and presses it only when it can be pressed (a greyed button is the tool
  saying it is not ready). It then reads the tool's own log: when the line for a run's beginning is followed by
  the line for its end, ModTrap asks the window to close, as a click on its X does. Whether the run did its work
  is told as for every tool: by its output files, and by what its log holds.
- Nothing is guessed, so each doubt leaves the tool open and to the owner, with the reason said: no such button
  outside a list (the same name is on each group's own button, inside the list of groups); more than one; the
  button greyed for five minutes; a press after which the log shows no run begun, three times over; a run whose
  end the log never states (ModTrap does not close a tool because it has gone quiet: a long patcher is quiet).
- How the press is made: through Windows' interface for assistive tools, which reaches a button that has no
  window handle of its own (XE01§13's messages do not). It is spoken to from a helper program of ModTrap's own,
  started for one press: a mistake there ends the helper, not ModTrap. The helper checks what it reads against
  what the window system says (the window's process, that it is a window) before it presses, and otherwise
  presses nothing. LIKELY right, not yet seen working: it was written from the interface's published layout
  without a Windows PC to run it on.
- MT25 ("ModTrap closes no tool") is amended by this as by WHY§90: a window is closed where "done" is a fact the
  tool itself wrote down.
- The tool's log reading no longer calls a blocking error at the start of a session an error: some pass by
  themselves, as this one did. It says how often, and that the log's last lines tell how things stood.
- Checked: tests with stand-ins (greyed at first and not pressed, then pressed, the run's end read, the window
  asked to close, the output seen; a press that starts nothing made three times, then left to the owner and never
  closed; a run without an end in the log never closed; the setting off; the helper answering in one line and
  pressing nothing where it cannot).
- Not checked: the press itself, on a PC. The owner's next run is its first.
- **Later (2026-11-22, the session file of 0.3.23).** Checked on the owner's PC: 31 seconds after the start
  ModTrap pressed the run button, the run began at that second, the log stated its end 26 seconds later, and the
  window closed when asked. The helper worked as written (WHY§94 for what the run then did).

### 94. The press worked on the owner's PC; the framework's run compiles again and its compiler crashes inside MO2: the compiler goes on MO2's own list of programs it leaves alone, and a tool is started once more for a stated reason

`2026-11-22` · DECIDED · `#tools #mo2 #safety` · refs: MT32, MO01§11, TL01§22, WHY§90, WHY§93, MT14, MT15

- The owner, with the session file of 0.3.23: "Synthesis started patching this time, but it had errors and then
  closed on its own."
- FACT (the session file). The press, the reading of the run's end and the closing all happened as meant
  (WHY§93's Later line). The run itself failed in its first group, in 26 seconds, and wrote nothing.
- FACT (the framework's log, TL01§22). Version 0.35.5 builds every patcher again as the first thing of a run,
  whatever was built before; the builds made outside MO2 were only what let it show itself ready. For three
  patchers the build tool decided to compile, and the compiler ended with the access violation, as in every
  build inside MO2 on this PC and in none outside it.
- FACT (MO01§11). MO2 hooks each program a hooked program starts, unless its name is on a list MO2 keeps in its
  settings ("Executables Blacklist"): such a program is started and left alone.
- LIKELY. The compiler crashes because it is hooked: the crash shows only inside MO2, the framework's own source
  names MO2's virtual file system for it (TL01§16), and the compiler reads nothing of the modlist (its sources
  and libraries lie in the user's temporary and package folders), so it loses nothing by being left alone. Not
  established until a run with the compiler on the list goes through.
- DECIDED (MT32). When a tool's own newest log shows the compiler's crash (the line is data), ModTrap adds the
  compiler, by the two names it is started under, to MO2's list before it starts the tool: one value of one
  section of MO2's settings file, every other byte kept (`mo2fix`). Only with MO2 closed, since MO2 writes its
  settings when it closes; a copy of the file as it was goes into the session's folder first; the change is in
  the History; a setting, on by default, turns it off. Where the file names no list, MO2's default list is
  written with the addition, so nothing MO2 left alone before is hooked now.
- DECIDED. After a tool has closed without output, the row of tools starts it once more, at most twice, when
  there is a stated reason that is not a guess: something ModTrap sets right before a start is still to be set
  right (versions, builds, this list), which that very run has shown; or the tool's log shows Windows refusing
  it a start, of the kind seen to pass (WHY§93). Otherwise the row ends as before.
- Not solved by this, if it shows again: Windows refusing the framework itself the start of a program ("Access
  is denied") in the middle of a run. The framework's newer versions run a built patcher directly and try a
  refused start again (TL01§22); 0.35.5 does neither.
- Checked: tests (the value added with MO2 closed and not with it open, the file as it was kept, every other
  byte the same, the default list kept, only plain program names ever written; the reasons for one more start).
- Not checked: on the owner's PC, and whether the compiler then goes through.
- **Later (2026-11-22, the session file of 0.3.24).** Checked on the owner's PC: before the framework's start
  ModTrap added the compiler's two names to MO2's list; the run then went through all three groups in four and a
  half minutes with no crash and no refused start, and wrote its plugins. The LIKELY above held (WHY§95).

### 95. The whole demaster went through on the owner's PC; ModTrap reads the settings files that name the plugin line by line, and gives one account of its checks after the demaster

`2026-11-22` · DECIDED · `#steps #process #revert` · refs: MT33, TL01§23, WHY§91, WHY§94, DESIGN§14, DESIGN§18

- The owner, with the session file of 0.3.24 and a picture of the step "Look at the settings files that name the
  mod's plugin": "looks like the demaster went through fine, MO2 has no warnings. Could this step be done by
  ModTrap as well? Could we implement after demaster checks?"
- FACT (the session file). One press: dry run, demaster of seven plugins, put in place, the behaviour engine run
  and closed by its switches, the compiler put on MO2's list (WHY§94), the patcher framework's run button pressed,
  three groups run, the window closed on the log's word; the modlist read with no problem; MO2 opened.
- FACT (the same file). The framework wrote the plugin of its third group to the file that wins in MO2's virtual
  folder, which after a demaster is ModTrap's own copy in ModTrap's mod; the stale original in the tool's output
  mod stays hidden beneath it. The game gets the new one. LIKELY the same for any tool that writes a plugin
  ModTrap demastered.
- DECIDED (the step). ModTrap reads each such file line by line. A line that is switched off is passed over.
  For the two frameworks whose handling was read in their source (TL01§23), ModTrap says where the line names
  the plugin: as what the line gives or changes, as a condition for what it reaches, or as an exclusion. The
  first two mean nothing once the mod is gone, and nothing else changes: the step is then ModTrap's, done, with no
  tick. An exclusion is left to the owner, with the line shown, because what the framework then does with the
  line depends on its version (TL01§23); so is a file of any kind ModTrap has not read the handling of.
- REJECTED: clearing every file by the name of its framework. What one of them does with an exclusion whose
  plugin is gone is to drop the whole line, in the version read; that is a change to everything else the line
  reached, and the owner should see it.
- DECIDED (the checks). The steps carry one account of what ModTrap has checked after the demaster, each line a
  fact it read or recorded: the load order's masters, the mods disabled, each tool's run noted with its output
  (WHY§91), the settings files read. "Checked" only when all hold; what is still the owner's is named beside it.
  The Process tab's last box shows them, and its summary says "complete and checked" with what is left.
- DECIDED (Revert). A plugin in ModTrap's own mod that a tool has written anew was left where it was by Revert,
  as "changed by something else"; ModTrap's mod then stayed behind with that one file. It is now set aside in the
  job's folder, kept, and ModTrap's mod goes: the original in the tool's own mod is in force again.
- Not done: moving such a plugin from ModTrap's mod to the tool's output mod after the tool's run. The game does
  not care where it lies; a later Revert handles it.
- Checked: tests (where a line names the plugin, a switched-off line, a file of an unknown kind, the step ModTrap's
  or the owner's accordingly; the account of checks; Revert with a plugin rewritten in ModTrap's mod); in a
  browser, the one go ending "complete and checked" with the play test left.

### 96. A Revert made before 0.3.25 left ModTrap's own mod folder behind with a plugin a tool had rewritten: harmless, said on the job, tidied with one press

`2026-11-22` · FACT · `#revert #page` · refs: WHY§95, WHY§83, DESIGN§11

- The owner, after WHY§95: "well I already done a revert, is that bad?"
- FACT (the code of 0.3.24). That Revert went line by line. It took ModTrap's mod out of the mod list, enabled the
  mods again with their plugins at their places, put the tools' kept output back, and removed ModTrap's plugins
  that were still as ModTrap had made them. The one a tool had written anew in place was left, and its folder
  with it. The folder is in MO2's mods folder and in no list: the game does not get it; MO2 shows such a folder
  as a new mod, not enabled. The modlist is as it was before the demaster.
- What it costs: a next demaster of the same mods finds the name taken and calls its mod "… (2)".
- DECIDED. The newest reverted demaster says when plugins of ModTrap's own mod are still on disk, stays on the job
  list, and the press that finishes a Revert (WHY§83) also sets those plugins aside in the job's folder and takes
  the emptied folder away. Not if MO2 has the mod in its list again: then it is MO2's and the owner's.
- Checked: a test (left behind by the earlier way, said on the job, tidied by the press, the three lists untouched).
- **Later (2026-11-22, the session file of 0.3.26).** Checked on the owner's PC: the press set the one plugin
  aside and the folder was gone; the modlist read 3,575 mods and no problem; a new demaster then went through
  whole.

### 97. Steps say who really does them; what is left to the owner in a settings file is said with file, line and what to do; a third framework read; Revert with MO2 open

`2026-11-22` · DECIDED · `#steps #page #tools` · refs: MT33, MT31, TL01§23, TL01§24, WHY§93, WHY§95, DESIGN§14

- The owner, with pictures of the Steps and Process tabs of 0.3.26 after a whole demaster: "can you look at steps
  an ensure they are correctly labelled against our current code, some steps still state run by user that aren't.
  Also some settings still need to be looked up by user, why is that and what settings? can you make the ModTrap
  specify those settings or files that need to be looked up by user? A path, some ID, steps to look it up?" And:
  "when the demaster is finished, ModTrap opens MO2, is it safe to run revert whilst MO2 is open or should it be
  greyed out?"
- FACT. A tool's step was labelled "ModTrap starts it · you run it" whenever the tool was in MO2's list, as when
  that was true of every tool. Since WHY§84 and WHY§93 ModTrap runs two of them itself.
- DECIDED. A tool's step is labelled by what happens: "ModTrap" where the tool has switches or a button ModTrap
  works it by and the owner's setting allows it, with the way named in the step; "ModTrap starts it · you run it"
  where ModTrap can only start it; "You" where it is not in MO2's list.
- FACT. Two more wordings were behind the code. The step for the patcher framework still said ModTrap's copy
  would hide the tool's new plugin; the tool in fact writes the new plugin in that copy's place (WHY§95), and the
  step now says so, before the run and after it. And ModTrap's own mod was listed as an output mod of the texture
  tool, because that tool's demastered plugin lies in it; ModTrap's mod is no tool's output mod.
- Why one settings file was left: it belongs to a third framework, whose handling ModTrap had not read. Its
  source was found and read (TL01§24): its lines add forms to lists, and can be written to hold only while a
  plugin is active or only while it is not. All three ways are settled by the framework itself once the mod is
  gone; the last means the line now takes effect, as its author wrote it for a modlist without the mod, and the
  evidence says so.
- DECIDED. What is still left to the owner in such a file is said in full, not folded away: the file's whole
  path (with a button to copy it), each line by its number and text, what the line means, and what to do about
  it. Left are only exclusions in the two distributors' files (WHY§95) and files of kinds not read.
- Revert with MO2 open: safe as it is, and not greyed. The page asks MO2 to close before it sends the Revert (it
  asks the owner first, unless the setting says to close without asking), and the program refuses a Revert while
  MO2 is open. The buttons now say so.
- Checked: tests (the labels by setting and tool; the wording before and after the tool's run; the third
  framework's lines; the path, lines and advice for what is left); in a browser, the rendering and the whole flow.

### 98. A scanner of every settings file in force in the modlist: the winner of each path, read to its end, no time limit; what it could not read is named; the frameworks installed are listed

`2026-11-22` · DECIDED · `#steps #tools #page` · refs: MT34, MT35, MT33, TL01§23, TL01§24, TL01§25, WHY§95, WHY§97, DESIGN§14

- The owner: "can you also add a scanner for all tools and frameworks, so they can be read at the end of the
  demaster process reliably?"
- FACT, in ModTrap's own code before this. The search for settings files that name the plugin (WHY§95) stopped
  after 12 seconds or 30,000 files, read only the first 512 KB of a file, listed at most 2,000 files of a mod's
  `SKSE/Plugins` folder and did not say when that listing was cut. It looked at every enabled mod's copy of a
  file, also one that a mod of higher priority replaces, and not at Overwrite or the game's folder. On a list of
  some 3,500 mods the answer "nothing names the plugin" could therefore rest on a search that had not finished.
- DECIDED. One scanner (`census.py`) replaces that search. It lists the game's Data folder, every enabled mod
  from the lowest priority and Overwrite; of files with the same path the last one wins, as in the game. It looks
  through each mod's top folder and, to their end, the folders named in ModTrap's data (`mentions.json`,
  "places"). Every winning file is read to its end, piece by piece. No time limit.
- It keeps, for each file, which plugins of the modlist the file names, never its text. A file is read once and
  remembered by path, size and date, so the look after the demaster costs a listing.
- What could not be listed or read (a folder that failed, a file that would not open, a file past 64 MB) is
  counted and named. Then the look was not whole: the settings-files step is the owner's and names those files.
  Only a whole look lets ModTrap say "none names the mod's plugin".
- The step now exists also when no file names the plugin, and states what was looked through. Before, no step
  was shown then, which could not be told from "not looked".
- METHOD. Finding which of some 3,750 names a text holds: from each ".esp", ".esm" or ".esl" backwards, the
  longest known name that ends there. Names are filed by their last six bytes and under those by length. A first
  version filed them by the last bytes only and took 2 s for 20,000 lines, because very many names end alike
  ("… - Patch.esp"); with the lengths it takes 0.05 s. An invented list of 3,500 mods with 14,000 settings files
  is listed and read in about 2 s here. The time on the owner's list is written in the log and on the Tools tab.
- The Tools tab has a card for it: files in force, hidden copies, what was passed over, the kinds of settings
  file (by the ending of their names) with whether ModTrap reads them line by line, and the frameworks installed,
  by their program files in `SKSE/Plugins` (TL01§25). While a scan goes, ModTrap counts as working (WHY§92).
- Left open (MT35): condition files of animation replacers lie under `meshes`, not in the places looked through.
- Checked: tests with invented files (the winner by priority, Overwrite above all, a disabled mod, each place, a
  name across two pieces of a large file, a file read again only when changed, the step when a file was passed
  over and when none names the plugin); the card in a browser.

### 99. The scanner walks all of meshes for the folders of animation replacers and reads which condition each mention belongs to; two conditions can hold once the mod is gone and stay the owner's; every look is written to the log with each failure

`2026-11-22` · DECIDED · `#steps #tools #log` · refs: MT35, MT36, MT34, TL01§26, WHY§98, WHY§95, DESIGN§14

- The owner, to MT35 and more: "yes, add the animation folders to the scanner, and make sure the scanner reports
  properly in logs so you can tell if it works and if it doesn't which files failed."
- FACT (TL01§26). The animation replacer walks the whole of `meshes` for folders of its two names, wherever they
  lie. So does the scanner now, for every mod in force: folders are found by name, and inside them every settings
  file is listed to the end. In the older layout a folder named after a plugin is itself a mention; the scanner
  records it as one.
- METHOD. The walk of `meshes` lists very many folders. A folder that held no folder when it was last listed, and
  has not changed since (by its date, which changes when something is added to it or taken from it), is passed
  by. An invented list of 1,200 mods with 690,000 files under `meshes` is walked in 0.7 s here, and in 0.3 s the
  second time. The owner's disk will differ; the log states the time.
- REJECTED: taking every line of a condition file that names the plugin as settled by the replacer. Read
  condition by condition (TL01§26), 43 of its conditions on a thing do not hold once the thing is gone, which is
  right: nobody has the thing. But the one on a scene compares with nothing and then holds for everyone who is in
  no scene, and the one on an enchantment can hold for an enchantment that is built on no other. An animation
  meant for one case could then be used generally. And a condition of another program's is not known at all.
- DECIDED. ModTrap reads which condition a mention belongs to from the file's own structure (the JSON tree, also
  through conditions inside one another; in the older text file, the name at the start of the line). A condition
  among the 43: settled, ModTrap's. One of the two, or of an unknown name, or a file that is not sound, or a
  mention outside any condition: the owner's, with the line and what to do. Where several mentions share a line,
  the least settled counts.
- The verdict holds only while that replacer's program file is installed: another program that uses the same
  files was not read, and its files are then the owner's.
- DECIDED (MT36). The scanner writes to the log, under its own name: sources and folders listed, files by where
  they lie, files read now and remembered, megabytes, the time of the listing and of the whole look, and
  "the look is whole" or "NOT whole". Each failure is a line: mod, path inside the mod, reason. It checks that
  the files in force equal those read plus those not read. A scanner that raises is caught, logged, and shown as
  failed; the step is then the owner's and the demaster is not called checked.
- Also: a file that named the plugin when scanned and cannot be opened for its lines is kept as one to look at,
  where before it would have dropped out in silence.
- Checked: tests with invented files (folders at any depth, the older layout's folder, conditions nested, on one
  line, unknown, unsound; the two unsettled; a file and a folder that cannot be opened and what the log says; a
  second look that fails the same way; a scanner that raises); the card and a whole demaster in a browser.

### 100. On the owner's list the scanner is whole in 20 s, then 3 s; the demaster of 0.3.29 went through clean; the Process tab's own Demaster button was not greyed while ModTrap scanned

`2026-11-22` · FACT · `#page #steps #process` · refs: WHY§92, WHY§98, WHY§99, MT30, MT36

- The owner, with a session file of 0.3.29: "the demaster button isn't greyed out in process page header whilst
  ModTrap is still doing its post launch scans. How do the logs look, was the demaster flawless?"
- FACT (the session's log). The scanner's first look after launch: 3,488 sources, 30,933 folders listed, 168
  folders of animation replacers, 11,549 settings files in force (6,918 in SKSE/Plugins, 3,999 in animation
  replacers' folders, 630 in top folders, 2 in FLM), 973 hidden, 37.5 MB read, whole, 20.2 s of which the listing
  3.4 s. Every later look: 2.5 to 3.3 s, with one or two files read anew and some 10,750 folders passed by.
- FACT. The whole demaster in one go went through: dry run, 7 plugins demastered and verified, 3 mods disabled,
  the behaviour tool run by its switches (33 files), the patcher framework run by its button (3 files), 0
  problems in the load order after each reading. One settings file named a ticked plugin before the patcher
  framework's run and was that tool's own output; after the run it no longer did. One file is left that names a
  plugin, of a kind ModTrap reads, with nothing to do.
- FACT. After the dry run MO2 took longer to close than the 16 s it was given, as once before; the demaster's own
  start closed it. It now gets 30 s, and a message that shows only then is closed as the first is.
- FACT, the fault. The gate (WHY§92) marks buttons by their words as the script makes them. The Process tab's
  "Demaster Selected" is a fixed button of the page and did not carry the mark; the same button on the Selection
  tab did. The server would have refused the start all the same (MT30), so nothing could go wrong, but the button
  looked ready.
- Fixed: the button carries the mark; at its start the page marks every fixed button by the same words; a test
  holds every fixed button with such words to the mark.

### 101. An update check: sources read from MO2's records and a Wabbajack file; Nexus and GitHub asked as MO2 asks; the owner's key kept under Windows' protection; not yet run against the real services

`2026-11-22` · DECIDED · `#updates #network #page` · refs: MT37, MO01§12, MO01§13, TL01§27, DESIGN§20

- The owner asked for it (MT37). Until now ModTrap made no connection but to its own page on this PC. This is the
  one exception, and it is kept narrow: two hosts, named in the code, and a test holds the code to them; an
  answer that points elsewhere is not followed.
- Sources, in the order they are trusted: the mod's `meta.ini` (the files installed by number, the mod's number,
  the archive, a web address), the `.meta` beside the downloaded archive, then the Wabbajack file's entry for the
  archive. A mod with no number and a GitHub address is a GitHub mod; other hosts cannot be asked for versions
  and are said so.
- The Wabbajack file's list is read piece by piece (METHOD: its archives and directives are walked one entry at a
  time, never the whole text), and only a summary is kept in ModTrap's folder, by the file's size and date.
  30,000 invented directives through pieces of 4 KB read right in the tests; the real size is not yet seen.
- The verdict for a Nexus mod follows MO2's own way (MO01§13), in ModTrap's own code: the installed file by its
  number, else by the archive's name; the chain of replacements; a newer current file is an update. Where the
  installed file cannot be told, or is marked old with no word of what replaced it, the state is "unclear" with
  what is known, never "up to date".
- REJECTED: asking about every mod at each scan. Some 3,000 mods with a number are more than the account's
  allowance for a day. One question for the month's list says which mods had a new file; a mod is asked about
  only then, or when its last asking is over four weeks old. The first scans of a large list are therefore
  spread over several scans, enabled mods and those in the month's list first.
- REJECTED: taking the key from MO2. MO2 keeps its own in Windows' store for MO2; it is not ModTrap's to take.
- The key: one file in ModTrap's own folder, written through DPAPI on Windows; the page gets only "a key is
  kept"; the log gets no part of it (a test reads the log, the page's state and the state for the key's text).
- A scan does not count as ModTrap working (WHY§92): it changes nothing and reads nothing a demaster needs, so
  nothing is greyed for it.
- NOT YET CHECKED: against the real Nexus and GitHub, and with a real Wabbajack file. The answers' fields are as
  MO2 reads them, and the tests use stand-ins shaped so. The owner's first scan, and its lines in the log, are
  the check; anything that differs shows there as an error in words, not as a wrong "up to date".
- Checked: tests (the records of a mod; the list's file, also large and broken ones; the chain, the archive's
  name, what cannot be told; what is asked again and when; the allowance; no key; the two hosts only; the key
  never given back); the tab in a browser with stand-ins.

### 102. The bar of ticked mods sits at the free end of the row of sections instead of over the page; ModTrap's own mod shows under the modlist's last separator only because it is placed above everything

`2026-11-22` · DECIDED · `#page` · refs: DESIGN§4, DESIGN§8, WHY§97

- The owner, with a picture: "when the user has mods selected this over top message with buttons covers the UI,
  can it be moved into header where there is no text? Also what is "ModTrap - … + …" in Not Yet Installed?"
- The bar ("2 mods ticked: …", "See what depends on them", "Untick all") floated over the bottom of the page and
  covered the last rows of the list. It is now part of the row of sections (Modlist, Demaster, …), at its right
  end, which is empty. Tried first: the header's row of chips; on a wide list that row is nearly full, the bar
  wrapped to a line of its own and the page jumped as mods were ticked. In the row of sections the height stays
  the same at 1500 and at 1000 pixels' width; the text of the bar is cut with an ellipsis before the row grows.
- The mod asked about is the one ModTrap makes for a demaster: it holds the plugins ModTrap rewrote (seven in the
  owner's demaster), is enabled, and is placed above every other mod so that its plugins win over the originals,
  which stay untouched in their own mods. The Mods tab groups mods by the modlist's separators; the list's last
  separator is called "Not Yet Installed", so a mod placed above everything shows under it. The label is the
  list's, not a state of the mod. Revert takes the mod out again.

### 103. A menu on a mod by the right mouse button; a source link of the owner's own, kept outside the mod; a drop zone for a Wabbajack file, downloads' meta files and mods' folders; of a Wabbajack file the page sends only the list

`2026-11-22` · DECIDED · `#updates #page` · refs: MT38, MT37, WHY§101, TL01§27, MO01§12, DESIGN§20

- The owner asked for both (MT38).
- The link is not written into the mod's `meta.ini`, though MO2 has a field for it: that file is the mod's and
  MO2's, and ModTrap changes no file of a mod it did not make (MT9). It is kept in ModTrap's folder by modlist
  and mod, and read before the mod's own records: it is the owner's own word on the source.
- What a dropped meta file is good for: a list installed by Wabbajack often keeps its downloads in a folder that
  is not MO2's downloads folder, so MO2's own records of the archives are not where ModTrap looks. A download's
  `<archive>.meta` names the mod's and the file's number (MO01§12); it is matched to the mods by the archive each
  was installed from. A mod's `meta.ini` alone does not say which mod it is of, so it is taken with its folder,
  whose name is the mod's. A given meta file fills in only where the mod's own records say nothing.
- A dropped folder is looked through at its top and one folder down: that covers one mod's folder, a folder of
  mods, and a folder of downloads, and never walks a whole drive.
- METHOD. A browser gives a dropped file's bytes, not its path, and a Wabbajack file can be gigabytes. The page
  reads the archive's directory at the file's end (also the large kind, for more than 65,535 entries or sizes
  past 4 GB), finds the entry called `modlist` (TL01§27), and sends only that entry's bytes as they lie in the
  file. ModTrap unpacks them as it reads, writes nothing but its summary, and deletes what arrived. Checked in a
  browser with an invented file of 66,000 entries, and in tests with the bytes packed and unpacked.
- The path field stays, for a file too awkward to drag.
- While the Updates tab is shown, a drop anywhere on the page is for the update check; elsewhere a drop still
  opens a modlist or adds a mod's archive as before.
- The menu is the page's own, not the browser's: rows as buttons, closed by Escape, a click elsewhere, a scroll
  or leaving the window; the arrow keys move in it.
- Checked: tests (the kinds of link and what is refused; the link before every record and no file of the mod
  changed; given meta files, and the mod's own record winning; the list's bytes, broken bytes; through the
  requests); in a browser the menu on both tabs, the box, the button's file chooser and a real drop.

### 104. The Updates tab is laid out as the modlist: priority, separators, MO2's notes; an Update column whose button opens the newer file's own page for a download through MO2; ModTrap still downloads nothing

`2026-11-22` · DECIDED · `#updates #page` · refs: MT39, MT40, MT37, MT38, MO01§12, WHY§101, WHY§103, DESIGN§20

- The owner asked for both (MT39).
- The list was flat, sorted by state, cut at 600 rows. It is now built from the same list of mods the Mods tab
  has: lowest priority first, a heading for each separator that folds, the state filters hiding what does not
  match and the headings of groups left empty. A heading says how many updates are out below it.
- "Comments": MO2 keeps two texts of the owner's for a mod in its `meta.ini` (MO01§12): `comments`, which MO2
  shows in its Notes column, and `notes`, a longer text kept as HTML. The column shows the first; the second as a
  mark whose words, with the markup taken out, show under the pointer. The search looks in both.
- What the button does was the open point. The owner's words say "update button". ModTrap's update check was
  settled as asking and reading only (MT37), and updating a mod of a tuned modlist is a change with dependants.
  DECIDED for now: the button leads to the newer file and MO2 does the rest; whether ModTrap should go further is
  put to the owner as MT40, with a recommendation.
- LIKELY, not checked against the site: Nexus's own "mod manager download" button opens the file's page with
  `file_id` and `nmm=1`, on which the site hands the download to the mod manager set up for such links. ModTrap
  opens that address. If the site takes it otherwise, the page that opens is still the newer file's own.
- The verdict now carries the newer file's number, so that the address is of that file and not of the mod's
  list of files. Where the state is unclear, the button is drawn lighter and leads to the mod's files.
- "Ask about this mod now" asks about the named mods whatever is kept, counts against the same allowance, and
  is not recorded as "the last scan".
- METHOD. The list is some 3,500 rows. It is drawn anew only when something it shows has changed (states, newest
  versions, links, filters, folds), and at most every ten seconds while a scan goes; the head is not redrawn
  while the owner is typing in it. The key and the sources parts fold away once they are set up.
- Checked: tests (priority and the two notes; the address the button opens; single mods asked now); in a browser
  the order, the headings and their folding, the filter, the button and the menu.

### 105. The update button fetches the newer file where the host gives one to a program (Nexus for a paying account's key, GitHub), else opens its page; the file goes to Add mods as a newer version: right above the old mod, which is disabled; LoversLab only through the owner's browser

`2026-11-22` · DECIDED · `#updates #add #network` · refs: MT40, MT41, MT37, MT21, MT9, MO01§14, MO01§15, WHY§101, WHY§104, DESIGN§16, DESIGN§20

- The owner's answer to MT40 (its note): fetch with a key, open the page without; GitHub and LoversLab too; install
  through Add mods. Also asked in the same turn: whether the sweep had been used, and how safe a key in ModTrap is.
- FACT (MO01§14, MO01§15). A key alone does not make Nexus give a program a download: only a paying account's
  does. So "with a key" becomes: ask Nexus once what kind of account the key is of; fetch for a paying one; for
  any other, open the file's page as without a key. The button's tooltip says beforehand which it will do, so the
  owner is not surprised by a page opening.
- GitHub needs no key. Which file of a release is the mod's: the one named as the installed archive; else the one
  whose name differs only in digits; else the only archive. Otherwise ModTrap does not guess and opens the page.
- REJECTED: logging in to LoversLab for the owner. It gives files to a logged-in session only; a program would
  need the owner's password or session, which ModTrap does not ask for or keep. Its page opens in the owner's
  browser, and the downloaded file is handed to ModTrap by the mod's menu. That menu row serves any site.
- The fetching goes out to more hosts than the asking: the store of release files at GitHub and the hosts Nexus
  names. The list is in the code, a test holds the code to it, the key is sent to none of them, and an answer
  that points on is followed only to such a host.
- DECIDED (MT41). An update through Add mods was not a case the add job knew: it would have put the newer
  version where a new mod goes, beside the old one, both enabled. Now the staged archive carries the name of the
  mod it is a newer version of. The analysis judges it at that mod's place; the plan puts it right above and
  disables the old one; a plugin already in the load order is left where it is; the by-line way back enables the
  old one again; the check after the add catches a newer version that dropped a needed plugin.
- FACT, found by a test before it shipped: the plan first placed the newer version's plugin anew although the
  load order named it already, and the by-line way back then took its line out, leaving a dependant with an
  inactive master. Such plugins are now not in the plan at all.
- Without ModTrap's switch for changes nothing is fetched: there would be nothing to do with the file.
- NOT YET CHECKED against the real services: the account question, the download address, the hosts' names. With
  stand-ins: fetched, unpacked, planned and added in a browser; the modlist then read "+new" right above "-old".
- On the owner's two questions. The sweep ran on the whole repository before every commit of this work and is
  git's gate before every push; each said clean. The key: kept in one file of ModTrap's folder, written through
  Windows' protection for the owner's account, sent to Nexus's service only, never to the page, the log or a
  session file (tests hold this). Said plainly to the owner: any program running as the owner's Windows account
  could read it, as with MO2's own; the key can be withdrawn on Nexus at any time; and the Windows part of the
  keeping has run only in tests on another system so far, where it fails closed (no key kept) if Windows refuses.

### 106. ModTrap watches MO2's and the browser's Downloads folders for a file the owner fetched on a site, and a setting lets a newer file be added without asking: one press where the host lets a program fetch, one more on the site where it does not

`2026-11-22` · DECIDED · `#updates #add #page` · refs: MT42, MT43, MT40, MT41, TL01§28, MO01§12, MO01§14, WHY§105, DESIGN§20

- The owner chose the watch (MT42, option A) and asked whether one press can do it all.
- The watch is what Wabbajack does for files fetched by hand (TL01§28), in ModTrap's own code. ModTrap looks only
  while it waits for a download, every two seconds, into two folders: MO2's downloads folder and the browser's.
  A file counts when it is an archive, newer than the press that opened the page, not under a name an unfinished
  download has, of the same size at two looks, and openable.
- Which mod a file is for. In MO2's folder: the mod's and the file's number in the record MO2 writes beside the
  archive (MO01§12). In the browser's folder: the file's name as Nexus gives it, also with the " (1)" a browser
  adds. REJECTED: taking any new archive for the one mod waited for when its name is known and differs: the
  owner may well download something else meanwhile, and with the setting below a wrong archive would be added.
  Only a site that gives no name to go by (LoversLab) has the one new archive taken, and only while that mod
  alone is waited for.
- The browser's folder is asked of Windows (its Downloads folder can be moved); the owner can name another. Its
  path is shown on the page and never written to the log: it holds the owner's Windows name.
- One press (MT43). What stood between a file being here and it being added were two presses on Add mods. A
  setting, off to begin with, lets the page go on by itself: when the staged archive is unpacked and analysed,
  is the only thing on the list, has no installer with questions and lacks nothing it needs, the page asks for
  the plan and runs it. Everything else of an add is unchanged: MO2 must be closed (the page asks, or closes it
  with the owner's setting for that), the modlist is read again afterwards, a failure puts all back.
- What cannot be made one press, said to the owner plainly: a free Nexus account and LoversLab hand out a file
  only on a press on their own page. ModTrap does not press buttons on a site for the owner.
- FACT, a fault in a test of this work and not in ModTrap: a test started its scan while the scan begun at launch
  was still going, and so sometimes counted the wrong one. It failed about one run in ten. The tests now wait for
  the launch scan first.
- Checked: tests (the browser's folder by name, with an unfinished file, an older one and another mod's passed
  by; MO2's folder by numbers; a site with no name; stopping and the end of waiting); in a browser both ways to
  the end: a Premium account in one press, a free one with the file saved as the browser saves it, each ending
  with the newer version above the disabled older one.

### 107. On the owner's list a scan without a key asks nothing and ends at once, which looked like a dead button; the button now says so and leads to the key, with where the key is made

`2026-11-22` · FACT · `#updates #page` · refs: MT37, WHY§101, WHY§104

- The owner, with a picture and a session file of 0.3.35: "Clicking Scan for updates doesn't seem to be doing
  anything? Where do I get Nexus key from?"
- FACT (the session's log). The scan ran, twice: 3,576 mods, 3,503 of them with a number at Nexus (3,000 different
  numbers), none from GitHub, 73 with no source that can be asked; no key kept; nothing asked; 0.0 seconds. The
  page did say "no Nexus key is kept", in small print under the last scan's line. A press that ends at once with
  a line of small print reads as a press that did nothing.
- The reading of sources works on the real list: every mod's own record gave its number, with no Wabbajack file.
- Fixed. With no key and no mod from GitHub, the button asks nothing of the program at all: it says at once how
  many mods come from Nexus and that Nexus needs the key, opens the key's part and puts the cursor in its field.
  A scan that does run says "Scanning…", and what came of it when it ends. The last scan's line says "Nexus was
  not asked" where it was not.
- The key's part now has the steps to make one, with a link to Nexus's page for it. LIKELY, not checked against
  the site today: the page is the account's "API Keys" page, with the personal key at its bottom. The steps say
  the way by hand as well, in case the address has moved.
- FACT (the picture). The line "MO2's own last check saw version 0.8.0.0 as the newest" stood beside an installed
  version "d2025.1.9.0": MO2 writes such a version itself, from a file's date, when a mod gives none. The two say
  nothing by comparison. MO2's word is now passed on only where both are plain numbers and MO2's is the higher.
- The tab's own description still said that ModTrap downloads nothing; since MT40 a mod's update button can fetch.
  It now says what a scan does and what the button does.

### 108. The owner was right that a scan needs no key: Nexus's newer public service answers without one; the scan is rebuilt on it, the key kept only for fetching and as a fallback

`2026-11-22` · DECIDED · `#updates #network` · refs: MT44, MT37, MT40, TL01§29, MO01§13, WHY§101, WHY§107

- The owner, after 0.3.36 told them a key was needed: "I see no reason why it would need a nexus key to check if
  there are any updates for mods."
- FACT, my error. WHY§101 built the scan on what MO2's source shows: MO2 sends a key with every question, to
  Nexus's older service. From that I wrote that Nexus answers a program only with a key, and never checked
  whether Nexus has another way. It has (TL01§29). The claim was an inference from one program's habit, stated
  as a fact about the service.
- METHOD. This session's network did not reach Nexus's services. A second environment that does was proposed to
  the owner and approved; this session could not move to it, so a helper session on it asked the live service,
  with no key and only about two well-known public mods, and reported the literal questions and answers.
- DECIDED. The scan asks the public service first. Fifty mods to a question give each mod's time of last upload.
  Where the installed archive's name carries that same time (Nexus writes the upload's time into a file's
  name), the installed file is the mod's newest and nothing more is asked. Otherwise the mod's files are asked
  for, five mods to a question; a question that is refused is asked again mod by mod.
- The verdict without a word of what replaced what: the files of one line of versions share a group (TL01§29,
  LIKELY). The newest current file of the installed file's group, uploaded after it, is its newer version. This
  also keeps a mod's other lines apart: a newer main file is no update for an installed patch of another line.
  Where the installed file is not found among the mod's files, the older rules hold (by the archive's name, by
  version, else "unclear").
- What is kept from the older way: the key and its service remain, used only where the public service does not
  answer as expected at the outset, and for fetching (MT40). The key is never sent to the public service; a test
  holds that.
- The public service is said by Nexus to be still changing. An answer in a form ModTrap does not know is said in
  words, in the log and on the page, and never taken for "no update".
- NOT YET CHECKED by ModTrap's own code against the live service: the helper asked the questions by hand. The
  owner's next scan is the check, with its lines in the log.
- Later, 2026-11-22: checked. The helper session ran ModTrap's own scan, unchanged, from the pushed commit
  `7869d5c` (0.3.37), against the live service with no key, for three invented rows on the two public mods. Three
  questions, each answered with no error, in 1.2 seconds. An old file of the first mod, named as its archive is
  named: update, to the mod's current main file, by the group. The same mod's current file, by its number:
  current. The second mod, by the time in its archive's name alone: current, without its files being asked for.
  Not yet seen: a scan of some 3,000 mods, fifty to a question and five to a question for files; and how many
  questions the service allows.
- Checked: tests with a stand-in for the public service (states by group and by time; no key sent; files asked
  for only where needed; a second scan; fifty and five to a question; the service absent, with and without a
  key; a service that asks to wait; a game's name that is no name); the page in a browser.

### 109. A source without typing: the mark a browser leaves on a downloaded file names its address; and a mod ModTrap adds had no source in its record, so an updated mod could no longer be asked about

`2026-11-22` · DECIDED · `#updates #add` · refs: MT45, MT38, MT41, MO01§12, WHY§103, WHY§105

- The owner asked for an efficient way to give a GitHub source, supposing rightly that the archive's contents do
  not name it.
- LIKELY, not checked on a Windows PC from here: browsers on Windows write, beside a downloaded file's own bytes,
  a small text ("Zone.Identifier") with `HostUrl`, the address of the file, and `ReferrerUrl`, the page the
  download was started on. It stays with the file while the file stays on a disk that keeps such texts, and is
  lost when the file is copied through a program that does not carry it, or unpacked. For a file from GitHub the
  file's own address is often that of GitHub's store, and the page is the release's; so both are looked at, and a
  GitHub address in either counts first.
- DECIDED. Where meta.ini, the download's meta file, what the owner gave and the Wabbajack file all say nothing,
  the archive named in the mod's record is looked for in MO2's downloads folder and its mark read. One small read
  for each mod that has no source; nothing where the archive is gone. On another system, or with no mark, nothing
  is found and nothing changes.
- FACT, a gap found while answering. The record ModTrap wrote for a mod it added held the archive's name only. A
  newer version put in by ModTrap (MT41) therefore had no source of its own unless MO2's downloads folder still
  held a record beside its archive: after an update fetched by ModTrap, or one taken from the browser's folder,
  the new mod would have shown "cannot be asked". The record now carries the source in MO2's own fields
  (MO01§12): the game, the mod's and the file's number, the version; or the web address, with the flag MO2 uses
  for an address of the owner's. The owner's own link for the older mod is copied to the newer one's name.
- A new mod taken from MO2's downloads folder gets what MO2's record beside the archive says, else the mark's
  address.
- Values written into the record have line ends and quotes taken out; an address that is not a web address is
  not written.
- The pattern for a GitHub address now also reads a release's page (`/releases/tag/…`), not only a release's
  file: a link pasted from the release page records which release is installed.
- Checked: tests (the mark's two addresses and which counts; texts that are no addresses; a mod with no record
  getting its source from the mark while a mod with a record keeps its own; the record of a newer version read
  back by ModTrap's own reader; the hand-over through Add mods). The reading of a real mark on Windows is not
  checked.

### 110. A download from Nexus's page was not taken: the public service gave a storage code where a file's name was expected; a download is now known by the browser's mark, or by the mod's number and the upload's time in its name

`2026-11-22` · FACT · `#updates #network` · refs: MT46, MT42, MT44, TL01§29, WHY§106, WHY§108, WHY§109

- The owner's session file at 0.3.38 shows the scan without a key working on the real list: 3,000 distinct mods
  asked when they last had a new file, the files of 2,190 asked for, none left, in 500 questions and 184.4 s.
- The same file shows why a download started on Nexus's page was not taken. For the mod the owner updated, the
  public service's `uri` of the newer file was not a file's name but a code of three short parts and a long one,
  divided by slashes: where the file is stored. ModTrap showed that code as the file's name and waited for a
  download of exactly that name, which no browser writes. LIKELY: the service gives such codes for files uploaded
  through Nexus's newer uploader; older files still carry a name.
- The files question now also asks each file's `name`, its name on the mod's page. That is what the owner is
  shown; where it is empty too, "the mod's newer file". A `uri` counts as a file's name only where it ends as an
  archive does.
- A download is now known, in this order: by the numbers MO2 writes beside an archive in its own folder; by the
  browser's mark on the file (WHY§109), where the page it came from is the mod's page at Nexus, same game and same
  number; by the exact name, where one is known; by the mod's number and the upload's time, which Nexus puts at
  the end of every download's name ("…-<mod's number>-<version>-<time>.7z") and which the service gives as the
  file's `date`. A name of that shape that fits no waited mod is nobody's: before this, the installed file
  downloaded again would have been taken as the newer one, by the likeness of its name (found by a new test).
- Only where one mod alone is waited for, and nothing above speaks, an archive is taken whose name begins as the
  file's name on the page does, or as the installed archive's.
- Checked: tests (a storage code is never shown or waited for; the download known by number and time while the
  installed file and another mod's file are passed by; known by the mark whatever its name, another page's file
  left; the one-mod fallback), and in a browser against a stand-in service: the file dropped into the watched
  folder under a name ModTrap was never told is taken to Add mods. Not checked: a real download on the owner's PC.

### 111. A site's page in a small window of its own: a window ModTrap can close stays tied to ModTrap's tab, which the site's page could then send elsewhere; cut loose by default, tied only by the owner's setting

`2026-11-22` · DECIDED · `#updates #page #safety` · refs: MT46, MT40, MT42, WHY§105, WHY§106

- The owner asked whether Nexus's page must open at all without a key, and otherwise to stay on ModTrap's tab.
- It must: the public service names a mod's files and gives no address to fetch one from; the address is made by
  Nexus's page for the signed-in browser, or by the keyed service for a paying account only (WHY§105). ModTrap
  takes no password and does not act as the owner's browser (the secrets policy), so the press on Nexus's page
  stays the owner's.
- A page cannot open a tab behind itself: browsers put a new tab or window in front. The nearest thing is a small
  window beside ModTrap, opened on the owner's press, which leaves ModTrap's tab as it is. It is opened empty at
  the press itself, because a browser lets a page open a window only then, and sent to the address once ModTrap's
  answer names it; it is closed again where ModTrap fetches the file itself.
- Found in a browser: a window whose tie to ModTrap is cut (`opener` set to nothing, as "noopener" does) cannot be
  closed by ModTrap afterwards, nor found again by its name. And a window whose tie is kept gives the site's page
  a handle on ModTrap's tab, by which it may send that tab to any address: the known danger "noopener" exists
  against. There is no third way: any window a page may close is one that can reach the page.
- DECIDED: cut loose by default; the owner closes the window. A second setting, off, keeps the tie, only for
  addresses at Nexus, GitHub and LoversLab; ModTrap then closes the window when the file is here or the waiting
  ends, uses the one window for the next mod, and holds a "leave this page?" question on its own tab while such a
  window is open, so that the tab cannot be sent anywhere unseen. Any other address is always cut loose.
- What the tie could cost at worst: ModTrap's tab replaced by another page. ModTrap's server answers only its own
  page (requests of another origin are refused), so nothing of the modlist could be changed through it.
- Checked in a browser against a stand-in page: cut loose, the page sees no opener and stays open after "stop
  waiting"; tied, the page sees its opener, is closed on "stop waiting" and when the file arrives. The page test
  that forbids outside addresses and inline code still holds.
- Later (2026-11-23, MT47, WHY§112): the owner had asked for a tab, not a window. The window is now a setting
  that is off; the page opens as a tab, and the setting that keeps the tie holds for a tab as for the window.

### 112. The download was still not taken, and a window was not what the owner asked for: the page handed the file to a mod manager instead of the browser; the watch looked only while ModTrap's tab was asked; a download is now known by its size, and the site's page is a tab again

`2026-11-23` · DECIDED · `#updates #page #network` · refs: MT47, MT46, MT42, TL01§30, WHY§105, WHY§106, WHY§110, WHY§111

- The owner's session file at 0.3.39: the page was opened for the mod twice (23:57 and 23:59) and the log says
  nothing more of it until the file was packed three minutes later. FACT: the log could not tell what the watch
  saw, because the watch wrote nothing; that is itself a fault, mended here.
- FACT (the owner's pictures): the page ModTrap opened carried `nmm=1`, the way of Nexus's "mod manager
  download". LIKELY the cause that nothing was saved: on that page the press hands the download to a program
  registered for such links (MO2's handler), and the browser saves no file; with MO2 closed, as it is while
  ModTrap adds mods, nothing visible follows. Not proved from here. The page is now opened without it, the way
  of "manual download", where the browser itself saves the file into its Downloads folder, which ModTrap watches.
- FACT (found by reading the code): the watch looked only when ModTrap's page asked for the Updates tab's
  state, and a browser slows or stops the asking of a tab that is not in front, as ModTrap's is not while the
  owner is on the site's page. The watch now runs by itself for as long as a download is waited for.
- FACT (TL01§30): for every file uploaded since the summer of 2026 the public service gives a storage code, not
  the name; no field gives the name the download is saved under; `sizeInBytes` gives the size to the byte. So a
  download is now also known by its size, which holds whatever the name, and tells two waited mods apart. The
  files of the one mod are asked afresh at the press (one question), so that the number, the name on the page
  and the size waited for are the page's at that moment; what an older scan kept had neither name nor size.
- A file with no archive's ending to its name is now looked at too: an archive is known by its first bytes (zip,
  7z, rar), and unpacked under its name with the ending those bytes call for. A new file that is no archive is
  passed by and said so in the log.
- The one-mod fallback of WHY§110 now holds only where no size is known: a size that is known and differs says
  the file is another.
- Found by the new test, before any release: the first wiring gave the watch the function that takes in a file
  ModTrap fetched itself, which moves the file; a download of the owner's would have been moved out of their
  Downloads folder. The watch now gets only the function that reads a file where it lies, and the test asserts
  that every file in the watched folder is still there afterwards.
- The log now says, without the folder's path (it holds the owner's name on the PC): at the press, what the
  download is known by and whether the browser's folder was found; for each file that came after the press,
  once, that it is being written, is no archive, fits no waited mod (with what is waited for), or is whole and
  by what it was known; and the end of the waiting.
- The tab: DECIDED as in MT47. A page cannot open a tab behind itself (WHY§111); a real link pressed with Ctrl
  or the middle button is opened by the browser itself, behind ModTrap's tab, so the update button is now such a
  link, and ModTrap then only starts watching. LIKELY, not checked: Firefox's own setting
  `browser.tabs.loadDivertedInBackground` makes every tab a page opens load behind the one in front; that is
  the owner's to set in their browser, not ModTrap's.
- Checked: tests (the watch by itself takes a download with a name that says nothing and no ending, by its
  size, passes by a text file, an unfinished download and an archive of another size, and leaves all four files
  where they are; the address has no `nmm=1`), and in a browser against a stand-in service: a plain press opens
  a tab that sees no opener; the nameless file is taken to Add mods as the mod's newer version; a middle click
  is left to the browser and starts the watch; with the tie kept, ModTrap closes the tab when the file arrives.
  Not checked: a real download from Nexus on the owner's PC, and under which name the browser saves it.

### 113. Still a window in the owner's browser, and nothing told of a download in progress: Firefox answers window.open with “noopener” among its features with a window; a folder's listing on Windows gives a file being written no size

`2026-11-23` · LIKELY · `#updates #page #windows` · refs: MT48, MT47, WHY§111, WHY§112

- The owner's session file at 0.3.40. FACT: at the press the log says the download is known by the mod's number,
  its size to the byte and the time of its upload, and that the browser's folder is there. No file is told of in
  the 107 seconds until the session was packed. The owner's picture, taken in that time, shows Nexus's page with
  its "Start download" button not yet pressed, in a window of its own with next to no furniture.
- So two things are open and cannot be told apart from here: the button on the site was not pressed, or it was
  and the download had not ended when the session was packed (a file of that size takes a minute or two).
- LIKELY, from what is commonly told of Windows' file system and not checked on Windows from here: what a folder's listing says of a
  file lags on Windows while the file is being written; its size reads as nothing until the writing ends. The
  watch took a file's size and time from the listing, so a download in progress was not told of, on the page or
  in the log, and the row went on saying that ModTrap waited for the press. Each file that came after the press
  is now asked of itself. A file counts as having come after the press by when it was made or last written,
  whichever is later, where the system keeps the time of making.
- The row now says what to do ("press “Start download” on Nexus's page") and, once a file is being written, how
  far it is, against the size the site gave. The log gets a line every half minute while the watch waits: how
  many files came since the press and how far the one being written is; so the next session file tells which of
  the two it was.
- LIKELY, from the owner's picture and not checked in Firefox from here: Firefox answers `window.open` that has
  "noopener" among its features with a window of its own, where Chromium opens a tab. With the window of MT46
  switched off, ModTrap still opened the page that way. A tab with no tie is now opened by a link with
  `rel="noopener noreferrer"` pressed for the owner, and the tab for a download by `window.open` with no features
  at all, at the press itself, cut loose or tied afterwards (WHY§111). Nowhere is "noopener" given as a feature.
- DECIDED (MT48): closing the site's page is on as ModTrap comes, because the owner asked for it; the reasons it
  was off (WHY§111) stand and are said with the setting.
- Not done, and the owner's to decide: reading the browser's own settings for where it saves downloads. Where
  the browser saves elsewhere than Windows' Downloads folder, the owner names the folder on the Updates tab.
- Checked: tests (a download in progress is told with how far it is), and in Chromium against a stand-in: a
  plain press opens a tab, the row says to press, then "downloading 27%", then the tab is closed by ModTrap and
  Add mods holds the file; "Open its page" opens a tab that sees no opener. Not checked: Firefox, Windows.

### 114. The download works on the owner's PC; an update was judged as a new mod, with eight steps of tools and judgements, and the Updates tab still asked for it: an update now has its own few steps, and an older version replaced is shown as such

`2026-11-23` · DECIDED · `#updates #add` · refs: MT49, MT41, MT43, MT47, MT48, DESIGN§16, TL01§31, WHY§105, WHY§112, WHY§113

- FACT (the owner's session file at 0.3.41): the whole way worked. Ten seconds after the press on ModTrap's
  button a download was being written in the browser's folder; sixteen seconds later it was whole and known "by
  its size, to the byte"; it was unpacked (8,932 files), added by itself (the setting of MT43), enabled one
  priority above the older version, and the older version disabled. The owner was brought to Add mods, and says the
  press on the site's own button was what it took (WHY§113's first reading).
- FACT (same file): the saved name had a shape ModTrap had not seen, recorded in TL01§31. It ends with the
  file's own short code, which the public service gives; a download is now also known by that code together with
  the mod's number in its name, and a name that carries another file's code is nobody's.
- The owner's two complaints are both right. After the add, Add mods showed eight steps to go: look at shared
  files, check records through xEdit, run four tools again, a look in the game. And the Updates tab still showed
  the older mod with "Update out" and its button.
- Why the steps came: before the add, the analysis knew the mod was a newer version (the unpacked archive said
  so) and placed it by the older one; after the add, the mod was read from MO2 like any other and nothing said
  it was an update, so it was judged as a new mod. And even before the add, the steps of a new mod were all
  there, only with the place changed.
- DECIDED (MT49): an update has its own short list: what the mod needs (kept, because a newer version can name
  a new master), put it in the older one's place, a plugin the older version did not have, what the newer
  version changes (told, not asked), the load order's health. No step is ticked by hand. The older version is
  left out of the mods the newer one is compared with: what it shares with the mod it stands in for is no
  conflict. That an added mod is an update is read from the add's own record for as long as the add stands.
- What the newer version changes is found by comparing both folders' files by name and size, without reading
  them. The tools named are those that read a kind of file that differs; they are named in a note, and nothing
  is asked. Rejected: leaving the tools out altogether. An update that changes animation files does leave a
  behaviour tool's output stale, and the owner should be able to know it without being made to act on it.
- The Updates tab: rather than record what replaced what, it is read from the modlist as it is: a mod whose
  newer file (by its number at Nexus) is installed in another, enabled mod is an older version. This also holds
  for an update the owner made in MO2 by hand, and undoes itself when the add is reverted.
- A favourite's mark is copied to the newer version when its archive is taken in, as the owner's source link is.
- Not done: what the owner wrote of the older mod in MO2 (its notes) is not copied to the newer one.
- Checked: tests (an update's steps before the add, after it, and without the word that it is an update; the
  add's record; the older version shown as replaced and the newer as up to date; a download known by the file's
  code), and in a browser against a stand-in service, with the setting of MT43 on: one press, the file comes,
  the add runs by itself, Add mods says every step is done, and the Updates tab shows the older version as
  such and the newer one, a favourite, as up to date.

### 115. The add did not go by itself because an entry left on Install mods' list stood in its way; the update is now carried through on the server, in an Updater of its own, with ModTrap's downloads folder and nothing downloaded twice

`2026-11-23` · DECIDED · `#updates #add #page` · refs: MT50, MT49, MT43, MT42, MT21, DESIGN§16, DESIGN§20, TL01§28, WHY§105, WHY§111, WHY§112, WHY§114

- FACT (the owner's session file at 0.3.42): the owner took the earlier update out again, then pressed the
  arrow once more. The download came and was known (this time by the file's own code in its name), was unpacked,
  and then "analysed 2 mod(s): 3 step(s) to go": the mod taken out was still on the "To add" list of the page,
  and the page's own rule, that an add goes by itself only when it is the one thing on the list (MT43), held it
  back. The owner saw a first step that read like work by hand and took it that ModTrap cannot add a mod.
- The fault is in where the carrying-through lived: in the page, tied to one tab's list. It is now on the
  server, a run of its own for one mod, with nothing of Install mods' list in it; the page only shows it. That
  is also what lets it go on while ModTrap's tab is not in front.
- The run's stages are the ones the owner asked to see as boxes: find, download, unpack, check, put in place,
  check the result. The change to the modlist is still the add job's, with its record and its Revert (MT21);
  what an update is and is not asked is MT49's.
- The press on the site, said plainly, since the owner asks why it is still there: without the key of a Premium
  account Nexus gives a file's address only to its own page in a signed-in browser (WHY§105). A program that
  pressed that button for the owner would be doing what Nexus forbids a program to do for an account that is
  not Premium; Wabbajack, for the same reason, has such an account press each download by hand (TL01§28).
  ModTrap does not go round it. What ModTrap can do is make the press needless wherever the file is already on
  the PC, and be done with one press where the account's key allows fetching.
- Nothing twice. The owner's browser folder held the same file three times by now. Before a download ModTrap
  looks in its own downloads folder (by the source, else by size), in MO2's downloads folder (by the numbers MO2
  wrote beside the file, else by size) and in the browser's (by size, to the byte; where the site gave no size,
  by the mod's number and the file's code in the name). The answer comes within the press, so that no page is
  opened where the file is here.
- ModTrap's downloads folder amends MT42's "moves and deletes nothing". DECIDED from the owner's words
  ("download mod files there"): a file the owner downloaded in the browser for an update, known to be the
  site's file to the byte, is moved into ModTrap's folder; a setting makes it a copy. A file in MO2's downloads
  folder is MO2's: referred to, never moved. Where a file of the same source is already in ModTrap's folder, the
  other copy is left where it is and not taken in again.
- The watch for a download (WHY§112) now hands what it finds to the run that waits for it; with no run waiting,
  to Install mods as before.
- The setting of MT43 has no part in an update any more and is no longer shown; the Updater goes through by
  itself. It still holds for a newer version that reaches Install mods another way.
- Checked: tests (the whole run from a browser's download; the file moved, listed, and the mod installed; taken
  out and pressed again with nothing downloaded and nothing unpacked twice; a file from an earlier day used by
  its size; a file in MO2's folder used from there; a fetch with a key; stopping; the folder named anew), and in
  a browser against a stand-in service: one press, the page for the press, the boxes to their end, the page
  closed, the Downloads tab, the list's two rows, "Take it out again", and a second press that downloads nothing.
  Not checked: on the owner's PC.

### 116. A package for Windows: CPython from NuGet, a launcher of our own built with MinGW-w64, the path set by a ._pth file; built here, and not run here, since Wine does not start in this container

`2026-11-23` · METHOD · `#release #windows` · refs: MT51, MT22

- The owner asked for a program to start, and for each release to be handed over in the conversation.
- Rejected: a tool that packs Python programs into one .exe. Those are built on Windows, for Windows; none is
  to hand here, and what they make is a program ModTrap's own "files differ" check (MT22) could not look into.
- The package: CPython for Windows as the Python Software Foundation itself publishes it on NuGet (version and
  checksum fixed in tools/build_exe.py; its licence read, and kept in the package), ModTrap's folder beside it,
  and a small launcher of our own. A file `python313._pth` beside that Python names its library and ModTrap's
  folder; with such a file Python takes nothing else of the PC into its path, so an installed Python, PATH and
  the registry play no part.
- The launcher (tools/exe/launcher.c) starts that Python with `-m modtrap`, hands on its own arguments, waits,
  and ends with Python's result. It is built twice with the MinGW-w64 cross compiler: once plain, once passing
  `--allow-changes`. Two programs rather than one that allows changes: the switch stays the owner's choice
  (DESIGN§8), made by which program they start.
- FACT: the package was built here and its contents checked (every module ModTrap imports is in the package's
  Python; the launchers hold the command lines they should). It was NOT run: Wine, installed to try it, does not
  start in this container ("free(): invalid pointer" before any program runs). So the package also holds two
  command files that start the same Python the same way, should a launcher not run.
- An unsigned program fetched from elsewhere is met by Windows with a warning the first time; the package's
  note says how to go on.
- FACT: the owner's sweep, which a file handed to the owner must pass, looks inside the package and reports the
  e-mail addresses of CPython's own authors, written in its source and its libraries: 215 findings, none of them
  the owner's. They are not ModTrap's to remove (the Python is published as it is) and not ModTrap's to allow
  (the sweep's list of what is allowed is the owner's). So the package is built two ways: without Python inside,
  which passes the sweep and is what is handed over, and whose launcher starts the Python installed on the PC
  (the "py" launcher, else "python", with ModTrap's folder given to it); and with Python inside, which is built
  the same way and waits for the owner's word on the sweep. The launcher is the same program in both: it takes
  the Python beside it where there is one.
- Later (2026-11-23, MT51's note): the owner chose the package without Python, with Python as what ModTrap needs
  on the PC. The build with Python inside, and the launcher's look for a Python beside it, are taken out.

### 117. The update never began because the owner started the look-only program; the browser can be taken back to ModTrap's tab by ModTrap's program, not by its page; the press at Nexus goes only with a Premium account's key, and is not pressed by a program

`2026-11-23` · DECIDED · `#updates #page #release #windows` · refs: MT52, MT51, MT50, MT48, DESIGN§9, TL01§28, TL01§29, WHY§105, WHY§111, WHY§115, WHY§116

- FACT (the owner's session file at 0.3.43): ModTrap ran from the package (the launcher found the PC's own
  Python, 3.14), and the session says "changes allowed: no". The owner had started `ModTrap.exe`, which in MT51
  was the program that changes nothing; pressed there, a mod's update button only opens the mod's page and says
  so in a passing note. No update was begun, so nothing was downloaded. The log holds no line of the Updater.
- So the first of the two things the owner calls failed was, this time, the package's doing: of two programs the
  plainly named one was the one that could not do the work. DECIDED: `ModTrap.exe` passes the switch for
  changes; the other program is named for what it is, "look only". The switch is still a choice made by which
  program is started, and a real job still needs the proving run first (DESIGN§9).
- Staying on ModTrap's tab. A page cannot open a tab behind itself nor bring itself to the front (WHY§111), and
  that held. But ModTrap is a program too, on the same PC, and a program may press a key. So after its page
  opens a site's page, the page tells the program, and the program presses the browser's own key for "the tab
  before this one", Ctrl+Page Up: a new tab opened from a page stands right after it. Guards, since a key
  goes to whatever window is in front: it is pressed only when that window is a browser's (by its window class:
  Firefox's, or the one Chrome, Edge and their kin share) and its title no longer begins as ModTrap's does; the
  title is read again afterwards, and where the tab before was not ModTrap's, the key for "the tab after" puts
  the browser back where it was. The page that is opened first, empty, no longer carries ModTrap's name in its
  title, so that the two can be told apart. Nothing is read from the browser but the title and the class of the
  window in front.
- The press at Nexus. Twice more the owner asks that nothing be pressed there. What can be done: Nexus's key
  service gives a file's address to a program for a Premium account (WHY§105), and then there is no page at all.
  LIKELY the owner's account is Premium: its downloads in the session files ran at 7 to 8 MB a second (134 MB in
  16 and in 19 seconds), well above what Nexus gives an account that is not. So the key is now asked for where
  the need shows, on the Updater tool beside the update that waits; the box tells where the key is made and how
  it is kept; Nexus is asked at once what kind of account it is of, and the owner is told; and an update that was
  waiting for the press is begun again and fetched by ModTrap.
- Not built, and why: a program that presses Nexus's download button in the owner's browser. It could be done on
  Windows as the key press above is. But for an account that is not Premium that press is the one thing Nexus
  requires a person to do (TL01§28: Wabbajack keeps to it; TL01§29: Nexus's rules for programs), and a program
  doing it puts the owner's account at risk of being closed. For a Premium account it is needless: the key does
  it within the rules.
- The package: one folder, `ModTrap`, in every version (the build now works in a folder beside the archive and
  names the folder inside it by a constant); a version resource in both programs, made with the cross compiler's
  resource tool, so that Windows shows the version under Properties.
- Checked: tests (the key press with a stand-in for the window in front: taken back; nothing pressed where
  ModTrap's tab stayed in front or the window is no browser's; put back where the tab before was another;
  titles that only begin like ModTrap's), and in a browser against a stand-in service: the page asks the program
  to come back; a key given while an update waits is found to be a Premium account's, and the update goes on by
  itself and ends, fetched by ModTrap. Not checked, and not checkable here: the key press itself on Windows, in
  Firefox; a real fetch from Nexus with a real key.

### 118. The whole update works on the owner's PC, the tab return too; the first press took half a minute and a second press began a second update; a new mod's steps named tools that had nothing to do with it: tools are now judged by the kinds of records, and a new mod is installed with one press

`2026-11-23` · DECIDED · `#add #updates #page #release` · refs: MT53, MT52, MT50, MT49, MT21, DESIGN§16, TL01§31, WHY§114, WHY§115, WHY§117

- FACT (the owner's session file at 0.3.44, started from `ModTrap.exe`): the update of a mod went through from
  the press to the end, the file taken from the browser's folder where an earlier download had left it, moved
  into ModTrap's downloads folder, unpacked and installed. And "a site's page was opened in a new tab; back on
  ModTrap's tab: yes": the key press of WHY§117 works in the owner's Firefox.
- FACT (same file): the first press was answered only after 32 seconds. Before the answer, the look for the file
  read, in MO2's downloads folder, the record beside every one of several thousand archives. The owner, seeing
  nothing, pressed again after 20 seconds; that second press found no update begun yet, began its own, and by
  then the first had moved the file, so the second opened Nexus's page. The owner stopped it.
  Mended twice over: a file is now looked for by its size as the folder lists it, and MO2's records are read only
  where the site gave no size; and a second press for a mod whose update is still being begun starts nothing.
- FACT (the owner's picture): a new mod with one plugin, scripts and a script extender's files was given steps to
  run four tools "again", among them two that build plugins from the load order. The old reason was only that the
  mod brings a plugin. DECIDED: a plugin's top groups name the kinds of records it holds, and reading them costs
  a few seeks whatever the plugin's size. A tool that builds a plugin from plugins is named only where its output
  and the new plugin hold records of a common kind. Where either cannot be read, the tool is named, to be on the
  safe side. LIKELY good enough, not proven: a tool may read a kind of record it writes none of.
- The owner asks whether a new mod can simply go last, and where else if not. A new mod placed last (before the
  tools' outputs) wins every file it shares with an ordinary mod; that is what MO2 does with a new mod too. What
  can be told from files is which files and whose; which mod ought to win one cannot. So ModTrap installs it
  last, tells what it overwrites there, and leaves any other place to the owner's hand. Rejected: choosing by
  itself a lower place where the new mod overwrites nothing; its own files would then be the ones overwritten,
  and it would be ModTrap's guess that it should lose.
- Manual placement is a mode of the Mods tab, not a list of its own: the owner knows that list. While it is on,
  the list is in MO2's order with its filters off and its groups unfolded, a click on a row means the place and
  nothing else, and leaving the tab ends it. The place is named to the server as the entry the mod goes before
  (or "last of all"); the analysis is the Installer tool's own, made for that place, and the add job takes the
  place from it.
- One press: the plan that was shown first is gone for a new mod as it was for an update (WHY§115). What stood
  in it is in the steps, and the install can be taken out again as before.
- The favourite's mark: nothing is written when a mod is updated. An older version whose newer one carries the
  mark is not shown as a favourite; so the list is right for updates made before this, and after an uninstall.
- The mod the owner dropped was named after its whole file name, in the form of TL01§31. What the site added is
  now taken off, and the number and version in it are kept as the mod's source; the time of upload in such a
  name is read for the update check (to the minute: the end of that minute is taken).
- One program in the package (MT53): the owner asks what the look-only program is for, and it has tripped them
  once (WHY§117). It is dropped from the package; the command line without the switch stays as it is.
- Checked: tests (a place chosen by hand judged there and used by the add job; "last of all"; the tools named by
  kinds of records; names of both forms; a favourite's mark; the Installed list; a second press), and in a
  browser against a stand-in modlist: a dropped archive named in Nexus's newer way becomes a mod of its plain
  name with its source; no step is to be ticked; the line follows the pointer; the box tells; OK installs at the
  place; Installed mods lists it; Uninstall takes it out; one press installs it last, before the outputs.
  Not checked: on the owner's modlist.

### 119. The owner dropped a mod and waited: the install waited for a button further up the page, under a list that read like tasks for the owner; a dropped mod now installs by itself, and ModTrap's own steps are named as ModTrap's

`2026-11-23` · DECIDED · `#add #page` · refs: MT54, MT53, MT50, WHY§115, WHY§118

- FACT (the owner's session file at 0.3.45): the archive was dropped, unpacked and read ("4 step(s) to go"); the
  setting for placing by hand was switched on and the archive dropped again; in neither case was an install
  asked for. Two minutes later the session was packed. The owner's picture shows the page scrolled to the list,
  whose first entry read "Copy the unpacked mod into MO2's mods folder · ModTrap · to do"; the button that does
  it was above, out of view.
- So "one press" was understood by ModTrap as a press on "Install mod", and by the owner as the drop itself. The
  owner's reading is the simpler one, and it is what the Updater already does with a press on the arrow
  (WHY§115). DECIDED: the drop installs. The page watches the dropped archive until it is unpacked and read and
  ModTrap's own reading has settled, then does what the button does; with the setting for placing by hand, it
  opens the choosing of the place instead.
- What must not happen by itself: an installer's questions answered by guessing (the page waits for the owner's
  answers, then goes on); an install where a master is missing (it stops and says so); an install repeated after
  the owner took it out again (the watch ends when it has acted once).
- The list's words. A step of ModTrap's own that is not done yet was marked "to do", and numbered, exactly as a
  step of the owner's. It is now marked "ModTrap does this", the list is headed as ModTrap's work, and the count
  at the top names only what is the owner's. The button is also in the tab's top bar, where it cannot scroll away.
- Found while doing this: the first change of the words went into the Demaster's list of steps, whose line of
  code is the same; the browser check showed the installer's list unchanged, and the change was moved.
- Checked in a browser against a stand-in modlist: an archive dropped, nothing pressed, is installed last before
  the outputs; no entry is marked "to do"; with the setting for placing by hand, the drop leads to the Mods tab
  in its placing mode; after "Uninstall" the mod waits on the list with "Ready to install" and the button at the
  top, and is not installed again by itself.

### 120. Install and placement by hand work on the owner's list; a separator is added through the add job; lists sort by their columns' titles; the launcher is a windowless program that starts ModTrap's console minimised

`2026-11-23` · DECIDED · `#add #page #release #windows` · refs: MT55, MT54, MT53, MT21, MO01§2, WHY§116, WHY§118, WHY§119

- FACT (the owner's session file at 0.3.46, and their word): a new mod was dropped, read, and installed, its
  plugin activated; placing by hand worked too. The owner now finds the order "read, show, then press" right.
  So the setting of MT54 is off as ModTrap comes; nothing else of it changes.
- A separator. FACT (the owner's own list, read only for this): MO2 keeps a separator as an entry of the
  profile's list named "<name>_separator", with either sign before it, and a folder of that name among the mods.
  DECIDED: rather than a second way of writing MO2's list, the separator goes through the add job as a mod with
  no files, placed before the entry that follows the one it goes below. The job's check of its result, which
  asks of a mod that it be enabled, asks of a separator that it be in the list as a separator. So the safe
  folder, the history and "Uninstall" hold for it as for a mod.
- Titles that sort. The Mods tab already had three orders in a select; the titles now set the same thing, so
  the select and the titles cannot disagree, and the order is kept with the session as before. Sorted by
  anything but priority, the mods are one list without separators: a separator has a place only among
  priorities. While a place is chosen by hand, the order stays MO2's.
- The console. The owner asks whether the console can be part of the page. What it shows is already on the page
  (the Log tab). What it also is: the place the program lives, and a way to end it. DECIDED for now: keep it,
  minimised. The launcher is built as a program without a window of its own, and starts Python in a new console
  that is asked to start minimised and not take the front; started with words on the command line, the console
  is shown. Because nobody watches a minimised console, the launcher waits four seconds and says so in a box if
  ModTrap ended by then with an error.
  LIKELY, not checked: Windows' newer terminal may not honour the request to start minimised; ModTrap then
  starts as before, with its console in front. Not done: running with no console at all; it would want a log
  file to turn to when starting fails, and a test on Windows.
- Checked: tests (a separator added below a mod, read back as one, the load order untouched, names refused,
  taken out again), and in a browser against a stand-in modlist: titles sort the Mods tab, the Updater list and
  Installed mods both ways with the arrow; the box asks the separator's name and the list shows it below the
  mod. The launcher is built and is a program of the windowless kind; it was not run (WHY§116).

### 121. The Modlist page changes MO2's lists as MO2 does: one job per change, MO2's own rule for plugins, a disabled mod's plugin keeps its line, a scanner that reads record headers

`2026-11-23` · DECIDED · `#page #mo2 #safety` · refs: MT56, MT55, MT14, MT15, MT9, MO03§2, MO03§3, MO03§4, MO03§5, MO03§6, MO01§2, DESIGN§8, DESIGN§11, WHY§64, WHY§120

- One table, two tabs. The mods' table is built once and shown on two tabs; each row has both boxes and the tab
  decides which shows. Building 3,500 rows a second time for the second tab would have cost what a rescan costs.
- A job per change, not a pending list. MO2 writes its lists at every tick; a page that gathered changes and wrote
  them at a press would be a third way of working for the owner. So each tick, drag and rename is a small job
  (`listjob`): the guards of every job that writes, the lists copied first, the result read back, the history,
  and "Undo", which puts the copied files back while they are still as the job left them and otherwise turns back
  only the job's own lines (DESIGN§11). The page sends one change after the other and waits for ModTrap to have
  read the modlist again in between.
- The read-back reads the three list files only. Reading the whole modlist again inside the job (as the add job
  does) looks into every mod's folder: twice per tick on the owner's list. METHOD: the job checks the lines
  themselves (every other line as it was, its own lines as planned); the full reading follows once, as after
  every job. Measured on an invented list of 3,500 mods and 2,300 plugins: about 2 s from the tick to the list
  shown again, most of it that one reading.
- MO2's rule, written from the facts (MO03§2 to §4), not from its code. FACT: new plugins go last; masters keep to
  their block; nothing loads before its own masters. LIKELY: MO2's code, to the letter, puts a new master one
  place before the block's last; ModTrap puts it at the block's end, which MO2 then leaves alone (MO03§3).
- Rejected: the installer's smarter place (before what the tools made, DESIGN§16.3) for a ticked mod. The owner
  asked for MO2's logic, and a list that behaves in two ways under one tick would surprise. Instead the plan and
  the scanner say when a plugin lands after a tool's output, and whether the two change the same records.
- A disabled mod's plugin keeps its line. MO2 drops it (MO03§2), and with it the place it had. ModTrap switches
  the plugin off and leaves the line: enabled again, it stands where it stood. A line without a file is what MO2
  itself meets after a mod was removed, and it drops it at its next write; then the plugin is new, and goes last.
- What is asked and what is told. Asked first: a master missing or inactive, other mods' plugins that would lose a
  master, the game's limit on plugins (254 full ones). Told afterwards: a plugin placed after a tool's output, a
  second file of the same name, several plugins activated together (MO2's own remark, MO03§5).
- The scanner reads headers, not fields. With ModTrap's own reader (WHY§64) a record is known by the plugin it
  belongs to and its id there; two plugins that hold the same record of a master both change it, and the later
  one wins. Looking through 2,300 small invented plugins took 0.3 s; on real ones it is bounded (12 s, then "cut
  short"). It cannot tell whether the later plugin carries the earlier one's change forward: that is the record
  check through xEdit.
- Dragging is done with the mouse's own events, not the browser's drag and drop: that one is taken on this page
  by dropped folders and archives, and gives a page no say over the line shown.
- A moved or renamed line keeps its sign. FACT (the tests' invented list, and WHY§120's reading of the owner's):
  a separator's line carries either sign. The move first wrote "-" for every separator; the read-back refused it,
  and the sign is now taken from the line itself.
- Checked in a browser against stand-in modlists, small and large: tick on and off, the question box and both of
  its answers, three ticks in a row, a drag with the list scrolling on at its edge, a folded separator dragged
  with its mods, rename, "Move to priority…", Undo by its button and by Ctrl+Z, the scan's note and card, and Pick
  mods with its own ticks. Not checked on Windows: only the owner's PC can.

### 122. A hidden list forgets its place, so each list's place is noted while it is shown; a file dropped on the list is installed at that place by a run of the page's own, apart from the Installer tool's list

`2026-11-23` · DECIDED · `#page #add` · refs: MT57, MT56, MT55, MT53, WHY§121, WHY§116, DESIGN§16.8, DESIGN§21

- The list snapped to its top. FACT (seen in a browser): while ModTrap reads the modlist again, the page hides
  every tab's section, and a section that is not shown reads as scrolled to 0 and comes back at 0. The place
  0.3.48 kept was read after the section was hidden: always 0. The check of 0.3.48 used a row near the top, where
  0 was also the right answer; it proved nothing. METHOD: each list's place is noted from its own scroll events,
  only while it is shown and the modlist is ready, and given back whenever its section is shown again. That also
  covers a look at another tab, which lost the place the same way. Checked 36,000 px deep in a list of 3,500 mods:
  after a tick, Undo, Rescan, another tab and back, and a dropped install, the list stood where it was; the
  Plugins list kept a place of its own.
- A dropped file's place. The browser's own drag events are used here (a file from Explorer comes no other way);
  the line and the place are the ones of Manual placement and of a dragged row, from one function. FACT: when
  the file is let go the header folds back and the rows move up; the place read after that was one row off. It is
  now read before the header folds.
- The run is the page's own, with only the dropped archives in it. The Installer tool's list may hold other mods
  still waiting; "Install mod" there installs the whole list, and a drop at a place must not carry them along
  (WHY§116 met the same with a stale entry). So the run asks for the analysis and the install with its own
  archives and its place; the archives are put on the Installer tool's list as well, which then shows them as it
  shows any mod. Nothing new on the server: the analysis and the add job already take a place.
- Rejected: asking once more before the install. The owner's order of words puts the install before the box of
  details, and the drop names both mod and place; a wrong drop is one "Uninstall" away. Recorded in MT57 as the
  one point that was read into the words.
- Rejected: the mod's own installer questions inside the box. They need the Installer tool's whole card; the box
  hands over, and the place goes with it.

### 123. ModTrap reads .7z itself; what its reader does not read goes to 7-Zip or to Windows' own unpacker

`2026-11-23` · METHOD · `#adding #safety #licence` · refs: MT58, MT21, WHY§41, WHY§48, DESIGN§16.1

- FACT (the owner's session file at 0.3.49): a mod dropped as .7z was refused, "needs 7-Zip, which ModTrap did not
  find on this PC". WHY§41 had ruled out an unpacker of ModTrap's own "for now" and left Windows' `tar` as untried.
- The owner's point decides it: ModTrap writes .7z itself (WHY§48), so it can read it. METHOD: `sevenz_read.py`,
  from the format's published description, nothing copied. Python's own lzma, zlib and bz2 do the decompression;
  the reader parses the header (also a compressed one), builds each folder's chain of coders, and checks every
  file's CRC, so a mistake of the reader cannot pass as a file.
- What 7-Zip puts before the packer. BCJ and Delta are filters Python's decoder knows, but only in a chain that
  ends in LZMA2 and so says where it ends. FACT (tried): with old-style LZMA under BCJ, the last bytes never came
  out. METHOD: where the filter stands before anything but LZMA2, the unpacked bytes are packed again lightly and
  unpacked through a chain that ends in LZMA2. BCJ2, 7-Zip's x86 filter with four streams, is decoded by our own
  code, in memory, up to 512 MB.
- Checked against 7-Zip 23.01 with invented files and real programs as the programs' part: default, ultra,
  non-solid, header not packed, LZMA, BCJ, BCJ2, Delta, ARM, Deflate, BZip2, stored: every file the same. A
  password (also over the header) is told as one; PPMd is told as not read. A .7z written by ModTrap on the
  owner's PC read through, 354 files, every checksum right. Not checked: an archive from Nexus (none is here, and
  none may be kept); the owner's next drop is that check.
- The order for a .7z: ModTrap's reader; if it says "not read" or "damaged", the owner's 7-Zip; else Windows'
  `tar.exe`. A .rar: 7-Zip, else `tar.exe`. FACT: `tar.exe` is bsdtar; tried here as the same program (3.7.2):
  it lists and unpacks .7z, refuses a step upwards, and names a password. LIKELY, not seen: the one of Windows 11
  from 23H2 has the LZMA part (the one of Windows 10 has not; ModTrap asks it what it is and says so).
- Safety as before (WHY§41): names checked before anything is written, links refused, sizes capped, the result
  walked for links; with `tar`, what was written is measured too, since its listing is only what the archive says.

### 124. The Plugins tab changes the load order within MO2's limits and marks rows instead of asking; ModTrap replaces its own files from a release package and starts again

`2026-11-23` · DECIDED · `#page #mo2 #release #safety` · refs: MT58, MT56, MT22, MO03§3, MO03§4, WHY§68, WHY§121, DESIGN§17, DESIGN§21

- Plugins. The owner asked for marks on rows, not boxes that ask. So a tick is carried out at once and its
  consequences are shown: the rows of plugins that now lack a master carry ⚠, the Health count rises, and Undo
  is one press. Different from mods (MT56), where the unsafe is asked first: there one tick can switch off many
  plugins at once.
- Dragging within limits, not freely with warnings. MO2 does not let a plugin stand where the game would not
  load it as listed (MO03§3, §4); a list ModTrap wrote otherwise would be changed by MO2 at its next start. The
  server works out the nearest allowed place and says why (`loadcheck.place_moved`); the page shows it.
- The scan's mark is per plugin and asked for, or follows a move: scanning every plugin of a list of 3,700 up
  front would take minutes. Marks of scans are dropped when the order changes, since they describe the old one.
- Self-update: files, not a network. The owner hands ModTrap a release package; ModTrap fetches nothing. The
  package is trusted as the owner's; what is checked is that it is one, stays inside its folder, and is whole
  (its program's mark is the one its `version.json` names, MT22).
- Order of the update: copy the version in use aside; write; compare the mark on disk; start the new program once
  in a process of its own (import only); put the copy back if any of it fails. Then start anew: the new start
  takes over from the running one as any second start does (WHY§68), on the same port, and the open page asks
  the address until another start answers, then loads itself anew.
- The Python inside a package is left alone: the running one holds its files. A package with Python inside
  updates the program only.
- Checked here, on Linux, with a package folder made of ModTrap's own files: box, a wrong file, the release file,
  update, restart, page anew at the new version, 2.4 s. Not checked: Windows, where a running `ModTrap.exe` cannot
  be written over (it is then renamed aside first) and where the new start gets a console of its own, minimised.

### 125. The split view shows the two sections that exist, side by side, and builds nothing twice

`2026-11-23` · METHOD · `#page` · refs: MT59, MT58, MT56, WHY§121, WHY§122, DESIGN§21

- The page's sections already stand in a row that shows one of them. The split view shows two, the mods' and the
  plugins', with a bar between them, and sets the left one's share. No second table: 3,500 mod rows and 3,700
  plugin rows exist once, and every handler (tick, drag, menu, the line of a place, Undo, the dropped file) serves
  both views without knowing which is shown. What asked "is the Mods tab shown" now asks "are the mods shown".
- The line's place is kept in the session's saved view, with the tab and the filters.
- Marking across the sides is done on the owner's click only, never while the lists are drawn again: bringing a
  row into view while they scroll would pull the list from under them.
- Each list keeps its own scroll place in the split view too (WHY§122: the place belongs to the list, not the tab).
- Checked in a browser on a stand-in modlist: the line dragged and its place kept across a re-reading and a change
  of tab, the double-click, a tick on the left and a drag on the right, Ctrl+Z, the marks across the sides, and the
  plain tabs whole again afterwards.
- **Later (2026-11-23).** "Swap sides" turns the row of the two sections round and nothing else; the share that is
  kept is the mods' side's, so that dragging the line and the arrow keys mean the same on either arrangement. The
  button first stayed hidden: it was set before the tab's name was, and the browser check showed it.

### 126. A star-number is a place to go to, not a filter; a found row is brought into view once per number; each search box waits on its own

`2026-11-23` · METHOD · `#page` · refs: MT60, MT59, MT56, WHY§122, WHY§125

- A number names one row, and its neighbours are what the owner wants to see with it: so `*138` leaves the list
  whole and goes there. Narrowing the list to one row would show the row without its place.
- The lists are filtered again for many reasons (a tick, a fold, the page saving its view). Going to the row at
  each of them would pull the list back while the owner scrolls. METHOD: the row is brought into view once for each
  number typed; Enter asks for it again.
- The glow is capped at a hundred rows found by words: a single letter finds thousands, and a glow on all of them
  marks nothing.
- FACT (found by the browser check of the split view): the Mods and the Plugins box shared one short wait before
  filtering, so typing in one within that wait dropped the other's search. Never met while one box was shown at a
  time; each box now has its own.
- METHOD (a note on checking): the stand-in server puts the page together once, at its start. A fix to the page is
  only tried once that server is started again; one run here checked the old page and showed the old fault.
- Checked in a browser on stand-in lists of 3,500 mods and 2,000 plugins: a number inside a folded group, a
  separator's number, a number nobody has, the star alone, words that find ten rows and words that find
  thousands, Enter after scrolling away, both boxes of the split view at once, and the Updater list.

### 127. Column widths are kept by the kind of table and put on every table as it is drawn; the last shown column takes the rest

`2026-11-23` · METHOD · `#page` · refs: MT61, MT59, MT55, WHY§122, WHY§125

- One mechanism for every table, not one per list: the page watches for tables being drawn and gives each its
  lines and its kept widths. Several lists are drawn anew at every change (the Updater list, Installed mods,
  Downloads); nothing had to be added where they are drawn.
- Until a line is first held, a table lays itself out as before. Then the widths it has are fixed, so that only
  the column being set changes. One column must take what the others leave, or the browser spreads the spare room
  over all of them: the last column that is shown has no line and no width. FACT (seen): in the split view the
  plugins' last columns are left out, and with the widths put on all the shown ones every column grew; the
  "last shown" is now worked out each time the tab changes.
- FACT (seen): a list drawn anew while a line was held left the drag working on a table no longer on the page.
  The widths are therefore kept by the table's kind while the line is held, and every table of that kind follows.
- FACT (seen): the Updater list's heading row scrolled away with the list, which put its lines out of reach (and
  out of the browser check's window, which is how it was noticed). It now stays at the top.
- Checked in a browser on stand-in lists, small and of 3,500 mods: a column narrowed and widened, the glow only
  while held, a press on the line not sorting, a press on the heading sorting, the widths after a Rescan, after
  the page was loaded anew, after a search drew the Updater list anew and in the split view, and the double-click.
- **Later, 2026-11-23.** The owner found the fault in "the last shown column takes the rest": setting the column
  before it moved the whole side of the list. Reworked in WHY§128.

### 128. Every column has its own width and the table is their sum; a mod's web is one box for each mod, read in two passes; a conflict is told by masters, not by what is inside a record; the picture goes through the server

`2026-11-23` · METHOD · `#page #model #updates #safety` · refs: MT62, MT61, DESIGN§23, DESIGN§24, TL01§32, WHY§127, WHY§121

**Columns.**

- FACT (the owner's screenshot at 0.3.54, and seen here): with one column left to take the rest, a line next to
  it changed two columns at once, and the browser moved the rest of the row to fit. A table whose every column
  has a width, and whose own width is their sum, has nothing left to share out: a line then moves one edge.
- The line that glows down the list while a line is held is one element laid over the page at the column's edge,
  not a border on thousands of cells: on a list of 3,500 rows a border changed per cell was slow to follow.
- Columns change places by moving cells, row by row, when a table is drawn: a table has no order of columns apart
  from its cells. Each cell carries the number of the column it was built as, so sorting, the split view's
  left-out columns and the kept widths go by that number wherever the column stands.
- A heading starts to move only after the mouse has gone a few pixels, so a press still sorts.
- Rejected: laying the tables out as grids, to reorder by style alone. Every table would have had to be rebuilt,
  and the fixed heading rows and the drop lines of MT56 and MT57 rest on rows being rows.

**The web.**

- Two passes, because the headers are in memory and the files and records are not: the first answer is there
  with the click, the second in the seconds §21's scanner takes. One request that waited for both would have
  shown nothing for those seconds.
- One box for one mod. Rejected: one box for each tie. A patch needs the mod, overwrites a file of it and changes
  its records: three boxes for one mod, and a line count that grows with them, read worse than one box with its
  kinds listed when pressed.
- Sides by meaning, not by a layout that arranges itself. Rejected: a force-laid graph. It puts boxes somewhere
  different at every opening, needs a library or a good deal of code of our own, and says nothing by position.
  Left and right for what a mod stands on and what stands on it, above and below for who wins, can be read
  without the colours.
- LIKELY: on the owner's list a framework has hundreds of mods that need it. A side therefore shows a fixed
  number of boxes, the weightiest first, and lists the rest; the kinds can be switched off to give the others the
  room.
- A patch is told by two signs together (the whole mod depends on this one; its name says patch, fix, tweak or
  the like). FACT (the stand-in list): by masters alone, a mod built on two others and a patch between them look
  the same. Told by name alone, any mod with "fix" in its name would be a patch for everything it needs.
- A conflict is told by masters: two plugins change the same record, neither names the other as a master, and no
  active plugin names both. That is what can be read from headers in the time a pop-up may take. It is not
  xEdit's conflict: xEdit compares what is inside the records. The box says which of the two it is.
  SPECULATION: on a large list most pairs flagged this way are harmless, because the later plugin was made from
  the earlier one's values without naming it; the count is a list of places to look, not of faults.
- The drawing is the page's own: boxes are buttons laid over lines drawn as SVG paths. The SVG namespace is taken
  from the browser, so the page's source still holds no outside address (the page test's rule).

**The picture.**

- FACT (TL01§32): Nexus's public service names a mod's preview picture without a key, and the picture hosts
  serve it without one; GitHub draws one for any repository.
- The page may load nothing from outside (DESIGN§2), and that rule is worth more than a picture. So the server
  fetches it and the page gets it as data: the content policy is unchanged.
- Only from the three hosts TL01§32 names, only https, only a file whose first bytes are a picture's, with a size
  limit; the owner's Nexus key is never sent there (`Net.picture` sends no key at all).
- Kept a month in ModTrap's own folder: the sites are asked once per mod, and only for a mod whose web is opened.
  Never for the whole list: 3,500 requests for pictures nobody looks at.
- LoversLab and other sites: no picture. Theirs need a signed-in visitor, and ModTrap signs in nowhere.

**Checked** in a browser on an invented list with one busy mod (needs, dependants, patches, a tool's output,
files overwritten both ways, conflicts, settled conflicts): the kinds and their counts, the boxes by side, the
"+ N more" lists, a kind switched off and on, a box's details, a mod put in the middle and back, the link and the
picture, Esc. **Not checked:** the picture against the live sites from ModTrap itself (this session cannot reach
them; the addresses were read by a session that can), and the time the second pass takes on the owner's list.

### 129. The console is hidden, not done without; only a console of ModTrap's own is hidden

`2026-11-23` · METHOD · `#launcher #safety` · refs: MT63, MT64, MT51, MT22, DESIGN§24, WHY§120, WHY§124

- FACT (`modtrap/logbook.py`): every line the console shows is also kept for the page's Log. Nothing reads from
  the console, and no feature waits on it. The owner's "do we need a terminal": no.
- Rejected: starting Python with no console at all. ModTrap starts console programs (7-Zip, Windows' tar, its
  own helper for pressing a tool's button); a console program started by one that has no console gets a new
  window of its own. A hidden console is inherited instead, and nothing flashes up. It also leaves every print
  in the program working as it does.
- The launcher starts the console hidden, and ModTrap hides it again itself: LIKELY needed where Windows hands
  new consoles to its Terminal program, which may not take "hidden" from whoever starts it. SPECULATION: on such
  a PC the window may show minimised instead of not at all; not tried here.
- Whose console: the launcher says "this console is yours" with a switch; and a ModTrap that is alone in its
  console owns it too, which covers the start after a self-update made by a version that did not know the switch.
  A console with a command prompt in it has two programs, and is never hidden: hiding the owner's own window
  would be a fault of a worse kind than a window too many.
- A start that fails would vanish with a hidden window: it is shown instead and waits for a key.
- With no window, a closed tab leaves nothing to see of a ModTrap that still runs. It is harmless (the next start
  takes over, WHY§68), and whether it should end itself is the owner's to say: MT64.
- **Not checked:** any of it on Windows. The launcher is built here and its source read by a test; what a hidden
  console does on the owner's PC is for the owner's first start to show.

### 130. An evaluation compares files and reads formats' marks, and says what it cannot tell; a double is told by its page and its file's name, not by its page alone; the list is scanned in one pass from the top

`2026-11-23` · METHOD · `#adding #model #page` · refs: MT65, MT66, MT9, DESIGN§25, TL01§33, WHY§121, WHY§128

- FACT (the owner's screenshot at 0.3.55): a mod dropped on the list overwrote one file each of 25 mods, and the
  box could only list them. Whether that matters could not be read from it. LIKELY those 25 files are one paper
  (a read-me or the like) that many mods carry under one name; the evaluation now says so in one line.
- FACT (`api._new_staged`): a new mod whose name is taken was named "name (2)" without a word. That is how the
  owner got a second copy of a mod. The check now comes before anything is installed.
- What can be told without a tool, and is: whether two files are the same (byte for byte, within a budget of
  bytes and time); what kind a file is, by its path; what format it is in, by its first bytes (TL01§33); which
  version of the game is installed, from the game's program file.
- What cannot, and is said in the box: what two plugins change inside one record; whether a mesh and a texture
  from two mods fit each other; whether a script that replaces another is the better one. For these the finding
  says why it matters and where to look.
- Levels by what the modding community's own guides report (TL01§33): an older-format archive and an older-format
  animation are faults; an older-form plugin is mostly harmless, so it is a note; an older-format mesh is worth a
  look.
- A double is not "the same page at Nexus": FACT (the owner's list, WHY§103) one page gives a main file and its
  patches, installed as several mods. It is the same page and the same file name without its version, or the
  name the file would give its mod. Tested: another file of the same page is not a double.
- The whole-list scan lists every enabled mod's files once, from the highest priority down, keeping for each path
  only a number for the path and the mod that wins it. A mod is then weighed against all the mods above it in
  the same pass. Rejected: comparing every pair of mods. Rejected for the scan: reading files' content; only
  archives' first bytes and script extender plugins are opened.
- Not built: a whole-list table of records two plugins both change. By the rule of WHY§128 a large list has
  thousands of such pairs; it would be a list nobody can act on. Said to the owner.
- "Show it in the list" missed because the mod's card opens above the list after the row was brought into view,
  which moves the list under it. The card now comes first, and the row is looked for again after the page has
  settled.
- Checked in a browser on a stand-in list: an install weighed, the two tabs, a second drop of the same mod asked
  about, cancelled and taken as an update, the menu's entries, the Scan button and the Health tab. **Not
  checked:** the time the deep scan takes on the owner's list (bounded at four minutes, and it says when it was
  cut short); the formats' marks against real files, which are not to hand here (TL01§33 says what each rests on).

### 131. A closed tab is told by the page's goodbye, not guessed; a worker in the browser and a link of ModTrap's own kind bring it back; the link carries nothing

`2026-11-23` · DECIDED · `#page #launcher #safety` · refs: MT64, MT63, MT22, DESIGN§26, DESIGN§2, WHY§68, WHY§129

- MT64's worry was a wait that is wrong. The page's goodbye (sent as the page is left) removes most of the wait:
  the last page gone is known in seconds. A reload sends it too and is back at once, hence eight seconds' grace.
  The four-minute silence is only for a browser that ended without a word.
- LIKELY (browsers' own behaviour, as their makers describe it): a hidden tab's timers are slowed to about one a
  minute, so a page that still lives asks at least that often; a tab put to sleep runs nothing, and is told
  first, so it can say so and is then not counted as gone.
- A wrong close must cost nothing: ModTrap closes only with nothing in hand, the session is saved as Quit saves
  it, and the page can start it again.
- A page cannot start a program. The ways there are: a link of a kind Windows knows a program for; or a helper
  that keeps running to be asked. A helper is the unseen program MT63 took away. So: a link.
- The link is entered without "%1": Windows then hands nothing of the link to the program. FACT (tested on the
  entry's text): the command is the program's path and one fixed word. A link that could carry a folder or a
  switch would let any web page that the owner allowed once choose what ModTrap opens.
- A tab brought back with ModTrap gone shows the browser's own error unless something of ModTrap's answers in
  the browser: a service worker. It answers only a page being asked for, only when ModTrap does not, and only
  with the one small page it kept. Rejected: keeping ModTrap's own page in the browser. It holds the start's
  token, and a page from an earlier start is of no use.
- The content policy gains `worker-src 'self'`, for that one file; nothing else changes.
- The kept page waits ten seconds before it opens the link by itself: a ModTrap that is starting anyway (after
  its own update, or by hand) is there within that. After a Quit it does not open it by itself at all.
- Checked in a browser against a real start of ModTrap here: a reload does not close it; ModTrap ended under the
  page brings the kept page; ModTrap started again brings its page back by itself; the tab closed ends ModTrap
  in about eight seconds; a tab opened with ModTrap gone shows the kept page. **Not checked:** the link itself
  and the registry entry (Windows only), the browser's question, and a tab put to sleep by a real browser.

### 132. An uninstall is a move on the same drive; every list change is a job with its own Revert, shown for good; a mod is renamed as MO2 renames it

`2026-11-23` · METHOD · `#page #safety #model` · refs: MT66, MT9, MT56, DESIGN§27, DESIGN§11, MO03§6, WHY§121

- The removed mod's folder goes beside MO2's mods folder, not into the session's folder: ModTrap's own folder is
  on the system drive, a modlist usually is not, and a move across drives is a copy of gigabytes followed by a
  deletion. Beside the mods folder it is a renaming: instant, and nothing is ever deleted. MO2 does not look into
  a folder it does not know.
- The lists of every profile lose the mod's line, since MO2 drops a line whose folder is gone when it next loads
  that profile; doing it at once keeps what ModTrap reads and what MO2 will show the same. Each profile's line
  (its sign, and what it stood before) is in the job's record, so that a Revert by line can put it back there.
- A plugin leaves the load order only if no other enabled mod has a file of that name: where one has, the plugin
  is that mod's from now on, as it would be in MO2.
- FACT (`listjob`): moves and separator renames were jobs with history entries already, and `list_undo` took a
  job's name; only the newest one's Undo was on the page. The History now lists all of them, so nothing new had
  to be built to make them revertable, only shown.
- A Revert out of order works by the rule of DESIGN§11 (own lines only, when the lists changed since). FACT
  (seen in the browser check): an uninstall reverted, then an older rename reverted with a move standing between
  them. A job whose record names a mod by a name it no longer has says so and leaves that line.
- A mod is renamed as MO2 renames it (MO03§6), no more: FACT (MO2's source at the commit of MO03,
  `src/mainwindow.cpp:2495-2497`) MO2 writes the new name into the profiles' lists and nothing else, so its own
  settings that name a mod (the mod a tool writes into) are left pointing at the old name. ModTrap therefore
  refuses to rename such a mod and says why.
- ModTrap's own notes keyed by a mod's name (a source link, a favourite) are carried to the new name, and back on
  Revert. Not carried: the records of earlier jobs, which name the mod as it was then.
- The menu's Uninstall is the same for a mod ModTrap installed: one way, always revertable from the History. The
  install's own "Uninstall" (on the Installer tool and in the install box) still puts the lists back as they were
  before that install.
- Checked in a browser on a stand-in list: a mod renamed, moved, another uninstalled after the question, the
  History's table, the uninstall and the rename reverted out of order. **Not checked:** on Windows, where the move
  is `os.rename` on one drive; and the second question for an original mod, which needs a list file (tested at
  the route).

### 133. A name is a title and a version from the most trustworthy source that has one; it is asked while the archive unpacks; a side of the web grows the sheet, not the boxes

`2026-11-23` · METHOD · `#adding #page #updates` · refs: MT67, MT65, MT62, MT40, DESIGN§28, DESIGN§23, TL01§31, WHY§130

- FACT (TL01§31, and the owner's example): a download from Nexus is named title, the mod's number, the version,
  the time of upload and a code. `from_archive_name` took the title and the version from it already; the name
  ModTrap gave used the title alone, and "(version)" for an update.
- The order of the three sources is by what each is: the source's word is about this very file; the file's name
  was written by the site but can be changed by anyone; a version inside the archive is the author's and often
  left at an older number. FACT (seen in mods' installer files generally): many carry none.
- A version at the end of a name from elsewhere is taken only where it is written as one (digits, a dot, digits):
  "Lantern 2" is a title, "Lantern 2.1" a title and a version. Tested on both forms of Nexus's names and on
  plain ones.
- An update keeps the title of the mod it replaces, cut at that mod's own version: the owner's names for mods
  (and a modlist author's) are theirs, and a download's name is often another.
- The name is asked when the file is taken in, not when it is unpacked: the question is answered while the
  archive unpacks, and an install then waits for nothing. The price: a version that only a file inside tells is
  not in the offered name; it renames the mod afterwards unless the owner gave a name.
- Changing a name after the mod was read would leave what was read under the old name, so the kept reading is
  dropped and made anew.
- For the Updater the name has to be known before there is a file. The page asks, and the server keeps the wish
  for that mod until the update's file is taken in; it is used once.
- A double is now also told by the title in a mod's name ("Lantern 2.1" for a file "Lantern … 2.2"), since mods
  no longer carry the bare title; and a mod's version by its name where nothing else records it.
- The web: a side shown whole adds rows or columns and makes the sheet larger; the boxes keep their size and the
  frame scrolls. Rejected: shrinking the boxes to fit, which makes every name unreadable at a few dozen; and
  laying a long side out in one line, which makes the picture many screens long for a mod that hundreds need.
  Columns of twelve keep a side of a hundred within about eight columns.
- Checked in a browser on stand-in lists: the name offered for a download named as Nexus names it, Enter keeping
  it, a name typed over it, a taken name said and asked again, an update offered "Title newer-version"; a side
  of the web opened (rows below, a second column to the right), no boxes overlapping, folded again. **Not
  checked:** the Updater's question against a live update (it needs the sites), and a side of several hundred
  boxes for how it reads.

### 134. On the owner's list nearly every "same plugin twice" was a patch; a double is a title, and what is said of it depends on whether it is in the game

`2026-11-23` · FACT · `#model #page` · refs: MT68, MT65, DESIGN§25, WHY§130

- FACT (the owner's session file at 0.3.57 and their screenshot): the look at opening gave 132 findings on a list
  of 3,579 mods: 129 "worth a look", nearly all "a plugin of the same name in two enabled mods", where the winner
  was a patch, a fix or the list author's own version of the mod. A list of 129 warnings that are all as intended
  hides the one that is not.
- FACT (same): the one "likely fault" was one file installed as two mods of different names, each a part of it:
  intended. And an older version left disabled beside the newer one was told with the same words as a fault.
- So a double is no longer "the same file" or "the same plugin's name" but the same title, compared whole. What
  is said depends on what is in the game: nothing of a disabled older version is (obsolete, a note); nothing of
  an enabled mod wholly inside its newer version is (redundant, a note); files of two enabled versions that do
  not cover each other are (worth a look).
- "Wholly inside" is looked at for the pair alone: the lower mod's files are listed and the higher mod is asked
  for each. That is a few pairs on a list, not a listing of every mod.
- Two mods from the same file with different titles are compared as well, but only told where the lower is
  disabled and older, or wholly inside the higher: a part of a file installed on its own is neither.
- FACT (same log): the look took 32 to 35 seconds at the first opening and ran twice at once, once from the
  opening and once from the page asking; the second opening took 1.5 seconds. The time went into reading every
  mod's own record from a cold disk and listing every mod's script extender folder. The folders are no longer
  listed, the look runs in a thread of its own, once for a modlist as read, and the page is told "looking".
- FACT (same log): ModTrap's own update from 0.3.54 over 0.3.55 to 0.3.57 worked on the owner's PC, and a mod's
  picture was fetched from its site there (the first time either ran outside this session's stand-ins).

### 135. What fits is reckoned on the sheet before it is drawn, at the smallest size a box can be read at

`2026-11-23` · METHOD · `#page` · refs: MT69, MT67, MT62, DESIGN§28, WHY§133

- FACT (the owner's screenshot at 0.3.59): a mod with 25 mods on one side showed seven and "+ 18 more" in a
  window with room for all of them.
- The picture is a sheet of boxes at fixed places, scaled to its frame. Whether a set of sides fits is therefore
  a sum: the sheet's width and height for that set, times the smallest scale at which a box holds two lines
  (0.78 of the sheet's own size), against the room the window leaves the picture. Nothing has to be drawn to
  know it.
- The room is the window's height less what stands around the picture (measured once the box is drawn, reckoned
  before), and the frame's width.
- A column holds as many boxes as that height takes, so a side that fits in one column is not split in two.
- A side that fits has no "Show fewer": there is nothing to gain by folding it. A side opened by hand keeps it.
- Checked in a browser at three window sizes on the stand-in list: at the two larger ones all 32 mods are boxes,
  nothing scrolls and nothing overlaps; at the small one the sides keep their "+ N more".

### 136. MO2's Conflicts column is a property of the whole list, so the whole list is listed once and kept; a new plugin goes before the tools' outputs whatever it changes

`2026-11-23` · METHOD · `#model #page #adding` · refs: MT70, MT65, MT62, DESIGN§29, DESIGN§16.3, MO04§2, WHY§130, WHY§134

- FACT (MO04§2): a mod's state in MO2's Conflicts column depends on every enabled mod's files: MO2 has them all
  in one tree. There is no way to tell it for one mod from that mod's folder. ModTrap lists every enabled mod's
  files once, highest priority first: a mod's files then meet only the files of the mods above it, which says at
  once what it loses, and marks those mods as winning.
- The listing here follows MO2's tree (MO04§2), not ModTrap's own idea of a mod's files: no limit on a mod's
  size, hidden files left out, the three things MO2 takes out at a mod's top left out. Papers elsewhere in a mod
  count, as they do in MO2.
- LIKELY (the owner's log: the look at the mods' own records took 34 s on a cold disk, 1.7 s after): the first
  listing of a large list takes tens of seconds to minutes; later ones seconds. So it runs off the page, and each
  mod's list is kept while the folder looks the same from above. A change deep inside a mod that leaves its top
  entries' times alone is not seen until "Rescan": said in the design.
- The marks are ModTrap's own (a sign and words in the tooltip), in MO2's four states. MO2's icons are part of
  MO2 and are not copied.
- The plugins' groups follow the mods' separators because that is what the owner's MO2 shows. The load order is
  not sorted by separator, so a group is a run, and a name can come again. A plugin whose mod is disabled has no
  separator to go by and stays in the run it stands in, or every such plugin would break a group in two.
- **The owner's question, how a new plugin is placed.** FACT (`adding.tail_start`, and the owner's log: the
  plugin went to position 3733, directly before the first tool-made plugin): last among the plugins installed by
  hand, before the run of plugins the modlist's tools made; a master at the end of the masters; never before its
  own masters. It does not weigh conflicts. Why not: a tool's output is made from the load order before it, and
  a plugin after an output overrides what the tool built without the tool knowing of it; "before the outputs,
  then run the tools again" is right whatever the plugin changes. Where a plugin should stand among the hand-
  installed ones is a question of what it is meant to win over, which no file says; the owner drags it there.
- Checked in a browser on a stand-in list: the three columns, the marks against the mods' files, a press on a
  mark opening the web with the conflict kinds alone, the list sorted by a new column, the plugins' groups
  folded, unfolded and searched. **Not checked:** the time of the first listing on the owner's list, and the
  states against the owner's MO2 mod by mod (the screenshot shows MO2's marks, not which state each is).

### 137. The page greys what the server already refuses; a re-read keeps the page; a run of the load order is not a separator's group; two saves at once shared one temporary file

`2026-11-23` · METHOD · `#page #safety #sessions` · refs: MT71, MT70, MT14, DESIGN§30, DESIGN§8, WHY§121, WHY§136

- FACT (`listjob._begin`, `addjob`, `changes`): every job that changes MO2's lists begins by seeing MO2 closed
  and refuses otherwise. Nothing could be written under an open MO2 before this change. What was wrong was the
  page: a tick with MO2 open asked to close MO2, or closed it without asking where the setting said so. A tick is
  not a reason to close a program the owner is working in.
- So the page now says no and does nothing, for the changes that are made at once. Flows that take many steps and
  name the closing of MO2 in their plan (the demaster) keep it.
- One rule on the page for all of them: a path of the API that changes the lists is not sent while MO2 is open,
  and the buttons are marked by their words as the busy-gate marks its own (WHY§100), so a new button of that
  kind is caught without being listed.
- FACT (`renderState`): every change set the page to "reading", which hid the summary, the tabs and every tab's
  content and showed the first-opening page, then drew everything again. The lists kept their scroll place only
  because it was put back after. The page now knows a modlist it has shown before, and leaves it on show.
- FACT (the owner's screenshot at 0.3.61): grouped by runs of the load order, "Outputs", "Demaster" and others
  headed many groups, because the load order goes back and forth between the mods of different separators. One
  group for each separator has no doubles; the price is that a group's plugins are then not always neighbours in
  the load order, which its line says.
- FACT (MO2's source at the commit of MO01, searched for it): MO2 itself has no groups in its plugins' list. The
  owner's MO2 shows groups with names that are not the mods' separators, as runs of the load order. Where they
  are kept is not known; the session's pack now carries the names of the files in the profile's folder.
- FACT (the owner's log at 0.3.61): "the session's log could not be saved: PermissionError" once, as the logs
  were packed. `write_atomic` named its temporary file by the program's number alone, so two threads saving the
  same file at once wrote and swapped one temporary file between them; and Windows refuses a swap while the old
  file is held open by a reader. Nothing was lost (the log is in memory and saved again), but both are closed:
  a name for every write, and the swap tried again.
- FACT (same log): MO2's columns on the owner's list: 3,716 entries' dates and notes in 1.6 s; 593,153 files of
  3,487 enabled mods listed in 5.7 s; 672 mixed, 489 overwriting, 632 overwritten, 87 redundant.
- Checked in a browser with a stand-in MO2 "open": ticks greyed and stopped with a word, the menu's changing
  entries off, nothing changed; then closed: a tick works, and on the 3,500-mod list nothing was hidden while it
  was read anew and the bar was on show.

### 138. A progress symbol is not decoration: it moves even where the PC asks for less motion

`2026-11-23` · FACT · `#page` · refs: MT72, MT71, WHY§61

- FACT (the page's styles): three rules switched animations off where the browser reports that the PC asks for
  less motion (Windows' "show animations" set to off): for the turning circle, for a going step's mark and a live
  run's dot, and for the bar of MT71. All the circles are one style, used in 25 places of the page.
- FACT (the owner's screenshot): on the owner's PC the circle stood still everywhere, which means that setting is
  off there. A still circle beside "Reading your modlist…" says the opposite of what it is there to say.
- The wish for less motion is about movement that is for show or that sweeps across the screen. A small symbol
  turning in its place is the message itself. So those four keep moving; the flash of a row gone to stays off.
- Checked in a browser set to ask for less motion: the circle's animation is in force and its angle changes
  between two looks; the dot and the bar likewise.

### 139. MO2's plugin groups are an extension's file; a group is a run, so a new plugin's group follows from where it stands

`2026-11-23` · FACT · `#model #page #safety` · refs: MT73, MT71, MT70, MO05, DESIGN§31, WHY§137

- FACT (MO05§1, §2): the groups of the owner's plugin list are not MO2's own. An extension that replaces MO2's
  plugin list keeps them in the profile's `plugingroups.txt`, one `name|group` line for each grouped plugin,
  rewritten whole whenever MO2 writes its plugin lists. Found by the listing of the profile's folder that the
  session's pack has carried since 0.3.62 (MT71's open note).
- FACT (MO05§3): a group is not stored as a thing. It is the run of neighbours in the load order with the same
  name. A plugin with a name its neighbours lack is a group of one; a name carried by plugins apart is two groups.
  This is the very thing the owner called duplicates in MT71, there by ModTrap's own doing; in MO2's own data it
  can only be shown as it is.
- METHOD: so a new plugin's group cannot be chosen apart from its place. The place is settled first (MT70: before
  the tools' outputs), then the group follows: inside a group, that group; between groups, the name of the mod's
  separator, which is what the page showed before and what the owner expected to find in MO2. Rejected: always
  the separator's name (it would cut a group in two where the plugin lands inside one, and begin a second group of
  a name already in use elsewhere); always the group of the plugin before (a new plugin would silently join the
  last ordinary group, whatever it is). Left without a group where neither rule gives a clean answer: the owner
  sees it under "No group" and says.
- METHOD: the writer changes single lines and keeps every other byte, at the line's place by name, so that a
  Revert by lines is possible once MO2 has written the file anew, and a stale line is never a harm (MO05§2).
  ModTrap never makes the file: where it is absent, that MO2 has no groups, and a file made by ModTrap would be
  read by nothing.
- FACT (the module loaded at start): reading the groups must not load the writer of MO2's lists, which is loaded
  only where changes are switched on (MT8, a test holds it); the reader uses the instance's own file reading, and
  the writer is brought in inside the one function that writes.
- METHOD (the web's conflicts): "neither is the other's master" is the mark of a conflict between two plugins
  made by hand. A tool's output is made from the whole load order and holds the winning record of each, with
  masters only where a record points at another plugin: by that mark alone it conflicts with hundreds of mods,
  which is what the owner saw on ModTrap's demastered copies of the outputs. The later plugin being tool-made
  decides it; the earlier one being tool-made does not, because a hand-made plugin after the outputs does undo
  them. A patch told only by its name is not counted as tool-made: its name says what it was made for, not that
  it saw the plugin it overrides.
- Checked: on a copy of the owner's file the rule gives the one plugin without a group the name of its mod's
  separator, the writer adds one line at its place and keeps the other 3,742 lines as they were, and taking the
  group away again gives the file back byte for byte. Not checked on the owner's PC: that MO2 shows the new group
  after the next start, and the web of the demastered mod with the new rule.
- Not done: a demaster's Revert that puts back plugin lines MO2 had dropped (DESIGN§11) does not put back their
  groups, which MO2 dropped with them. The groups file is not among that job's safe copies, and nothing is written
  without one (MT14). Such a plugin shows under "No group", for the owner to give it one.
- Later (2026-11-23, MT74, WHY§140): done. A demaster takes the groups file into its safe, and its Revert puts the
  groups back; and the web's rule for ModTrap's copies no longer rests on who made the plugin.

### 140. A demastered copy inherits its plugin's place among the others; the rule of MT73 looked at who made the plugin, not at what the demaster changed

`2026-11-23` · METHOD · `#model #page #safety` · refs: MT74, MT75, MT73, DESIGN§32, DESIGN§23, DESIGN§11, MO05§2, WHY§139, WHY§83

- FACT (the owner's screenshot of 0.3.64): the web of ModTrap's demaster mod still showed 355 mods in conflict.
  Its seven plugins are two tools' outputs and five hand-made plugins, most of them the list author's own patches
  (the plugins' groups in MO2 say so: two stand in the outputs' group, the five in three ordinary groups of the
  load order). WHY§139's rule asks whether a tool made the later plugin, so it cleared the two and left the five.
- METHOD: the owner's point was never about tools. It was that these files only stand in for the originals. That
  is exact: the demaster's change run takes a master out and leaves every record the plugin overrides as it was
  (the dry run and the check after it hold that), and the copy takes the original's place in the load order by its
  name. So for any other plugin P, the set of records the copy and P both change, and which of the two loads
  later, is what it was between the original and P. Whether that was ever a conflict is a question about the
  modlist (MT75), not about the demaster. The web of ModTrap's own mod is where the owner looks for what ModTrap
  did, so there it must not be told as a conflict.
- METHOD (the limit): "as it was before" is only true of a plugin that was there before. The copy's file time is
  when the demaster made it; a mod's folder is made when MO2 or ModTrap installs it, and made anew by an update
  (MO04§3, the Installation column). A mod whose folder is younger than the copy is weighed by the ordinary rules.
  Not caught: a mod installed before the demaster and enabled only after it. The demaster's safe folder holds the
  lists of that time and could say; left until it matters.
- Rejected: telling such pairs by a kind of their own. The ten kinds each have a colour and a side of the picture;
  "records it changes" with the reason beside it says what is the case.
- Rejected for now, and asked as MT75: taking the author's hand-made patches out of the conflicts wherever they
  stand. That needs to know what came with the list, or a guess by how many mods a plugin is built on.
- METHOD (the gap of WHY§139): a demaster takes MO2's groups file into its safe with the three lists, so that the
  groups of that time can be read when plugin lines MO2 dropped are put back (`groups_back`). A demaster made
  earlier has no such copy: there the only thing known is where the plugin stands now, so it gets the group it
  stands inside, and none at a group's edge, where two answers are possible. MT14 is kept by taking the copy at
  that moment, before the write.
- Checked: on invented lists, both directions and both sides of the web, the mod that came since, the Revert by
  lines to the byte with the groups' copy, and the Revert of a demaster without one. Not checked on the owner's
  PC: the web of the demaster mod, where every mod of the list is older than the copies and the mods installed on
  the 23rd are younger.

### 141. Which records two plugins both change predicts no fault, so it is told as none

`2026-11-23` · DECIDED · `#model #page` · refs: MT76, MT75, MT74, MT73, MT62, DESIGN§33, DESIGN§23, WHY§140, WHY§139

- FACT (three rounds with the owner's list): every conflict ModTrap told was a false alarm. 129 notes on doubles
  (MT68), 355 conflicts on the demaster mod (MT73), the same again after a tool's output was let off (MT74). Each
  round made the rule finer and left the next class standing.
- FACT (what ModTrap reads): for a record, that a plugin holds it; for a file, its name, size and first bytes. Not
  what is changed inside a record. Whether the later plugin's record carries the earlier one's change, or drops
  it, or should drop it, cannot be seen from that; "neither is the other's master" was a guess at the author's
  intent, and on a curated list of thousands of plugins the guess is wrong nearly every time, because the load
  order itself is the author's settling of it.
- FACT (the game): two plugins changing one record never stop the game: the last one loaded is used, whole. What
  stops it, or a plugin, is of another kind and can be read exactly: a master that is not there, not active or
  loads too late, too many plugins, a file in a format this game does not read, a navmesh deleted.
- DECIDED (the owner, MT76): so the first is not told and the second is. A warning that is wrong most of the time
  teaches the owner to pass over the ones that are right.
- METHOD (what went): the record pass of `modweb.far` with the rules of WHY§139 and WHY§140 on top of it, the
  page's four kinds and their side of the picture, the automatic scan and its marks. What stayed is on request:
  `loadcheck.overrides` behind "Scan what it overwrites", told plainly, for the owner who wants the facts.
- METHOD (the evaluation's levels): a finding about whose file wins is information; the one such finding with a
  crash behind it is a skeleton that wins with fewer bones, and it is a warning only where the sizes say so.
- Later readers: the web's record pass is in the history of this file's repository at 0.3.65, if a way to read
  inside records ever makes it worth having again (MT23 is the open question nearest to it).

### 142. xEdit settles what bytes could not, when asked; a leftover in a tool's plugin is the owner's to leave

`2026-11-24` · DECIDED · `#tools #steps #xedit #page` · refs: MT23, MT24, DESIGN§34, DESIGN§16.5, TL01§13, XE01§18, XE01§19, WHY§73, WHY§77, WHY§78

- The owner, asked what MT23 and MT24 are and given the recommendations: "as recommended". So MT23 (a), a check of
  its own started from the tool's step, and MT24 (b), the values shown and the choice left to the owner.
- METHOD: the comparison by meaning already runs on the owner's PC: the dry run's script turns a part of a record
  into text of its names and values (`Shape`), leaving out unused bytes, and compares texts (XE01§18, WHY§77). The
  new script uses that same function on three versions of a record instead of two. It calls nothing the dry
  run's and the record check's scripts do not call; a test holds it to that, and to balanced blocks and declared
  names, because no xEdit runs where ModTrap is written.
- METHOD: which versions. The dry run's stake (XE01§19) was told from the plugins it loaded, and narrowed
  afterwards with ModTrap's own reader over the whole load order (WHY§77). With the whole load order in xEdit,
  the script finds for itself, among the plugins no tool made, the last leaving plugin and the last that stays;
  only where a leaving plugin has the last word can a tool's copy owe anything to it.
- FACT (what the three answers mean): "as the mod" is proof by meaning, where bytes gave proof only for tools
  that write as xEdit does. "As the next in line" clears a plugin, a patcher's too: that is the gain TL01§13
  named. "Neither" stays open: a value worked out by the tool, from which of the two nothing shows; it is said
  as it is, with the records and values, and the tool is still told to run "to be sure".
- DECIDED: one run for all tools' plugins. Loading the load order is the cost (minutes on the owner's list);
  reading a few more plugins adds little, and one result serves every tool's step.
- DECIDED: a check counts for a plugin only while the plugin is the same file. The tool's own run writes it anew,
  and the old check says nothing of the new file.
- DECIDED (MT24): the choice is the owner's and is kept on ModTrap's side, not as a tick in the browser, because
  ModTrap's run of the tools one after another must pass a left tool over. The step's state for everything that
  counts open steps is "not needed"; the page words it "left by you until its next run".
- Limit: the check needs the mods enabled. After a demaster is in place it cannot be made without a Revert; the
  step says so. A check made before stays valid across the demaster, since the tools' plugins do not change by it.
- Not checked on the owner's PC: the script itself. Its first real run is the owner's; a failure shows as the
  check failing with xEdit's own message, and changes nothing.

### 143. A greyed control must say why where it is pressed; a group is made of picked plugins, and a drop on its line is the one way to join at its edge

`2026-11-24` · METHOD · `#page #model` · refs: MT77, MT73, MT71, MT58, DESIGN§35, DESIGN§31, DESIGN§30, MO05§3, MO05§4, WHY§137, WHY§139

- FACT (the owner's pictures): MO2 was open beside ModTrap. By MT71 the menu's entry was greyed and the drag did
  not begin. The reason was in the entry's tooltip, which a browser does not show for a disabled button, and in
  the line under the header, far from the pointer. The owner took the features to be missing and asked for them.
- METHOD: the reason belongs where the press is. A menu gets a line of words and, as its first entry, the one
  thing that helps ("Close MO2…", which asks first). A drag that cannot begin tells it once the pointer has
  moved far enough to be a drag. The greying itself stays: MT71 is the owner's own rule, and the server refuses
  the change in any case.
- Rejected: letting the entries stay live and closing MO2 as part of them. That is what MT71 took away ("ModTrap
  no longer closes MO2 for these by itself").
- METHOD (creating a group): MO2 makes a group of the rows that are picked. ModTrap's list had no picking, so a
  group could only be given plugin by plugin. Picking is the browser's usual one (click, Ctrl, Shift); a plain
  click still opens the plugin's details, so nothing that worked before changes.
- FACT (MO05§3): a group is a run of neighbours. Picked plugins that stand apart become several groups of one
  name. That is not refused, because the owner may be about to drag them together; it is said in the question.
- METHOD (the edge): WHY§139's rule for a move joins a group only between two of its plugins, as the extension's
  own rule does (MO05§4), so a plugin could not be put first or last in a group by dragging. The group's line is
  a place no plugin has, and letting go on it has one plain meaning: before the first plugin, and into the group.
  The move's job takes the group named only where the plugin then stands beside that group; where MO2's limits
  put it elsewhere, the ordinary rule decides. Where the plugin already stands directly before the group, nothing
  moves and only its group is written.
- Checked in a browser on an invented list: the menu with MO2 open and closed, the drag's word, two plugins
  picked and made a group, a drop on a group's line. Not checked on the owner's PC.

### 144. A bulk list is a queue and a run of small jobs, not one big analysis; a drag's aim must follow the list as well as the pointer

`2026-11-24` · METHOD · `#page #model #safety` · refs: MT78, MT67, MT65, MT57, MT54, MT53, DESIGN§36, DESIGN§16, DESIGN§18, WHY§143

- FACT (the owner's session): about twenty archives were dropped on the Installer tool, ten at a time. That page
  reads every mod on it against the whole modlist and against each other at every change (DESIGN§16), which is
  why it stops at twenty; its mods also stay on it after they are installed. Both are right for one mod looked at
  closely and wrong for many put in at once.
- METHOD: the bulk list keeps the two things apart. Taking in (copy, unpack, name, installer's answers) needs no
  analysis and no limit: a queue, one file at a time, and a route that tells how any number of unpacked archives
  stand without reading them against the modlist. Installing needs the analysis, because the plan rests on it
  (what a mod needs, where its plugins go): it is made for a lot of eight at a time, at the place chosen, with the
  same two routes the Installer tool uses. So nothing new decides where a plugin goes or whether a mod can go in.
- METHOD (order): every lot is placed directly before the same entry of MO2's list, so each lot comes to stand
  after the one before it and the bulk list's order is the order in MO2. Eight is a balance: one reading of the
  modlist for each lot instead of each mod, and a lot small enough that its Uninstall is not a blunt tool.
- METHOD (faults): a refused lot says only that something in it is wrong. Each of its mods is then tried by
  itself, and a mod that fails for want of a master is tried once more at the end, after the others are in. A
  fault that would stop every lot (MO2 open, the probe) ends the run instead of being counted eight times.
- METHOD (duplicates): three tests, cheapest first: the file's name on the list; MO2's own record of having
  installed that file; and, once it is taken in, ModTrap's test for the same mod in the modlist (MT65, MT68) and
  the same title and version on the list. The last needs the file taken in first, so its line shows briefly and
  is then taken away with a note.
- FACT (the page): the list must outlive a reading anew of the modlist, which every lot causes. The page's kept
  state is applied again at each reading; the bulk list is rebuilt from it only for another session.
- FACT (the drag, from the session's log and the code): the move the owner made was carried out as asked: before
  the first plugin of the last group. The page had sent that place. A drag's target was set on the pointer's
  move, and the list's own scrolling at its edge moved the rows without any move of the pointer. MO2's limits
  were never in play. Fixed by asking for the row under the pointer's last place after every step of scrolling,
  for both lists; and by taking the room below the last plugin for the end of the load order.
- METHOD (picking): one set of picked mods serves both lists, since both show the same mods; a plain click still
  does what it did (shows the mod), so only Ctrl and Shift are new. What a menu offers for several is what the
  server already takes for several: the ticks, an uninstall, a move, an asking.
- Checked in a browser on an invented list: fifteen files of which twelve went in, in order, from a chosen place;
  the three kinds of duplicate, a file that is no archive and a broken one; an installer's answers; a name typed
  over; picking with Ctrl and Shift on both lists and a menu for three; the clears; a drag held at the edge. Not
  checked on the owner's PC, and not with archives of real size or by the hundred.

### 145. A record of something done is not a claim on its name; where "refresh" ends and a change begins

`2026-11-24` · FACT · `#model #page` · refs: MT79, MT78, MT71, MT67, DESIGN§37, DESIGN§16.1, WHY§122, WHY§137, WHY§144

- FACT (the owner's session): ModTrap's work folder held 53 records of archives taken in, every one in the state
  "installed". Nine of the mods in the bulk list had such a record from an install some hours earlier; those nine
  mods were no longer in the modlist. Each of the nine was named with "(2)", and the log shows the plain name
  given to the first install and "(2)" to the second, with nothing else of that name anywhere.
- FACT (the code): the names a new mod could not have were the modlist's mods and every record in the work
  folder, whatever its state. A record is kept after its mod is installed so that an Uninstall can put the mod
  back on the Installer tool's list; nothing removes it when the mod leaves the modlist another way.
- So the fault was in what counts as taken, not in the bulk installer: the Installer tool would have done the
  same. A record whose mod is installed says nothing the modlist does not say (the mod is there under that
  name, or it is gone); only an archive still waiting to be installed needs its name kept from the next one.
- Not done: removing such records. Each holds an unpacked copy, which an Uninstall of that install puts back on
  the list; the owner's "Clear" buttons (MT78) remove them. They cost disk room, and no longer anything else.
- METHOD (the numbers already given): they cannot be told from a name the owner chose, except by this: the name
  ends in a number in brackets and no mod has the name without it. That is told on the Health tab, and renaming
  is the owner's press, through the rename that exists (MT66's job, one for each mod, each with its Revert).
- METHOD ("every refresh"): the owner asked for the bottom of the list "after launch and every refresh". MT71,
  also the owner's, says that a list read again after a change stays where it is. Both hold if "refresh" is what
  the owner does to see the list afresh (starting ModTrap, loading the page, opening a modlist, "Rescan") and not
  what ModTrap does by itself after each change. The second would move a row just ticked out of sight.
- METHOD: a list that is not shown has no height to scroll. So the bottom is owed to each of the three lists and
  paid when the list is first shown (its tab opened, the Updater list drawn).
- Checked in a browser on an invented list of seventy mods: the three lists at their bottom at the start, the
  arrows, the place kept after a tick at the top, the bottom after Rescan, and two wrong numbers taken off.

### 146. A plugin the game does not load is a fault as far as something calls it; the scripts say

`2026-11-27` · METHOD · `#model #safety` · refs: MT80, MT76, MT65, DESIGN§38, DESIGN§25, DESIGN§33, WHY§141

- FACT (the owner's session): the Health tab named a script extender plugin built for game version 1.5 in a mod,
  in a game of 1.6. A mod directly above it, called a fix for it, replaces six of its files. The scan judges only
  the copy of a plugin that the game loads, and still named this one: so the plugin is not among the six. The
  finding was right as far as it went, and said nothing of what the fix does.
- What a fix for such a plugin can be, told by files alone: (1) the plugin in the right version, at the same
  path: seen already. (2) Scripts that no longer call the plugin. (3) The script that declared the plugin's
  functions, replaced by one that does their work in Papyrus. (2) and (3) are in the scripts.
- FACT (the format, from its public description): a compiled script holds its names in a table, and for each
  function a mark for "native" (declared here, done elsewhere) and its instructions; a call by a script's name
  carries that script's name and the function's. ModTrap's reader (`pex.py`) is its own code and follows a file
  to its last byte or answers nothing. Checked against eleven compiled scripts of two open-source mods, read
  outside the repository and not kept: all eleven read to the end, with the native functions of the ones that
  have them (379 in one) and the calls by name of the others.
- METHOD: a script is the plugin's face where it declares native functions and the plugin's bytes hold the
  script's name and the name of one of those functions (a plugin registers each function under both). A script
  calls the plugin where it calls such a function by that script's name. Asked twice: of the mod's own copies,
  and of the copies the game loads. A copy that cannot be read counts as calling still.
- The plugin is "no longer called" only where the mod's own scripts did call it and the loaded ones do not, or
  the face itself is replaced by a script that declares none of the functions. Where the scripts say nothing of
  the plugin (no face: it works without Papyrus, or its scripts are packed in an archive), the finding stays
  as it was: nothing is called fixed on a guess (MT76 asks for warnings of real problems, not for silence).
- Limit, said on the page: the scripts of other mods are not read. A third mod that calls the plugin is not
  seen. Reading every script of a list of 600,000 files for each such plugin is not worth the wait.
- Rejected: taking a mod named a fix, or one directly above, as the fix. A name says what its author meant, not
  what the files do; here the fix replaces other files, and whether the plugin still matters is in the scripts.
- Also: an archive in the older game's format is judged only where the game loads that copy, as the plugin was;
  and the scan of every mod no longer stops listing a mod at 60,000 files or four seconds (the owner's scan was
  "cut short" by one large mod on every run): it lists up to two million, within the scan's own limit of time.
- Not verified: the owner's two mods themselves. Their files are not in the session, and their page could not
  be read from here. After a new scan the Health tab says which of the three cases it is.

### 147. "Not asked yet" beside a link just given reads as a link not understood; a name's version; pre-releases

`2026-11-27` · FACT · `#updates #page` · refs: MT80, MT67, MT37, MT44, DESIGN§38, WHY§103, WHY§101, WHY§109

- FACT (the owner's session log): 24 source links were given in a quarter of an hour, 21 of them to GitHub
  repositories; each was logged as kept, with its kind told rightly. The last scan had run two minutes before
  the first of them. No scan followed, so all of them read "Not asked yet". The one repository that had an
  answer had been given a day earlier, with a start of ModTrap in between. Nothing was registered by itself.
- FACT (the code): the addresses the owner asks about (a tab of a Nexus page, a repository's Releases) were
  understood before: the reader took the beginning of an address and passed over the rest. Not understood were
  an address without its beginning, `www.github.com`, GitHub's other hosts, Nexus's newer forms, a tag in the
  address of a repository's packed code, and GitHub's own pages (taken for repositories of an account "orgs").
- So the fault was in when ModTrap asks, not in what it reads. A link given by hand is a question put: the mod
  is asked about then, alone (one question, whatever a scan would hold back), or after the scan that is going.
- FACT: the staged records of archives taken in by hand hold no version, and the record ModTrap wrote for such
  a mod stated none; the mod's name ends with it (MT67). The Updater had the version in front of it and said
  "which release is installed is not recorded".
- METHOD (a version from a name): the one a name ends with is ModTrap's own way of naming, and is taken as the
  mod's version where no record states one: it can say "current" and "update". A number elsewhere in a name
  (a name with dots for spaces, an archive's name) can only confirm: if it is the newest release's, the mod is
  current; if it is not, nothing follows, since such a number may be the game's version or another mod's.
- FACT (GitHub's service): "the latest release" answers with the newest full release and with "not found" for
  a repository that has only pre-releases. The list of releases gives both, newest first, at the same cost of
  one question. One of the owner's mods carries a pre-release's version in its name.
- METHOD: what is kept of a repository is marked with its making; an answer kept by an older ModTrap (to the
  other question) is asked for anew, without the older answer's mark of sameness, which was for another address.
- Checked in a browser on an invented list with a stand-in for GitHub: three forms of address, the words said
  back, the question at once, "by its name" in the Installed column, a pre-release named beside a full release.

### 148. Versions are put in order only where both are understood; a page with one file says more than was taken from it

`2026-11-27` · METHOD · `#updates` · refs: MT81, MT80, MT67, DESIGN§39, DESIGN§38, WHY§147, WHY§101

- FACT (the owner's screen, the day after WHY§147): of 23 repositories asked about, most read "Up to date" or
  "Update out" by the version in the mod's name. Left "Unclear" or without a version: a name with dots for spaces
  that ends in its version; a name that ends in a pre-release's version, where the repository's newest release is
  the full release of the same numbers; a newest release whose tag puts words before its numbers; and a mod at
  Nexus whose page has no main file.
- METHOD (order): a version is its numbers, then one of three: a pre-release (alpha, beta, pre, rc, each with its
  count), the release, a release with a letter after it. So 0.7.0-rc1 is older than 0.7.0, and 7.5.2a newer than
  7.5.2. A tag may carry words before its numbers; one that carries anything else (two versions, a build's mark)
  is not understood. Two versions are compared only where both are understood and both, or neither, count by
  years. Anything else stays "unclear": a false "update" on a list of thousands is worse than an honest "unclear".
- METHOD (a name's end): `adding.version_in` takes a version after a space, a hyphen or an underscore, as ModTrap
  itself writes one. Read besides, for the Updater only and only where no record states a version: one after a
  dot, and one with a pre-release's mark, at the very end of the name. ModTrap's naming of mods is not changed.
- FACT (the code): where the installed file could not be told among a Nexus page's files, the version was
  compared with main files only, and a page with none was "unclear" whatever its other files said.
- METHOD (Nexus): a page with no main file is judged by its current files (optional, update, miscellaneous).
  And where a page has one current file in all, the installed mod is a state of that one file: a lower version
  is an update, a higher one is said so. With more files than one it may be another of them, and stays unclear
  unless a version matches. An earlier test said "unclear" for the one-file case; the reason given there (it may
  be another file) does not hold where there is no other.
- Not verified on the owner's PC: what the Nexus page of the one mod in question holds.

### 149. Two installers were one installer with two front ends; what "stops" were; a list that only grew

`2026-11-27` · FACT · `#page #add #safety` · refs: MT81, MT55, MT54, MT57, MT78, MT53, DESIGN§39, DESIGN§16, WHY§120, WHY§144

- FACT (the code): the mods' list and the Installer tool installed through the same server calls. The list's
  drop ran them in one go, in a box with stages. The tool's drop took the archive in and waited for "Install
  mod" (MT55, the owner's own choice four days earlier); with the owner's setting for placing by hand it then
  went to the Mods tab for a click, and asked once more before installing. Three presses against none.
- FACT: the list's run ended, with a pointer to the tool, where the archive had an installer.
- So the run was made the one installer: it takes a place or none, and where it has none it gets the usual one
  or asks for one click. The installer's questions are a stage of the run, shown in its box; the card is the one
  the tool had. The second question after a place chosen by hand is gone for a run: what the mod overwrites
  there is in the box afterwards, with "Uninstall" beside it, as it always was for the list's drop.
- FACT (the limit): every mod installed was put on the tool's list of what is in hand, and stayed until
  cleared. That list is analysed whole at every reading of the modlist (the owner's log: nine mods read again
  after each change, four to five seconds each time), and twenty was its most. Nothing took a mod off it.
- So an installed mod leaves that list. What the owner asked to see, the latest installs, is a list of its own,
  read from the installs' records; a mod's full report is one press away. Kept once: a page that still holds
  such mods from an older ModTrap takes off the ones an install put there.
- FACT (disk): each install left ModTrap's unpacked copy of the mod in the session's folder, so that an
  Uninstall could put the mod back on the list; the owner's session held 87. Fifty are kept, by when they were
  installed. An Uninstall of an older one takes the mod out as before and does not put it back on the list.
- METHOD (an installer's options): "is this mod installed" has two answers that files can prove. The installer
  may ask itself (a condition on a plugin being active). And the option's own plugins name their masters. Both
  are looked up in the load order. A match of an option's name with a mod's name was not used: names promise
  nothing. An option that goes with nothing beyond the game and the installer itself gets no mark.
- METHOD (the page in parts): the steps had one order, the order the analysis makes them in, which is not the
  order things happen (copying came before "what the mod needs"). Four parts, by what a step is: a condition,
  the install, a telling, an afterwards. Only the first can hold the install up, and only it is the owner's.
- Checked in a browser on an invented list: a plain archive from the tool with no press after the name; one
  with an installer, from the tool and from the list, with the marks; one placed by hand with one click; the
  tool's parts; each zone's glow. Not checked on the owner's PC, nor with a real installer of many steps.

### 150. "Remove" after an update is the uninstall that exists, run on the modlist as the update left it

`2026-11-28` · METHOD · `#add #updates #safety` · refs: MT82, MT66, MT49, MT14, MT15, DESIGN§40, DESIGN§27, WHY§149

- FACT (the owner's session log of 2026-11-26): an update through the Updater, and nineteen seconds later the
  older version uninstalled by hand. The setting asked for is that second step, taken by ModTrap.
- METHOD: ModTrap deletes no mod (its standing rule). The uninstall of MT66 moves a mod's folder aside whole and
  takes its lines out of the lists, with the lists copied to its safe folder first, the result read back, and an
  undo. "Remove" is that job, not a new way of taking a mod out.
- FACT (the code): the uninstall decides which plugins leave the load order by asking which enabled mod still
  gives each one. Asked of the modlist as it was before the update, the answer is wrong: the newer version is
  not in it, and the plugins the two versions share would leave the load order with the older one. So the
  modlist is read anew after the update, and the removal is planned on that reading. The request waits for it.
- METHOD (the way back): the update's job keeps a note of which uninstall followed it. Taking the update out
  undoes that uninstall first, reads the modlist again, and then reverts the update; in the other order the
  update's Revert would enable a mod that is not there.
- METHOD (other profiles): an uninstall takes a mod's line out of every profile. Another profile that has the
  older version enabled would lose the mod, and would have the newer one only as MO2 adds an unknown folder:
  disabled. That is a change to a profile the owner is not looking at, so such an older version is left, and
  ModTrap says why. A profile that has it disabled loses nothing it uses.
- A removal that fails (MO2 opened in between, a file in use) leaves the update whole and the older version
  disabled. Nothing of the update is put back for it: the update was verified before the removal began.

### 151. The version in a download's name is not always the file's; the code at its end is the file

`2026-11-28` · FACT · `#updates #add` · refs: MT67, MT81, DESIGN§41, DESIGN§39, TL01§31, WHY§110, WHY§148

- The owner's report (a real mod's name replaced by words in square brackets): "for [a mod], modtrap sees v1.1
  and states unclear. The mod itself on nexus has two v1.0 version, one for SE and one for AE. can you check
  where the logic fails and fix?"
- FACT (the owner's session log, the page the owner showed): the archive was downloaded in the browser under
  Nexus's newer kind of name, "[file's name] [mod's number] 1.1 [day and time]Z [code].zip". The page states
  version 1.0 for that file, and has two main files, both 1.0, uploaded in the same minute. So the version in
  such a name is not always the version the page states. Why it differs here is not known: nothing ModTrap can
  read says how the site makes that part of the name.
- FACT (the code): ModTrap took the name's version as the file's: the mod was named "[file's name] 1.1" (the
  owner renamed it), and its record stated 1.1. The Updater knew the installed file only by a file's number or
  by the archive's whole name; a mod installed from a browser's download has neither, so it fell back to
  comparing versions, 1.1 against 1.0, and said "unclear".
- FACT: the last part of such a name is the file's own short code, which the public service gives for every
  file and ModTrap keeps (WHY§110). It was used to know a download that had just arrived, and nowhere else.
- So: the installed file is known by that code, before anything else that the name says. Known, it is judged as
  a file known by its number is: by what replaced it, or by the newer files of its own line of versions. The
  row shows the version the page states for it. Two main files of one version are then no trouble: each is its
  own line.
- At install, the same: where the name ends with a code, what is kept of the page says which file it is; where
  nothing is kept, the page is asked once and waited for six seconds. The file's version from the page names
  the mod, and the file's number goes into the mod's record, as MO2 writes it for its own downloads. Without an
  answer the name's version stands, as before.
- Not changed: a mod already named. The owner's is named rightly by the owner's own hand; its record still
  states 1.1, which the Updater no longer goes by.

### 152. A run that hands its work over must look again; better that it does not hand it over

`2026-11-28` · FACT · `#updates #add #page` · refs: MT83, MT81, MT49, MT82, DESIGN§42, DESIGN§39, WHY§149

- FACT (the owner's session log): an update fetched from GitHub, unpacked, and at once "waits for the owner: its
  installer asks which parts to install: answer its questions on Install mods; the update goes on from there".
  Fifteen minutes later the answers and "Update mod" on Install mods: the add ran, the older version was removed
  (MT82, working on its first real run), the modlist read back clean. The Updater tool showed "waits for you".
- FACT (the code): at an installer the run's own thread ended, in the state "waits for you, handed over".
  Nothing looked at that run again. "The update goes on from there" was true of the update and never of the run.
- So two things. The run no longer ends at an installer it can read: it waits for the record of the unpacked
  archive to leave the state "installer", which the answers do, and goes on. The questions are the same card as
  on Install mods and in the installer's box (MT81), drawn inside the run, so there is one page to be on.
- And a run that is still handed over (the two cases left: a missing master, an installer ModTrap cannot read)
  is looked at each time the page asks how the runs stand: where its archive's record reads "installed", the
  run is closed as done, with the install found among the session's adds, so that its Uninstall works.
- METHOD (waiting): the run waits in the state "waits for you", not "going on": ModTrap's check for "something
  else is going" counts only runs that are going, so a question left unanswered for an hour holds nothing up.
  The wait ends by the answers, by "Stop", by the archive being taken off the list, or after twelve hours.
- Checked in a browser on an invented list: the questions under the run's stages, an option changed, "Use these
  answers", and the run through to "done" with the older version disabled. Not checked on the owner's PC.
