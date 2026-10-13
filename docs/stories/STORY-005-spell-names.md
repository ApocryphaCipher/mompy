# STORY-005: Spell names from the player's own files

**Parent:** [EPIC-001](../epics/EPIC-001-momctl-core.md)
**Status:** proposed (2026-10-13)
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

Fields such as `spell 59` and `researching` take a name (`"Aura of Majesty"`) when the game folder has **`SPELLDAT.LBX`**. Mirror's `Mirror.Spells` reads it: entry 0 is 215 records of 36 bytes, the index is the spell number,
`+0` name (18 bytes), `+23` realm, `+26` casting cost, `+28` research cost. mompy reads it at run time (a path option or the default install folders) and falls back to numbers.
No names are shipped. A bundled fallback list is Kevin's decision (see the backlog).

## Definition of done

A test on a synthetic LBX built in the test; `peek wizard 1 spell "Earth Lore"` on a real game.
