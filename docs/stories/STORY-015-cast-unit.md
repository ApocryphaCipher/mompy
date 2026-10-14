# STORY-015: `mompy poke wizard N cast unit.<name>`: summon any unit, no fuss (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-13), not yet pushed; checked on a real game. **Priority: nice to have.** Depends on [STORY-003](STORY-003-poke.md) (`poke`) and on the spike [STORY-016](STORY-016-spike-summon-a-unit.md), which finds out what the game writes when a unit appears.
**Size:** medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

```
mompy poke wizard 1 cast unit.war_bears              # one War Bears, owned by wizard 1, at their summoning city
mompy poke wizard 1 cast unit.war_bears --count 3
mompy poke wizard 1 cast unit.swordsmen --at blackstone
```

Like [`cast <global>`](STORY-012-cast.md): no mana, no spell book, none of the game's checks. Any unit type in the game, regardless of books: a fantastic creature, a normal racial unit, a boat or a catapult.
The unit is created **in the units table** (`0xB734` in a save, `0x7E060` in the research setup's memory; 1009 records of 32 bytes) with the wizard as owner.

**Where:** by default **the summoning circle's coordinates** (Kevin: the position is easy, set it there) — the wizard's summoning city (the Magic screen's "Summon To", which is the summoning circle in the wizard record: `peek wizard 1 summoning_circle`); `--at <city name>` (STORY-011's lookup) or `--at x,y,plane`.

## What it has to do (from the units table layout in Mirror's `docs/reference/kazzmir-save-layouts.md`)

A record is 32 bytes: `+0..+2` x, y, plane; `+3` owner; `+4` max moves; `+5` unit type; `+6` hero slot; `+7` finished; `+8` moves left; `+9,+10` destination; `+11` status; `+12` level; `+14` experience; `+17` damage; `+18` draw priority;
`+21` sight range; `+23` mutations; `+24..+27` enchantments. So a summon needs: a **free slot** (a dead record has owner `0xFF`), the **live count** updated, and every field filled in sensibly for the type
(max moves and sight range come from the game's own per-type data, which `gama`'s layout puts in memory at the data segment + `0x19C`, 256 records of 36 bytes: *unchecked*). What else the game writes, and what it needs to *show* the unit
(a unit moved by writing its position vanished from the map until End Turn, 2026-09-23), is the spike's question.

**No race to set** (Kevin's question, 2026-10-13): a unit record has no race field. The race belongs to the unit *type* (`+5`: type 40 is Barbarian Swordsmen, type 140 Orc Bowmen; the summoned creatures are "fantastic" and have none). The unit's banner colour follows its **owner** (`+3`), which is the wizard.
So a summon is a type, an owner and a place. Race only enters the *name*: several races share names ("Swordsmen", "Bowmen", "Spearmen"), so `unit.swordsmen` is ambiguous and the lookup lists the matches (`barbarian_swordsmen`, `orc_swordsmen`, ...) instead of guessing, while `unit.war_bears` is unique.

## Refusals (the game's own rules, so a bad summon cannot corrupt the map)

- A tile holds **at most nine** units; one tile belongs to **one owner** (Mirror's `edit_units` checks the same: another owner's units or city on the tile refuses).
  **A full stack:** Kevin's expectation is that the game pops the unit next to the city when the summoning circle's tile is full. That is what the game's *summon routine* does when it runs; a record written by hand does not run it. [STORY-016](STORY-016-spike-summon-a-unit.md) tests what the game does with a tenth unit written onto a full tile (moves it next door, ignores it, breaks). Until that is known `cast` does not rely on it: it places the unit itself on the nearest free neighbouring tile (same plane, no foreign units or cities on it) and says where it went. If the game turns out to do it, that step is dropped.
- **Heroes** (types 0 to 34) are not summoned this way: a hero is also an entry in the wizard's hero list with item slots, which is [EPIC-010](https://github.com/ApocryphaCipher/Mirror/blob/main/docs/epics/EPIC-010-heroes.md)'s job in Mirror and a later story here.
- No free slot: say so.
- A land unit placed on ocean (or a boat on land) is allowed but warned about.

## Names

`unit.war_bears` needs the type's name. Mirror carries the names of the 198 types (`lib/mirror/save_file/unit_types.ex`, with the race put in front of names several races share, e.g. "Barbarian Spearmen"). Where mompy gets them is open and is Kevin's call, as for spells:
read them from the game's own memory if the type table holds them (the spike checks), from the player's files at run time, or ship the list. The same element-name matching as `globals.<name>` applies (underscores, case, unique prefix).

## Definition of done

`cast unit.war_bears` on the real game gives a War Bears stack of the wizard's colour at the summoning city that shows on the map (after End Turn if that is what the game needs), can be moved, and survives a turn and a save and load; refusals tested with the fake DOSBox.
Mirror's editor could learn to **add** units from the same result (it can move and edit units today, not create them): note it in Mirror's backlog when this lands.

## Outcome

Built as `mompy/summon.py` and `poke wizard N cast unit.NAME [--count N] [--at CITY|x,y,plane]`, with `tests/test_summon.py`.

- Names come from the running game's unit type table (STORY-016), so nothing is shipped. A name shared by races lists the type numbers; `unit.58` works. Heroes (types 0 to 34) are refused.
- The record is built from scratch: position, owner, max moves and sight from the type's record, level 0 for summoned creatures (type 154 and up) and level 1 for the rest. *Guess:* the draw-priority byte (`+18`); the game rewrote it on its own (0x0A to 0 and 5 in the records read back).
- Free slots: dead records first (plane and owner both 0xFF), then appended after the live count. The count is written last; if it fails the records are put back.
- A full tile (nine), another owner's units or another owner's city sends the unit to the first free neighbour; no room anywhere is refused.
- Real game (fork 0.84.0-alpha, Kevin's MAXIMUS save, 2026-10-13): War Bears (by a hand-written spike, then through `cast`), Sprites and a Dark Elf Cavalry at Blackstone: all showed in the city screen, all walked. The Cavalry shows as a Regular with 0 experience, as written. War Bears survived an End Turn.
- Also fixed: `doctor` and every command called the unit table broken while a unit that died this turn was still in it (marked 0xFF); test added that fails without the fix.
- Not done: a boat or land-water check (a land unit on the sea is allowed, unwarned), a save and load with a cast unit, a tenth unit written onto a full tile by hand (STORY-016's question; `cast` avoids it).
