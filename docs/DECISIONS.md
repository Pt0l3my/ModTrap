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
  patches, their tools, and a Steps tab); MT16 settled by the facts; MT19 (a drop box for the modlist folder); MT20 (Quit, and sessions: one
  active session per modlist).
- **2026-11-21.** MT21 (adding mods safely: analysis, steps, and carrying out what ModTrap can; the how is
  ModTrap's to choose); MT22 (a version with every update, and one ModTrap at a time).
- **2026-11-22.** MT25 (a tool that can do so runs and closes by itself; ModTrap closes no tool); MT26 (the steps
  state facts: before the dry run, only that it comes first). MT27 (the patcher framework's library versions are checked and set
  right before it starts). MT28 (its patchers are built outside MO2 first when they are not built). MT29 (a tool's step is done
  by ModTrap's record of its run, not by a tick). MT30 (nothing is started while ModTrap is still reading or scanning). MT31 (a tool with only a button
  is run by ModTrap pressing it). MT32 (a compiler that crashes inside MO2 is put on MO2's list of programs it leaves alone). MT33 (ModTrap reads
  the settings files that name the plugin, and gives one account of its checks after the demaster). MT34 (a scanner of every
  settings file in force in the modlist, and of the frameworks installed).
- **Open.** MT35 (should the scanner also look through the animation folders, for the conditions of animation replacers). MT23 (a tool check through xEdit, with the whole load order loaded); MT24 (ModTrap puts a leftover in a
  tool's plugin right itself). Followed meanwhile, for the owner to confirm: MT12 (no session link in commits), MT13 (the
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

**Note, 2026-11-21.** The first real dry runs showed what case C is on a real list and that the dependant's
remaining masters answer it: case C is automatic where the dry run's evidence shows the dependant only carries the
part on from the mod, and still "needs you" otherwise (WHY§55). The owner's words that led there: "basically it's
about finding what xedit find registered for the big patch files the modlist features".

**Note, 2026-11-22.** A script's property that points at a record of the mod counts as an entry of a list (case
B): the property is taken out of the script's list of properties, or the one object out of a property that is a
list of objects, and the plan says so in so many words (WHY§76, XE01§21). The owner's list showed it: a settings
plugin whose own quest script pointed at the mod, and nothing else of the mod in it. The owner may overrule.

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

**Note, 2026-11-20, later (under MT17).** The owner's real modlist showed that a patch is often one plugin inside a
patch collection (WHY§26). Auto therefore also deactivates single plugins, in the profile's `plugins.txt`, where
disabling the whole mod would switch off patches the list still needs. The history records these the same way,
with a Reactivate on each.

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

## MT19

**A drop box for the modlist folder** · *2026-11-20 · The owner's request*

**Decision.** The page has a drop box: the owner drops the modlist's folder on it, and ModTrap finds the MO2
instance and registers its path (WHY§30). The path can still be pasted.

**Owner's words.** "can you also add a dropbox (ask engine agent about design) so users can just drop the modlist
directory and the ModTrap reads the executable of the MO2 and registers the path?"

## MT20

**Quit, and sessions** · *2026-11-20 · The owner's request*

**Decision.**

- A **Quit** button closes ModTrap. The session is kept, and starting ModTrap again shows exactly the state it was
  in before.
- Work is kept in **sessions**, each in a folder of its own, named after its modlist by ModTrap and renameable by
  the owner. A new session is separate from the others, and the owner can switch between sessions.
- **One active session per modlist.** One session can hold as many demasters as the owner wants. More sessions on
  the same modlist may be started, but they are locked until the current one is verified finished and safe for the
  next to begin.

**Owner's words.** "Can you also implement a quit button that closes down the tool (closes the browser page), but the
session is reserved, and upon starting ModTrap again, the user is presented the exact same state of the session prior
to quit it was in. We could also save sessions in their own directory with their (auto name them by modlist, user can
rename manually). When the user begins a new session it will start as separate sessions, and the user cam switch
between sessions. Only one active session should be allower per modlist in my opinion, one sessions can do as many
demaster as the user want anyway, but multiple demaster sessions may cause conflict and confusion and messed up
files in modlist. We can allow to start new session, but those will be locked hntil the current session is veryfied
finished and safe for other sessions tk begin their demaster process."

**How it is built, and two limits** (WHY§33). A browser lets a page close its own tab only if the page opened it,
so after Quit the page says ModTrap has closed and that the tab can be closed. "Verified finished and safe" today
means that nothing of the session is still going, since nothing ModTrap does yet changes a modlist; when it can
demaster, the check also requires every step of the session's jobs to be done and the modlist's health check to be
clean (DESIGN§14, DESIGN§15).

## MT21

**Adding mods safely** · *2026-11-21 · The owner's request; the how is left to ModTrap (as MT17)*

**Decision.** ModTrap gets a second set of features, beside taking mods out: adding extra mods to a modlist
safely. The owner drops the wanted mods (or picks them); ModTrap analyses each against the whole modlist and tells
what it conflicts with, what is affected and in what order, compiles the steps to add it safely, and carries out
the steps it can. Anything else that serves this may be built; the owner gave full freedom.

**Owner's words.** "I wonder if we could also add feature set to safely add extra mods to the modlist. Basically,
what I normally do is when I want more mods added to the modlist, I just add them last, and ensure the esp is also
overwriting at the bottom of the plugin list (so at bottom both mod and plugin list). But I suppose that's rather
crude. Do you think we could add a feature set that would allow the user to just drop wanted extra mods and ModTrap
could analyze and tell any conflicts, what is affected and in what chain or order, a step list to install safely,
and to carry out steps that it can (and anything else that you think could be implemented, you are given full
freedom)."

**Settled under that freedom** (DESIGN§16, WHY§40; the owner may overrule any of it):

- **MO2 installs, ModTrap takes over from there.** The mod is installed in MO2 as always and left disabled; ModTrap
  does not unpack archives or run installers.
- **The place:** after every ordinary mod and before what the modlist's tools made, among the mods and in the load
  order alike; not below everything.
- **Nothing is written yet.** The analysis and the steps only read. Putting a mod in its place joins the part that
  is switched off (WHY§36, WHY§39), with the same safe folder, history and Revert, and a mod added by ModTrap is
  taken out again by disabling it, never by deleting it (MT9).

**Later, 2026-11-21: the owner on "MO2 installs".** "Well, what I wanted was that the user jusf drops a mod in
ModTrap, then ModTrap does the evaluation, compiles steps, and does most of the work on its own except for some
tools like synthesis that is not shipped with ModTrap. Can that be done?" So the first point above is replaced:
**the owner drops the mod's archive on ModTrap, and ModTrap takes it from there**: it unpacks the archive, analyses
it, compiles the steps and carries out all it can; left to the owner are the tools ModTrap does not contain, an
installer's questions, and playing (DESIGN§16.1, DESIGN§16.8, WHY§41). The other two points stand.

## MT22

**Versions** · *2026-11-21 · Decided by the owner; the how is left to ModTrap (as MT17)*

**Decision.** ModTrap carries a version that changes with every update, and uses it so that an older ModTrap is
never mistaken for a newer one.

**Owner's words.** "that's an issue, we need to start involving version updates to prevent that error" (the error:
an update unpacked while ModTrap ran, so that a new script ran under the old program, WHY§67).

**Settled under that freedom** (DESIGN§17, WHY§68; the owner may overrule any of it):

- The version is `0.3.n`; `n` rises with every change that is pushed. The owner is told the number with each change.
- It is shown on the page, in ModTrap's window, in its log and in every saved session file.
- A ModTrap whose files changed while it runs starts no job, and says which version is running and which is on disk.
- One ModTrap at a time: a new start makes one that is still running save its session and close, and takes its
  place. One in the middle of a job is left alone.
- ModTrap does not fetch updates itself (MT11 leaves an updater for later).

## MT23

**A tool check through xEdit** · *Open*

**Question.** Should ModTrap have a separate, read-only run of xEdit that loads the whole load order and compares,
record by record and by meaning, each tool-made plugin's copy with the mod's version and with the version next in
line? It would say for each record a tool holds: the same as the mod's (run the tool again), the same as the next
in line's (nothing of the mod in it), or neither (the tool's own value). Today ModTrap compares bytes, which holds
for tools built on xEdit and not for a patcher that writes records its own way (TL01§13, WHY§73).

**Options.**

- (a) **A check of its own**, started from the tool's step ("Check this tool through xEdit"). xEdit loads every
  active plugin: several minutes and much memory on a list of thousands; nothing is changed.
- (b) **Part of every dry run.** Always exact, and every dry run takes those minutes.
- (c) **Not at all.** A patcher that holds a record the mod has a stake in is simply run again, to be sure: its
  run is short.

**Recommendation.** (a). It costs nothing unless asked for, and it is the only way short of running the tool to
tell a patcher's copy made from the mod from one that only looks different. For a tool as quick as the patcher
framework, (c) is what the owner would mostly do anyway; (a) earns its keep for tools whose run takes long.

**Until decided.** (c) is what ModTrap does.

## MT24

**A leftover of the mod in a tool's plugin: run the tool, or let ModTrap put it right** · *Open*

**Question.** A tool's plugin can hold a value it took from the mod in a record it only carries along (a cell it
puts its own things into). Today the step says "run the tool again". For a generator whose run takes hours that is
a heavy answer to one field. Should ModTrap put such a field right itself: in a copy of the tool's plugin, in
ModTrap's own mod, set the field to what the plugin next in line says, as it does for a patch that carries a part on
from the mod (MT4, case C)?

**Options.**

- (a) **ModTrap puts it right**, as part of "Demaster Selected", named in the plan. The change run then also loads
  the tool's plugins and their masters (a longer run), and ModTrap's mod holds copies of them; the tool's next run
  makes them anew, and ModTrap says when its copy has become the stale one.
- (b) **Only say it.** The step shows the values and leaves the choice: run the tool, or leave the leftover until
  the tool's next run.
- (c) **As now:** "run the tool again".

**Recommendation.** (b) now, (a) once a real leftover shows up that matters: none has yet (every one so far was
bytes that mean nothing, or my own slip, WHY§77, WHY§78).

**Until decided.** (c), with the values shown.

## MT25

**Tools that run and close by themselves** · *2026-11-22 · Asked by the owner; the how is left to ModTrap (as MT17)*

**Owner's words.** "Would it be possible for Modtrap to not only start but close the tools after they confirm
their part is done?"

**Settled under that freedom** (WHY§84, TL01§16; the owner may overrule any of it):

- A tool that has switches of its own to do its work and close is started with them, beside the arguments MO2 has
  for it. Which tools and which switches is data, read in each tool's own source. So far: the behaviour engine.
- ModTrap closes no tool's window itself: it cannot know for every tool what "done" looks like, and closing one
  too early loses its work. A tool without such switches stays the owner's to work and close.
- A setting, on by default, turns this off.
- MO2's own message after a run, which kept a tool's run from ending, is closed by ModTrap, as after a dry run.

## MT26

**The steps state facts** · *2026-11-22 · Decided by the owner*

**Owner's words.** "Can you implement a stronger and more deterministic tool that will not predict but only state
facts that are actually true. if steps needs a dry run first then it should state that and only after show what
the steps would look like."

**Decision.** Until a dry run of the ticked mods is done, the Steps tab shows only the dry run and that the rest
follows from it. What it shows afterwards rests on what was read, and a verdict on a tool is the same before the
demaster as after it (WHY§86, DESIGN§14).

**Note, 2026-11-22.** Asked whether the patcher framework should run after every demaster whatever the evidence
says, the owner first said yes, then put it right: "I mean after every demaster that requires the tool". So a tool
runs when the steps call for it, by proof or to be sure (WHY§73, WHY§86), and not otherwise; when it runs, it runs
whole (every group and patcher its own run button starts, WHY§93).

## MT27

**The patcher framework's library versions** · *2026-11-22 · Asked by the owner; the how is left to ModTrap (as MT17)*

**Owner's words.** "can you make ModTrap to check the patches what versions are required and automatically set them
to that version?"

**Settled under that freedom** (WHY§89, TL01§19; the owner may overrule any of it):

- ModTrap sets the versions only on proof: the program's own last log shows the versions its profile is still
  set to as not fitting, and states the versions the program was built with. Those are set.
- It does so before it starts the program, in the program's settings file, keeps a copy of the file as it was
  with the session, and records the change in the History.
- A setting, on by default, turns it off; ModTrap then only says what it found.
- It is a tool's own file, outside any demaster: Revert does not undo it.

## MT28

**Building the patcher framework's patchers outside MO2** · *2026-11-22 · Asked by the owner; the how is left to ModTrap (as MT17)*

**Owner's words.** "can ModTrap also build the patchers outside MO2 automatically? is that safe?"

**Settled under that freedom** (WHY§90, TL01§20; the owner may overrule any of it):

- When the framework's own last log names patchers whose build is not there, ModTrap opens the program by
  itself, outside MO2, waits until its log and its build records show every patcher built, asks its window to
  close, and then starts it through MO2.
- Nothing in the program is pressed; its settings file is put back if opening it changed the file; the program is
  asked to close, never ended. This amends MT25 for this one case: ModTrap closes this window, because "done"
  is a fact on disk and nothing was run in it.
- If the build fails outside MO2 too, ModTrap makes no start through MO2 and says what the log holds.
- A setting, on by default, turns it off.

## MT29

**A tool's step is done by a record, not by a tick** · *2026-11-22 · Decided by the owner*

**Owner's words.** "it still says that pandora run is complete from previous session, that should be rerun after
each demaster. since we already made these tool processes automatic, maybe we should remove the manual override, it
just introduces more error."

**Decision.** A tool's step has no "I have done this". It is done when ModTrap has noted, with the demaster in
place, a run of that tool that it started and that wrote its output; every Revert and every new demaster asks for
the tools again (WHY§91). A tick stays only where no such record can exist.

**Note, 2026-11-22.** Asked whether a run the owner makes from MO2 itself should be told from the tool's output
files and counted: "I don't care, we only want our ModTrap to do its job flawlessly, what the user does outside the
ModTrap is irrelevant and can't take responsibility." So it is not built: only a run ModTrap started counts, and what
is done outside ModTrap is neither looked for nor answered for.

## MT30

**Nothing is started while ModTrap is still reading or scanning** · *2026-11-22 · Decided by the owner*

**Owner's words.** "can you also make ModTrap monitor its own loading, checking, scanning processes so the tools and
features are greyed until those are done? I noticed that after launch I can launch a demaster even though scans are
still ongoing."

**Decision.** ModTrap tells what reading and scanning of its own is going; until all of it has finished, what would
change the modlist or start a program is greyed on the page and refused by the program, and the one go waits and
goes on by itself (WHY§92, DESIGN§18).

## MT31

**A tool with no switch, only a button, is run by ModTrap pressing it** · *2026-11-22 · Asked by the owner; the how is left to ModTrap (as MT17)*

**Owner's words.** "it done everything until synthesis needed to run (even started, ran and closed Pandora), but it
did not start synthesis. It seems Synthesis was ready to run (no errors this time)."

**Settled under that freedom** (WHY§93, TL01§21; the owner may overrule any of it):

- ModTrap presses the tool's run button, named as data, once the tool has it ready, and never while it is greyed.
- It asks the tool's window to close when the tool's own log says the run has come to its end; never because the
  tool has gone quiet. This amends MT25 as MT28 did.
- Any doubt (no such button, several, a press that starts nothing, no end in the log) leaves the tool open and
  the owner's, with the reason said.
- The same setting as for tools with switches turns it off.

## MT32

**A compiler that crashes inside MO2 goes on MO2's list of programs it leaves alone** · *2026-11-22 · Under MT17: the result is the owner's, the how is ModTrap's*

**Owner's words.** "Synthesis started patching this time, but it had errors and then closed on its own." Before
it, on what ModTrap is for: "we only want our ModTrap to do its job flawlessly".

**Settled under that freedom** (WHY§94, MO01§11, TL01§22; the owner may overrule any of it):

- When a tool's own log shows its compiler crashing inside MO2, ModTrap adds the compiler to MO2's "Executables
  Blacklist", in MO2's settings file, before it starts the tool again.
- Only with MO2 closed; a copy of MO2's settings file as it was is kept with the session; the change is in the
  History; a setting, on by default, turns it off.
- It is MO2's own setting, outside any demaster: Revert does not undo it. The kept copy, or MO2's Workarounds
  page, is the way back.
- After a tool closed without output, the row of tools starts it once more, at most twice, only for a stated
  reason.

## MT33

**The settings files that name the plugin, and checks after the demaster** · *2026-11-22 · Asked by the owner; the how is left to ModTrap (as MT17)*

**Owner's words.** "looks like the demaster went through fine, MO2 has no warnings. Could this step be done by
ModTrap as well? Could we implement after demaster checks?"

**Settled under that freedom** (WHY§95, TL01§23; the owner may overrule any of it):

- ModTrap reads those files line by line and settles the step itself where every line only gives something of the
  mod's or reaches only the mod's things. A line that leaves the mod's things out, and a file of a kind whose
  handling ModTrap has not read, stay the owner's, with the lines shown.
- After a demaster ModTrap gives one account of its checks, each a fact it read or recorded, and says the
  demaster is complete and checked only when all hold, naming what is left to the owner.

## MT34

**A scanner of every settings file in force, and of the frameworks installed** · *2026-11-22 · Asked by the owner; the how is left to ModTrap (as MT17)*

**Owner's words.** "can you also add a scanner for all tools and frameworks, so they can be read at the end of the
demaster process reliably?"

**Settled under that freedom** (WHY§98, TL01§25; the owner may overrule any of it):

- One scanner looks through the whole modlist for the steps of a demaster and again after it: the game's Data
  folder, every enabled mod and Overwrite, with no time limit. Of files with the same path only the winner counts,
  as in the game. Each file is read to its end.
- What it could not list or read is named, and then the settings-files step is the owner's: ModTrap says
  "none names the plugin" only when it looked through everything.
- The Tools tab shows what the scanner covers: the files in force, the kinds of settings file with whether ModTrap
  reads them line by line, and the frameworks installed.
- It only reads. It keeps no file's text, only which plugins of the modlist a file names.

## MT35

**Should the scanner also look through the animation folders** · *Open*

The scanner (MT34) looks through each mod's top folder, `SKSE/Plugins` and `FLM`: where the frameworks ModTrap has
read keep their settings files. Animation replacers keep condition files beside the animations, under `meshes`, and
a condition can name a plugin. Those folders hold very many files, and ModTrap has not read such a replacer's source.

- **A. Leave them out** (as now): the scan stays short; a condition that names the mod's plugin is not found.
- **B. Add them** once the replacer's source is read: the first scan of a large list takes longer (how much is
  seen from the scanner's time on the owner's list, which the log and the Tools tab now state).

**Recommendation: B**, as the next step, after the owner's next session file shows how long the scan takes. By what
is publicly said of such replacers, a condition about a plugin that is not loaded simply does not hold, so nothing
breaks meanwhile; that is LIKELY, not read in source.
