# STORY-014: Spike: the wonky globals (Spell of Mastery, Planar Seal, ...)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** A **spike**.
**Size:** small to medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 ("except maybe Spell of Mastery, Planar Seal, and some other wonky spell mechanics ... spike to investigate questionable spells")

## The question

Most globals are a flag on the caster. Some are not, or are limited to one holder, or end the game:

- **Spell of Mastery** is not one of the 24 global bytes. Its progress is probably the wizard record's `mastery_research` (`+0x22`, listed in the wizard-record notes as unchecked). Casting it wins the game; what does a hand-set value do (a win screen? nothing)? Careful: test on a throwaway game.
- **Planar Seal** blocks travel between the planes for everyone; can two wizards hold it, and what happens to a unit that is mid-travel?
- **Time Stop** changes how turns run (only the caster moves); a flag set mid-turn may leave the turn order in a state nobody planned.
- **Armageddon** and **Meteor Storm** act over time and on the map; they may keep a countdown or a target elsewhere than the 24 bytes.
- **Great Wasting** and **Eternal Night** change the map or the light on both planes.
- Any other global whose description says "only one wizard can have it" or "ends when...". Read `spellbook.pdf` (in the game folder) for each of the 24 and list what looks special.

## How

Read the spell book's text for the 24 and make a list; for each questionable one, a game on the advanced SAVE2 and `cast`: a second wizard casting the same one, one End Turn, a `snapshot` diff of the whole wizard block *and* the other tables (cities, units, nodes, terrain) to find what else changed, and a note of what the screen showed.
Write what is found into `docs/reference/`; decide for each: plain `cast`, `cast --force`, or not offered. The proposal in STORY-012 (Time Stop, Planar Seal, Armageddon, Meteor Storm, Great Wasting) is the starting list.

## Definition of done

A short page per questionable global (or one table): what a hand-set flag does, whether two holders work, and the decision; STORY-012's `--force` list and the field table's marks updated.
