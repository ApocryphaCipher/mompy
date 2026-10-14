import contextlib
import io

from mompy import layout
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.peek import PeekError, peek
from mompy.poke import PokeError, poke, undo
from mompy.where import find_city

from .fake_dosbox import FakeDosbox, HomeTestCase, game_memory
from .test_where import put_city


def population_at(slot):
    return layout.CITIES.reference + slot * layout.CITIES.stride + 20


class CityCase(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.mem = game_memory(cities=0)
        put_city(self.mem, 0, "Blackstone", 51, 22, 1, 0)
        put_city(self.mem, 1, "Blackwater", 5, 6, 0, 3, population=4)
        put_city(self.mem, 3, "Darkmoor", 39, 20, 1, 2, population=4)      # slot 2 is empty
        self.server = FakeDosbox(self.mem)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__)
        self.api = DosboxApi(self.server.url)

    def differing(self, before):
        return [i for i in range(len(before)) if before[i] != self.mem[i]]


class FindCityTest(CityCase):
    def test_by_name_prefix_and_number(self):
        self.assertEqual(find_city(self.api, "Darkmoor"), 4)
        self.assertEqual(find_city(self.api, "dark"), 4)
        self.assertEqual(find_city(self.api, "blackstone"), 1)
        self.assertEqual(find_city(self.api, "2"), 2)

    def test_ambiguous_and_unknown_are_refused(self):
        with self.assertRaisesRegex(PeekError, "could be Blackstone, Blackwater"):
            find_city(self.api, "black")
        with self.assertRaisesRegex(PeekError, "no city called 'nowhere'"):
            find_city(self.api, "nowhere")


class PokeCityTest(CityCase):
    def test_population_changes_only_that_byte_and_is_labelled_by_name(self):
        before = bytes(self.mem)
        self.assertEqual(poke(self.api, 4, "population", "25", block_name="city"),
                         "city Darkmoor population: 4 -> 25")
        self.assertEqual(self.differing(before), [population_at(3)])
        self.assertEqual(self.mem[population_at(3)], 25)

    def test_undo_puts_it_back(self):
        before = bytes(self.mem)
        poke(self.api, 4, "population", "25", block_name="city")
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)

    def test_out_of_range_is_refused_and_nothing_is_written(self):
        before = bytes(self.mem)
        for bad in ("0", "26", "-1", "lots"):
            with self.assertRaises(PokeError, msg=bad):
                poke(self.api, 4, "population", bad, block_name="city")
        self.assertEqual(bytes(self.mem), before)

    def test_read_only_fields_are_refused(self):
        for name in ("owner", "x", "name"):
            with self.assertRaisesRegex(PokeError, "not editable"):
                poke(self.api, 4, name, "1", block_name="city")

    def test_an_empty_slot_is_refused(self):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PeekError, "no city in slot 3"):
            poke(self.api, 3, "population", "5", block_name="city")
        self.assertEqual(bytes(self.mem), before)

    def test_a_slot_outside_the_table_is_refused(self):
        with self.assertRaisesRegex(PokeError, "there is no city 101"):
            poke(self.api, 101, "population", "5", block_name="city")

    def test_dry_run_writes_nothing(self):
        before = bytes(self.mem)
        out = poke(self.api, 4, "population", "9", dry_run=True, block_name="city")
        self.assertEqual(out, "(dry run) would write city Darkmoor population: 4 -> 9")
        self.assertEqual(bytes(self.mem), before)

    def test_same_value_is_not_written(self):
        self.assertIn("already 4", poke(self.api, 4, "population", "4", block_name="city"))
        self.assertEqual(self.server.writes, [])


class CityCommandTest(CityCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([*args, "--url", self.server.url])
        return code, out.getvalue(), err.getvalue()

    def test_poke_and_peek_a_city_by_name(self):
        code, out, _ = self.run_cli("poke", "city", "darkmoor", "population", "25")
        self.assertEqual((code, out.strip()), (0, "city Darkmoor population: 4 -> 25"))
        code, out, _ = self.run_cli("peek", "city", "darkmoor", "population")
        self.assertEqual((code, out.strip()), (0, "population = 25"))

    def test_peek_the_whole_record(self):
        out = peek(self.api, "city", 4, None)
        self.assertIn("city 4 (Darkmoor)", out)
        self.assertIn("plane = 1 (Myrror)", out)

    def test_an_ambiguous_name_exits_1(self):
        code, _, err = self.run_cli("poke", "city", "black", "population", "5")
        self.assertEqual(code, 1)
        self.assertIn("mompy: 'black' could be", err)

    def test_a_wizard_can_be_named_but_an_unknown_name_is_refused(self):
        self.assertEqual(self.run_cli("peek", "wizard", "freya", "gold")[0], 0)
        code, _, err = self.run_cli("peek", "wizard", "zed", "gold")
        self.assertEqual(code, 1)
        self.assertIn("'zed' is not a wizard here", err)


class RunAsScriptTest(CityCase):
    def test_python_mompy_without_dash_m_works_too(self):
        import subprocess
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        done = subprocess.run([sys.executable, "-W", "error", str(root / "mompy"), "peek", "city", "darkmoor", "population",
                               "--url", self.server.url], capture_output=True, text=True, timeout=60)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "population = 4"), done.stderr)
