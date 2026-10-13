# EPIC-001: momctl, a command line for a running game

**Status:** proposed (2026-10-13), nothing built
**Owner:** [Kevin](https://github.com/KevinAsbury)

## The idea

`momctl peek wizard 1 gold` and `momctl poke wizard 1 gold 30000`: read and change a running *Master of Magic* through DOSBox Staging's
memory API, safely (compare-and-swap, range checks, undo) and with the offsets and limits that Mirror's research has already verified.
It is for players ("give me 30000 gold") and for the research loop (change a value, look at the screen, no save, load and End Turn).

Why not a TSR inside DOS: it would work without the API but means real-mode code that hooks the keyboard and draws over the game's graphics mode in
the game's own scarce memory, to be written and debugged almost blind. The API already exists and is built into DOSBox Staging. A TSR is a later,
separate project if players want it.

## Stories

- [STORY-001](../stories/STORY-001-doctor.md): `doctor`: find the server, check the layout looks right, say whether writes work
- [STORY-002](../stories/STORY-002-field-table-and-peek.md): the field table and `peek`
- [STORY-003](../stories/STORY-003-poke.md): `poke` with compare-and-swap, range checks, `--dry-run` and `undo`
- [STORY-004](../stories/STORY-004-snapshot-and-diff.md): `snapshot` and `diff`
- [STORY-005](../stories/STORY-005-spell-names.md): spell names from the player's own `SPELLDAT.LBX`
- [STORY-006](../stories/STORY-006-more-fields.md): relations, treaties, global enchantments, the defeated flag; locate the missing blocks
- [STORY-007](../stories/STORY-007-packaging.md): install with `pipx`, the README, the licence
- [STORY-008](../stories/STORY-008-stock-dosbox.md): confirm it works against the released DOSBox Staging binaries

Suggested order: 008 (a quick check that decides everything else), 001, 002, 003, then 004 to 007.
