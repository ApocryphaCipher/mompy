# STORY-023: `cast mass.<spell>`: a unit enchantment on a whole stack (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-13), checked on a real game. **Priority: nice to have.** Needs [STORY-010](STORY-010-where.md) (places, including `pointer`: built) and the way `pew` and `unit mercury` pick a stack.
**Size:** small to medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 ("add 'mass' spells to unit stacks: `... hellgate cast mass.flight` and maybe a mouse version doing the same")

## What to do

Put a unit enchantment on **every unit of a stack** at once, with no mana, no book and none of the game's checks, like [`cast`](STORY-012-cast.md) for global enchantments and [`cast unit`](STORY-015-cast-unit.md) for creatures:

```
mompy poke city hellgate cast mass.flight          # every unit on Hellgate's tile
mompy cast mass.flight --at pointer                # the stack under the mouse
mompy cast mass.flight --at 50,18,myrror           # any tile
mompy dispel mass.flight --at hellgate             # and take it off again
```

The exact spelling of the command is open (Kevin wrote the first form). The place is any of the places `pew` takes (a city's name, `x,y,plane`, `pointer`); heroes are included here (this writes only the unit's own record, there is no hero-list problem).

## What is known

- A unit's enchantments are a **u32 bitmask at `+24..+27`** of its record ([unit-movement.md](https://github.com/ApocryphaCipher/Mirror/blob/main/docs/reference/unit-movement.md), ReMoM's `UE_FLAGS` in the evidence vault): Water Walking `0x100`, Iron Skin `0x1000`, Endurance `0x2000`, Spell Lock `0x4000`, Invisibility `0x8000`, Wind Walking `0x10000`, Flight `0x20000`, Resist Magic and more in the high word. *To do:* write out the full list from the sources, and check each against the unit screen.
- The record keeps **no caster**: the owner pays. ReMoM's `Unit_Mana_Upkeep` charges mana per enchantment each turn, so a stack with a handful of enchantments costs the wizard mana at End Turn.
- Writing the bit is one compare-and-swap per unit (`+24..+27`, four bytes), one `undo` for the stack, like `unit mercury`.

## To find out (a small spike first)

- Does a **hand-set bit** show on the unit's screen and do what the spell does (Flight: the unit flies, its icon changes)? Try Flight on a Cavalry. *Guess:* yes; upkeep is charged at End Turn.
- What happens when the owner **cannot pay** the upkeep at End Turn (the game dispels something? the same open question as for global enchantments, [STORY-013](STORY-013-spike-globals-by-hand.md))?
- Which enchantments are **not** plain bits: ones that carry a value, or that other tables must know about (a *mass* enchantment on a city?). Keep to unit bits first.
- The map draws from a stack picture it built earlier ([ram-layout.md](../reference/ram-layout.md)): a flight icon may need the map view nudged to appear.

## Definition of done

On the real game: `cast mass.flight` on a stack (by city name, and by `pointer`) makes every unit fly, `dispel` and `undo` both take it off, and one End Turn shows the mana upkeep (or what the game does when it cannot be paid), written down. Tests with the fake DOSBox for the bit, the stack, the heroes and the undo.

## Outcome

Built as `mompy/mass.py` with `tests/test_mass.py`:

```
mompy poke city hellgate cast mass.flight        mompy poke city hellgate dispel mass.flight
mompy unit cast mass.flight --at pointer         mompy unit dispel mass.flight --at x,y,plane|city
```

- **All 32 unit enchantments**, by name (case, `_`, unique prefix, `mass.` optional; an ambiguous prefix is listed): ReMoM's `UE_FLAGS_L` (low word, +24..+25) and `UE_FLAGS_H` (high word, +26..+27) read as one u32. Four bits were already known from kazzmir's remake via Mirror's unit-movement.md (Water Walking 0x100, Invisibility 0x8000, Wind Walking 0x10000, Flight 0x20000) and agree with ReMoM.
- Every unit on the tile (heroes and any owner included): one compare-and-swap per unit, all or none, one `undo` for the stack, `--dry-run`, already-done writes nothing.
- **Real game (fork 0.84.0-alpha, 2026-10-13):** Flight on a stack of four Nagas (which walk): **it showed on all four units' screens and they flew** (Kevin). After one End Turn the bit was still set on all four. Dispel: the bit cleared on all four.
- **Upkeep: not measured.** Mana fell from 29959 to 29942 over that turn, but the Nagas are summoned creatures that cost mana on their own, so the 17 is *not* Flight's cost; the cost of Flight alone was not isolated (compare a turn with and without it on the same units).
- **What the game does when the mana runs out (found 2026-10-13, answers the question for unit upkeep in [STORY-013](STORY-013-spike-globals-by-hand.md)):** mana set to 0 with Flight on the Nagas, one End Turn: the game showed **"UNITS DISBANDED"**: the four Nagas, four Guardian Spirits and a Sky Drake, each "dispelled: lack of mana", and **"UNIT SPELLS DISSIPATED"** (a list of unit types, Griffins, Spearmen, Swordsmen, Halberdiers...). Afterwards the wizard's 26 remaining units all had enchantments 0 (Flight gone) and mana was still 0. So unpaid upkeep costs a wizard his **summoned creatures** (ordinary units survived) and **every unit enchantment**, not just the new one. *Not tested:* a partial shortfall (does it disband only enough to balance?) and the same for global enchantments.
- Not tested: the other 31 enchantments on screen (names and bits are from the two sources, only Flight was looked at).
