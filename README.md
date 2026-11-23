# ModTrap

A local tool for Mod Organizer 2 and Skyrim that takes a mod out of a modlist the way Soul Trap takes a soul from a
body: it removes the mod as a master from every plugin that depends on it, so that the mod can be disabled without
"missing master" errors.

**Status: in the making, and not yet proven on a real modlist.** ModTrap opens a page in your browser that shows an
MO2 modlist as MO2 has it: every mod with its priority, every plugin with its place in the load order, each plugin's
masters and what needs it, and, for the mods you tick, everything that depends on them. A **dry run** then starts
your own xEdit through MO2 with ModTrap's script, which only reads, and lists what a demaster would take out of each
dependant plugin. A Steps tab lists everything the demaster takes, and checks each step against the modlist's files.

The demaster itself ("Demaster Selected") is built but switched off: it makes copies in a safe folder, has xEdit
write demastered copies of the dependants as new files, checks them, and then, with MO2 closed, adds a mod of its
own with those copies, switches off the patches made only for the mod and disables the mod. Revert puts everything
back, and a History tab lists every change. By default nothing ModTrap does changes your modlist.

Before any of that is allowed on a modlist, ModTrap must pass its **probe** there (Tools tab, in a ModTrap started
with `--allow-changes`): it does its whole work once on three tiny invented plugins in two test mods of its own, and
removes them again. No mod of yours is touched by it.

ModTrap also helps to **add** a mod: drop the mod's archive on the page. ModTrap unpacks it in its own work folder
(a .zip and a .7z with its own readers; a .rar, or a .7z packed in a rare way, through 7-Zip or the unpacker
Windows 11 comes with), asks the mod's own installer questions if it has any, and tells what the mod
needs, where it should go among the mods and in the load order, which files of which mods it would replace, which
tools must run again, and the steps in order. From the steps it can start your xEdit, read-only, to list the records
the new plugin takes from other plugins, and start the modlist's tools through MO2 for you to work.

Putting the mod into MO2 for you ("Add it for me", with "Take it out again") is built but switched off: it exists
only when ModTrap is started with `--allow-changes`, and that is meant for once it has been proven on a real modlist.

With `--allow-changes`, the Modlist section's Mods tab works as MO2's own list does, with MO2 closed: tick a mod to
enable or disable it (its plugins are placed by MO2's own rule: a new one last, a master at the end of the masters'
block, none before its own masters), drag a row to move it, rename a separator. What is not safe is asked first;
every change can be undone; and a scanner tells, for a mod, whether its plugins stand safely in the load order and
which records and files it overwrites. The ticks that choose mods for a demaster are on Demaster's "Pick mods" tab.

The Plugins tab works the same way: tick a plugin to activate or deactivate it, drag it to another place in the load
order (within the limits MO2 itself keeps), and a symbol on a plugin's row says when something is wrong with it or
when it overwrites what other plugins change; a press on the symbol tells it in full.

A split view shows the mods and the plugins side by side, parted by a line that is dragged sideways. In a search
box, a star and a number (`*138`) goes to the entry with that priority. Every table's columns are set in width by
the lines between them, and moved to another place by their headings.

A click on a mod's name opens its web: the mod in the middle of every mod it has to do with (what it needs, what
needs it, patches for it, what it overwrites and what overwrites it, records two plugins both change), each in the
colour of its kind, with a link to the mod's page and, from Nexus or GitHub, the one picture that page opens with.

An installed mod is weighed at its place: which of its overwrites change nothing, which are what a patch or a
retexture is for, and which are the usual ways a modlist breaks; and whether its own files fit this game. A mod
that is in the modlist already is said so before it is installed, with both versions. Doubles are looked for when
a modlist is opened, and "Scan" in the header looks through every mod's files; what is found is on the Health tab.

Any mod can be uninstalled or renamed from its menu. An uninstalled mod is moved aside, whole, never deleted; the
History lists every change of the mod list (moves, renames, uninstalls) for good, each with its Revert.

A mod that is installed or updated is named by its title and its version ("Example Mod 1.2"), and the name is
offered in a box to change or keep.

The mods' list has MO2's own Conflicts, Installation and Notes columns, worked out by MO2's rules; a press on a
conflict mark draws the mods in conflict. The plugins' list shows MO2's own plugin groups where MO2 keeps them (its plugin manager extension's
`plugingroups.txt`), and ModTrap gives a plugin it installs or moves its group there; without them it is grouped by
the mods' separators.

ModTrap shows no window but its page in the browser: its program's console is hidden, and what it writes is on the
page's Log. It closes when its page is closed, never in the middle of a job, and a tab the browser brings back
starts it again.

ModTrap updates itself: the version at the top of the page is a button, and a release file dropped in its box is
checked, put in place (the version in use is kept aside), tried, and started.

To try it on Windows from the package (`ModTrap-<version>-win64.zip`, built by `tools/build_exe.py`): unpack it and
start `ModTrap.exe`, which starts it with `--allow-changes`. It runs on the Python
installed on the PC (3.10 or newer), or on its own where the package was built with Python inside.

To try it from this repository (Windows, Python 3.10 or newer): download it, then double-click `ModTrap.cmd`, or run

```
python -m modtrap
```

in its folder. Drop your modlist's folder (the one MO2 itself is in) on the page, or paste its path and press Open. Your work is kept in a session: press Quit, start ModTrap again, and you are back where you were. The page is served on your
own PC only (127.0.0.1), and nothing is sent anywhere. 

**Updating.** Download the repository again, unpack it into an empty folder (not over the old one) and start
`ModTrap.cmd` there. A ModTrap that is still running saves its session and closes by itself, and the new one takes
its place; your sessions are kept outside ModTrap's folder and come back. The version is at the top of the page and
in ModTrap's window. If you replace the files of a running ModTrap instead, it notices, starts nothing more, and
asks to be quit and started again.

For a quick look without the page:

```
python -m modtrap scan "C:\Modlists\Example" --mod "Some Mod"
```

and, for what it takes to add a mod that MO2 has installed:

```
python -m modtrap add "C:\Modlists\Example" --mod "Some New Mod"
```

If something goes wrong, "Save this session" on the Log tab packs the session's log and records into one .7z file,
with your folders and user name taken out and nothing of any mod in it, to send when asking for help.

See:

- [docs/design/0001-design.md](docs/design/0001-design.md): what ModTrap is to do and how;
- [docs/DECISIONS.md](docs/DECISIONS.md): the owner's decisions, and the questions still open;
- [docs/research/](docs/research/README.md): what MO2's and xEdit's own sources say, each fact with its source;
- [docs/REASONING.md](docs/REASONING.md): why the design is the way it is, and what was ruled out.

ModTrap runs on your own PC, serves a page to your browser on 127.0.0.1 only, and calls your own installed MO2 and
xEdit. It contains neither of them, and no mod files. MIT licence.
