import contextlib
import io
import struct

from mompy import layout
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.poke import PokeError, undo
from mompy.unit import MERCURY, mercury

from .test_summon import SummonCase, unit_at


class MercuryCase(SummonCase):
    def setUp(self):
        super().setUp()
        # game_memory(units=4): units 0..3 owned by wizards 0..3 at (5+i, 7), plane 0; give each some moves left
        for i in range(4):
            self.mem[unit_at(i) + 8] = i + 1


class MercuryTest(MercuryCase):
    def test_a_wizards_units_get_the_top_value_and_nothing_else_changes(self):
        before = bytes(self.mem)
        out = mercury(self.api, wizard=1)
        self.assertEqual(out, "1 of 1 units set to 63.5 moves (wizard 1 (Jafar)'s units)")
        self.assertEqual(self.mem[unit_at(0) + 8], MERCURY)
        self.assertEqual(self.differing(before), [unit_at(0) + 8])
        self.assertEqual(self.mem[unit_at(0) + 4], before[unit_at(0) + 4])         # max moves untouched

    def test_a_stack_on_a_tile(self):
        self.fill_tile(51, 22, 1, 0, 3)
        out = mercury(self.api, at="blackstone")
        self.assertIn("3 of 3 units", out)
        self.assertEqual([self.mem[unit_at(4 + i) + 8] for i in range(3)], [MERCURY] * 3)
        self.assertEqual(self.mem[unit_at(0) + 8], 1)                              # other tiles left alone

    def test_a_dead_unit_is_not_touched(self):
        at = unit_at(0)
        self.mem[at:at + 32] = bytes([0xFF, 0xFF, 0xFF, 0xFF]) + bytes(28)
        with self.assertRaisesRegex(PokeError, "no units"):
            mercury(self.api, wizard=1)

    def test_undo_puts_every_unit_back(self):
        before = bytes(self.mem)
        self.fill_tile(51, 22, 1, 0, 2)
        mid = bytes(self.mem)
        mercury(self.api, at="51,22,1")
        undo(self.api)
        self.assertEqual(bytes(self.mem), mid)
        self.assertNotEqual(mid, before)

    def test_dry_run_and_already_full(self):
        before = bytes(self.mem)
        self.assertTrue(mercury(self.api, wizard=1, dry_run=True).startswith("(dry run) would set"))
        self.assertEqual(bytes(self.mem), before)
        mercury(self.api, wizard=1)
        self.assertIn("already have 63.5 moves, nothing written", mercury(self.api, wizard=1))

    def test_refusals(self):
        before = bytes(self.mem)
        for kwargs, pattern in (({}, "say which units"), ({"at": "x", "wizard": 1}, "say which units"),
                                ({"wizard": 6}, "no wizard 6"), ({"at": "nowhere"}, "no city called"),
                                ({"at": "30,30,0"}, "no units")):
            with self.assertRaisesRegex(PokeError, pattern):
                mercury(self.api, **kwargs)
        self.assertEqual(bytes(self.mem), before)

    def test_a_failed_write_takes_the_others_back(self):
        self.fill_tile(51, 22, 1, 0, 3)
        before = bytes(self.mem)
        self.server.fail_write_number = 3
        with self.assertRaises(PokeError):
            mercury(self.api, at="blackstone")
        self.assertEqual(bytes(self.mem), before)

    def test_the_command(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["unit", "mercury", "--wizard", "1", "--url", self.server.url]), 0)
            self.assertEqual(main(["unit", "mercury", "--url", self.server.url]), 1)
        self.assertIn("63.5 moves", out.getvalue())
        self.assertIn("mompy: say which units", err.getvalue())
