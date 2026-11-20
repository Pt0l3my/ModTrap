# Owner decisions

The project owner's decisions on ModTrap, binding, one entry each, numbered MT1 onwards. A new question takes the next
free id as an entry marked **Open**, with its options and a recommendation; the owner's answer is recorded in the
entry with its date and their words; a later decision amends an earlier one by a dated note, never by rewriting it,
and ids are never renumbered. Everything is cited by code: `WHY§n` is the [reasoning log](REASONING.md), `MO01` and `XE01` are the
[research notes](research/README.md), `DESIGN§n` is [design 0001](design/0001-design.md).

## By date

- **2026-11-20.** MT1 (what "demaster" means), MT2 (the page: scan, tick, one button, a terminal), MT3 (built like
  DataPiler; the sweep), all from the owner's messages of that day.
  The owner's answers of the same day: MT6 (patch-only mods are proposed for disabling), MT7 (Skyrim SE and every AE
  version), MT8 (ModTrap detects xEdit's version and the modlist's tools), MT9 (Auto: ModTrap disables mods,
  records them, and can re-enable them), MT10 (the repository exists), MT11 (installed and started as DataPiler),
  MT14 (the safe folder and Revert) and MT15 (the full modlist and load order, and a history).
  Later the same day: MT17 (the result that counts; the method is ModTrap's to choose), under which MT4 (cases A and
  B automatic, the rest reported) and MT5 (a ModTrap mod above the originals) were settled; MT18 (generated
  patches, their tools, and a Steps tab); MT16 settled by the facts.
- **Open.** None. Followed meanwhile, for the owner to confirm: MT12 (no session link in commits), MT13 (the
  reference system).

## MT1

**What "demaster" means** · *2026-11-20 · Decided by the owner*

**Question.** Three meanings were put: (a) remove a mod as a master from every plugin that depends on it, dealing
with what they take from it; (b) xEdit's Clean Masters only; (c) clearing a plugin's ESM flag.

**Decision.** (a), with (b) as its last step: the "Master Removal" procedure of the guide the owner supplied (WHY§2).
For each plugin that depends on the unwanted mod: report what needs it, remove those records or elements, Clean
Masters, report again until nothing is left.

**Owner's words.** "this shows the steps and procedure to demaster a mod (SDA) from JoJ modlist."

## MT2

**The page** · *2026-11-20 · The owner's request*

**Decision.** ModTrap sees the mods installed in MO2 for the selected modlist folder; the owner selects mods from the
scanned list; one button, "Demaster Selected", starts the work; the work is shown as it happens, in a terminal.

**Owner's words.** "I would like the tool to be able to see mods that are installed in MO2 (of the selected modlist
directory), then let the user select mods to demaster from the scanned mod list. Click a button "Demaster Selected",
and watch it do its work (terminal)."

**Note.** Design 0001 puts a plan and a dry run between the button and the changes (DESIGN§6.1, DESIGN§6.2). Whether the owner
wants those two confirmations, or one, is part of MT4.

## MT3

**Built like DataPiler; the sweep first** · *2026-11-20 · Decided by the owner*

**Decision.** ModTrap learns from DataPiler and may reuse its code freely (both are the owner's, MIT), credited in
`NOTICE`. The privacy and safety sweep (privsweep, from the owner's private repository) is installed and gates
every push.

**Owner's words.** "Learn from Datapiler (you can ask from Engine agent for more info) tool, I am sure that will help
to hook into a process, gather data, and then carry out alterations." · "Reading DataPiler: yes you can do what you
want with it." · "privsweep: yes".

## MT4

**What is taken out of a dependant, and what is never forced** · *2026-11-20 · Left to ModTrap by the owner*

**Question.** The guide leaves a judgement to the user: "remove the whole record … or make a more surgical edit". A
tool needs rules. Which?

**Options.**

- (a) **Four cases, nothing forced** (DESIGN§5). A: the dependant's copy of a record that belongs to the trapped
  mod is removed. B: an entry in a list (a FormID list, a levelled list, keywords) is removed and the record kept.
  C: a single field that cannot be absent gets the value it has in the dependant's remaining masters. D: anything
  else stops that dependant, which is left untouched and reported as "needs you". Always a dry run first that lists
  every change, then a second confirmation.
- (b) **Cases A and B only.** C counts as D. Fewer automatic fixes, more left to the owner, less that can surprise.
- (c) **Always remove the whole record** that mentions the trapped mod. Simplest; loses whatever else that record
  did (for a patch, often its whole purpose).
- (d) **Report only.** ModTrap finds and lists everything; the owner edits in xEdit by hand.

**Recommendation.** (b) for the first version, growing into (a) once the dry-run reports from the owner's real
modlist show how common case C is. The dry run and second confirmation stay in every option: they are what makes
"watch it do its work" safe.

**Answer, 2026-11-20 (to a different question).** The owner answered about the mod itself: it is disabled, never
removed; that is recorded under MT9. Owner's words: "nothing gets removed, what I normally do after demaster is to
just disable the mod in MO2 (not remove, just disable) and let it stay there."

**The question, put again in plain words (still Open).** To demaster a dependant plugin, the records and entries
*inside that dependant* that point at the unwanted mod have to be taken out of it, as the guide does by hand
("delete … records from these patches"); otherwise the master cannot be dropped. Which of these may ModTrap do by
itself: (a) cases A to D of DESIGN§5; (b) only A (the dependant's copies of the unwanted mod's own records) and B
(single entries in lists), anything else reported as "needs you"; (c) the whole record every time; (d) report only.
Recommendation unchanged: (b). The safe folder and Revert (MT14) now stand behind every option.

**Decision, 2026-11-20 (the owner left the method to ModTrap; MT17).** (b), growing into (a): ModTrap takes out by
itself a dependant's copies of the trapped mod's own records (case A) and single entries in lists (case B). A
single field that cannot be absent (case C) is first only reported; it becomes automatic once dry runs on real
modlists show that restoring the value from the remaining masters is reliable. Anything else (case D) leaves that
dependant untouched and becomes a step for the owner in the job's Steps tab (MT18), with the record and field
named. Reason: MT17's "play the game without issues" is better served by an honest "this one needs you" than by a
forced edit.

## MT5

**Where the result goes** · *2026-11-20 · Left to ModTrap by the owner*

**Question.** The guide's procedure changes the dependant plugins in place, inside their own mod folders. Should
ModTrap?

**Options.**

- (a) **A new mod.** The demastered plugins are written to a new mod folder, `ModTrap - <name>`, in the instance's
  mods folder. Enabled, it wins over the originals; deleted, everything is as before. The originals are never
  changed, and are checked by hash before and after (DESIGN§6.3 to DESIGN§6.5).
- (b) **In place**, as in the guide, with ModTrap's own backups and a restore button.

**Recommendation.** (a). A Wabbajack-installed list also stays verifiable against its original files this way. It
rests on one unproven point about xEdit (WHY§4), which the probe settles first (DESIGN§9); the fallback keeps (a)
either way.

**The owner's proposal, 2026-11-20.** "would it be better to copy over files, work on them separately, then verify
the demastered files, then insert into modlist directory (to replace the original files and to apply our demanster),
verify again with MO2 that everything looks ok."

**Taken into the design.** Work on copies, verify the copies, put them in place, verify the instance again:
DESIGN§6.3 to DESIGN§6.5, with the originals copied to the safe folder first (MT14).

**Still Open: how the verified files are put in place.**

- (a) **A ModTrap mod above the originals.** MO2 then uses ModTrap's files in place of the originals, which stay as
  installed. Revert is disabling one mod. With Auto (MT9) ModTrap places and enables it itself.
- (b) **Replace the originals in their mod folders.** No extra mod in the list. The files of an installed modlist
  then differ from what its installer put there, so an update or repair of the list may flag or restore them;
  Revert copies the originals back from the safe folder.

**Recommendation.** (a), for that last reason (WHY§18). Both give the same result in the game, and both are
revertible.

**Decision, 2026-11-20 (the owner left the method to ModTrap; MT17).** (a): the verified files go into a ModTrap
mod placed above the originals, which stay as installed (WHY§18). ModTrap places and enables that mod itself under
Auto (MT9). The safe folder (MT14) is still taken, since the profile is changed.

## MT6

**Dependants that should be disabled, not demastered** · *2026-11-20 · Decided by the owner*

**Question.** The guide disables patches that exist only for the unwanted mod, and demasters only the plugins that
do other things too (WHY§2). How should ModTrap tell them apart?

**Options.**

- (a) **ModTrap proposes, the owner decides.** After the dry run, a dependant of which nothing or almost nothing
  would remain is proposed as "disable this yourself"; every dependant's treatment can be changed on the page.
- (b) **Demaster everything**, even if an empty plugin results.
- (c) **The owner marks each dependant by hand**, no proposal.

**Recommendation.** (a).

**Decision, 2026-11-20.** (a): ModTrap works out which mods are patches or extras that exist only for the mod being
demastered, and proposes disabling them; the owner can change each (DESIGN§5).

**Owner's words.** "that's correct, MO2 needs to be able to determine these patch/extra mods that require demastered
mod as dependency as propose to user to disable them." (The sentence says MO2; ModTrap is meant, as the tool that
does the proposing.)

## MT7

**Which games** · *2026-11-20 · Decided by the owner*

**Options.** (a) Skyrim Special Edition and Anniversary Edition only; (b) also Skyrim VR; (c) also the 2011 Skyrim
(LE).

**Recommendation.** (a) first. The design does not shut the others out: xEdit handles them, and ModTrap's own
reader only needs the plugin header, which differs little.

**Decision, 2026-11-20.** Skyrim Special Edition and every Anniversary Edition version. Not LE, not VR.

**Owner's words.** "yes we will support Skyrim SE and all AE versions."

## MT8

**Which xEdit, and the modlist's other tools** · *2026-11-20 · Decided by the owner*

**Question.** ModTrap uses the xEdit already set up as an executable in the owner's MO2. Which version does the
owner run? The research was done against 4.1.5f, the version in the screenshots.

**Options.** (a) 4.1.5f or newer required, older refused with a message; (b) whatever is found, untested.

**Recommendation.** (a). The owner is asked only to say which version their MO2 starts (the window's title bar
shows it).

**Decision, 2026-11-20.** ModTrap detects xEdit's version itself and works with the versions in common use; it also
detects the other tools the modlist comes with. How: DESIGN§13, and the probe as the test of compatibility
(WHY§15). The owner's own xEdit is 4.1.5f (WHY§14), the release the research was done at. Only xEdit is ever run
by ModTrap; the other tools are shown, and named in the reminder after a job.

**Owner's words.** "Can we make ModTrap be able to detect version (do the same for other tool if applicable) then be
compatible with relatively popular versions? Would it make sense for ModTrap to detect tools used by modlist? see
image".

## MT9

**Who enables and disables mods in MO2** · *2026-11-20 · Decided by the owner*

**Question.** After a run, the output mod must be enabled and the trapped mods disabled. Who does it?

**Options.**

- (a) **The owner, in MO2.** ModTrap lists the steps and never writes to a profile. MO2 can stay open throughout.
- (b) **ModTrap**, by editing the profile's `modlist.txt` and `plugins.txt`. One click fewer; requires MO2 to be
  closed (an open MO2 would overwrite the files), and makes ModTrap a program that edits the owner's profile.

**Recommendation.** (a) for the first version; (b) can be added later as an option once the rest is trusted.

**Decision, 2026-11-20.** A setting, **Auto**, on by default: ModTrap disables the mods itself. A mod is only ever
disabled, never removed, and stays where it is. Every mod ModTrap disables is entered in its history with its
priority in the modlist and each of its plugins' positions in the load order, and can be re-enabled from there with
a click (DESIGN§6.5, DESIGN§12). ModTrap writes the profile only while MO2 is closed (WHY§16).

**Owner's words.** "this could be a setting (Auto - On by default) so ModTrap disables these mods automatically but
also registers these disabled mods in its history, so user can refer to them (make sure you always cite mod priority
placement and its esp/esl/esm placement in Plugins. Also add option for user to click on these disabled mods to
re-enable them."

**Note.** This relaxes the brief's "never alter the profile": ModTrap now changes `modlist.txt`, under MT14's
backups.

## MT10

**The repository** · *2026-11-20 · Decided by the owner*

**Question.** ModTrap has no repository yet; the work is in a local one and nothing is pushed.

**Options.** (a) the owner creates an empty repository named ModTrap, private until a first release; (b) public from
the start, like DataPiler.

**Recommendation.** (a). Also to settle: the name on the licence's copyright line (now "the ModTrap authors"; DataPiler
uses the owner's public handle).

**Decision, 2026-11-20.** The owner created the repository, named ModTrap, in their account. Owner's word: "done".

**Still to settle.** The name on the licence's copyright line, and the first push (MT16).

**Note, 2026-11-20, later.** The repository came with a `main` holding the owner's own `LICENSE` (MIT), whose
copyright line the owner chose. That file is kept as it is; the copyright line is settled.

## MT11

**How ModTrap is installed and started** · *2026-11-20 · Decided by the owner*

**Options.**

- (a) **As DataPiler:** a small launcher and a PowerShell script that find Python and start the server; an updater
  later. Python standard library only.
- (b) **An MO2 plugin** (a Python plugin inside MO2 itself). Closer to MO2, but it would run inside MO2 (GPL-3.0)
  and could not use DataPiler's page, server or launcher.

**Recommendation.** (a): it is what the owner asked for, and it keeps ModTrap's code and licence apart from MO2's.

**Decision, 2026-11-20.** (a), as DataPiler. Owner's word: "correct".

## MT12

**The session link in commit messages** · *Open*

**Question.** The brief ModTrap was started from says that commit messages keep the `Co-Authored-By` line and leave
out the link to the chat session. The owner did not recall the rule; the session that wrote the brief has been asked
where it comes from.

**Until decided.** The link is left out (the cautious choice: it can be added later, but not removed once pushed).

**Note, 2026-11-20.** That session answered: it is the owner's own choice of 2026-11-16 for their other projects
("Stop adding them"), made because the link points to a private transcript and tells a reader nothing (WHY§12). Open
only until the owner confirms it holds for ModTrap too.

**Note, 2026-11-20, later.** Verified: the rule is in DataPiler's `CLAUDE.md` on its branch `feat/v0.2.41`, pushed
that day, in those words and with that date (WHY§12). ModTrap follows it; the owner can still say otherwise.

## MT13

**The owner's reference system** · *2026-11-20 · Adopted on the word of the session that started ModTrap; for the owner to confirm*

**Question.** That session passed on, as the owner's request, that ModTrap use the reference, tag and label system
of the owner's other projects.

**Done.** `wp` (`tools/workplan`) taken from EldenNet with ModTrap's codes; research notes MO01 and XE01 with a
label and a source on every statement; the reasoning log in the same form as EldenNet's; the rules in `CLAUDE.md`
(WHY§13). The roadmap with stage ids is left for when there is more to plan.

## MT14

**The safe folder and Revert** · *2026-11-20 · The owner's request*

**Decision.** After the dry run, when the affected files are known, ModTrap copies every one of them into a safe
folder: automatic and mandatory. **Revert** copies the originals back and returns everything to how it was
(DESIGN§6.2, DESIGN§11, WHY§17). "Affected files" includes the patches and generated plugins the modlist comes
with, wherever the dry run finds them among the dependants.

**Owner's words.** "I also want you to make Modtrap detect what files are affected (e.g. what patch/bash files that
the modlist comes with) and save them after dry run (at that point it should be able to tell) as mandatory automatic
process (a safe folder containing copies of those files), so if something goes wrong, the user can select "Revert"
which will copy original files back and revert everything to default."

## MT15

**The full modlist, the full load order, and a history** · *2026-11-20 · The owner's request*

**Decision.** ModTrap shows the full modlist with priorities and the full plugin list (esp, esl, esm) with
positions, and keeps a history of every change it makes: what was disabled, changes of priority or position, each
with date and time (DESIGN§4, DESIGN§12).

**Owner's words.** "Also let's makle ModTrap be able to see full modlist and priorities and also plugins (esp, esl,
esm) and their priorities and register changes made in history (what was disabled, priority changes with date and
time)."

## MT16

**The first push** · *2026-11-20 · Settled by the facts*

**Question.** The repository is empty. The rule is to work on a topic branch, never on `main` unless the owner
asks; but an empty repository has no `main` yet, and the first branch pushed becomes its default.

**Options.** (a) `main` gets one first commit holding only the licence, the notices, the README and the project
rules, and the design goes on its branch `design/0001-design`; (b) everything so far goes to `main`; (c) only the
design branch is pushed, and becomes the default until a `main` exists.

**Recommendation.** (a).

**Outcome, 2026-11-20.** The question fell away: the repository was not empty. Its `main` already held the owner's
first commit (the licence), so the design branch was placed on top of it and pushed as `design/0001-design` at the
owner's word ("I installed the GitHub App, try pushing now"). `main` is untouched.

## MT17

**The result that counts, and who chooses the method** · *2026-11-20 · Decided by the owner*

**Decision.** A job is done when: the chosen mods are demastered cleanly; the modlist is clean (no missing master,
no incompatibility and no bad patch or generated patch left behind by the demaster); and the game plays without
issues that come from the demaster. How ModTrap gets there (how it handles files and the rest) is ModTrap's to
choose; the owner is asked only when their input is really needed.

**Owner's words.** "In the end there result I want: Demastered mods cleanly, modlist is clean (no missing master,
incompatibilities, bad patches/bashes), and play the game without issues (coming from demaster). How you achieve is
down to you, meaning how you want to handle files etc. I leave that to you what works best, unless you really need
my input (I think you know better in most cases)."

**What this binds.** Every job ends with checks against this result, not with "the script ran" (DESIGN§6.5,
DESIGN§14). What ModTrap cannot check by itself (whether the game plays well) is said plainly and left as the
owner's last step (WHY§21).

## MT18

**Generated patches, the tools that made them, and a Steps tab** · *2026-11-20 · The owner's request*

**Decision.** ModTrap detects which tool made each of the modlist's generated patch files (a patcher's output, for
example), and where such a file is affected by a demaster it tells the owner to run that tool again. Each job has a
**Steps** tab that compiles every step the full demaster needs, ModTrap's and the owner's, worked out from the mods,
the tools, the modlist's patches and what depends on what (DESIGN§13, DESIGN§14, WHY§22).

**Owner's words.** "can you also make ModTrap detect what tools have been used for modlist patch files (e.g.
synthesis) if required, and instruct the user to run the tool. Perhaps best way to do this would be to add a "Steps"
tab for each Demaster job which tab compiles the steps required for the full demaster for the user (by detecting
mods, tools, modlist patches and their dependencies, etc.)."
