"""The field table (``fields.toml``): what each part of a game record is, where it sits, what it may hold.

Every field says how sure we are: ``checked`` (seen to drive the real game) or ``guess``. Offsets are from the
start of a record. See ``docs/reference/ram-layout.md`` for where each was checked.
"""

from __future__ import annotations

import struct
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from typing import Dict, List, Optional, Sequence, Union

_SIZES = {"u8": 1, "i8": 1, "u16": 2, "i16": 2}
_STRUCT = {"u8": "<B", "i8": "<b", "u16": "<H", "i16": "<h"}

Value = Union[int, str, List[int]]


class FieldError(Exception):
    """An unknown field or element; the message lists what exists."""


@dataclass(frozen=True)
class Block:
    name: str
    stride: int
    count: int
    first_number: int
    describe: str


@dataclass(frozen=True)
class Field:
    block: str
    name: str
    offset: int
    type: str
    count: int = 1
    length: int = 0
    labels: Union[None, str, List[str]] = None
    enum: Dict[str, str] = field(default_factory=dict)
    min: Optional[int] = None
    max: Optional[int] = None
    writable: bool = False
    derived: bool = False
    format: str = ""                 # "map_position": x, y, plane; shown with the plane name and the city there
    confidence: str = "guess"
    note: str = ""

    @property
    def size(self) -> int:
        """Bytes this field occupies in a record."""
        return self.length if self.type == "text" else _SIZES[self.type] * self.count

    @property
    def is_array(self) -> bool:
        return self.type != "text" and self.count > 1

    def decode(self, raw: bytes) -> Value:
        """The bytes of this field as a number, a list of numbers, or text."""
        if len(raw) != self.size:
            raise ValueError(f"{self.name}: expected {self.size} bytes, got {len(raw)}")
        if self.type == "text":
            return raw.split(b"\0", 1)[0].decode("latin-1")
        step = _SIZES[self.type]
        values = [struct.unpack(_STRUCT[self.type], raw[i:i + step])[0] for i in range(0, len(raw), step)]
        return values if self.is_array else values[0]

    def encode(self, value: Value) -> bytes:
        """The reverse of ``decode`` (a later story writes with it; tested here so the two agree)."""
        if self.type == "text":
            data = str(value).encode("latin-1")
            if len(data) >= self.length:
                raise ValueError(f"{self.name}: text of {len(data)} bytes does not fit {self.length - 1}")
            return data.ljust(self.length, b"\0")
        items = value if isinstance(value, (list, tuple)) else [value]
        if len(items) != self.count:
            raise ValueError(f"{self.name}: expected {self.count} values, got {len(items)}")
        return b"".join(struct.pack(_STRUCT[self.type], v) for v in items)

    def label_for(self, index: int, wizard_names: Sequence[str] = ()) -> str:
        """The name of element ``index`` (0-based): a spellbook realm, a retort, another wizard..."""
        if self.labels == "wizards":
            names = list(wizard_names) + ["neutral"]
            return names[index] if index < len(names) else str(index + 1)
        if isinstance(self.labels, list) and index < len(self.labels):
            return self.labels[index]
        return str(index + 1)

    def element(self, selector: str, wizard_names: Sequence[str] = ()) -> int:
        """The 0-based index of an element, from its label or its 1-based number.

        Labels ignore case, underscores, hyphens and apostrophes (``aura_of_majesty``, ``natures-wrath``);
        a unique prefix works (``aura``); an ambiguous one lists its matches instead of guessing.
        """
        if not self.is_array:
            raise FieldError(f"{self.name} is a single value, it has no elements")
        wanted = _normal(selector)
        labels = [_normal(self.label_for(i, wizard_names)) for i in range(self.count)]
        if wanted in labels:
            return labels.index(wanted)
        if wanted.isdigit() and 1 <= int(wanted) <= self.count:
            return int(wanted) - 1
        prefixed = [i for i, l in enumerate(labels) if wanted and l.startswith(wanted)]
        if len(prefixed) == 1:
            return prefixed[0]
        if len(prefixed) > 1:
            raise FieldError(f"{selector!r} could be "
                             + ", ".join(self.label_for(i, wizard_names) for i in prefixed[:6]))
        raise FieldError(f"{self.name} has no element {selector!r} (1 to {self.count}"
                         + (f", or {self._label_help(wizard_names)}" if self.labels else "") + ")")

    def _label_help(self, wizard_names: Sequence[str]) -> str:
        shown = [self.label_for(i, wizard_names) for i in range(min(self.count, 8))]
        return ", ".join(shown) + (", ..." if self.count > 8 else "")


def _normal(text: str) -> str:
    """A name for comparing: lower case, underscores and hyphens as spaces, no apostrophes, one space between words."""
    return " ".join(text.lower().replace("_", " ").replace("-", " ").replace("'", "").split())


_cache: Optional[Dict[str, object]] = None


def _load() -> Dict[str, object]:
    global _cache
    if _cache is None:
        doc = tomllib.loads(resources.files("mompy").joinpath("fields.toml").read_text(encoding="utf-8"))
        blocks = {n: Block(n, b["stride"], b["count"], b["first_number"], b["describe"])
                  for n, b in doc["blocks"].items()}
        fields = [Field(**f) for f in doc["field"]]
        _cache = {"blocks": blocks, "fields": fields}
    return _cache


def blocks() -> Dict[str, Block]:
    return _load()["blocks"]  # type: ignore[return-value]


def all_fields(block: Optional[str] = None) -> List[Field]:
    return [f for f in _load()["fields"] if block in (None, f.block)]  # type: ignore[union-attr]


def find(block: str, name: str) -> Field:
    """The field called ``name`` (case-insensitive, ``-`` and ``_`` alike), or ``FieldError``."""
    key = name.strip().lower().replace("-", "_")
    for f in all_fields(block):
        if f.name == key:
            return f
    names = ", ".join(f.name for f in all_fields(block))
    raise FieldError(f"no {block} field {name!r}. Fields: {names}")
