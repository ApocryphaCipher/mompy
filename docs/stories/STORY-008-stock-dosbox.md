# STORY-008: Works with released DOSBox Staging

**Parent:** [EPIC-001](../epics/EPIC-001-momctl-core.md)
**Status:** proposed (2026-10-13)
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

Everything else assumes that an unmodified **DOSBox Staging 0.83.0** has the memory API *and* the write. The source says yes (`src/webserver/memory.cpp`
at tag `v0.83.0` has `PUT` and `If-Match`), but nobody has run the **released binaries**.

1. Download the official release for macOS, and if possible Windows and Linux (ask Kevin for help or for a tester on those).
2. Run Master of Magic, `webserver_enabled = true`, read a wizard record with `curl`, and write one gold value with a compare-and-swap; look at the game's screen.
3. Write down in [reference/dosbox-api.md](../reference/dosbox-api.md) which builds work, and what the user has to change in the config.
4. If a build does **not** have it, say how to get one (the research fork, or a build from source).

## Definition of done

The reference doc lists, per platform, a DOSBox release that was tried, and the result.
