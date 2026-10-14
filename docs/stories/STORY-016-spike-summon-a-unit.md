# STORY-016: Spike: what does the game write when a unit is summoned?

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** A **spike**.
**Size:** small (one play session)
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 (the idea behind STORY-015)

## The question

[STORY-015](STORY-015-cast-unit.md) creates a unit by writing a record. Which bytes does the game itself write when it summons one, and what makes the new unit appear? Do not guess a template: **watch the game do it.**

## How

Needs [STORY-004](STORY-004-snapshot-and-diff.md) (`snapshot` and `diff`) and the memory API; the research fork's watches can help.

1. In the real game (the advanced SAVE2, a wizard with a summoning spell: War Bears, Sprites...), take a `snapshot` of the units table, the live unit count, the wizard record and the city table. Cast the spell and let it complete (End Turn); take another. `diff` them: the **new unit's 32 bytes**, the count, and **anything else** that changed (a city's garrison count, mana, casting state, a per-tile stack list).
2. Do it again with a **normal** unit built in a city, and a **fantastic** one (a different realm) and a **boat**, to see which fields differ by kind.
3. Where do **max moves** and **sight range** come from? Compare the new record with the per-type table in memory (data segment + `0x19C`, 256 × 36 bytes, per `gama`'s layout: names, costs and speeds may be there).
4. **Write the record by hand** into a free slot (owner `0xFF` marks a free one) with the learnt template and update whatever else the diff showed. Does the unit appear at once, after End Turn, or not at all? Does it move, fight, cost upkeep, survive a save and load?
5. What marks a slot **free**, and does the game reuse the lowest free slot or append?
6. **A full stack.** In play, summon (or finish building) a unit in a city whose tile already holds nine of your units and watch where it appears: next to the city? Which neighbour, and by what rule (first free in some order, nearest)? Then write a **tenth** record onto a full tile **by hand**: does the game move it, ignore it, show a stack of ten, or break at End Turn? (Kevin's expectation: the game pops it next door. That is the summon routine's job; the question is whether the game also tidies a tile that is over-full some other way.) The answer decides whether `cast` must pick a free neighbouring tile itself.

## Definition of done

A page in `docs/reference/`: the unit record a summon produces, per kind; every other byte the game touches; what a hand-made record needs to show and work; and the free-slot rule. STORY-015 is then written from it. (The same page tells Mirror how to add units to its editor.)

## Findings so far (2026-10-13, Kevin's MAXIMUS game, fork 0.84.0-alpha)

The record format and a first hand-written summon, without `snapshot`/`diff` (watched, not diffed):

- **The unit type table is in memory** (`DGROUP + 0x19C`, 36 bytes a record, 198 types; DGROUP is the wizard table's address minus `0x9ECA`, at 0x289F0 in this build). Each record starts with a pointer (u16, from DGROUP) to the type's **name**, so names need no shipped data: they are read from the running game. Checked by reading War Bears (179), Sprites (180), Guardian Spirit (176), Fire Elemental (158), Cavalry (60).
- **Unit record fields that come from the type table** (compared over all 160 live units): max moves `+4` = type `+9` (159 of 160; the odd one out likely carries a speed enchantment); `+22` = type `+19` (160 of 160, value 1 in every unit seen; *guess:* sight range). The type table's `+10` reads like the cost (Cavalry 100).
- **Units built by cities** (Kevin's four, owner 0): `x y plane owner maxmoves type 0xFF(hero slot) 1 maxmoves(left) 0 0 1 level 0 exp ...`. `+7` and `+11` were 1 on every wizard-owned unit and 0 on the neutral ones (*guess:* active / visible).
- **A hand-written War Bears** (type 179), cloned from a Guardian Spirit record with position, type, `+4`/`+8` (type `+9`) and `+22` (type `+19`) filled in, written at slot 160 (the first slot after the live count, which held stale bytes of an old record, so the "free" slot is **not** zeroed), then the live count `160 -> 161`: **it showed in the Blackstone city screen at once (no End Turn), then on the map, and walked** (Kevin, 2026-10-13). Moving it wrote `+9,+10` (the destination), `+11` = 3 (a unit on the way), `+8` moves left to 0 and changed `+18` from 10 to 7.
- Still open: End Turn and a save and load with the hand-made unit; a boat and a normal racial unit (`+18`, `+12`, level and upkeep); a full stack (nine units) on the tile; the dead-slot rule.
