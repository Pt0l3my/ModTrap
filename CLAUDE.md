# ModTrap: notes for Claude

ModTrap is a local tool on the owner's PC for Mod Organizer 2 (MO2) and Skyrim. It "demasters" chosen mods in a
modlist: it removes them as masters from the plugins that depend on them, by running the owner's own xEdit inside the
MO2 instance with ModTrap's own script. Its decisions are in [docs/DECISIONS.md](docs/DECISIONS.md) (MT1 onwards), its
findings in [docs/REASONING.md](docs/REASONING.md), its design in [docs/design/](docs/design/).

## Privacy and safety: the sweep comes first

- Nothing is pushed or uploaded before the privacy and safety sweep passes. The sweep is the owner's `privsweep`, kept
  only in the owner's private Skyrizz repository under `tools/privsweep/`, never copied here or into any public
  repository, and installed as git's global pre-push gate. If `~/.config/privsweep` is missing, run
  `python3 -I tools/privsweep/privsweep.py install` in the Skyrizz checkout first. Sweep by hand what the gate does
  not cover: a message to another session (`privsweep.py text message`, the text on stdin) and a file sent to the
  owner (`privsweep.py files PATH`).
- Never bypass it: no `--no-verify`, no change to `core.hooksPath`, no HOME or GIT_CONFIG override.
- Nothing personal about the owner in any file, commit, page or upload: real name, account names, machine names,
  contact details, API keys, local paths, endpoint addresses or IPs. The owner's own local commands go in chat only.
  Examples and tests use placeholders, with paths on drive C:.
- Commit identities are noreply addresses only; use the environment's default git identity. No model identifiers of
  the assistant in files, apart from the commit trailer.

## Mods

- Never commit, upload or redistribute anyone's mod files, plugins or their contents, nor record names, FormIDs or
  text taken from a real mod. ModTrap's output stays on the owner's PC.
- Test fixtures are invented: tiny plugins written by ModTrap's own code, with invented names.
- ModTrap never changes a file in the game's folder or in an original mod's folder. What it writes goes to its own
  work folder and to its own output mod.

## Licences

- ModTrap is MIT. Write our own code. Read a dependency's licence before adopting it and list it in `NOTICE`.
- MO2 is GPL-3.0 and xEdit is MPL-2.0: never copy their code or their scripts, never bundle them. ModTrap calls the
  owner's own installed copies. ModTrap's xEdit script is ours.
- Untrusted copies (clones, downloads, uploads) go in their own folder outside the repository, are read with
  `python3 -I` or grep, and are never built or run.

## Working rules

- Work on a topic branch (`design/`, `feat/`, `fix/`, `docs/`, `test/`, `chore/`), never directly on `main` unless
  the owner asks. Push only at meaningful milestones or when asked. Open a pull request only when asked.
- Ask the owner, with a recommendation, about anything the design leaves open, as an MT entry marked Open.
- `docs/REASONING.md` is append-only: dated entries labelled FACT, LIKELY, SPECULATION, METHOD or DECIDED.
- Text the owner reads uses British spelling.
