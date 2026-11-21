# XE02. The plugin file header (Skyrim SE)

## 1. Source

`github.com/TES5Edit/TES5Edit`, tag `xedit-4.1.5f` at `f5c00f3`: its record definitions for Skyrim, which describe
the file format. Cited as `file:line`. Read only; ModTrap's reader is written from this description, not from
xEdit's code.

## 2. The header record

- **FACT.** A plugin starts with one record of type `TES4`, "Main File Header" (`Core/wbDefinitionsTES5.pas:12764`).
- **FACT.** A record header is: the 4-letter type, the size of the record's data as an unsigned 32-bit number, then
  the record's flags (`Core/wbDefinitionsCommon.pas:1240-1245`).
- **LIKELY.** After the flags come the form ID (4 bytes), version control info (4 bytes), the form version (2
  bytes) and 2 more bytes, making a 24-byte header in Skyrim SE; all numbers little-endian. From the same
  definition, read only in part, and from the format as widely documented.

## 3. The header's flags

- **FACT.** `0x00000001` is ESM (a master file), `0x00000080` is Localized, and in Skyrim SE `0x00000200` is ESL
  (a light plugin) (`Core/wbDefinitionsTES5.pas:12765-12775`).

## 4. The header's fields

- **FACT.** In order: `HEDR`; `OFST` and `DELE` (ignored); `CNAM`, the author; `SNAM`, the description; then for each
  master a `MAST` with its file name followed by a `DATA` of 8 bytes; then `ONAM`, `SCRN`, `INTV`, `INCC`
  (`Core/wbDefinitionsTES5.pas:12776-12791`).
- **LIKELY.** Each field is a 4-letter type, a 16-bit size and that many bytes; `MAST`, `CNAM` and `SNAM` are
  zero-ended strings; `HEDR` is 12 bytes (a version number as a float, the number of records, the next object id).
  As widely documented; the reader checks sizes and refuses what does not fit.
- **LIKELY.** The master list's order is the order of the `MAST` fields, and it is that order the load-order prefix
  of a form ID refers to.

## 5. What ModTrap reads

- **METHOD.** Only this record: the flags, the author, the description and the master names. The reader stops at
  the end of the header record and never reads a plugin's other records (WHY§10).
- **METHOD.** A file that does not start with `TES4`, whose sizes run past the end of the file, or whose header is
  larger than a fixed cap is reported as unreadable and never guessed at.

## 6. The header's version, and the room in the load order

- **FACT.** The `HEDR` field starts with a version number, a 4-byte float. xEdit writes 1.7 into a new Skyrim
  plugin, and 1.71 for Skyrim SE (`Core/wbDefinitionsTES5.pas:13643-13645`, `Core/wbImplementation.pas:3132`).
- **LIKELY.** 1.71 came with game version 1.6.1130 and allows a wider range of record numbers in a light plugin; an
  older game needs a backport to load such a plugin as meant. Known from the modding community, not read in a
  source here; ModTrap only points the version out (DESIGN§16.2).
- **FACT.** xEdit gives a light plugin one of the places `FE 000` to `FE FFF` and refuses more ("Too many light
  modules"), and gives a full plugin a place below `FE` (`Core/wbImplementation.pas:3145-3158`): 4096 light and 254
  full plugins.
- **METHOD.** ModTrap counts the active plugins of each sort against those two numbers (DESIGN§16.2).
