# STORY-003: poke, safely

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** done (2026-10-13): built, tested with a fake DOSBox, and run on Kevin's real game
**Size:** medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`mompy poke wizard 1 gold 30000`:

- range-check against the field table (refuse and say why; never clamp silently); refuse a `guess` field without `--force`;
- read the current bytes, write with **`If-Match` set to them**, and stop on a 412 (`someone or the game changed it`);
- print `gold: 8293 -> 30000`; `--dry-run` prints it without writing;
- keep a log of old bytes (`~/.mompy/undo.jsonl`) and `mompy undo` puts the last write back (again with a compare-and-swap);
- fields that are written on **both** wizards (a relation or a treaty) write both, or neither.

## Definition of done

Tests against the fake server (a 412 changes nothing; undo restores; a refused value writes nothing); the real game shows 30000 on its main screen and survives one End Turn.

## Outcome (2026-10-13)

Built: `mompy poke wizard N FIELD[.ELEMENT] VALUE [--dry-run] [--force]` and `mompy undo` (`mompy/poke.py`), a remembered game address (`mompy/game.py`), and `mirrored` fields.

- **Values:** a number, an enum word (`alliance`, `known`; for `none (peace)` either `none` or `peace`), `on`/`off` for 0..1 flags, text for `name` (1 to 19 printable ASCII), or `a,b,c` for a whole small array. A field the game works out again (`derived`) or that is not `writable` is refused; a `guess` field needs `--force` (none is writable today; the check is tested with a hand-made field).
  Nothing is clamped: a bad value says what is allowed. Whole `spells` (214) and whole `relations`/`treaty_status` are refused: one element at a time.
- **Safe writes:** each write is a compare-and-swap on the bytes just read; a mismatch (the game moved) or a refusal (`webserver_allow_writes` off) writes nothing and says why. A value already there writes nothing and logs nothing. `--dry-run` writes and logs nothing.
- **Both or neither:** `relations` and `treaty_status` (`mirrored = true` in `fields.toml`) are kept by the game on both wizards of a pair; element *i* of wizard N also sets element N-1 of wizard i+1. The neutral player has no record in the table, so one side. If the second write fails the first is put back and nothing is logged. A wizard's own slot is refused.
- **Undo:** `$MOMPY_HOME/undo.jsonl` (default `~/.mompy`), the last 200 changes. `undo` takes the last: only if every address still holds what mompy wrote does it restore (compare-and-swap, reverse order); otherwise it refuses and keeps the entry. A damaged log line is skipped and counted.
- **The remembered address:** `peek` and `poke` no longer read all 16 MiB each time. The base found is kept in `cache.json`, keyed by the DOSBox URL, and trusted only after a 6 KB read still shows the five wizard names and a plausible city; a stale or damaged cache is a rescan, never an error. `doctor` still scans fully: it is the check.
- **A bug the tests found in `doctor`'s scan** (from STORY-001): it required every wizard name to be three or more characters and anchored on the first wizard, so a wizard named "Al" made `doctor`, `peek` and `poke` all report "no wizard table found". Names of 1 to 19 characters are accepted now (as Mirror's editor allows), and the scan tries each wizard as the anchor. Tested.
- **Tests isolated from the real home:** every test runs with `MOMPY_HOME` in a temporary folder (a first version of the cache wrote into the real `~/.mompy`; that was cleaned up).
- 77 tests (32 new), warnings as errors, with the fake DOSBox: each write changes only the intended bytes, every refusal writes nothing and logs nothing, the race and refusal answers, the pair rule (including a failing second write), undo in reverse order and when the game changed, and the cache (the second command does not scan; stale, corrupt and moved-game caches rescan).
**Real game, 2026-10-13** (fork `0.84.0-alpha (83716)`, MAXIMUS loaded, `webserver_allow_writes = true`):
- `doctor` READY, then `poke wizard 1 gold 12345` (`gold: 30000 -> 12345`; a `--dry-run` first changed nothing): **the main screen showed 12345** (Kevin).
- `poke wizard 1 relations.freya 40` wrote **both** records (two writes, `0x32a0d` and `0x32ed4`; Freya's view of Jafar and Jafar's view of Freya both read 40) and one `undo` put both back to 0.
- **One End Turn:** the gold was **12410** (12345 plus the turn's income, not reset). `undo` then **refused** ("gold was changed since: not undone, and the entry is kept"), as designed, and the original 30000 was put back with a plain `poke`.
- The remembered address held across all of it: no full memory scan after the first command.
- *Not tried on a real game:* the READ-ONLY refusal text (writes disabled), a mid-turn race (only in the fake), `--force`, and a hostile cache (tested only against the fake).
