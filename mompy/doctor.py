"""``mompy doctor``: is it safe to read and write this running game?

Run before anything is written. It checks, in order: the DOSBox web API answers (and which version);
the game's memory can be read; the game's tables are found and look right (the address moves with the DOSBox
build, so they are *found*, not assumed); and that a write is accepted (by writing back the bytes that are
already there, so a healthy game is never changed by it).
"""

from __future__ import annotations

from typing import List, NamedTuple, Optional

from . import layout, locate, version as versions
from .api import MEMORY_SIZE, ApiError, DosboxApi, Mismatch, WritesDisabled

OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skip"


class Check(NamedTuple):
    name: str
    status: str
    detail: str


class Report(NamedTuple):
    checks: List[Check]
    wizard_base: Optional[int]    # where the game's wizard table was found; None if not
    can_write: bool

    @property
    def ready(self) -> bool:
        """True when nothing failed and a write is accepted: safe for ``peek`` and ``poke``."""
        return self.can_write and not any(c.status == FAIL for c in self.checks)


def diagnose(api: DosboxApi) -> Report:
    checks: List[Check] = []

    # 1. the server, and its version
    try:
        info = api.info()
    except ApiError as err:
        checks.append(Check("DOSBox", FAIL, f"{err}. Start DOSBox Staging with webserver_enabled = true."))
        return Report(checks, None, False)
    ver = versions.parse(str(info.get("version", "")))
    checks.append(Check("DOSBox", OK if ver else WARN,
                        info.get("version", "unknown version") + ("" if ver else " (version not recognised)")))

    # 2. the memory, all of it: the game's tables are found by scanning
    try:
        memory = api.read(0, MEMORY_SIZE)
    except ApiError as err:
        checks.append(Check("Memory", FAIL, str(err)))
        return Report(checks, None, False)
    checks.append(Check("Memory", OK, f"read {len(memory) // (1024 * 1024)} MiB"))

    # 3. the wizard table
    try:
        game = locate.find_game(memory)
    except locate.GameNotFound as err:
        checks.append(Check("Game", FAIL, str(err)))
        return Report(checks, None, False)
    if game.alternatives:
        checks.append(Check("Game", WARN, f"{len(game.alternatives) + 1} places look like the wizard table "
                                          f"({', '.join(hex(b) for b in [game.base] + game.alternatives)}); using the first"))
    checks.append(Check("Game", OK, "wizards: " + ", ".join(game.names)))
    chosen, table_checks = game, game.checks

    expected = versions.expected_wizard_base(ver)
    if expected is None:
        checks.append(Check("Address", OK, f"wizard table at {chosen.base:#x} (no expectation for this version)"))
    elif expected == chosen.base:
        checks.append(Check("Address", OK, f"wizard table at {chosen.base:#x}, as expected for this DOSBox"))
    else:
        checks.append(Check("Address", WARN, f"wizard table at {chosen.base:#x}, but {expected:#x} was expected "
                                              f"for this DOSBox ({chosen.base - expected:+#x}); a different 'stacks' "
                                              "setting or game release moves it. The tables checked out, so mompy uses where it found them."))
    for t in table_checks[1:]:
        checks.append(Check(f"  {t.name}", OK, f"at {t.address:#x}: {t.detail}"))

    # 4. writes: put back the byte that is already there
    probe = chosen.base + layout.WIZARD_NAME_AT
    can_write = False
    try:
        current = api.read(probe, 1)
        api.write(probe, current, expect=current)
        can_write = True
        checks.append(Check("Writes", OK, "accepted (wrote one byte back unchanged, with a compare-and-swap)"))
    except WritesDisabled as err:
        checks.append(Check("Writes", FAIL,
                            f"refused: {err}. Read-only: set webserver_allow_writes = true in DOSBox's config "
                            "(the research fork needs it; stock DOSBox Staging 0.83 does not)."))
    except Mismatch:
        checks.append(Check("Writes", WARN, "the byte changed while testing (the game is running); run doctor again"))
    except ApiError as err:
        checks.append(Check("Writes", FAIL, str(err)))

    return Report(checks, chosen.base, can_write)


def render(report: Report, url: str) -> str:
    marks = {OK: "ok  ", WARN: "WARN", FAIL: "FAIL", SKIP: "skip"}
    lines = [f"mompy doctor  ({url})", ""]
    width = max(len(c.name) for c in report.checks)
    for c in report.checks:
        lines.append(f"  [{marks[c.status]}] {c.name.ljust(width)}  {c.detail}")
    lines.append("")
    if report.ready:
        lines.append("Verdict: READY. Reading and writing are safe.")
    elif report.wizard_base is not None and not any(c.status == FAIL and c.name != "Writes" for c in report.checks):
        lines.append("Verdict: READ-ONLY. The game was found, but writes are not accepted.")
    else:
        lines.append("Verdict: NOT READY. Nothing will be written until the above is fixed.")
    return "\n".join(lines)
