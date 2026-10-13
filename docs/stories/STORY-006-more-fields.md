# STORY-006: Relations, treaties, global enchantments, the defeated flag

**Parent:** [EPIC-001](../epics/EPIC-001-momctl-core.md)
**Status:** proposed (2026-10-13)
**Size:** large
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

Add the fields Mirror checked in the game (2026-10-12/13): visible relations and treaty status (written on both wizards), the 24 global enchantment bytes, the defeated flag, spells and what is researched.

**First, find them in memory:** the fortress block (save offset `0x65F8`, 6 × 4 bytes, the "active" byte is the defeated flag), then items and lairs. Find each by its shape
(the way the wizard table can be found by its names), write the RAM address and how it was checked into [ram-layout.md](../reference/ram-layout.md).

**Test live what Mirror could only test through saves:** setting a global enchantment by hand (does the game start its effect, charge the upkeep, list it on the Magic screen), and whether a treaty set live is kept through an End Turn.

## Definition of done

Each new field is in the table with a confidence mark and was seen in the game; the findings go into the reference doc.
