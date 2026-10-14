# STORY-027: heal, weapons and experience for a whole stack (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-14); heal and the creature skips seen live, weapons and experience on ordinary units and heroes not yet. **Priority: nice to have.** All three are small: the unit record is known ([STORY-024](STORY-024-unit-fields.md)) and the place selector exists (`pointer`, a city's name, `x,y,plane`, as in `pew`, `unit mercury` and mass spells).
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

## Outcome

```
mompy unit heal --at pointer [--skip-heroes]
mompy unit weapons adamantium --at blackstone          # normal | magic | mithril | adamantium (or 0 to 3)
mompy unit experience max --at 51,22,myrror [--skip-heroes]
```

Built as `mompy/stack.py` with `tests/test_stack.py`. Kevin's rules: **heroes are healed**, **maximum experience includes heroes** ("they might have a higher XP table"), **weapons leave heroes alone**, and `--skip-heroes` leaves heroes out of any of them. Summoned creatures are skipped for weapons and experience (they carry no weapon grade and do not level).

- **heal:** damage (`+17`) to 0 for everyone on the tile, heroes and creatures included.
- **weapons:** the low two bits of `mutations` (`+23`); the flags (undead...) are kept; ordinary units only.
- **experience max:** `level` and `experience` written together (one 4-byte compare-and-swap). The numbers come from **the game's own experience table**, which is in memory (`TBL_Experience`, data segment `+0x1D74`, nine values: **0, 20, 60, 120, 200, 300, 450, 600, 1000** on Kevin's game). ReMoM's code (in the Evi vault) caps an ordinary unit at the Elite entry (120, level 3) and a hero at the last entry (1000, level 8, Demi-God): so that is what "max" writes for each. The table is checked (starts at 0, strictly rising) before anything is written.
- Each prints how many were changed and why the others were not (`heroes left alone: 1, summoned creatures carry no weapons: 1, already so: 2`); one `undo` for the stack; `--dry-run`.
- **Real game (2026-10-14, a stack of four Sky Drakes under the pointer):** `heal` reported all four unhurt; one was wounded with `poke unit 38 damage 6 --force` and `unit heal --at pointer` put it back to 0 (the other three "already so"). `weapons` and `experience max` skipped all four as summoned creatures ("summoned creatures carry no weapons: 4", "... do not level: 4"). **Not seen yet:** weapons on ordinary units and maximum experience on ordinary units and on a hero, on a unit screen (the hero cap, 1000 and level 8, comes from the game's table and ReMoM's code).
