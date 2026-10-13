# STORY-012: `mompy poke wizard N cast <global>`: put a global enchantment straight on a wizard (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** Depends on [STORY-003](STORY-003-poke.md) (`poke`).
**Size:** small to medium (most of it is checking each global in the game)
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

```
mompy poke wizard 1 cast aura_of_majesty        # put it on wizard 1's global list: no mana, no spell book, no casting turn
mompy poke wizard 1 dispel aura_of_majesty      # take it off again
```

`cast` is the one byte the game keeps for a global: byte *n* of the caster's 24 global bytes at `+0x482` of the wizard record set to 1 (Aura of Majesty is byte 3, Just Cause 18; checked in the game, 2026-10-12). The wizard it is poked into is the **caster**.
It skips the spell's cost, the spell book and every check the game makes when you cast, and a spell is normally cast at End Turn, so this makes it active *now*.
The name is the element name of the `globals` field, so `globals.aura_of_majesty`, `aura_of_majesty` and a unique prefix (`aura`) all work (STORY-002).
Like every `poke`: a compare-and-swap, `--dry-run`, an undo entry; `cast` on one already active says so and writes nothing.

## What we do not know yet (the reason this is a research story as much as a coding one)

STORY-051 in Mirror asked the same thing for saves and never got its edit test. A byte set by hand is not a cast spell. For each of the 24 globals, check in the real game, with the live write (no save needed, so no End Turn to get there):

1. Does the **effect start**, or is the byte only a record of it? (Aura of Majesty: do relations rise at the next End Turn?)
2. Is the **upkeep charged** each turn (the Magic screen's mana figure), or does the game forget it? Does an unaffordable upkeep **dispel** it, as casting would?
3. Does it appear in the **Magic screen's "Overland Enchantments" box**, and on the right wizard?
4. Does anything else need writing? Some globals look bigger than a flag (Time Stop changes how turns run, Armageddon and Meteor Storm have effects over time, Great Wasting and Eternal Night act on the map). A global that needs a second write is **not offered** by `cast` until it is understood.
5. Can **two wizards hold the same global**? The game may treat the second as a mistake.

Each global gets a confidence mark in the field table: `checked` once it has been seen to work, otherwise `guess`, and a guess is refused without `--force` (AGENTS.md section 4). Start with the cheap, well-understood ones (Nature Awareness, Aura of Majesty, Just Cause).

## Definition of done

`cast` and `dispel` work for at least the three globals above on the real game, showing in the Magic screen's box, with the effect and the upkeep recorded in `docs/reference/` (and shared with Mirror's STORY-051, which then needs no separate test). Tests with the fake DOSBox for the write, the refusals and the undo.
