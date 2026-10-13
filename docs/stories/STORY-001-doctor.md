# STORY-001: doctor: is it safe to write?

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** done (2026-10-13): built, tested against a fake server, and run once against Kevin's real game
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`mompy doctor` answers, before anything is written:

- Is the server up (`/dosbox/info`) and which DOSBox version is it?
- Does a write work? *(Changed while building it: not a scratch location. The game may use any of the 16 MiB (extended or expanded memory), so a scratch address is not safe once the game runs. `doctor` writes back **the byte that is already there** at the first byte of a wizard name, with a compare-and-swap, which tests the write path and changes nothing.)*
- **Where is the game's memory?** Not at a fixed address: scan the 16 MiB for five printable names at the wizard record stride (`0x4C8`) and take the shift from `0x328BA`. *First case:* the released macOS DOSBox 0.83.0 put it at `0x3239A` (shift `-0x520`), 2026-10-13, with default settings **and** with Kevin's config file; his research fork with that same config has it at `0x328BA`. So the base depends on the DOSBox build: 0.84-and-later reserves memory for DOS `STACKS` (81 paragraphs + 1 header = `0x520`, exact; see [ram-layout.md](../reference/ram-layout.md)), and a `stacks` setting other than the default moves it again. A tester's setup will differ.
- Does the game's memory **look like the layout in [ram-layout.md](../reference/ram-layout.md)?** Five names, printable, at the wizard stride; city, unit and node counts in range.
  If not, say so and make every later command refuse (unless the player gives the table's address by hand).
- Which extras does this server have (screenshot, pause)? *(Not built: the only way to know is to send the request, and a screenshot or a pause acts. Deferred; commands that need an extra will try it and say clearly if it is missing.)*

Output is plain text with a clear verdict, and an exit status 0 or 1.

## Definition of done

Tested against a fake server (a small local `http.server` in the tests) for each verdict, and run once against Kevin's game.

## Outcome (2026-10-13)

Built: `mompy/api.py` (the client: version, reads, compare-and-swap writes, and the 403 and 412 answers as exceptions), `version.py` (parsing, and the expected wizard-table address per DOSBox version: `0x328BA` for 0.84 and later, `0x3239A` for 0.83),
`layout.py` (every table as an offset from the wizard table), `locate.py` (the scan, and the plausibility checks for wizards, cities, units and nodes), `doctor.py` and `cli.py`.
Verdicts: **READY** (exit 0), **READ-ONLY** (the game was found, writes refused: it names `webserver_allow_writes`) and **NOT READY** (no API, no game, or tables that do not look right: nothing is written).

- The scan reads all 16 MiB once and looks for five printable names at the wizard record stride (names must be NUL-padded). Candidates are then checked: cities (name, position on the 60 × 40 map, plane, owner), the unit count and units, and nodes. If two places qualify it says so and takes the first.
- An address other than the one expected for the DOSBox version is a **warning**, not a failure: the tables are what decide.
- **A bug the tests caught:** the real server's 412 answer nests the current bytes under `"memory"`, not at the top level (seen in the STORY-008 run); the fake server follows the real shape.
- Tests: 20, with a fake DOSBox server in `tests/`; warnings are errors. Not yet run: Python 3.9, and a real game.

**Real game, 2026-10-13:** Kevin's fork (`0.84.0-alpha (83716)`, the `apocrypha/research` build), MAXIMUS loaded, `webserver_allow_writes = true`:
every check `ok`, verdict **READY**, exit 0, **0.2 s** in all. Wizard table at `0x328BA` (as expected for 0.84): Jafar, Freya, Sss'ra, Sharee, Tauron;
cities 33 plausible of 100 slots at `0x6F980`; units 147 live and all 147 plausible at `0x7E060`; nodes 30 of 30 at `0x85FE0`; the write accepted. Read back afterwards: the wizard names were unchanged.
*Not tried on a real game:* the READ-ONLY verdict (start the fork without `webserver_allow_writes`), the 0.83.0 layout (the stock build is gone; the STORY-008 run found `0x3239A` there), Python 3.9.
