# STORY-028: name tables for people to look things up (spells, globals, retorts, unit types, ...) (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-14). **Priority:** next, for the first users.
**Size:** small to medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-14 ("we need to include name tables for the spells and globals and such. Maybe the GitHub wiki is a good spot to stick that info and then just link to the tables from the readme")

## The need

A new user types `mompy poke wizard 1 cast aura_of_majesty` or `spells.earth_lore` or `create 60` and needs to know **what names and numbers exist**: the 24 global enchantments, the 18 retorts, the 214 spells, the 198 unit types, the 32 unit enchantments, the lair kinds, the experience levels. Today only some of it is reachable (`mompy fields` lists fields, `peek wizard 1 globals` shows the names that are set, an unknown name lists the choices) and none of it is in one place.

## Where it goes

Kevin's idea: **the GitHub wiki**, linked from the README. Two practical points:

- A GitHub wiki is a separate git repository (`mompy.wiki.git`) that only exists after the first page is created in the web interface, and it is **not reviewed through pull requests**. Putting text there is publishing, so it is Kevin's to switch on and to push. The pages can be prepared here as markdown (`docs/wiki/`) and **generated from the field table** (`fields.toml`), so they cannot go stale, with a test that checks the generated pages match.
- The alternative, tables as pages in `docs/reference/` linked from the README, is versioned with the code and goes through the same review. Either is fine; the generated markdown is the same.

## One decision for Kevin: the game's own names

- **Safe to publish as tables (mompy already ships them):** the 24 global enchantments (order and names from the manual, in `fields.toml`), the 18 retorts, the 32 unit enchantments (ReMoM's list), lair kinds, node types, experience levels, the field list per block (what `mompy fields` prints), the sign rule for `poke`.
- **The 214 spell names and the 198 unit type names are the game's own text.** mompy reads them from the running game on purpose and ships none ([STORY-005](STORY-005-spell-names.md)); a public table of them would be shipping them. (Mirror, which edits saves, already ships unit and building names; the backlog says so.) Options: **(a)** publish them anyway, **(b)** do not, and add commands that print them from the running game: `mompy names spells`, `mompy names units` (each number with its name, searchable), so the wiki says how to list them instead of listing them. **Recommendation: (b)**: it keeps the "nothing from the game is shipped" promise, and the lists are always right for the player's game.

## To do

1. `mompy names spells|units|globals|retorts|enchantments|kinds` (the last four from the field table, the first two from the game), `--json`.
2. A generator for the markdown tables from `fields.toml`, and a test that the pages in `docs/wiki/` (or `docs/reference/names/`) are up to date.
3. The README links to them; the wiki (if used) gets its first page from Kevin and the generated files pushed by him.

## Definition of done

A stranger can find every name `mompy` accepts without reading the source, from the README in two clicks; nothing from the game's own files is in the repository or the wiki unless Kevin chose (a).
