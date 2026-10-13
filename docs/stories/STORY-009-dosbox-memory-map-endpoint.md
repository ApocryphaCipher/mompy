# STORY-009: Ask DOSBox where the game was loaded (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** Not needed for the first release: `doctor` finds the tables by scanning.
**Size:** small (mompy side); the DOSBox side is its own ticket
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

The game's tables sit at different addresses in different DOSBox builds (`0x520` apart between 0.83.0 and 0.84-alpha, because 0.84 reserves memory for DOS
`STACKS`; see [ram-layout.md](../reference/ram-layout.md)). `doctor` scans the 16 MiB for five wizard names at the record stride, which works but reads all of memory.

DOSBox's API does not say where a program was loaded. A new read-only endpoint, `GET /api/v1/dos/memory-map` (the DOS memory-control-block chain: segment, size, owner), is
specified in the DOSBox fork's own docs (`docs/apocrypha/stories/STORY-008`), as a candidate for its own upstream pull request. With it `mompy` could:

- find the game's load segment from the chain, add the fixed offset to the data segment (read once from a known-good run) and get the table addresses **exactly**;
- keep the scan as a cross-check, and as the fallback for DOSBox builds without the endpoint.

## Definition of done

`doctor` uses the endpoint when it exists (the version check from STORY-001 says so) and prints which method found the tables; both methods agree on a real game.
Depends on the DOSBox side being built; until then this ticket waits.
