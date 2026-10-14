import contextlib
import io
import struct

from mompy import layout
from mompy.cli import main
from mompy.mass import ENCHANTMENTS, change, find_enchantment
from mompy.poke import PokeError, undo

from . import test_pew
from .test_summon import SummonCase, unit_at


def enchantments(mem, i):
    return struct.unpack_from("<I", mem, unit_at(i) + 24)[0]


class FindTest(SummonCase):
    def test_the_names_and_their_bits(self):
        self.assertEqual(ENCHANTMENTS["Flight"], 0x20000)
        self.assertEqual(ENCHANTMENTS["Wind Walking"], 0x10000)
        self.assertEqual(ENCHANTMENTS["Water Walking"], 0x100)
        self.assertEqual(ENCHANTMENTS["Invisibility"], 0x8000)
        self.assertEqual(ENCHANTMENTS["Immolation"], 1)
        self.assertEqual(len(ENCHANTMENTS), 32)
        self.assertEqual(len(set(ENCHANTMENTS.values())), 32)

    def test_lookup_is_forgiving_but_never_guesses(self):
        self.assertEqual(find_enchantment("mass.flight"), "Flight")
        self.assertEqual(find_enchantment("Wind_Walking"), "Wind Walking")
        self.assertEqual(find_enchantment("mass.iron"), "Iron Skin")
        self.assertEqual(find_enchantment("resist_m"), "Resist Magic")
        with self.assertRaisesRegex(PokeError, "could be Resist Elements, Resist Magic"):
            find_enchantment("resist")
        with self.assertRaisesRegex(PokeError, "no unit enchantment is called 'fly'"):
            find_enchantment("fly")
        with self.assertRaisesRegex(PokeError, "which enchantment"):
            find_enchantment("mass.")


class MassTest(SummonCase):
    stack = test_pew.PewTest.stack

    def test_a_whole_stack_gets_the_bit_and_only_the_bit(self):
        ids = self.stack(51, 22, 1, 0, 3)
        self.stack(52, 22, 1, 0, 1)
        self.mem[unit_at(ids[0]) + 24] = 0x01                          # one unit already has Immolation
        before = bytes(self.mem)
        out = change(self.api, "blackstone", "mass.flight", True)
        self.assertIn("Flight on for 3 of 3 units at Blackstone (Myrror 51, 22)", out)
        self.assertEqual([enchantments(self.mem, i) for i in ids], [0x20001, 0x20000, 0x20000])
        touched = {unit_at(i) + k for i in ids for k in range(24, 28)}
        self.assertEqual(sorted(set(self.differing(before)) - touched), [])
        self.assertEqual(enchantments(self.mem, ids[-1] + 1), 0)       # the neighbouring tile's unit is untouched

    def test_dispel_clears_only_that_bit(self):
        ids = self.stack(51, 22, 1, 0, 2)
        for i in ids:
            struct.pack_into("<I", self.mem, unit_at(i) + 24, 0x20001)
        out = change(self.api, "blackstone", "flight", False)
        self.assertEqual([enchantments(self.mem, i) for i in ids], [1, 1])
        self.assertNotIn("upkeep", out)

    def test_heroes_and_every_owner_on_the_tile_are_included(self):
        ids = self.stack(51, 22, 1, 0, 1, kind=5)                      # a hero
        change(self.api, "blackstone", "flight", True)
        self.assertEqual(enchantments(self.mem, ids[0]), 0x20000)

    def test_undo_puts_every_unit_back(self):
        self.stack(51, 22, 1, 0, 3)
        before = bytes(self.mem)
        change(self.api, "blackstone", "flight", True)
        self.assertEqual(undo(self.api), "undid: mass Flight on -> off")
        self.assertEqual(bytes(self.mem), before)

    def test_dry_run_and_already_done(self):
        self.stack(51, 22, 1, 0, 2)
        before = bytes(self.mem)
        self.assertTrue(change(self.api, "blackstone", "flight", True, dry_run=True).startswith("(dry run) would put Flight on for 2 of 2"))
        self.assertEqual(bytes(self.mem), before)
        change(self.api, "blackstone", "flight", True)
        n = len(self.server.writes)
        self.assertIn("already on for all 2 units", change(self.api, "blackstone", "flight", True))
        self.assertEqual(len(self.server.writes), n)
        self.assertIn("already off", change(self.api, "blackstone", "water_walking", False))

    def test_the_pointer_and_coordinates(self):
        ids = self.stack(51, 22, 1, 0, 2)
        test_pew.put_view(self.mem)
        change(self.api, "pointer", "flight", True)
        self.assertEqual(enchantments(self.mem, ids[0]), 0x20000)
        self.stack(10, 12, 0, 1, 1)
        self.assertIn("Arcanus (10, 12)", change(self.api, "10,12,arcanus", "invisibility", True))

    def test_refusals_write_nothing(self):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "no units at Arcanus \\(30, 30\\)"):
            change(self.api, "30,30,0", "flight", True)
        with self.assertRaisesRegex(PokeError, "no unit enchantment"):
            change(self.api, "blackstone", "fly", True)
        self.assertEqual(bytes(self.mem), before)

    def test_a_failed_write_takes_the_others_back(self):
        self.stack(51, 22, 1, 0, 3)
        before = bytes(self.mem)
        self.server.fail_write_number = 2
        with self.assertRaises(PokeError):
            change(self.api, "blackstone", "flight", True)
        self.assertEqual(bytes(self.mem), before)

    def test_the_commands(self):
        ids = self.stack(51, 22, 1, 0, 2)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["poke", "city", "blackstone", "cast", "mass.flight", "--url", self.server.url]), 0)
            self.assertEqual([enchantments(self.mem, i) for i in ids], [0x20000] * 2)
            self.assertEqual(main(["poke", "city", "blackstone", "dispel", "mass.flight", "--url", self.server.url]), 0)
            self.assertEqual([enchantments(self.mem, i) for i in ids], [0, 0])
            self.assertEqual(main(["unit", "cast", "mass.wind_walking", "--at", "blackstone", "--url", self.server.url]), 0)
            self.assertEqual(enchantments(self.mem, ids[0]), 0x10000)
            self.assertEqual(main(["unit", "dispel", "mass.wind_walking", "--at", "blackstone", "--url", self.server.url]), 0)
            self.assertEqual(main(["unit", "cast", "--url", self.server.url]), 1)
        self.assertIn("Flight on for 2 of 2", out.getvalue())
        self.assertIn("mompy unit cast mass.flight --at PLACE", err.getvalue())
