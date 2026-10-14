# STORY-007: Install, README, licence

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-14); the repo is still private, so the public install line is untried
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`pipx install mompy` (or run `python -m mompy`), a README a stranger can follow (turn on the web API, start the game, run `doctor`), the platform notes from STORY-008,
and a **licence** (Kevin's choice: MIT like `gama`, or GPL like DOSBox). No game files in the package; check the built package for any.

## Definition of done

A clean machine (or a fresh virtualenv) installs it and runs `mompy doctor` against a game; the package contains only the code and the field table.

## Outcome

- **Licence: MIT** (Kevin, 2026-10-14, the same text as `gama`'s). `LICENSE` in the repository and in the wheel; `license = "MIT"` in `pyproject.toml`.
- **Distribution: from GitHub only** (Kevin's choice, no PyPI): `pipx install git+https://github.com/ApocryphaCipher/mompy`. It will work for other people once the repository is **public** (Kevin's call; it is private now, where only someone logged in with access can install it). Nothing was uploaded anywhere. Version **0.1.0**; a `v0.1.0` tag is Kevin's to make with the merge.
- **The package:** `pyproject.toml` (setuptools, which is a build-time tool only: the package has **no dependencies**), a `mompy` command (`mompy.cli:main`), `python -m mompy`, Python 3.12 or newer.
- **Checked** (2026-10-14, macOS, Python 3.14): built a wheel, listed it (only `mompy/*.py`, `fields.toml`, the licence and metadata: **no game files, no tests, no docs**), installed it into a **new virtualenv** from another folder, and ran `mompy --version`, `mompy peek`, `mompy fields` and **`mompy doctor` against the running game: READY**; `pip list` there shows nothing but mompy. Every file parses as Python 3.12 (`ast`, not a run: 3.12 and 3.13 were not available here).
- **README** rewritten for a stranger: what it is, a warning that it writes into a running game, install, a four-step quick start (turn the web API on, load a game, `doctor`, look then change), the safety rules, honest platform notes (macOS only so far, Windows and Linux untried), and the licence. The old "just started" status paragraph is gone.
- `tests/test_packaging.py` (7 tests): the version agrees everywhere, the licence is declared and shipped, no dependencies, the command points at a real function, `fields.toml` ships, only code and the field table are packaged, and **no game file (`.lbx`, `.gam`, `.exe`...) is anywhere in the repository** (AGENTS.md section 5).
- Not done: Windows and Linux (STORY-008), Python 3.12 and 3.13 runs, a public repository, a release tag.
