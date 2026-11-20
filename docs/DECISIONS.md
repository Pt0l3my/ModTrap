# Owner decisions

The project owner's decisions on ModTrap, binding, one entry each, numbered MT1 onwards. A new question takes the next
free id as an entry marked **Open**, with its options and a recommendation; the owner's answer is recorded in the
entry with its date and their words; a later decision amends an earlier one by a dated note, never by rewriting it,
and ids are never renumbered. Findings are cited from [REASONING.md](REASONING.md) as R-numbers, the design as
[design 0001](design/0001-design.md).

## By date

- **2026-11-20.** MT1 (what "demaster" means), MT2 (the page: scan, tick, one button, a terminal), MT3 (built like
  DataPiler; the sweep), all from the owner's messages of that day.
- **Open.** MT4 (what is removed, and what is never forced), MT5 (where the result goes), MT6 (dependants that
  should be disabled, not demastered), MT7 (which games), MT8 (which xEdit), MT9 (who enables and disables mods in
  MO2), MT10 (the repository), MT11 (how ModTrap is installed and started), MT12 (the session link in commits).

## MT1

**What "demaster" means** · *2026-11-20 · Decided by the owner*

**Question.** Three meanings were put: (a) remove a mod as a master from every plugin that depends on it, dealing
with what they take from it; (b) xEdit's Clean Masters only; (c) clearing a plugin's ESM flag.

**Decision.** (a), with (b) as its last step: the "Master Removal" procedure of the guide the owner supplied (R1).
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

**Note.** Design 0001 puts a plan and a dry run between the button and the changes (§6.1, §6.2). Whether the owner
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

**What is removed, and what is never forced** · *Open*

**Question.** The guide leaves a judgement to the user: "remove the whole record … or make a more surgical edit". A
tool needs rules. Which?

**Options.**

- (a) **Four cases, nothing forced** (design §5). A: the dependant's copy of a record that belongs to the trapped
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

## MT5

**Where the result goes** · *Open*

**Question.** The guide's procedure changes the dependant plugins in place, inside their own mod folders. Should
ModTrap?

**Options.**

- (a) **A new mod.** The demastered plugins are written to a new mod folder, `ModTrap - <name>`, in the instance's
  mods folder. Enabled, it wins over the originals; deleted, everything is as before. The originals are never
  changed, and are checked by hash before and after (design §6.3 to §6.5).
- (b) **In place**, as in the guide, with ModTrap's own backups and a restore button.

**Recommendation.** (a). A Wabbajack-installed list also stays verifiable against its original files this way. It
rests on one unproven point about xEdit (R12), which the probe settles first (design §9); the fallback keeps (a)
either way.

## MT6

**Dependants that should be disabled, not demastered** · *Open*

**Question.** The guide disables patches that exist only for the unwanted mod, and demasters only the plugins that
do other things too (R2). How should ModTrap tell them apart?

**Options.**

- (a) **ModTrap proposes, the owner decides.** After the dry run, a dependant of which nothing or almost nothing
  would remain is proposed as "disable this yourself"; every dependant's treatment can be changed on the page.
- (b) **Demaster everything**, even if an empty plugin results.
- (c) **The owner marks each dependant by hand**, no proposal.

**Recommendation.** (a).

## MT7

**Which games** · *Open*

**Options.** (a) Skyrim Special Edition and Anniversary Edition only; (b) also Skyrim VR; (c) also the 2011 Skyrim
(LE).

**Recommendation.** (a) first. The design does not shut the others out: xEdit handles them, and ModTrap's own
reader only needs the plugin header, which differs little.

## MT8

**Which xEdit** · *Open*

**Question.** ModTrap uses the xEdit already set up as an executable in the owner's MO2. Which version does the
owner run? The research was done against 4.1.5f, the version in the screenshots.

**Options.** (a) 4.1.5f or newer required, older refused with a message; (b) whatever is found, untested.

**Recommendation.** (a). The owner is asked only to say which version their MO2 starts (the window's title bar
shows it).

## MT9

**Who enables and disables mods in MO2** · *Open*

**Question.** After a run, the output mod must be enabled and the trapped mods disabled. Who does it?

**Options.**

- (a) **The owner, in MO2.** ModTrap lists the steps and never writes to a profile. MO2 can stay open throughout.
- (b) **ModTrap**, by editing the profile's `modlist.txt` and `plugins.txt`. One click fewer; requires MO2 to be
  closed (an open MO2 would overwrite the files), and makes ModTrap a program that edits the owner's profile.

**Recommendation.** (a) for the first version; (b) can be added later as an option once the rest is trusted.

## MT10

**The repository** · *Open*

**Question.** ModTrap has no repository yet; the work is in a local one and nothing is pushed.

**Options.** (a) the owner creates an empty repository named ModTrap, private until a first release; (b) public from
the start, like DataPiler.

**Recommendation.** (a). Also to settle: the name on the licence's copyright line (now "the ModTrap authors"; DataPiler
uses the owner's public handle).

## MT11

**How ModTrap is installed and started** · *Open*

**Options.**

- (a) **As DataPiler:** a small launcher and a PowerShell script that find Python and start the server; an updater
  later. Python standard library only.
- (b) **An MO2 plugin** (a Python plugin inside MO2 itself). Closer to MO2, but it would run inside MO2 (GPL-3.0)
  and could not use DataPiler's page, server or launcher.

**Recommendation.** (a): it is what the owner asked for, and it keeps ModTrap's code and licence apart from MO2's.

## MT12

**The session link in commit messages** · *Open*

**Question.** The brief ModTrap was started from says that commit messages keep the `Co-Authored-By` line and leave
out the link to the chat session. The owner did not recall the rule; the session that wrote the brief has been asked
where it comes from.

**Until decided.** The link is left out (the cautious choice: it can be added later, but not removed once pushed).

**Note, 2026-11-20.** That session answered: it is the owner's own choice of 2026-11-16 for their other projects
("Stop adding them"), made because the link points to a private transcript and tells a reader nothing (R29). Open
only until the owner confirms it holds for ModTrap too.
