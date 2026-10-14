import contextlib
import io
import struct

from mompy import layout
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.pew import pew
from mompy.poke import PokeError, undo
from mompy.pointer import tile_under_pointer
from mompy.unit import mercury
from mompy.game import connect

from .test_summon import BASE, SummonCase, unit_at


def put_view(mem, pointer=(130, 119), origin=(45, 17), plane=1):
    dgroup = BASE - layout.DGROUP_BELOW_WIZARDS
    struct.pack_into("<2H", mem, dgroup + layout.POINTER_IN_DGROUP, *pointer)
    struct.pack_into("<2H", mem, dgroup + layout.VIEW_ORIGIN_IN_DGROUP, *origin)
    struct.pack_into("<H", mem, dgroup + layout.VIEW_PLANE_IN_DGROUP, plane)


class PointerTest(SummonCase):
    def tile(self, **view):
        put_view(self.mem, **view)
        return tile_under_pointer(self.api, connect(self.api))

    def test_the_tile_under_the_pointer(self):
        self.assertEqual(self.tile(), (51, 22, 1))                     # Hellgate-style check: pointer 130,119 with origin 45,17

    def test_the_map_edges_and_the_plane(self):
        self.assertEqual(self.tile(pointer=(0, 20), origin=(0, 0), plane=0), (0, 0, 0))
        self.assertEqual(self.tile(pointer=(239, 199), origin=(0, 30), plane=1), (11, 39, 1))

    def test_the_world_wraps_at_sixty_columns(self):
        self.assertEqual(self.tile(pointer=(130, 119), origin=(57, 17)), (3, 22, 1))

    def test_not_over_the_map(self):
        for pointer in ((250, 100), (100, 10), (319, 199), (0, 19)):
            with self.assertRaisesRegex(PokeError, "not over the map"):
                self.tile(pointer=pointer)

    def test_a_view_that_does_not_look_right_is_refused(self):
        with self.assertRaisesRegex(PokeError, "does not look right"):
            self.tile(plane=7)
        with self.assertRaisesRegex(PokeError, "does not look right"):
            self.tile(origin=(45, 38))                                 # rows run off the bottom of the map


class PewTest(SummonCase):
    def stack(self, x, y, plane, owner, n, kind=40):
        live = struct.unpack_from("<H", self.mem, layout.UNIT_COUNT_REFERENCE)[0]
        for i in range(n):
            at = unit_at(live + i)
            self.mem[at:at + 6] = bytes([x, y, plane, owner, 2, kind])
        struct.pack_into("<H", self.mem, layout.UNIT_COUNT_REFERENCE, live + n)
        return list(range(live, live + n))

    def test_the_units_on_a_city_tile_die_and_nothing_else_changes(self):
        ids = self.stack(51, 22, 1, 0, 3, kind=179)
        self.stack(52, 22, 1, 0, 1)                                    # a neighbour survives
        before = bytes(self.mem)
        out = pew(self.api, "blackstone")
        self.assertIn("3 killed at Blackstone (Myrror 51, 22): War Bears (Jafar), War Bears (Jafar), War Bears (Jafar)", out)
        for i in ids:
            self.assertEqual(list(self.mem[unit_at(i) + 2:unit_at(i) + 4]), [0xFF, 0xFF])
        changed = self.differing(before)
        self.assertEqual(sorted(set(changed) - {unit_at(i) + k for i in ids for k in (2, 3)}), [])
        self.assertEqual(struct.unpack_from("<H", self.mem, layout.UNIT_COUNT_REFERENCE)[0], 4 + 4)   # the count stays
        self.assertEqual(self.mem[layout.CITIES.reference], ord("B"))                                   # the city stays

    def test_undo_brings_them_back(self):
        self.stack(51, 22, 1, 0, 2)
        before = bytes(self.mem)
        pew(self.api, "blackstone")
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)

    def test_by_coordinates_and_by_pointer(self):
        self.stack(10, 12, 0, 1, 2)
        self.assertIn("2 killed at Arcanus (10, 12)", pew(self.api, "10,12,arcanus"))
        self.stack(51, 22, 1, 0, 1)
        put_view(self.mem)
        self.assertIn("1 killed at Blackstone", pew(self.api, "pointer"))

    def test_heroes_are_spared_and_a_tile_of_only_heroes_is_refused(self):
        self.stack(51, 22, 1, 0, 1, kind=179)
        hero = self.stack(51, 22, 1, 0, 1, kind=5)[0]
        out = pew(self.api, "blackstone")
        self.assertIn("1 hero spared", out)
        self.assertEqual(self.mem[unit_at(hero) + 2], 1)               # the hero is untouched
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "only heroes"):
            pew(self.api, "blackstone")
        self.assertEqual(bytes(self.mem), before)

    def test_dry_run_writes_nothing_and_an_empty_tile_is_refused(self):
        self.stack(51, 22, 1, 0, 2)
        before = bytes(self.mem)
        self.assertTrue(pew(self.api, "blackstone", dry_run=True).startswith("(dry run) would kill 2 at Blackstone"))
        self.assertEqual(bytes(self.mem), before)
        with self.assertRaisesRegex(PokeError, "no units at Arcanus \\(30, 30\\)"):
            pew(self.api, "30,30,0")

    def test_dead_units_are_not_killed_twice(self):
        self.stack(51, 22, 1, 0, 2)
        pew(self.api, "blackstone")
        with self.assertRaisesRegex(PokeError, "no units"):
            pew(self.api, "blackstone")

    def test_a_failed_write_brings_the_others_back(self):
        self.stack(51, 22, 1, 0, 3)
        before = bytes(self.mem)
        self.server.fail_write_number = 2
        with self.assertRaises(PokeError):
            pew(self.api, "blackstone")
        self.assertEqual(bytes(self.mem), before)

    def test_mercury_takes_the_pointer_too(self):
        self.stack(51, 22, 1, 0, 2)
        put_view(self.mem)
        self.assertIn("2 of 2 units to 63.5 moves", mercury(self.api, at="pointer"))

    def test_the_command(self):
        self.stack(51, 22, 1, 0, 1)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["pew", "blackstone", "--url", self.server.url]), 0)
            self.assertEqual(main(["pew", "blackstone", "--url", self.server.url]), 1)
        self.assertIn("pew! 1 killed", out.getvalue())
        self.assertIn("nudge the map view", out.getvalue())
        self.assertIn("mompy: there are no units", err.getvalue())


class WherePointerTest(SummonCase):
    def test_where_pointer_names_the_tile_city_and_units(self):
        from mompy.where import where
        PewTest.stack(self, 51, 22, 1, 0, 2, kind=179)
        put_view(self.mem)
        self.assertEqual(where(self.api, "pointer"),
                         "Myrror (51, 22)  city Blackstone, owner Jafar  2 units: War Bears (Jafar), War Bears (Jafar)")
        put_view(self.mem, pointer=(250, 100))
        from mompy.peek import PeekError
        with self.assertRaisesRegex(PeekError, "not over the map"):
            where(self.api, "pointer")
