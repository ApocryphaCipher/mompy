# STORY-018: `mompy pew`: kill the units on the tile under the mouse (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** Depends on [STORY-003](STORY-003-poke.md) (`poke`) and, for the mouse, on [STORY-010](STORY-010-where.md) (`where`).
**Size:** small (once the mouse tile is known)
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 ("mompy pew could be a more advanced command. Maybe it kills everything under a mouse stack (units, not cities or anything)")

## What to do

Point the mouse at a stack in the running game and run:

```
mompy pew                          # every unit on the tile under the mouse: pew.  (4 units: Sprites x3, Magic Spirit)
mompy pew blackstone               # or name the place: a city's tile (its garrison dies, the city does not)
mompy pew 51,22,myrror             # or the tile
mompy pew --enemy                  # only units that are not the player's;  --mine, --owner freya
```

It kills **units only**: no cities, nodes, lairs, buildings or terrain. The tile is the one `mompy where` reports (STORY-010: the mouse, or STORY-011's name lookup, or explicit coordinates).

## How the game marks a dead unit (checked)

Mirror's `docs/reference/live-ram-map.md` (2026-09-23, the node guardians dying in a real fight): "dead units are marked in place": the record's **plane and owner both become `0xFF`**, the live count stays, and the record is swept at End Turn
(`Mirror.SaveFile.Units` skips plane `0xFF`). So `pew` writes those two bytes on each unit record at the tile, with a compare-and-swap per record, and prints what it killed (type names, owners).

## Decisions and open questions

- **Heroes.** A hero is also an entry in his wizard's hero list (name, items, slot). Killing the unit record and leaving the list entry may leave a dangling hero. By default `pew` **spares heroes** and says so (`2 units, 1 hero spared; --heroes to include`); killing one properly clears the hero-list entry too, which is the heroes epic's knowledge and a spike (what does the game do on a real hero's death?).
- **Units inside something.** Units carried by a boat sit at the boat's tile (the same position); check whether a stack on a boat is one tile of records or has a link field (`+19` "in tower" is for towers) and what happens to the passengers when only the boat dies. Default: kill the whole tile.
- **No undo of death for the player.** `pew` logs the old bytes so `mompy undo` can bring the stack back (plane and owner restored) until End Turn sweeps the records; after that it cannot. Say so in the output.
- **No mouse over the map**: refuse with a message (STORY-010's "not over the map").
- **Confirm?** A joke command that kills a stack should not take two keystrokes, but it should print exactly what it did; `--dry-run` shows the list without writing.

## Definition of done

On the real game: `pew` on a known stack (a neutral lair's guards, or the player's own test stack) removes it from the map (the game may need End Turn to redraw: say so) without touching a city on the same tile; heroes spared; `undo` before End Turn restores them. Tests with the fake DOSBox for the tile filter, the heroes, the dead marker and the undo.
