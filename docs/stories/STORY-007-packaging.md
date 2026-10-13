# STORY-007: Install, README, licence

**Parent:** [EPIC-001](../epics/EPIC-001-momctl-core.md)
**Status:** proposed (2026-10-13)
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`pipx install mompy` (or run `python -m mompy`), a README a stranger can follow (turn on the web API, start the game, run `doctor`), the platform notes from STORY-008,
and a **licence** (Kevin's choice: MIT like `gama`, or GPL like DOSBox). No game files in the package; check the built package for any.

## Definition of done

A clean machine (or a fresh virtualenv) installs it and runs `momctl doctor` against a game; the package contains only the code and the field table.
