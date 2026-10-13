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
The name is the element name of the `globals` field (no spaces needed), so `globals.aura_of_majesty`, `aura_of_majesty` and a unique prefix (`aura`) all work (STORY-002).
Like every `poke`: a compare-and-swap, `--dry-run`, an undo entry; `cast` on one already active says so and writes nothing.

## Decisions (Kevin, 2026-10-13)

1. **No checking before writing.** `cast` writes the byte and lets the game do its sums, now or at End Turn. No "verify the effect first" gate.
2. **Upkeep is the game's business.** It will be adjusted at End Turn; if the wizard cannot afford it the game may dispel it. That is fine and is not mompy's concern. For a spell that has a power-up level, `cast` uses the **maximum** power (see the spike below for how a power level is stored, if it is).
3. **It shows in the Magic screen's "Overland Enchantments" box**, on the wizard it was cast on.
4. **Whether a global needs more than the flag is open**: flag it as a test and see. That is a spike ([STORY-013](STORY-013-spike-globals-by-hand.md)), not a reason to hold `cast` back.
5. **Two wizards may hold the same global.** The exceptions, to be investigated in a spike ([STORY-014](STORY-014-spike-wonky-globals.md)): Spell of Mastery, Planar Seal and "some other wonky spell mechanics".

So `cast` ships for every global in the 24-byte list. The **questionable ones** (the list below, a proposal for STORY-014 to confirm) need `--force` until the spike has looked at them; everything else is a plain `cast`:
Time Stop, Planar Seal, Armageddon, Meteor Storm, Great Wasting. *(Spell of Mastery is not one of the 24: its research is tracked in the wizard record's `mastery_research` field (`+0x22`, unchecked), so `cast` cannot do it; STORY-014 looks at it.)*

## Definition of done

`cast` and `dispel` write the right byte for any global, refuse the questionable ones without `--force`, and `cast` on one already active writes nothing. Seen once on the real game: Aura of Majesty cast on Jafar appears in the Magic screen's box and relations rise at the next End Turn (the game's own sums). Tests with the fake DOSBox for the write, the refusals, `--force` and the undo.
