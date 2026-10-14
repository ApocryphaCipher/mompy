# STORY-021: `mompy unit mercury`: give a stack all the movement it needs (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-13); checked on a real game; not yet pushed. **Priority: nice to have.** Cheap once units can be found by place.
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 (the new War Bears walked off the city after being written in, and ran out of moves: "we need another command to max out a unit stack's movement to like 254 or 255")

## What to do

```
mompy unit mercury                  # the stack under the mouse (needs STORY-010)
mompy unit mercury --at blackstone  # the stack on a city, or --at x,y,plane
mompy unit mercury --wizard 1       # every unit of wizard 1
```

Set the units' **moves left** to the top (the unit record's `+8`, a byte) so they can walk all turn. Max moves (`+4`) stays as it is: the game works moves left back up from it each turn, so this is a one-turn boost. Compare-and-swap, `undo`, like every `poke`.

## To find out

- Does the game accept 254/255 moves left, or does it read the byte in some unit (the screen shows moves in halves)? Try 20 first, then 255. *Guess:* a larger value just lets the unit keep walking; terrain costs are subtracted.
- Does the stack move with the slowest unit's moves (the game's own rule)? Then every unit of the stack needs the value, hence "stack", not one unit.

## Definition of done

On the real game: after `unit mercury`, a stack walks across the continent in one turn; `undo` puts the moves back; End Turn restores the normal moves. Tests with the fake DOSBox.

## Outcome

Built as `mompy/unit.py`: `mompy unit mercury --at CITY|x,y,plane` or `--wizard N`, `--dry-run`, one `undo` for all units. No mouse (STORY-010 is still open); the mouse form can be added when it is.

- **The byte is signed, in half-moves: 127 is the top.** ReMoM's `s_UNIT.moves2` is an `int8_t`, so a 254 or 255 would read as negative. Real game (fork 0.84.0-alpha, 2026-10-13): 20 showed **10 moves**; 127 showed **63.5** and Kevin's Cavalry crossed most of the continent in one turn. Terrain costs are still paid; they just do not run out. The finished command was run on that Cavalry too (`--at x,y,plane`, then `undo`, then again).
- `+8` (moves left) only; max moves (`+4`) is untouched, so the next turn is normal.
- Dead records (plane and owner 0xFF) are skipped; a failed write puts the earlier ones back.
- Tests: `tests/test_unit.py` (fake DOSBox).
