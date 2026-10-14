# STORY-023: `cast mass.<spell>`: a unit enchantment on a whole stack (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** Needs [STORY-010](STORY-010-where.md) (places, including `pointer`: built) and the way `pew` and `unit mercury` pick a stack.
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
