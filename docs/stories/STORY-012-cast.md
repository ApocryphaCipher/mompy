# STORY-012: `mompy poke wizard N cast <global>`: put a global enchantment straight on a wizard (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-13): `cast` and `dispel` work on the real game (the Magic screen lists the enchantment). One End Turn seen: the game acts on it. **Priority: nice to have.**
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

## Outcome (2026-10-13)

Built: `mompy poke wizard N cast <global>` and `dispel <global>` (`mompy/cast.py`), on top of `poke`: a compare-and-swap on byte *n* of the wizard's 24 globals, logged for `undo`, `--dry-run` writes nothing. The name goes through the same element lookup as `peek` (`aura_of_majesty`, `natures-wrath`, `globals.aura_of_majesty`, a unique prefix; an ambiguous one such as `nature` lists its matches).
Already cast (or not cast): nothing written, nothing logged. Any wizard can be the caster, and two wizards may hold the same global (Kevin's answer 5; tested). The **five questionable ones** (Time Stop, Planar Seal, Armageddon, Meteor Storm, Great Wasting) need `--force` to cast; `dispel` never needs it.

- **Real game, 2026-10-13** (the fork, MAXIMUS loaded): `poke wizard 1 cast aura_of_majesty` printed `Aura of Majesty cast on wizard 1 (Jafar)`, mana stayed 29999 (nothing paid), and **the Magic screen's "Overland Enchantments" box listed Aura of Majesty** (Kevin looked, with a screenshot). *That answers question 3 of the ticket* (it shows in the box) *and the first half of question 1 for this spell*: the game accepts a hand-set byte without any casting.
- **One End Turn later (Kevin pressed it):** Aura of Majesty was **still active** and the relations rose: Jafar's view of Freya 0 to **2**, of Sharee -20 to **-16**, of Tauron -20 to **-16**; the wizards' views of Jafar moved the same amounts (kept on both sides); Sss'ra (not met) and the neutral player did not move. Mana went 29999 to **29990** (a normal turn on this save costs about 1): *probably* the upkeep (the spell book lists 5 a turn; retorts change it), not isolated.
  **A difference from a real cast:** when Kevin cast it through the game (2026-10-12) the first turn took *every* relation to 20, then +2 a turn; the hand-set flag gave +2 and +4 and no jump. *Guess:* the jump to 20 is the game's cast routine, the per-turn rise is the flag.
- **Not yet seen:** whether the game dispels it when the upkeep cannot be paid, and the same questions for the other 23 globals: the spike [STORY-013](STORY-013-spike-globals-by-hand.md). Also open: what a *power level* in the byte would mean (only 0 and 1 have been seen) and the questionable five ([STORY-014](STORY-014-spike-wonky-globals.md)).
- 109 tests (17 new), warnings as errors, with the fake DOSBox: the write changes only the one byte, every spelling of a name, ambiguous and unknown names, the caster is whichever wizard you name, two holders, already cast, dry run, the five need `--force` and the other 19 do not, `dispel` of a questionable one needs nothing, `undo`, writes disabled, the race, and the command line.

## Update (2026-10-14)

The `--force` list (Time Stop, Planar Seal, Armageddon, Meteor Storm, Great Wasting) is gone after the spike in [STORY-014](STORY-014-spike-wonky-globals.md): the other four went through a real End Turn without trouble and cast like any other; **Time Stop is refused** (even with `--force`), since set by hand it only shows and costs mana and the real spell needs the game's own scripting.
