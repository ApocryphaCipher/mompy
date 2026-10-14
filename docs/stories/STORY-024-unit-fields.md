# STORY-024: `peek unit N` and `poke unit N FIELD VALUE`: a unit block in the field table (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-14), checked on a real game
**Size:** medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-14 ("units first, then nodes and lairs"); the backlog's `poke unit 12 level 5`.

## Outcome

A `unit` block (32-byte records, 1009 of them, numbered **from 0** the way the game does and the way `pew` and `where pointer` print them: `War Bears #160`) with the same safety as every `poke`: compare-and-swap, a range per field, `--dry-run`, `undo`, a guess field needs `--force`, and a dead unit (plane and owner 255) is refused.

```
mompy peek unit 160                    # the whole record in words, with the unit's type name and owner
mompy peek unit 160 experience
mompy poke unit 160 level 3
mompy poke unit 160 moves_left 127
```

| Field | Notes |
| --- | --- |
| `x`, `y`, `plane` | editable, **guess** (`--force`): the map draws from a picture built earlier, so a moved unit seems to vanish until the map view is nudged |
| `owner` | read-only (a unit also belongs to a stack and a banner); shown as the wizard's name, neutral, or dead |
| `max_moves` | editable, guess |
| `type` | read-only, shown with its name from the game's own unit type table (`Halberdiers (59)`) |
| `hero_slot`, `sight`, `status` | read-only |
| `moves_left` | editable, **checked** (STORY-021): a signed byte of half-moves, 127 is the top |
| `level` | editable, **checked**: shown as written, then the game works it out from experience at End Turn (set `experience` too) |
| `experience` | editable, **checked** (`create` writes 120 and the unit screen showed Elite) |
| `damage` | editable, guess |
| `mutations` | editable, guess; shown as words: weapon grade (low two bits, seen on a unit screen: adamantium) and flags (undead...) |
| `enchantments` | read-only, shown as names (Flight...); `unit cast mass.NAME` changes them for a stack |

Layout sources: ReMoM's `s_UNIT` and the 2001 save-game page (both in the Evi vault), and the real game on 2026-10-13/14. Added a `u32` type to the field table for the enchantments.
`where pointer` and `pew` now print a unit's number (`Cavalry #158`) so it can be handed to `peek unit`.

Tests: `tests/test_unit_fields.py` (fake DOSBox).
Not done: `peek unit` by place (`unit --at blackstone` listing); owner, type and position are not checked on a real game for being safe to write.
