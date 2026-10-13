# mompy

Change a running game of *Master of Magic* from the command line:

```
momctl peek wizard 1 gold
momctl poke wizard 1 gold 30000
```

mompy talks to **DOSBox Staging's built-in web API** (`webserver_enabled = true`), which can read
and write the emulated machine's memory. It needs no game files of its own and ships none: only
offsets, ranges and what we have checked about them.

**Status: not built yet.** This repository holds the plan (see `docs/`). Nothing here has
been tried on anyone's machine but Kevin's.

## What it will need

- DOSBox Staging 0.83 or newer (its web API; `webserver_enabled = true`) running *Master of Magic* 1.31.
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
