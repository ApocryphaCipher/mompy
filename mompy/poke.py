"""``mompy poke`` and ``mompy undo``: change a field of the running game, safely.

Every write is a compare-and-swap (the bytes must still be what mompy just read), every value is range-checked against the
field table, and nothing is clamped silently. A field the game keeps on both wizards of a pair (a relation, a treaty) is written on
both or on neither. Each change is logged (``$MOMPY_HOME/undo.jsonl``) so ``undo`` can put it back.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from . import fields as F
from . import game as gamefile
from . import peek
from .api import ApiError, DosboxApi, Mismatch, WritesDisabled

LOG_LIMIT = 200
_YES = {"on", "yes", "true"}
_NO = {"off", "no", "false"}


class PokeError(Exception):
    """A refusal, in words for the player. Nothing was written (or what was written was put back)."""


class Target:
    """What one poke changes: a field, or one element of it, in one wizard's record."""

    def __init__(self, field: F.Field, element: Optional[int], address: int, size: int):
        self.field, self.element, self.address, self.size = field, element, address, size


def _normal(text: str) -> str:
    return " ".join(text.lower().replace("_", " ").replace("-", " ").split())


def _allowed_words(field: F.Field) -> dict:
    """Words that stand for each number of an enum field: ``alliance``, and for ``none (peace)`` both ``none`` and ``peace``."""
    words = {}
    for number, text in field.enum.items():
        base, _, rest = text.partition(" (")
        for word in (text, base, rest.rstrip(")")):
            if word:
                words[_normal(word)] = int(number)
    return words


def check_allowed(field: F.Field, force: bool) -> None:
    """Refuse a field the game does not accept (or works out again) and, without ``--force``, one we only guess."""
    if field.derived:
        raise PokeError(f"{field.name} is worked out again by the game; a write would be overwritten")
    if not field.writable:
        raise PokeError(f"{field.name} is not editable (mompy has not seen the game accept a change to it)")
    if field.confidence != "checked" and not force:
        raise PokeError(f"{field.name} is only a guess so far; --force to write it anyway")


def parse_item(field: F.Field, text: str) -> int:
    """One number for ``field`` from what the player typed: a number, an enum word, or on/off for a 0..1 flag."""
    word = _normal(text)
    if field.enum:
        known = _allowed_words(field)
        if word in known:
            return known[word]
    if field.min == 0 and field.max == 1:
        if word in _YES:
            return 1
        if word in _NO:
            return 0
    try:
        value = int(text.strip())
    except ValueError:
        raise PokeError(_expected(field)) from None
    if field.min is not None and field.max is not None and not field.min <= value <= field.max:
        raise PokeError(_expected(field))
    return value


def _expected(field: F.Field) -> str:
    rng = f" from {field.min} to {field.max}" if field.min is not None and field.max is not None else ""
    words = f", or one of: {', '.join(field.enum.values())}" if field.enum else ""
    return f"{field.name} is a whole number{rng}{words}"


def _parse_name(text: str) -> str:
    name = text.strip()
    if not 1 <= len(name) <= 19 or not re.fullmatch(r"[\x20-\x7E]+", name):
        raise PokeError("a name is 1 to 19 letters, digits or punctuation (no accents)")
    return name


def resolve(game, field: F.Field, number: int, element: Optional[str], names: List[str]) -> Target:
    """Where in memory the field (or one element) of wizard ``number`` sits."""
    block = F.blocks()["wizard"]
    record = game.base + (number - block.first_number) * block.stride
    if element is None:
        if field.mirrored or (field.is_array and field.count > 24):
            hint = f"{field.name}.NAME" if field.mirrored else f"{field.name}.N"
            raise PokeError(f"set {field.name} one element at a time ({hint})")
        return Target(field, None, record + field.offset, field.size)
    index = field.element(element, names)
    if field.labels == "wizards" and index == number - 1:
        raise PokeError("a wizard has no relation or treaty with himself")
    return Target(field, index, record + field.offset + index * field.item_size, field.item_size)


def _decode(target: Target, raw: bytes):
    f = target.field
    return f.decode_item(raw) if target.element is not None else f.decode(raw)


def _words(target: Target, value) -> str:
    f = target.field
    if f.type == "text":
        return str(value)
    if isinstance(value, list):
        return ",".join(peek._plain(f, v) for v in value)
    return peek._plain(f, value)


def _label(target: Target, names: List[str]) -> str:
    f = target.field
    return f.name if target.element is None else f"{f.name}.{f.label_for(target.element, names)}"


def _encode(target: Target, value) -> bytes:
    f = target.field
    return f.encode_item(value) if target.element is not None else f.encode(value)


def _parse(target: Target, text: str):
    f = target.field
    if f.type == "text":
        return _parse_name(text)
    if target.element is not None or not f.is_array:
        return parse_item(f, text)
    parts = [p for p in text.split(",")]
    if len(parts) != f.count:
        raise PokeError(f"{f.name} takes {f.count} comma-separated values, got {len(parts)}")
    return [parse_item(f, p) for p in parts]


def _write(api: DosboxApi, address: int, new: bytes, expect: bytes, label: str) -> None:
    try:
        api.write(address, new, expect=expect)
    except Mismatch as err:
        now = f" (now {err.current.hex()})" if err.current is not None else ""
        raise PokeError(f"the game changed {label} while mompy was working{now}; nothing written") from None
    except WritesDisabled:
        raise PokeError("DOSBox refuses writes. Set webserver_allow_writes = true in its config "
                        "(the research fork needs it; stock DOSBox Staging does not).") from None


def poke(api: DosboxApi, number: int, spec: str, text: str, dry_run: bool = False, force: bool = False) -> str:
    """Change wizard ``number``'s ``spec`` (``gold``, ``books.sorcery``...) to ``text``. Returns what to print."""
    found = peek.find_game(api)
    block = F.blocks()["wizard"]
    last = block.first_number + block.count - 1
    if not block.first_number <= number <= last:
        raise PokeError(f"there is no wizard {number} (1 to {last})")
    names = list(found.names)
    name, _, element = spec.partition(".")
    try:
        field = F.find("wizard", name)
        check_allowed(field, force)
        target = resolve(found, field, number, element or None, names)
    except F.FieldError as err:
        raise PokeError(str(err)) from None
    new_value = _parse(target, text)
    label = _label(target, names)
    try:
        current = api.read(target.address, target.size)
    except ApiError as err:
        raise PokeError(str(err)) from None
    old_value = _decode(target, current)
    if old_value == new_value:
        return f"{label} is already {_words(target, new_value)}, nothing written"
    change = f"{label}: {_words(target, old_value)} -> {_words(target, new_value)}"

    pair = None                     # the other wizard's side of a mirrored field
    if field.mirrored and target.element is not None and target.element < block.count:
        pair = Target(field, number - 1, found.base + target.element * block.stride + field.offset
                      + (number - 1) * field.item_size, field.item_size)
        change += f"  (and {names[target.element]}'s view of {names[number - 1]})"
    if dry_run:
        return f"(dry run) would write {change}"

    new_bytes = _encode(target, new_value)
    _write(api, target.address, new_bytes, current, label)
    writes = [{"address": target.address, "old": current.hex(), "new": new_bytes.hex()}]
    if pair is not None:
        try:
            pair_now = api.read(pair.address, pair.size)
            if pair_now != new_bytes:
                _write(api, pair.address, new_bytes, pair_now, f"{names[target.element]}'s view")
                writes.append({"address": pair.address, "old": pair_now.hex(), "new": new_bytes.hex()})
        except (PokeError, ApiError) as err:
            try:                    # both or neither: put the first side back
                api.write(target.address, current, expect=new_bytes)
                undone = "the first side was put back"
            except ApiError:
                undone = "the first side could NOT be put back: check it with peek"
            raise PokeError(f"{err}; {undone}") from None
    _log(api.url, label, _words(target, old_value), _words(target, new_value), writes)
    return change


# --- the undo log ---------------------------------------------------------------------------------------------

def _log_path():
    return gamefile.home() / "undo.jsonl"


def read_log() -> Tuple[List[dict], int]:
    """(entries, unreadable lines): a damaged line is skipped, never a crash."""
    entries, bad = [], 0
    try:
        lines = _log_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return [], 0
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if isinstance(entry, dict) and isinstance(entry.get("writes"), list):
                entries.append(entry)
                continue
        except ValueError:
            pass
        bad += 1
    return entries, bad


def _save_log(entries: List[dict]) -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in entries[-LOG_LIMIT:]), encoding="utf-8")


def _log(url: str, label: str, old: str, new: str, writes: List[dict]) -> None:
    entries, _ = read_log()
    entries.append({"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "url": url,
                    "label": label, "old": old, "new": new, "writes": writes})
    try:
        _save_log(entries)
    except OSError:
        pass                        # a log that cannot be written must not undo the write that was made


def undo(api: DosboxApi) -> str:
    """Put the last logged change back, if the game still holds what mompy wrote."""
    entries, bad = read_log()
    note = f" ({bad} unreadable log line{'s' if bad != 1 else ''} skipped)" if bad else ""
    if not entries:
        return "nothing to undo" + note
    entry = entries[-1]
    writes = entry["writes"]
    try:
        for w in writes:
            now = api.read(w["address"], len(bytes.fromhex(w["new"])))
            if now.hex() != w["new"]:
                raise PokeError(f"{entry.get('label', 'the last change')} was changed since (at {w['address']:#x}): "
                                "not undone, and the entry is kept")
        for w in reversed(writes):
            _write(api, w["address"], bytes.fromhex(w["old"]), bytes.fromhex(w["new"]), entry.get("label", "the value"))
    except (ApiError, KeyError, ValueError) as err:
        raise PokeError(str(err)) from None
    _save_log(entries[:-1])
    return f"undid: {entry.get('label')} {entry.get('new')} -> {entry.get('old')}" + note
