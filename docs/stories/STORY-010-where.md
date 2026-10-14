# STORY-010: `mompy where`: the map tile under the game's mouse cursor (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-13), checked on a real game. **Priority: nice to have.**
**Size:** medium (a research step first)
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 ("a mompy tool that gives you the map coords of the current cursor")

## What to do

Point the mouse at something in the running game and ask `mompy where`; it prints the plane and tile and what is there:

```
Myrror (51, 22)  city Blackstone, owner Jafar   2 units
```

The reverse (a name in, a place out) is [STORY-011](STORY-011-where-name.md), which needs no mouse and could come first. Uses: no more counting tiles to find a lair, a stack or a node's coordinates for Mirror's editors (move, lair and node tools) or for `mompy peek`; and a `--watch` mode
that follows the cursor and prints as it moves. The wizard, city, unit, node and lair tables are already readable ([ram-layout.md](../reference/ram-layout.md)); the tile contents come from them.

## What is already known (Mirror's `docs/reference/live-ram-map.md`, "Surveyor hovering, the map view and the plane", 2026-09-24)

- The overland map's **top-left tile** is a u16 pair at RAM `0x2F9EE` (the data segment + `0x6FFE`) in the research setup; it matched the screen every time. It moves with the DOSBox build like every other address:
  relative to the wizard table that is `-0x2ECC` (STORY-001's scan gives the shift).
- The **plane** being viewed is a u16 at RAM `0x34776` (*guess*, one experiment, later consistent).
- **Hovered tile = view origin + (mouse x / 2 / 20, (mouse y - 20) / 18)**: the visible map is 12 × 10 tiles of 20 × 18 pixels from screen row 20, INT 33h x runs 0 to 639, and x wraps at 60. *Checked* on about 300 hovers.

## What is missing: where to read the mouse

DOSBox's web API does not report the mouse. Two ways, to be settled by the research step:

1. **Find the game's own copy.** The game polls the DOS mouse driver every frame and probably keeps the cursor position in its data segment. Find the u16 pair that follows the cursor (the research fork's memory watches can: move the mouse over the map, see which addresses change).
   If it exists this works on **stock DOSBox Staging** with no changes.
2. **A DOSBox endpoint** that reports the DOS mouse driver's position (INT 33h AX=3): the fork already reads it for its signature log. See the DOSBox fork's own ticket (`docs/apocrypha/stories/STORY-009`); it is a small, upstreamable change, but needs a DOSBox build that has it.

## Limits to design for

- It cannot know *which screen* is showing (city, combat, spellbook...). The mouse is only meaningful over the overland map: `where` says "not over the map" when the cursor is outside the 12 × 10 viewport, and the story should look for a game variable that says which screen is up.
- The viewport scrolls and the map wraps horizontally at 60; the plane flips on the Plane button. All handled by the formula above, but each needs a test with fabricated memory.

## Definition of done

On the real game, point at five known things (Blackstone at (51, 22) on Myrror, a lair, a node, a unit stack, empty ocean) and `where` names each correctly, compared with the Surveyor panel or the map. Tests with a fake DOSBox.

## Outcome

Option 1 worked: **the game keeps the pointer's position in its own memory**, so this needs no DOSBox change and works on stock DOSBox Staging. Found with three snapshots of the data segment (top-left, bottom-right, and the middle) and one candidate pair surviving, then cross-checked by reading the map origin and the plane; the addresses and checks are in [ram-layout.md](../reference/ram-layout.md).

- `mompy where pointer` prints the plane, tile, the city and the units there, e.g. `Myrror (51, 22)  city Blackstone, owner Jafar  2 units: ...`; `--json` for scripts.
- `pointer` is also a *place*, accepted wherever one is: `pew pointer`, `unit mercury --at pointer`, `cast unit.NAME --at pointer`.
- Outside the map (the sidebar, the menu bar) it says "the pointer is not over the map".
- Not done: knowing which *screen* is showing (a city screen leaves the overland map's variables as they were, so `pointer` would still answer from them); a `--watch` mode.
