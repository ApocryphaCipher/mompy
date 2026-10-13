# STORY-020: `mompy poke city <name> build`: finish the current production next turn (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built and checked on a real game (2026-10-13), PR open. **Priority: nice to have.** After [STORY-019](STORY-019-poke-city.md) (needs the `city` block).
**Size:** small once 019 exists
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 (`mompy poke city darkmoor build`: "setting the building work queue to full so it completes next turn")

## What to do

```
mompy poke city darkmoor build          # what is being built is finished at the next End Turn
```

The game keeps (from Mirror's [live-ram-map.md](https://github.com/ApocryphaCipher/Mirror/blob/main/docs/reference/live-ram-map.md), checked in the real game):

- `+28` (u16): the item in production (building ids; 2 = Housing, 29 = Granary...)
- `+94` (u16): production stored so far (0 → 40 when a 40-cost Granary was bought; back to 0 when built)
- `+93` (u8): production per turn

So `build` is a write of `+94` to the item's cost. **What the story must settle:** where the cost comes from. *Guess:* the building cost table is in a game file (BUILDDAT.LBX) or the game's data segment; mompy ships no game data, so either read the cost from memory (find the table the game itself reads) or write "something very large" and let the game's own check (`stored >= cost`) complete it. *To check:* whether the game clamps, or overflows u16, with a big value. Writing a value just over the cost avoids both.

- Refuse when nothing is in production (`+28` is Trade Goods or Housing: nothing to finish).
- One undoable write, like every `poke`.

## Definition of done

On the real game: `poke city darkmoor build`, End Turn once, and the building stands (the city screen, and `+60`-style building byte, show it). Tests with the fake DOSBox.

## Outcome

Built as `mompy/city.py` and `mompy poke city NAME build`, with `tests/test_city_build.py`.

- **Decision:** the cost is not read. `build` writes `production_stored` = 2000, more than any building costs, as one logged compare-and-swap (`undo` puts it back). Reading the cost would need the game's own files; the overshoot turned out harmless.
- Refused: Housing and Trade Goods (nothing to finish); items outside 3 to 35 (units) without `--force`; the raw `production_stored` field needs `--force` too (it is marked a guess), `build` supplies it itself.
- **Real game (fork 0.84.0-alpha, Kevin's MAXIMUS save, 2026-10-13):** `build` on Blackstone (item 31) and Fellwood (item 15), one End Turn: both buildings now stand (flags at `+31+id` set), both stores read **0** afterwards (the 2000 did not carry over), and the game picked the next item (34, 26). Hellgate, untouched as a control, kept its 36 stored and did not build City Walls. A city Kevin bought into (Thanelorn, item 12) showed 100 stored before the turn: a bought building is the same state.
- Not done: units (`--force` is untested), and whether a building the city cannot have (already built) is handled by the game; the production-item field is read-only for now (changing what a city builds is not part of this story).
