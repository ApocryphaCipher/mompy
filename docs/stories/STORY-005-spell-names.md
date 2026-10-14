# STORY-005: Spell names from the player's own files

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-14), checked on a real game
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

Fields such as `spell 59` and `researching` take a name (`"Aura of Majesty"`) when the game folder has **`SPELLDAT.LBX`**. Mirror's `Mirror.Spells` reads it: entry 0 is 215 records of 36 bytes, the index is the spell number,
`+0` name (18 bytes), `+23` realm, `+26` casting cost, `+28` research cost. mompy reads it at run time (a path option or the default install folders) and falls back to numbers.
No names are shipped. A bundled fallback list is Kevin's decision (see the backlog).

## Definition of done

A test on a synthetic LBX built in the test; `peek wizard 1 spell "Earth Lore"` on a real game.

## Outcome

Built as `mompy/spellnames.py` (`tests/test_spellnames.py`), **without reading `SPELLDAT.LBX`**: the game keeps the whole spell table in memory (215 records of 36 bytes, name first, realm at `+23`), found at the wizard table plus `0x5DDF6` (0x906B0 in the research setup) or, if it is not there, by searching memory for "None" followed by "Earth to Mud". Checked 2026-10-14 against the file: all 215 names match. So no game folder is needed, nothing is shipped (the backlog question "bundle the names?" does not arise), and a game without the table falls back to numbers.

- `peek wizard 1 researching` and `research_candidates` print `Enchant Item (207)`; `spells.time_stop` or `spells.earth_lore` work for `peek` and `poke` (case, `_`, apostrophes ignored; a unique prefix works; an ambiguous one is listed); `poke wizard 1 researching vertigo` and `none`.
- The names ride on the list of wizard names every command already passes around (`locate.Names`, with a `.spells` list), so the change was small.
- Real game (fork 0.84.0-alpha, 2026-10-14): `researching = Enchant Item (207)`, `spells.Time Stop = 2 (known)`, `researching vertigo` resolved to 53 in a dry run, `spells.earth` listed Earth to Mud, Earth Lore, Earthquake, Earth Elemental, Earth Gate.
- Not done: spell names in `snapshot` diffs (a diff of `researching` prints the number).
