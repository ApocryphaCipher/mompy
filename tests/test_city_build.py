import contextlib
import io
import struct

from mompy import layout
from mompy.api import DosboxApi
from mompy.city import ENOUGH, build
from mompy.cli import main
from mompy.poke import PokeError, poke, undo

from .fake_dosbox import FakeDosbox
from .test_poke_city import CityCase


def put_production(mem, slot, item, stored=0):
    at = layout.CITIES.reference + slot * layout.CITIES.stride
    struct.pack_into("<H", mem, at + 0x1C, item)
    struct.pack_into("<H", mem, at + 0x5E, stored)


def stored_at(slot):
    return layout.CITIES.reference + slot * layout.CITIES.stride + 0x5E


class BuildTest(CityCase):
    def setUp(self):
        super().setUp()
        put_production(self.mem, 3, 29, stored=5)          # Darkmoor: a Granary, 5 stored
        put_production(self.mem, 0, 2)                      # Blackstone: Housing
        put_production(self.mem, 1, 1)                      # Blackwater: Trade Goods

    def test_it_fills_only_the_store_and_logs_it(self):
        before = bytes(self.mem)
        out = build(self.api, 4)
        self.assertIn(f"production_stored: 5 -> {ENOUGH}", out)
        self.assertIn("item 29", out)
        self.assertEqual(self.differing(before), [stored_at(3), stored_at(3) + 1])
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)

    def test_housing_and_trade_goods_have_nothing_to_finish(self):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "Housing, not a building"):
            build(self.api, 1)
        with self.assertRaisesRegex(PokeError, "Trade Goods, not a building"):
            build(self.api, 2)
        self.assertEqual(bytes(self.mem), before)

    def test_a_unit_needs_no_force(self):
        put_production(self.mem, 3, 158)
        self.assertIn("item 158", build(self.api, 4))

    def test_an_item_that_is_neither_needs_force(self):
        for item in (0, 50, 0xFFFC):
            put_production(self.mem, 3, item)
            with self.assertRaisesRegex(PokeError, "neither a building"):
                build(self.api, 4)
        self.assertIn("completes", build(self.api, 4, force=True))

    def test_already_full_and_dry_run(self):
        before = bytes(self.mem)
        self.assertIn("(dry run) would write", build(self.api, 4, dry_run=True))
        self.assertEqual(bytes(self.mem), before)
        put_production(self.mem, 3, 29, stored=ENOUGH + 1)
        self.assertIn("nothing written", build(self.api, 4))

    def test_the_command_by_name_and_a_missing_value(self):
        def run(*args):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                return main([*args, "--url", self.server.url]), out.getvalue(), err.getvalue()

        code, out, _ = run("poke", "city", "darkmoor", "build")
        self.assertEqual(code, 0)
        self.assertIn("city Darkmoor production_stored", out)
        code, _, err = run("poke", "city", "darkmoor", "population")
        self.assertEqual(code, 1)
        self.assertIn("say what to change population to", err)

    def test_the_store_alone_needs_force(self):
        with self.assertRaisesRegex(PokeError, "only a guess"):
            poke(self.api, 4, "production_stored", "50", block_name="city")
