import contextlib
import io
import json

from mompy import layout
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.peek import PeekError
from mompy.where import where

from .fake_dosbox import FakeDosbox, HomeTestCase, game_memory, put_field

BASE = layout.REFERENCE_WIZARD_BASE


def put_city(mem, i, name, x, y, plane, owner, size=3, population=7):
    at = layout.CITIES.reference + i * layout.CITIES.stride
    mem[at:at + 14] = name.encode().ljust(14, b"\0")
    mem[at + 14:at + 21] = bytes([1, x, y, plane, owner, size, population])


def game():
    mem = game_memory(cities=0)
    put_city(mem, 0, "Blackstone", 51, 22, 1, 0)
    put_city(mem, 1, "Blackwater", 5, 6, 0, 3, size=1, population=4)
    put_city(mem, 3, "Darkmoor", 23, 25, 0, 5)         # slot 2 stays empty: stale slots are skipped
    put_field(mem, BASE, "wizard", 2, "summoning_circle", [23, 25, 0])
    put_field(mem, BASE, "wizard", 3, "summoning_circle", [1, 1, 0])
    put_field(mem, BASE, "wizard", 4, "summoning_circle", [-1, 300, 7])
    return mem


class WhereTest(HomeTestCase):
    def ask(self, text, as_json=False):
        with FakeDosbox(game()) as fake:
            return where(DosboxApi(fake.url), text, as_json)

    def test_a_city_by_any_case_and_its_owner(self):
        self.assertEqual(self.ask("blackSTONE"),
                         "Blackstone: Myrror (51, 22), owner Jafar, a size 3 of population 7")

    def test_a_unique_prefix(self):
        self.assertIn("Blackstone: Myrror (51, 22)", self.ask("blackst"))

    def test_an_ambiguous_prefix_lists_its_matches_and_guesses_nothing(self):
        out = self.ask("black")
        self.assertIn("2 names start with", out)
        self.assertIn("Blackstone", out)
        self.assertIn("Blackwater: Arcanus (5, 6), owner Sharee, a Hamlet of population 4", out)

    def test_a_whole_name_beats_longer_names(self):
        with FakeDosbox(game()) as fake:
            mem = fake.memory
            put_city(mem, 4, "Black", 9, 9, 0, 1)
            self.assertTrue(where(DosboxApi(fake.url), "black").startswith("Black: Arcanus (9, 9)"))

    def test_neutral_cities_have_an_owner(self):
        self.assertIn("owner neutral", self.ask("darkmoor"))

    def test_a_wizard_gives_the_summoning_circle_and_the_city_there(self):
        self.assertEqual(self.ask("freya"), "Freya (wizard 2): summoning circle Arcanus (23, 25), the city Darkmoor")

    def test_a_wizard_without_a_city_at_the_circle(self):
        self.assertEqual(self.ask("sss"), "Sss'ra (wizard 3): summoning circle Arcanus (1, 1)")

    def test_a_nonsense_circle_is_not_printed_as_a_place(self):
        self.assertIn("no summoning circle position that makes sense", self.ask("sharee"))

    def test_no_match_suggests_near_names(self):
        with self.assertRaisesRegex(PeekError, r"nothing is called 'blakstone'; did you mean Blackstone"):
            self.ask("blakstone")
        with self.assertRaisesRegex(PeekError, "nothing is called 'zzzz'"):
            self.ask("zzzz")

    def test_an_empty_name_is_refused(self):
        with self.assertRaisesRegex(PeekError, "say a name"):
            self.ask("  ")

    def test_json(self):
        data = json.loads(self.ask("blackstone", as_json=True))
        self.assertEqual(data, [{"kind": "city", "name": "Blackstone", "plane": "Myrror", "x": 51, "y": 22,
                                 "owner": "Jafar", "size": "size 3", "population": 7000}])
        wiz = json.loads(self.ask("freya", as_json=True))[0]
        self.assertEqual(wiz["summoning_circle"], {"plane": "Arcanus", "x": 23, "y": 25, "city": "Darkmoor"})

    def test_reading_writes_nothing(self):
        with FakeDosbox(game()) as fake:
            where(DosboxApi(fake.url), "black")
            self.assertEqual(fake.writes, [])

    def test_the_command(self):
        with FakeDosbox(game()) as fake:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(main(["where", "blackstone", "--url", fake.url]), 0)
                self.assertEqual(main(["where", "nowhere", "--url", fake.url]), 1)
            self.assertIn("Blackstone: Myrror (51, 22)", out.getvalue())
            self.assertIn("mompy: nothing is called 'nowhere'", err.getvalue())
