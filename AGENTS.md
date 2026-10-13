# AGENTS.md

How to work on **mompy**, for people and AI agents. A story's acceptance criteria or an explicit request
from [Kevin](https://github.com/KevinAsbury) override this.

**Short version:** the smallest change that solves the task, every claim about the game checked against the real thing,
tests green, docs a little truer than you found them.

## 1. Done means checked

```
python -W error -m unittest discover -s tests -t .
python -m compileall -q mompy
```

Tests use `unittest` (standard library) and a fake DOSBox web server (`tests/fake_dosbox.py`), so they need no game and no DOSBox.
The code targets **Python 3.12 or newer** (Kevin: use modern Python). Only 3.14 has been run so far; the standard library is enough (`tomllib` reads the field table).

Do not weaken or skip a test to get green. If a check could not be run, say so and why.

## 2. Git

- Never commit to `main` once the repository has a remote. Branch (`feat/...`, `fix/...`, `docs/...`, `chore/...`),
  commit with the same prefixes and the story id (`feat: peek a wizard field (STORY-003)`), open a PR against `main`.
- Agents open PRs; **Kevin merges.** No auto-merge, no force-push of shared history.
- Copilot and other reviews: fix each finding or say why not, in a reply on its thread, and what was checked.

## 3. Game files and copyright

The game's files (`*.LBX`, `*.GAM`, `*.EXE`, anything decoded from them) **never go in this repository.** They stay in the player's own game folder,
outside it. Tests use synthetic data. The repository carries offsets, ranges and checked facts, and names only
as the player's own `SPELLDAT.LBX` supplies them at run time (a bundled fallback list is Kevin's call, see the backlog).

## 4. Ground truth

mompy writes into someone's running game. Every field in the table carries a confidence mark: **checked** (a write was seen
to drive the game, or two independent sources agree) or **guess**. A guess is never offered without `--force`. Facts come from
Mirror's `docs/reference/` and from your own check on a real game; when they disagree, the check wins and the table says why.

## 5. Safety of writes

- Every write is a compare-and-swap (`If-Match` with the bytes you expect). A 412 changes nothing.
- Range-check against the field table before sending. Refuse, say why, never clamp silently.
- Log the old bytes so `undo` works. `--dry-run` shows what would be written.
- Loopback only. Refuse to run if the layout check (`doctor`) fails: never write into memory that does not look right.

## 6. Code

Standard library only (Python 3.12+): `urllib`, `json`, `tomllib`, `argparse`, `struct`. Small functions, names from the game's
domain (wizard, record, field), no network calls except the DOSBox API on `127.0.0.1`.

## 7. Documentation and tickets

`docs/` is the project's state: `epics/`, `stories/` (indexed in `stories/README.md`), `backlog.md` (unsorted ideas),
`notes/` (dated session notes), `reference/` (what we know, and how we know it). A good idea that comes up mid-task becomes a
story or a backlog line, not a drive-by change. When a story is done, mark it, record the outcome in it, update the epic
and the index. At the end of a session, update the handoff note.

## 8. Reporting

Be concise and concrete: what changed, the decisions, the checks run and their results, what is unresolved.
Never claim a test passed, a build worked or a bug is fixed without having seen it.
