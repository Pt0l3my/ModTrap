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
  a write does), `#safety` (originals untouched), `#server`, `#page`, `#datapiler`, `#process`.
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
