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
