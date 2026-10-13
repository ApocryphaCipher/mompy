import contextlib
import io
import unittest

from mompy import fields as F
from mompy import layout, poke as poking
from mompy.api import DosboxApi
from mompy.banish import banish, unbanish
from mompy.cli import main
from mompy.peek import peek
from mompy.poke import PokeError, poke, undo

from .fake_dosbox import FakeDosbox, HomeTestCase, game_memory

BASE = layout.REFERENCE_WIZARD_BASE


def active_at(number):
    """Where wizard ``number``'s fortress ``active`` byte sits in the fake game."""
    return layout.FORTRESSES.reference + (number - 1) * layout.FORTRESSES.stride + 3


class BanishCase(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.mem = game_memory()
        self.server = FakeDosbox(self.mem)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__)
        self.api = DosboxApi(self.server.url)

    def differing(self, before):
        return [i for i in range(len(before)) if before[i] != self.mem[i]]


class BanishTest(BanishCase):
    def test_banish_changes_only_the_active_byte(self):
        before = bytes(self.mem)
        self.assertEqual(banish(self.api, 3), "wizard 3 (Sss'ra) is banished")
        self.assertEqual(self.differing(before), [active_at(3)])
        self.assertEqual(self.mem[active_at(3)], 0)
        self.assertEqual(self.mem[active_at(2)], 1)                  # the neighbours are untouched

    def test_unbanish_gives_it_back(self):
        banish(self.api, 3)
        before = bytes(self.mem)
        self.assertEqual(unbanish(self.api, 3), "wizard 3 (Sss'ra): banishment lifted")
        self.assertEqual(self.differing(before), [active_at(3)])
        self.assertEqual(self.mem[active_at(3)], 1)

    def test_nothing_to_do_writes_nothing(self):
        before = bytes(self.mem)
        self.assertEqual(unbanish(self.api, 3), "wizard 3 (Sss'ra) is not banished")
        banish(self.api, 3)
        n = len(self.server.writes)
        self.assertEqual(banish(self.api, 3), "wizard 3 (Sss'ra) is already banished")
        self.assertEqual(len(self.server.writes), n)
        self.assertEqual(len(poking.read_log()[0]), 1)               # only the one real change was logged
        self.assertNotEqual(bytes(self.mem), before)

    def test_the_player_needs_force(self):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "is you"):
            banish(self.api, 1)
        self.assertEqual(bytes(self.mem), before)
        self.assertEqual(banish(self.api, 1, force=True), "wizard 1 (Jafar) is banished")
        self.assertEqual(self.mem[active_at(1)], 0)
        unbanish(self.api, 1)                                         # giving it back never needs force
        self.assertEqual(self.mem[active_at(1)], 1)

    def test_only_wizards_one_to_five(self):
        before = bytes(self.mem)
        for number in (0, 6, 9, -1):
            with self.assertRaisesRegex(PokeError, "no wizard"):
                banish(self.api, number)
        self.assertEqual(bytes(self.mem), before)

    def test_dry_run_writes_and_logs_nothing(self):
        before = bytes(self.mem)
        self.assertEqual(banish(self.api, 3, dry_run=True), "(dry run) would banish wizard 3 (Sss'ra)")
        banish(self.api, 3)
        self.assertEqual(unbanish(self.api, 3, dry_run=True), "(dry run) would lift the banishment of wizard 3 (Sss'ra)")
        self.assertEqual(self.mem[active_at(3)], 0)
        self.assertEqual(self.differing(before), [active_at(3)])
        self.assertEqual(len(poking.read_log()[0]), 1)

    def test_a_fortress_table_that_does_not_look_right_is_not_written(self):
        self.mem[layout.FORTRESSES.reference + 8] = 200               # wizard 3's x: off the map
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "fortress table does not look right"):
            banish(self.api, 2)
        self.assertEqual(bytes(self.mem), before)
        self.assertEqual(self.server.writes, [])

    def test_writes_disabled_names_the_setting(self):
        self.server.allow_writes = False
        with self.assertRaisesRegex(PokeError, "webserver_allow_writes"):
            banish(self.api, 3)

    def test_the_game_changing_under_us_is_refused(self):
        self.server.race_on_write = True
        with self.assertRaisesRegex(PokeError, "changed fortress 3 active while mompy was working"):
            banish(self.api, 3)

    def test_undo_brings_the_wizard_back(self):
        banish(self.api, 3)
        self.assertEqual(undo(self.api), "undid: fortress 3 active banished -> in place")
        self.assertEqual(self.mem[active_at(3)], 1)


class FortressBlockTest(BanishCase):
    def test_peek_the_fortress_table(self):
        out = peek(self.api, "fortress", 3, None)
        self.assertTrue(out.startswith("fortress 3 (Sss'ra)\n"))
        self.assertIn("  x = 20", out)
        self.assertIn("  plane = 0 (Arcanus)", out)
        self.assertIn("  active = 1 (in place)", out)
        self.assertIn("fortress 6\n", peek(self.api, "fortress", 6, None))        # the neutral player's, no name
        banish(self.api, 3)
        self.assertEqual(peek(self.api, "fortress", 3, "active"), "active = 0 (banished)")

    def test_poke_only_takes_the_one_field_the_game_accepts(self):
        for spec, text, pattern in (("x", "5", "not editable"), ("plane", "1", "not editable"), ("active", "2", "from 0 to 1")):
            before = bytes(self.mem)
            with self.assertRaisesRegex(PokeError, pattern):
                poke(self.api, 3, spec, text, block_name="fortress")
            self.assertEqual(bytes(self.mem), before)
        self.assertEqual(poke(self.api, 3, "active", "banished", block_name="fortress"), "fortress 3 active: in place -> banished")
        self.assertEqual(poke(self.api, 6, "active", "0", block_name="fortress"), "fortress 6 active: in place -> banished")   # the neutral record, by poke

    def test_the_block_points_at_a_layout_table_and_fits(self):
        block = F.blocks()["fortress"]
        self.assertEqual((block.stride, block.count), (layout.FORTRESSES.stride, layout.FORTRESSES.count))
        self.assertEqual(layout.table(block.table), layout.FORTRESSES)
        self.assertEqual(layout.FORTRESSES.offset, 0x865C0 - 0x328BA)
        for f in F.all_fields("fortress"):
            self.assertLessEqual(f.offset + f.size, block.stride)
        with self.assertRaises(KeyError):
            layout.table("no such table")


class CliTest(BanishCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv) + ["--url", self.server.url])
        return code, out.getvalue().strip(), err.getvalue().strip()

    def test_banish_and_unbanish(self):
        self.assertEqual(self.run_cli("banish", "wizard", "3"), (0, "wizard 3 (Sss'ra) is banished", ""))
        self.assertEqual(self.run_cli("unbanish", "wizard", "3"), (0, "wizard 3 (Sss'ra): banishment lifted", ""))
        code, out, err = self.run_cli("banish", "wizard", "1")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("--force", err)
        self.assertEqual(self.run_cli("banish", "wizard", "1", "--force", "--dry-run"),
                         (0, "(dry run) would banish wizard 1 (Jafar)", ""))
        self.assertEqual(self.run_cli("peek", "fortress", "3", "active"), (0, "active = 1 (in place)", ""))
        self.assertEqual(self.run_cli("poke", "fortress", "3", "active", "0")[1], "fortress 3 active: in place -> banished")


if __name__ == "__main__":
    unittest.main()
