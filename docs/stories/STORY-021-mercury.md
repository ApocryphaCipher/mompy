# STORY-021: `mompy unit mercury`: give a stack all the movement it needs (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** Cheap once units can be found by place.
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
