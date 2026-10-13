# STORY-001: doctor: is it safe to write?

**Parent:** [EPIC-001](../epics/EPIC-001-momctl-core.md)
**Status:** proposed (2026-10-13)
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`momctl doctor` answers, before anything is written:

- Is the server up (`/dosbox/info`) and which DOSBox version is it?
- Does a write work? (Write a scratch location with a compare-and-swap and read it back; never a game table.)
- Does the game's memory **look like the layout in [ram-layout.md](../reference/ram-layout.md)?** Five names, printable, at the wizard stride; city, unit and node counts in range.
  If not, say so and make every later command refuse (unless the player gives the table's address by hand).
- Which extras does this server have (screenshot, pause)?

Output is plain text with a clear verdict, and an exit status 0 or 1.

## Definition of done

Tested against a fake server (a small local `http.server` in the tests) for each verdict, and run once against Kevin's game.
