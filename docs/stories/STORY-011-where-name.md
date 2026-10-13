# STORY-011: `mompy where <name>`: find a city (or a wizard) by name (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-13), PR open; checked on a real game. **Priority: nice to have.** The cheapest of the "where" ideas: it needs no mouse and no new knowledge.
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 ("mompy where <cityname> is a nice feature too")

## What to do

The reverse of [STORY-010](STORY-010-where.md): give a name, get the place.

```
mompy where Blackstone
Blackstone: Myrror (51, 22), owner Jafar, a Town of population 7

mompy where freya
Freya (wizard 2): summoning circle Arcanus (23, 25), the city Darkmoor ...
```

- **Cities.** Match the name case-insensitively; a unique **prefix** works (`black`); several matches are listed, never guessed. Print the plane (Arcanus or Myrror), the tile, the owner by the wizard's own name, and the size and population.
  The city table is already found and checked by `doctor` (name, position, plane, owner are what its plausibility test reads), so this needs only a small reader for those fields (the same ones STORY-006 adds to the field table).
- **Wizards.** A wizard's name gives their summoning circle (already in the field table) and the city standing there, as `peek wizard N summoning_circle` does now.
- `--json` for scripts. No match says so and lists the nearest names.
- The coordinates are the ones Mirror's editors take (the move tool, the city and node panels), so a `where` answer can be typed straight into them.

## Notes

- City names are in the game's save and memory, not a game file, so nothing here ships game data.
- Neutral and raider cities have names too; they are listed with owner "neutral".
- A *destroyed* city may leave a stale record in the table; `doctor`'s plausibility check is the same one to use, and the reader should skip records the game has marked empty (to confirm against Mirror's `Cities.parse`).

## Definition of done

On the real game: `where Blackstone` gives Myrror (51, 22) and owner Jafar (the Magic screen says "Summon To: Blackstone"); two other cities are checked against the map; an ambiguous prefix lists its matches. Tests with the fake DOSBox.

## Outcome

Built as `mompy/where.py` and `mompy where NAME [--json]`, with `tests/test_where.py` (13 tests, fake DOSBox).

- A whole name (any case) wins; otherwise a unique prefix; several matches are listed (as JSON, all of them), never guessed. No match suggests near names.
- Cities and wizards are searched together. A wizard prints the summoning circle and the city standing on it; a circle that is not on the map is reported as such, not printed.
- Size is the class byte (+19) with the three names we know (Outpost, Hamlet, Village), else `size N`; population is the byte at +20, in thousands. Both as Mirror's `Cities` documents them.
- Empty and stale city slots are skipped with `doctor`'s plausibility test.
- Real game (fork 0.84.0-alpha, Kevin's MAXIMUS save, 2026-10-13): `where Blackstone` gives Myrror (51, 22), owner Jafar, as the Definition of done says. Not yet done: Kevin comparing two other cities with the map.
