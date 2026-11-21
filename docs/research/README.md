# Research index

What MO2's and xEdit's own sources say, kept apart from the design so that a fact and its source can be checked.
Every statement carries a label: **FACT** (read in the named source at the named commit), **LIKELY** (inferred, not
yet proven), **SPECULATION**, **METHOD** (how something is or will be found out). The reasoning that follows from
these notes is in [REASONING.md](../REASONING.md) (`WHY§n`).

Sources are read only, never built or run, each cloned in its own folder outside this repository.

| Code | Note | Source |
|---|---|---|
| MO01 | [MO2: the instance and the command line](mo2/01-instance-and-command-line.md) | `github.com/ModOrganizer2/modorganizer`, `master` at `4ba22f0` (2026-10-05); GPL-3.0 by its `LICENSE` |
| MO02 | [A mod's installer file, as MO2 reads it](mo2/02-installer-file.md) | `github.com/ModOrganizer2/modorganizer-installer_fomod`, `master` at `7c39956` (2026-10-06); no licence file at its root, read only |
| XE01 | [xEdit: the command line and scripting](xedit/01-command-line-and-scripting.md) | `github.com/TES5Edit/TES5Edit`, tag `xedit-4.1.5f` at `f5c00f3` (2024-04-27); MPL-2.0 by its `LICENSE.txt` |
| XE02 | [The plugin file header](xedit/02-plugin-header.md) | the same xEdit source: its record definitions |
| TL01 | [How patching tools name and mark their output](tools/01-outputs.md) | the repositories of Wrye Bash, Synthesis and ParallaxGen, each at a named commit |

XE01 is supplemented by the source of the script engine xEdit uses, JVCL's interpreter (`github.com/project-jedi/jvcl`
at `b045b99`, MPL 1.1, `jvcl/run/JvInterpreter*.pas`): see WHY§34.

MO01 also draws on MO2's Bethesda game plugins (`github.com/ModOrganizer2/modorganizer-game_bethesda` at
`a6a2340`), for the two plugin list files.

Not yet researched: the virtual file system's handling of a changed file (MO01§5); xEdit versions other than
4.1.5f (WHY§15); and DynDOLOD's own documentation, for its output's names (TL01§5).
