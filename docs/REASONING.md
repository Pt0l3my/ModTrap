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
