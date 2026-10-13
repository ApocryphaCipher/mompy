# STORY-008: Works with released DOSBox Staging

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** in progress (2026-10-13): the macOS release is **done** (API, write, compare-and-swap, and a write to the real game's gold seen on its screen); Windows and Linux still to do
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

## Progress (2026-10-13)

- **macOS v0.83.0 release, checked:** the memory read, the `PUT`, the compare-and-swap and its 412 all work, as does the `Host` guard; the fork-only endpoints are absent.
  Details and the exact requests are in [reference/dosbox-api.md](../reference/dosbox-api.md). The check ran on a scratch address with no game, so it proves the API, not yet the game's tables.
- **macOS, real game, done:** Master of Magic ran in the released build and a write of wizard 1's gold (30000 to 12321, compare-and-swap) showed on the main screen ("12321 gp", Kevin); it was put back afterwards. **Finding:** the game's tables were `0x520` lower than in the research setup, so addresses
  have to be found by scanning, not hard-coded: that is STORY-001's job, and this run is its first test case (wizard table at `0x3239A`).
- **To do:** (b) a Windows run and a Linux run, by someone who has those; (c) if a platform lacks the API, record how to get one.
