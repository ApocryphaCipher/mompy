# STORY-013: Spike: what does the game do with a global set by hand?

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** A **spike**: a time-boxed experiment whose product is knowledge, not a feature.
**Size:** small to medium (a play session)
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 ("not sure, flag as a test and see")

## Data so far (2026-10-13)

- **Aura of Majesty** cast on Jafar by `mompy poke wizard 1 cast aura_of_majesty`: it **appeared in the Magic screen's "Overland Enchantments" box** at once, no mana paid. After one End Turn it was still active, relations rose (Freya 0 to 2, Sharee and Tauron -20 to -16, on both wizards' records) and mana fell 9 (about 8 more than a normal turn: probably the upkeep). A real cast had jumped every relation to 20 first; the flag alone gave +2/+4 (guess: the jump is the cast routine). Not tried: an unaffordable upkeep.

## The question

[STORY-012](STORY-012-cast.md) writes one byte and trusts the game to take it from there. Is that true for **every** global, or do some need more than the flag?

## How

Once `poke` exists, in a game on the advanced SAVE2 (so one End Turn is cheap): for each of the 24 globals, `cast` it on a wizard and watch **one End Turn**:

1. Does it appear in the Magic screen's "Overland Enchantments" box on that wizard?
2. Does the **effect** happen (the spell's own description in the spell book: `spellbook.pdf` in the game folder)? Aura of Majesty raises relations; Nature Awareness shows the map's resources; Just Cause raises fame...
3. Is the **upkeep** charged at End Turn (the Magic screen's mana income), and is it dispelled when unaffordable?
4. Did the game **crash**, hang or change anything unexpected (the research fork's `ReadMemoryCommand` log and a `snapshot` before and after show it)?
5. **Does the byte carry a power level?** So far the byte has been seen only as 0 or 1; if the game keeps a strength or a countdown in it, other values appear. Try 2, 3, 255 on a cheap global and see whether the effect changes. (This settles "max power for spells with power-ups" in STORY-012.)

Record each global in a table in `docs/reference/ram-layout.md` (or a new `globals.md`): works, partly, needs more, crashes; and set its confidence mark in the field table.

## Definition of done

A table of all 24 with a result each (some may say "not tried: needs a battle or a particular map"); the questionable ones are STORY-014's, not this story's; STORY-012's `--force` list updated from the result.
