# STORY-017: `mompy banish wizard N`: banish a wizard (and, if you mean it, finish them) (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** Depends on [STORY-003](STORY-003-poke.md) (`poke`). Contains a spike as its first step.
**Size:** small for the flag, medium for the rest
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 (first as a joke, `mompy pew wizard 3`, "just pew and dead"; then settled: **`mompy banish wizard 3`**. `pew` became a different command, [STORY-018](STORY-018-pew.md): kill the units under the mouse.)

## What to do

```
mompy banish wizard 3           # wizard 3 (Sss'ra) is banished.
mompy banish wizard 3 --dead    # and gone: no cities, no units, no heroes
mompy unbanish wizard 3         # banishment lifted
```

**`banish`** clears the **active** byte of the wizard's fortress record (`0x65F8 + 4 × wizard + 3` in a save; found by the scan from the wizard table in memory). Checked in the game, 2026-10-13: with that one byte at 0 the Magic screen draws the wizard as a **cracked stone frame**, with 1 it does not (both directions, one byte each).

## Banished is not dead (the manual, `MMOMS.TXT` section 5.3 "Losing Your Fortress")

When a wizard loses his fortress he does not leave the game: he **starts casting "Spell of Return"** (spell 214, Arcane), "whether you had any cities left or not", and only if he has **no cities** the following turn is he resigned. So the fortress flag is most likely **banished**,
which Mirror's wizard page now shows as **Banished** (Mirror PR 119 renamed it from "Defeated"). It matches our two observations: a living Freya with two cities got the cracked frame when the flag was cleared, and the Freya in `JAFAR-PLAYED` had the flag cleared and no cities, units or heroes at all (that one is *eliminated*).

So plain `banish` is the polite version: the wizard is banished, and the game's AI will try to cast Spell of Return and may come back. **`--dead`** is "eliminated": banish **and** remove everything he owns, the way `JAFAR-PLAYED`'s Freya was left.

## What `--dead` has to do (the spike, first)

From `JAFAR-PLAYED.GAM`'s Freya (eliminated by the game itself): no cities (where did hers go: to the conqueror, or neutral raiders?), no units (owner `0xFF` marks a dead record), hero slots 255, gold 0, and the conqueror's `+0x354` ("defeated wizards", a u16, read as 2 there; kazzmir's `DefeatedWizards`) counted her.
On a throwaway game, `banish --dead` a rival and watch **one End Turn**: do the AI's turns skip him, does the game notice the empty wizard, does the conqueror's count matter, does anything crash. The remaining questions: who gets the cities (set them **neutral**, owner 5, as Mirror's city editor does); what about enchantments he cast (global enchantments of a dead wizard: clear them); a wizard who is the *player* (refuse: `banish wizard 1` is refused without `--force`, since it ends your own game).

## Details

- Output is one line: `wizard 3 (Sss'ra) is banished.` (and `wizard 3 (Sss'ra) is dead.` for `--dead`). Already banished: say so, write nothing.
- A compare-and-swap like every `poke`, `--dry-run`, an undo entry. `unbanish` writes 1 back; for an eliminated wizard it can only lift the banishment (his cities are not coming back: the undo log can restore them within a session).
- Mirror: the wizard page could offer the same as a button (banish, lift) once the End Turn behaviour is known; note it in Mirror's backlog.

## Definition of done

`banish` on a rival in the real game shows the cracked frame at once; one End Turn recorded (does the AI cast Spell of Return? does it come back?). `--dead` per the spike. Tests with the fake DOSBox: the flag, the refusals, the undo.
