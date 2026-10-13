# STORY-001: doctor: is it safe to write?

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13)
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`mompy doctor` answers, before anything is written:

- Is the server up (`/dosbox/info`) and which DOSBox version is it?
- Does a write work? (Write a scratch location with a compare-and-swap and read it back; never a game table.)
- **Where is the game's memory?** Not at a fixed address: scan the 16 MiB for five printable names at the wizard record stride (`0x4C8`) and take the shift from `0x328BA`. *First case:* the released macOS DOSBox 0.83.0 put it at `0x3239A` (shift `-0x520`), 2026-10-13, with default settings **and** with Kevin's config file; his research fork with that same config has it at `0x328BA`. So the base depends on the DOSBox build: 0.84-and-later reserves memory for DOS `STACKS` (81 paragraphs + 1 header = `0x520`, exact; see [ram-layout.md](../reference/ram-layout.md)), and a `stacks` setting other than the default moves it again. A tester's setup will differ.
- Does the game's memory **look like the layout in [ram-layout.md](../reference/ram-layout.md)?** Five names, printable, at the wizard stride; city, unit and node counts in range.
  If not, say so and make every later command refuse (unless the player gives the table's address by hand).
- Which extras does this server have (screenshot, pause)?

Output is plain text with a clear verdict, and an exit status 0 or 1.

## Definition of done

Tested against a fake server (a small local `http.server` in the tests) for each verdict, and run once against Kevin's game.
