# ModTrap

A local tool for Mod Organizer 2 and Skyrim that takes a mod out of a modlist the way Soul Trap takes a soul from a
body: it removes the mod as a master from every plugin that depends on it, so that the mod can be disabled without
"missing master" errors.

**Status: in the making. Nothing ModTrap does changes your modlist yet.** ModTrap opens a page in your browser
that shows an MO2 modlist as MO2 has it: every mod with its priority, every plugin with its place in the load order,
each plugin's masters and what needs it, and, for the mods you tick, everything that depends on them. A **dry run**
then starts your own xEdit through MO2 with ModTrap's script, which only reads, and lists what a demaster would take
out of each dependant plugin. A Steps tab lists everything the demaster takes, to do by hand for now. The step in which ModTrap does it for you ("Demaster Selected") is written but switched off until it has been proven on a real modlist.

ModTrap also helps to **add** a mod: drop the mod's archive on the page. ModTrap unpacks it in its own work folder
(a .7z or .rar needs 7-Zip installed), asks the mod's own installer questions if it has any, and tells what the mod needs, where it should go among the mods and in the
load order, which files of which mods it would replace, which tools must run again, and the steps in order. Putting
the mod into MO2 for you is written into the design but not built: for now nothing in your modlist changes.

To try it (Windows, Python 3.10 or newer): download this repository, then double-click `ModTrap.cmd`, or run

```
python -m modtrap
```

in its folder. Drop your modlist's folder (the one MO2 itself is in) on the page, or paste its path and press Open. Your work is kept in a session: press Quit, start ModTrap again, and you are back where you were. The page is served on your
own PC only (127.0.0.1), and nothing is sent anywhere. For a quick look without the page:

```
python -m modtrap scan "C:\Modlists\Example" --mod "Some Mod"
```

and, for what it takes to add a mod that MO2 has installed:

```
python -m modtrap add "C:\Modlists\Example" --mod "Some New Mod"
```

See:

- [docs/design/0001-design.md](docs/design/0001-design.md): what ModTrap is to do and how;
- [docs/DECISIONS.md](docs/DECISIONS.md): the owner's decisions, and the questions still open;
- [docs/research/](docs/research/README.md): what MO2's and xEdit's own sources say, each fact with its source;
- [docs/REASONING.md](docs/REASONING.md): why the design is the way it is, and what was ruled out.

ModTrap runs on your own PC, serves a page to your browser on 127.0.0.1 only, and calls your own installed MO2 and
xEdit. It contains neither of them, and no mod files. MIT licence.
