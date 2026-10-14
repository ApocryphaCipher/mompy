# STORY-027: heal, weapons and experience for a whole stack (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-14). **Priority: nice to have.** All three are small: the unit record is known ([STORY-024](STORY-024-unit-fields.md)) and the place selector exists (`pointer`, a city's name, `x,y,plane`, as in `pew`, `unit mercury` and mass spells).
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-14 ("a heal all units under the mouse command", "set weapon quality on a unit stack, only the non fantastic creatures", "another command to set the experience on a unit stack to maximum")

## What to do

Three more `unit` actions, each on every unit on a tile, one compare-and-swap per unit, one `undo` for the stack, `--dry-run`, dead units skipped, a line saying how many were changed and how many were left alone and why. The names are open (Kevin has opinions about names):

```
mompy unit heal --at pointer                     # damage 0 on every unit on the tile
mompy unit weapons adamantium --at blackstone    # normal | magic | mithril | adamantium; ordinary units only
mompy unit experience max --at pointer           # the top experience (and level) a unit can have
```

- **heal:** the unit's `damage` byte (`+17`) to 0. ReMoM's note: Nature's Cures "sets this and only this to 0". *To check live:* a damaged unit shows full hearts at once (the map or unit screen may need a nudge, like every hand edit).
- **weapons:** the low two bits of `mutations` (`+23`), leaving the mutation flags (undead, demon wings...) alone. Only **ordinary units** (types 35 to 153): summoned creatures (154 and up) are skipped, as Kevin said, because they carry no weapon grade. *To decide:* **heroes** (types 0 to 34): skipped until someone looks at what a hero's weapons show (his items matter); boats and catapults (35 to 38) are included unless that looks wrong on screen.
- **experience max:** `experience` and `level` together, as `create` does (120 experience and level 3 for an ordinary unit: the cap the game applies at End Turn). Summoned creatures do not level: skipped. *To decide:* **heroes** reach level 8 and their thresholds are different (an unfinished question in the heroes epic): skipped until known.

## Notes

- `create` already makes a unit at maximum experience with adamantium weapons, and `mass.X` enchants a stack; these are the same idea for units that already exist.
- All three are plain `poke`s underneath (`damage`, `mutations`, `experience`, `level`), so each is checked against the field table's ranges.

## Definition of done

On the real game: a hurt stack heals; a stack of Spearmen becomes adamantine (the unit screen says so) while a Sprites in the same stack is untouched; a stack reaches Elite 120; `undo` puts each back. Tests with the fake DOSBox for the filter (creatures, heroes), the mutation-flag-preserving write, and the undo.
