# STORY-022: Spike: where does a unit's weapon quality (magic, mithril, adamantine) live?

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** A **spike**.
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 (units made by `create` should have "max XP and adamantine weapons")

## The question

[STORY-015](STORY-015-cast-unit.md)'s `create` makes units at maximum experience (grounded). Adamantine weapons are not: no document of ours says which byte of the unit record, if any, holds the weapon quality. *Guess:* the game derives it from the unit's home city's mineral and the wizard's Alchemy retort at the moment a unit fights, and stores nothing in the unit.

## How

1. Compare a unit built in a city with adamantine ore nearby (or a wizard with Alchemy, for magic weapons) with the same unit type from a city without: `peek`-style dump of both 32-byte records, field by field.
2. Cast Enchant Weapon-style spells are enchantments (`+24..+27`), not this.
3. If a byte differs, write it into a `create`d unit and check the unit's screen (it lists the weapon). If nothing differs, weapon quality is derived and cannot be set in the unit; the alternative is the city's mineral special in the map data.

## Definition of done

A page in `docs/reference/` saying where weapon quality is decided, from two independent sources (an AGENTS.md §6 rule). Then `create` can set it, or the story says it cannot.
