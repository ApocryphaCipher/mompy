# STORY-022: Spike: where does a unit's weapon quality (magic, mithril, adamantine) live?

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** done (2026-10-13): answered from the notes and seen on the unit screen. A **spike**.
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 (units made by `create` should have "max XP and adamantine weapons")

## The question

[STORY-015](STORY-015-cast-unit.md)'s `create` makes units at maximum experience (grounded). Adamantine weapons are not: no document of ours says which byte of the unit record, if any, holds the weapon quality. *Guess:* the game derives it from the unit's home city's mineral and the wizard's Alchemy retort at the moment a unit fights, and stores nothing in the unit.

## How

1. Compare a unit built in a city with adamantine ore nearby (or a wizard with Alchemy, for magic weapons) with the same unit type from a city without: `peek`-style dump of both 32-byte records, field by field.
2. Cast Enchant Weapon-style spells are enchantments (`+24..+27`), not this.
3. If a byte differs, write it into a `create`d unit and check the unit's screen (it lists the weapon). If nothing differs, weapon quality is derived and cannot be set in the unit; the alternative is the city's mineral special in the map data.

## Definition of done

A page in `docs/reference/` saying where weapon quality is decided, from two independent sources (an AGENTS.md §6 rule). Then `create` can set it, or the story says it cannot.

## Answer from what we already had (2026-10-13)

Kevin: "you are sitting on a 25-year MoM database". He was right; the evidence vault had it.

- **Source 1** (the 2001 save-game anatomy, `MoMSaveGame_Item.htm` in the vault, by Zastai): the unit byte at its `0x1B` holds "Weapon type & Mutation Flags": **the lower 2 bits are the weapon type** (0 normal, 1 magical, 2 mithril, 3 adamantium), the upper 6 bits are mutation flags. That document's unit offsets are ours plus 4 (its level `0x10`, experience `0x12`, damage `0x15` are our `+12`, `+14`, `+17`), so its `0x1B` is our **`+23`**, the byte Mirror already calls `mutations` (8 demon wings, 32 undead).
- **Source 2** (ReMoM's `s_UNIT` in `MOM_DAT.h`, same vault): the same record at `+23` is `mutations` and ReMoM tests `mutations & UM_UNDEAD` / `& 0x20`, the same bit as Mirror's 32. ReMoM's `e_WEAPON_QUALITY` is `wq_Normal, wq_Magic, wq_Mithril, wq_Adamantium` (0 to 3), the same four values. ReMoM's header does not say which byte carries it, so the byte is Source 1's claim; the values are both sources'.
- **Live data:** the 160 units in Kevin's game hold 0 or 1 in `+23` (the 1s are Jafar's and Freya's: magic weapons), never another value.
- Also from ReMoM: `+28` is `Rd_Constr_Left` (our 0xFF means none), `+22` is `Sight_Range`, `+18` `Draw_Priority`, `+11` `Status`, `+16` `Move_Failed`.

`create` now writes 3 in the low bits. **Checked on the real game (Kevin, 2026-10-13):** a Dark Elf Cavalry made by `poke city blackstone create 60` shows adamantium weapons and Elite with 120 experience on its unit screen, and walks. That is source 1 plus a visual check, which meets AGENTS.md section 6.
