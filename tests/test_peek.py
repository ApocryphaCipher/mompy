import contextlib
import io
import json
import unittest

from mompy import fields as F
from mompy import layout
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.peek import PeekError, describe_fields, peek

from .fake_dosbox import FakeDosbox, game_memory, put_field

BASE = layout.REFERENCE_WIZARD_BASE


def game():
    mem = game_memory()
    put = lambda n, name, v: put_field(mem, BASE, "wizard", n, name, v)
    put(1, "gold", 30000)
    put(1, "mana", 12345)
    put(1, "fame", 77)
    put(1, "books", [0, 12, 0, 3, 0])
    put(1, "retorts", [1 if i in (0, 13) else 0 for i in range(18)])
    put(1, "globals", [1 if i in (3, 18) else 0 for i in range(24)])
    put(1, "relations", [0, 70, 0, 50, -90, -81])
    put(1, "treaty_status", [0, 0, 0, 2, 3, 3])
    put(1, "spells", [2] * 50 + [1] * 8 + [3] * 6 + [0] * 150)
    put(1, "banner", 0)
    put(1, "summoning_circle", [38, 21, 1])
    put(2, "gold", 77)
    return mem


class FieldTableTest(unittest.TestCase):
    def test_every_field_fits_its_record_and_is_described(self):
        for block, b in F.blocks().items():
            seen = []
            names = set()
            for f in F.all_fields(block):
                self.assertNotIn(f.name, names, "duplicate field name")
                names.add(f.name)
                self.assertGreaterEqual(f.offset, 0)
                self.assertLessEqual(f.offset + f.size, b.stride, f"{f.name} runs past the record")
                self.assertIn(f.confidence, ("checked", "guess"))
                self.assertTrue(f.note, f"{f.name} has no note")
                if isinstance(f.labels, list):
                    self.assertEqual(len(f.labels), f.count, f"{f.name}: labels do not match the count")
                for lo, hi in seen:
                    self.assertTrue(f.offset + f.size <= lo or f.offset >= hi, f"{f.name} overlaps another field")
                seen.append((f.offset, f.offset + f.size))

    def test_ranges_fit_their_types_and_editable_fields_have_limits(self):
        limits = {"u8": (0, 255), "i8": (-128, 127), "u16": (0, 65535), "i16": (-32768, 32767)}
        for f in F.all_fields():
            if f.min is not None:
                lo, hi = limits[f.type]
                self.assertTrue(lo <= f.min <= f.max <= hi, f.name)
            if f.writable and f.type != "text":
                self.assertIsNotNone(f.min, f"{f.name} is editable but has no range")
            if f.derived:
                self.assertFalse(f.writable, f"{f.name} is derived by the game, a write would be undone")

    def test_offsets_are_the_documented_ones(self):
        """docs/reference/ram-layout.md; each was checked in the real game."""
        expected = {"name": 0x01, "fame": 0x24, "books": 0x5A, "retorts": 0x64, "research_left": 0x25A,
                    "mana": 0x25C, "researching": 0x262, "spells": 0x264, "gold": 0x356, "globals": 0x482,
                    "relations": 0x128 + 42, "treaty_status": 0x128 + 48}
        for name, offset in expected.items():
            self.assertEqual(F.find("wizard", name).offset, offset, name)
            self.assertEqual(F.find("wizard", name).confidence, "checked", name)

    def test_lookup_ignores_case_and_dashes(self):
        self.assertEqual(F.find("wizard", "Treaty-Status").name, "treaty_status")
        with self.assertRaises(F.FieldError) as caught:
            F.find("wizard", "goldd")
        self.assertIn("gold", str(caught.exception))


class DecodeTest(unittest.TestCase):
    def test_each_type_round_trips(self):
        cases = [("gold", 30000, b"\x30\x75"), ("relations", [0, 70, 0, 50, -90, -81], None),
                 ("summoning_circle", [38, -1, 1], None), ("banner", 4, b"\x04"), ("name", "Jafar", None),
                 ("books", [0, 12, 0, 3, 13], None)]
        for name, value, raw in cases:
            f = F.find("wizard", name)
            data = f.encode(value)
            self.assertEqual(len(data), f.size)
            self.assertEqual(f.decode(data), value, name)
            if raw is not None:
                self.assertEqual(data, raw)

    def test_signed_and_little_endian(self):
        self.assertEqual(F.find("wizard", "relations").decode(bytes([0, 0, 0, 0, 0xA6, 0xAF])), [0, 0, 0, 0, -90, -81])
        self.assertEqual(F.find("wizard", "gold").decode(bytes([0x75, 0x30])), 0x3075)       # 12405
        self.assertEqual(F.find("wizard", "summoning_circle").decode(bytes([38, 0, 0xFF, 0xFF, 1, 0])), [38, -1, 1])

    def test_text_stops_at_the_nul_and_must_fit(self):
        f = F.find("wizard", "name")
        self.assertEqual(f.decode(b"Jafar" + b"\0" * 15), "Jafar")
        with self.assertRaises(ValueError):
            f.encode("x" * 20)                          # no room for the NUL
        self.assertEqual(len(f.encode("x" * 19)), 20)

    def test_wrong_length_and_count_are_errors(self):
        with self.assertRaises(ValueError):
            F.find("wizard", "gold").decode(b"\x00")
        with self.assertRaises(ValueError):
            F.find("wizard", "books").encode([1, 2])

    def test_elements_by_label_or_number(self):
        books = F.find("wizard", "books")
        self.assertEqual(books.element("Sorcery"), 1)
        self.assertEqual(books.element("5"), 4)
        rel = F.find("wizard", "relations")
        self.assertEqual(rel.element("freya", ["Jafar", "Freya"]), 1)
        self.assertEqual(rel.element("neutral", ["Jafar"]), 1)
        for bad in ("sorcerer", "0", "6"):
            with self.assertRaises(F.FieldError):
                books.element(bad)
        with self.assertRaises(F.FieldError):
            F.find("wizard", "gold").element("1")


class PeekTest(unittest.TestCase):
    def setUp(self):
        self.mem = game()
        self.server = FakeDosbox(self.mem)
        self.server.__enter__()
        self.api = DosboxApi(self.server.url)
        self.addCleanup(self.server.__exit__)

    def p(self, number, spec=None, **kw):
        return peek(self.api, "wizard", number, spec, **kw)

    def test_a_number(self):
        self.assertEqual(self.p(1, "gold"), "gold = 30000")
        self.assertEqual(self.p(2, "gold"), "gold = 77")            # the second wizard's record
        self.assertEqual(self.p(1, "fame"), "fame = 77")

    def test_text_and_enums(self):
        self.assertEqual(self.p(2, "name"), "name = Freya")
        self.assertEqual(self.p(1, "banner"), "banner = 0 (blue)")

    def test_labelled_arrays_and_elements(self):
        self.assertEqual(self.p(1, "books"), "books = nature 0, sorcery 12, chaos 0, life 3, death 0")
        self.assertEqual(self.p(1, "books.sorcery"), "books.sorcery = 12")
        self.assertEqual(self.p(1, "books.4"), "books.life = 3")

    def test_flags_list_only_what_is_set(self):
        self.assertEqual(self.p(1, "retorts"), "retorts = Alchemy, Famous")
        self.assertEqual(self.p(1, "globals"), "globals = Aura of Majesty, Just Cause")
        self.assertEqual(self.p(2, "globals"), "globals = none")

    def test_relations_use_the_wizards_own_names(self):
        self.assertEqual(self.p(1, "relations"),
                         "relations = Freya 70, Sss'ra 0, Sharee 50, Tauron -90, neutral -81")
        self.assertEqual(self.p(1, "relations.freya"), "relations.Freya = 70")
        self.assertEqual(self.p(1, "relations.NEUTRAL"), "relations.neutral = -81")
        self.assertIn("Tauron war", self.p(1, "treaty_status"))
        self.assertIn("Sharee alliance", self.p(1, "treaty_status"))

    def test_a_wizard_has_no_relation_with_himself(self):
        self.assertNotIn("Jafar", self.p(1, "relations"))
        self.assertNotIn("Jafar", self.p(1, "treaty_status"))
        self.assertTrue(self.p(2, "relations").startswith("relations = Jafar "))      # others still see him
        self.assertNotIn("Freya", self.p(2, "relations"))
        data = json.loads(self.p(1, "relations", as_json=True))["fields"]["relations"]
        self.assertNotIn("Jafar", data)
        self.assertEqual(data["neutral"], -81)
        self.assertEqual(self.p(1, "relations.jafar"), "relations.Jafar = 0")        # still readable on request

    def test_the_summoning_circle_names_its_plane_and_city(self):
        self.assertEqual(self.p(1, "summoning_circle"), "summoning_circle = x 38, y 21, plane 1 (Myrror)")
        put_field(self.mem, BASE, "wizard", 2, "summoning_circle", [10, 20, 0])      # where City0 stands
        self.assertEqual(self.p(2, "summoning_circle"),
                         "summoning_circle = x 10, y 20, plane 0 (Arcanus), the city City0")

    def test_the_214_spells_are_summarised_and_one_can_be_asked_for(self):
        out = self.p(1, "spells")
        self.assertIn("50 known", out)
        self.assertIn("6 on the research list", out)
        self.assertIn("150 unknown", out)
        self.assertEqual(self.p(1, "spells.1"), "spells.1 = 2 (known)")
        self.assertEqual(self.p(1, "spells.214"), "spells.214 = 0 (unknown)")

    def test_the_whole_record(self):
        out = self.p(1)
        self.assertTrue(out.startswith("wizard 1 (Jafar)\n"))
        for f in F.all_fields("wizard"):
            self.assertIn(f"  {f.name} ", out)
        self.assertIn("  gold = 30000", out)

    def test_json(self):
        data = json.loads(self.p(1, "books", as_json=True))
        self.assertEqual(data["fields"]["books"], {"nature": 0, "sorcery": 12, "chaos": 0, "life": 3, "death": 0})
        self.assertEqual(json.loads(self.p(1, "gold", as_json=True))["fields"]["gold"], 30000)
        self.assertEqual(json.loads(self.p(1, "books.sorcery", as_json=True)), {"books": 12})
        everything = json.loads(self.p(1, as_json=True))
        self.assertEqual(everything["number"], 1)
        self.assertEqual(len(everything["fields"]), len(F.all_fields("wizard")))

    def test_mistakes_are_refused_with_the_reason(self):
        for number in (0, 6):
            with self.assertRaisesRegex(PeekError, "no wizard"):
                self.p(number, "gold")
        with self.assertRaisesRegex(PeekError, "Fields: name"):
            self.p(1, "goldd")
        with self.assertRaisesRegex(PeekError, "no element"):
            self.p(1, "books.sorcerer")
        with self.assertRaisesRegex(PeekError, "single value"):
            self.p(1, "gold.1")

    def test_peek_never_writes(self):
        before = bytes(self.mem)
        self.p(1)
        self.p(1, "relations")
        self.assertEqual(self.server.writes, [])
        self.assertEqual(bytes(self.mem), before)

    def test_it_finds_the_game_at_another_address(self):
        mem = game_memory(0x3239A)
        put_field(mem, 0x3239A, "wizard", 1, "gold", 4242)
        with FakeDosbox(mem, version="0.83.0 (7b400)") as fake:
            self.assertEqual(peek(DosboxApi(fake.url), "wizard", 1, "gold"), "gold = 4242")

    def test_no_game_is_refused_and_points_to_doctor(self):
        with FakeDosbox(game_memory(names=("", "", "", "", ""))) as fake:
            with self.assertRaisesRegex(PeekError, "mompy doctor"):
                peek(DosboxApi(fake.url), "wizard", 1, "gold")


class CliTest(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_peek_and_fields(self):
        with FakeDosbox(game()) as fake:
            code, out, err = self.run_cli("peek", "wizard", "1", "gold", "--url", fake.url)
            self.assertEqual((code, out.strip(), err), (0, "gold = 30000", ""))
            code, out, err = self.run_cli("peek", "wizard", "9", "gold", "--url", fake.url)
            self.assertEqual(code, 1)
            self.assertIn("no wizard 9", err)
            self.assertEqual(out, "")
        code, out, _ = self.run_cli("fields")
        self.assertEqual(code, 0)
        self.assertIn("treaty_status", out)
        self.assertIn("EDITABLE", out)
        self.assertEqual(out.splitlines()[0].split()[0], "BLOCK")
        code, _, err = self.run_cli("peek", "wizard", "1", "gold", "--url", "http://127.0.0.1:1")
        self.assertEqual(code, 1)
        self.assertIn("cannot reach", err)

    def test_the_fields_listing_marks_derived_and_guessed_fields(self):
        text = describe_fields("wizard")
        self.assertIn("no (derived)", next(l for l in text.splitlines() if " power_base " in l))
        self.assertIn("guess", next(l for l in text.splitlines() if " ratios " in l))


if __name__ == "__main__":
    unittest.main()
