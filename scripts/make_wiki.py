#!/usr/bin/env python3
"""Write the option tables (``docs/wiki/*.md``) from the field table, so they cannot go stale.

    python3 scripts/make_wiki.py            # rewrite docs/wiki/
    python3 scripts/make_wiki.py --check    # exit 1 if the files differ from what the field table says (the tests do this)
    python3 scripts/make_wiki.py --wiki-links --out DIR     # a copy for the GitHub wiki: links without ".md"

The tables say what you can *type*: a field, the names of its elements, the values it takes and an example. Where the game's own spell or unit
names would go they say ``<spell name>`` or ``<unit name>``: no name that comes from the game's files is written here (mompy reads those
from the running game).  Stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mompy import fields as F          # noqa: E402
from mompy import mass                 # noqa: E402

OUT = ROOT / "docs" / "wiki"
HEADER = ("<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->\n\n")
PAGES = [("Wizard", "wizard", "a wizard", "wizard 1 is you; a name works too: `wizard freya`"),
         ("City", "city", "a city", "by name (`darkmoor`) or number from 1"),
         ("Unit", "unit", "a unit", "numbered from 0, as `where pointer` and `pew` print them (`Cavalry #158`)"),
         ("Node", "node", "a magic node", "numbered from 0"),
         ("Lair", "lair", "a monster place: a Tower of Wizardry, node guardians, cave, dungeon, temple, keep, ruins or lair", "numbered from 0"),
         ("Fortress", "fortress", "a wizard's fortress", "numbered 1 to 6 like the wizards (6 is the neutral player)")]


def _values(f: F.Field) -> str:
    """What may be typed for this field, in a line."""
    if f.type == "text":
        return f"text, up to {f.length - 1} characters"
    if f.format == "spell":
        return "a `<spell name>` or its number; `none` for no spell"
    if f.format == "unit_type":
        return "a `<unit name>` or its type number; `none` for no unit"
    if f.format == "guard_count":
        return "`3` (three at full strength), `2/3` (two left of three) or a whole byte"
    if f.format == "node_owner":
        return "a wizard's name, `nobody`, or 0 to 4"
    if f.format == "owner":
        return "a wizard (read-only)"
    if f.enum:
        return "one of: " + ", ".join(f"`{v}`" for v in f.enum.values()) + " (or its number)"
    if f.min == 0 and f.max == 1:
        return "`on` / `off`"
    if f.min is not None and f.max is not None:
        return f"a whole number from {f.min} to {f.max}"
    return "a whole number"


def _how(f: F.Field, block: str) -> str:
    if not f.writable:
        return "read-only" + (" (the game works it out again)" if f.derived else "")
    how = "" if f.confidence == "checked" else " (a guess: needs `--force`)"
    word = f.enum or f.format in ("spell", "unit_type", "guard_count", "node_owner") or (f.min == 0 and f.max == 1)
    if f.type == "text":
        return "set it" + how
    if f.is_array and f.count > 24:
        return "one element at a time" + how
    if word:
        return ("set an element by its name" if f.is_array else "set it") + how
    if f.is_array:
        return "set an element (`75`), or change it by a sign (`+20`, `-5`); a whole array as `a,b,c`" + how
    return "set it (`75`), or change it by a sign (`+20`, `-5`)" + how


def _field_table(block: str) -> List[str]:
    rows = ["| Field | Type | Values | Change it | Sure | What it is |", "| --- | --- | --- | --- | --- | --- |"]
    for f in F.all_fields(block):
        kind = f"text[{f.length}]" if f.type == "text" else (f"{f.type} x {f.count}" if f.is_array else f.type)
        note = f.note.replace("|", "\\|").replace("\n", " ")
        values = _values(f) + (f"; the elements: [Elements of {f.name}](#elements-of-{f.name})" if f.is_array else "")
        rows.append(f"| `{f.name}` | {kind} | {values} | {_how(f, block)} | {f.confidence} | {note} |")
    return rows


def _element_tables(block: str) -> List[str]:
    out: List[str] = []
    for f in F.all_fields(block):
        if not f.is_array:
            continue
        out += ["", f"### Elements of {f.name}", ""]
        if f.labels == "wizards":
            out += [f"One element per wizard: `{f.name}.<wizard name>` (`mompy peek wizard 2 {f.name}.tauron`), and the neutral player last. A wizard has none for himself.",
                    "A change is written on both wizards' records." if f.mirrored else ""]
        elif f.labels == "spells":
            out += [f"One element per spell: `{f.name}.<spell name>` or `{f.name}.<number 1 to {f.count}>`. The name is the game's own, so it is not listed here: "
                    "`mompy peek wizard 1 spells.<unique start of the name>` finds it, and an ambiguous start lists the matches.",
                    "", "| Value | Meaning |", "| --- | --- |"] + [f"| `{v}` | {w} |" for v, w in f.enum.items()]
        elif isinstance(f.labels, list):
            out += [f"`{f.name}.<name>` or `{f.name}.<number 1 to {f.count}>`; a unique start of the name works.", "", "| # | Name |", "| --- | --- |"]
            out += [f"| {i + 1} | {name} |" for i, name in enumerate(f.labels)]
            if f.min is not None:
                out += ["", f"Each takes {_values(f)}."]
        else:
            out += [f"{f.count} values: `{f.name}.1` to `{f.name}.{f.count}`, or all of them as `a,b,c`."]
    return [l for l in out if l is not None]


def page(title: str, block: str, what: str, numbering: str) -> str:
    b = F.blocks()[block]
    lines = [HEADER + f"# {title} fields", "",
             f"Fields of {what} ({b.count} records; {numbering}).", "",
             f"```\nmompy peek {block} <number or name> [field[.element]]\nmompy poke {block} <number or name> <field>[.<element>] <value>\n```", ""]
    arrays = [f for f in F.all_fields(block) if f.is_array]
    if arrays:
        lines += ["**Element tables on this page:** " + ", ".join(f"[{f.name}](#elements-of-{f.name})" for f in arrays), ""]
    lines += _field_table(block) + _element_tables(block)
    return "\n".join(lines).rstrip("\n") + "\n"


def enchantments_page() -> str:
    lines = [HEADER + "# Unit enchantments and weapons", "",
             "For `mompy unit cast mass.<name> --at <place>` and `unit dispel mass.<name>`: one of these on every unit on a tile. A unique start of the name works.", "",
             "| Name | Bit |", "| --- | --- |"]
    lines += [f"| {name} | `0x{bit:08X}` |" for name, bit in mass.ENCHANTMENTS.items()]
    lines += ["", "## Weapon grades", "", "For `mompy unit weapons <grade> --at <place>` (ordinary units only): `normal`, `magic`, `mithril`, `adamantium` (or 0 to 3).", ""]
    return "\n".join(lines)


LOOKUPS = [("The 24 global enchantments (`globals.<name>`)", "Wizard", "#elements-of-globals"),
           ("The 18 retorts (`retorts.<name>`)", "Wizard", "#elements-of-retorts"),
           ("Spellbooks per realm (`books.<realm>`)", "Wizard", "#elements-of-books"),
           ("Spells: what `spells.<spell name>` takes (known, unknown...)", "Wizard", "#elements-of-spells"),
           ("Relations and treaties with each wizard", "Wizard", "#elements-of-relations"),
           ("The 32 unit enchantments (`unit cast mass.<name>`)", "Unit-enchantments", ""),
           ("Weapon grades (`unit weapons <grade>`)", "Unit-enchantments", "#weapon-grades")]


def home(ext: str = ".md") -> str:
    lines = [HEADER + "# mompy: what you can type", "",
             "Tables of the options of `mompy peek`, `poke` and friends, one page per kind of record. They are generated from the field table, so they match the program.",
             "", "## Look something up", "", "| I want to know... | Where |", "| --- | --- |"]
    lines += [f"| {what} | [{page}{anchor}]({page}{ext}{anchor}) |" for what, page, anchor in LOOKUPS]
    lines += ["", "## All the pages", "", "| Page | Records |", "| --- | --- |"]
    lines += [f"| [{t}]({t}{ext}) | {F.blocks()[b].count} |" for t, b, _, _ in PAGES]
    lines += [f"| [Unit enchantments and weapons](Unit-enchantments{ext}) | 32 enchantments, 4 weapon grades |", "",
              "**How to write a value:** a number sets the field (`75`); a sign changes it (`+20`, `-5`); `to -50` sets a negative value; a word picks a named value (`alliance`, `known`, `on`).",
              "A name from the game itself (a spell, a unit) is written where a table says `<spell name>` or `<unit name>`; mompy reads those names from your running game, so they are not listed here.",
              "", "[Back to the README](https://github.com/ApocryphaCipher/mompy#readme)", ""]
    return "\n".join(lines)


def build(ext: str = ".md") -> Dict[str, str]:
    files = {"Home.md": home(ext), "Unit-enchantments.md": enchantments_page()}
    for title, block, what, numbering in PAGES:
        files[f"{title}.md"] = page(title, block, what, numbering)
    return files


def main(argv: List[str]) -> int:
    wiki = "--wiki-links" in argv
    files = build("" if wiki else ".md")
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (out / name).write_text(text, encoding="utf-8")
        print(f"wrote {len(files)} pages to {out}")
        return 0
    if "--check" in argv:
        bad = [n for n, text in files.items() if not (OUT / n).is_file() or (OUT / n).read_text(encoding="utf-8") != text]
        extra = [p.name for p in OUT.glob("*.md") if p.name not in files] if OUT.is_dir() else []
        for name in bad + extra:
            print(f"docs/wiki/{name} is out of date: run python3 scripts/make_wiki.py", file=sys.stderr)
        return 1 if bad or extra else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} pages to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
