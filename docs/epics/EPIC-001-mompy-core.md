# EPIC-001: mompy, a command line for a running game

**Status:** proposed (2026-10-13), nothing built
**Owner:** [Kevin](https://github.com/KevinAsbury)

## The idea

`mompy peek wizard 1 gold` and `mompy poke wizard 1 gold 30000`: read and change a running *Master of Magic* through DOSBox Staging's
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
- [STORY-009](../stories/STORY-009-dosbox-memory-map-endpoint.md): ask DOSBox where the game was loaded (nice to have)
- [STORY-010](../stories/STORY-010-where.md): `mompy where`, the map tile under the game's mouse cursor (nice to have)
- [STORY-011](../stories/STORY-011-where-name.md): `mompy where <name>`, find a city or wizard by name (nice to have)
- [STORY-012](../stories/STORY-012-cast.md): `poke wizard N cast <global>`, a global enchantment straight on the wizard (nice to have)
- [STORY-013](../stories/STORY-013-spike-globals-by-hand.md): spike: what the game does with a global set by hand (nice to have)
- [STORY-014](../stories/STORY-014-spike-wonky-globals.md): spike: the wonky globals, Spell of Mastery, Planar Seal... (nice to have)
- [STORY-015](../stories/STORY-015-cast-unit.md): `poke wizard N cast unit.<name>`, summon any unit, no fuss (nice to have)
- [STORY-016](../stories/STORY-016-spike-summon-a-unit.md): spike: what the game writes when a unit is summoned (nice to have)
- [STORY-017](../stories/STORY-017-pew.md): `pew wizard N`, banish a wizard; `--dead` to finish them (nice to have)

Suggested order: 008 (a quick check that decides everything else), 001, 002, 003, then 004 to 007.
