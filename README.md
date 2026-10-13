# mompy

Change a running game of *Master of Magic* from the command line:

```
mompy peek wizard 1 gold
mompy poke wizard 1 gold 30000
```

mompy talks to **DOSBox Staging's built-in web API** (`webserver_enabled = true`), which can read
and write the emulated machine's memory. It needs no game files of its own and ships none: only
offsets, ranges and what we have checked about them.

**Status: just started.** `mompy doctor` exists (below); `peek` and `poke` are next (see `docs/stories/`).
Nothing here has been tried on anyone's machine but Kevin's.

## `mompy doctor`

```
python -m mompy doctor            # or: mompy doctor, once installed;  --url http://127.0.0.1:8086 is the default
```

It checks, without changing the game, that DOSBox's web API answers (and which version), that the memory can be read, that the game's tables are
found and look right (their address depends on the DOSBox build, so they are *found*, not assumed), and that a write is accepted (by writing back the byte that is already there).
It ends with `READY`, `READ-ONLY` or `NOT READY`, and exits 0 only for `READY`.

## What it will need

- DOSBox Staging with its web API on (`webserver_enabled = true`) running *Master of Magic* 1.31. Developed against **0.84-alpha** (Kevin's research fork);
  the 0.83.0 release works too (checked), and `doctor` recognises both. A fork build also needs `webserver_allow_writes = true` before it accepts a write; stock DOSBox Staging does not.
- Python 3.9 or newer. No other packages.

## Layout

```
mompy/              this repository
  mompy/            the Python package (standard library only)
  tests/
  docs/             epics, stories, notes, reference, backlog (the project's tickets)
```

The game's own files stay in the player's install folder; the repository never contains them. To read DOSBox Staging's
source, clone [dosbox-staging/dosbox-staging](https://github.com/dosbox-staging/dosbox-staging) anywhere outside this folder.

Related: [Mirror](https://github.com/ApocryphaCipher/Mirror) edits *save files* (and holds the verified
research on the formats), and `gama` turns memory dumps into data.
