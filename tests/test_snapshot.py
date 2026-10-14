import contextlib
import io
import json
import struct

from mompy import layout
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.snapshot import SnapshotError, diff, list_snapshots, take

from .fake_dosbox import put_field
from .test_summon import BASE, SummonCase, unit_at

DGROUP = BASE - layout.DGROUP_BELOW_WIZARDS


class SnapshotCase(SummonCase):
    def snap(self, name, **kw):
        return take(self.api, name, **kw)


class TakeTest(SnapshotCase):
    def test_a_snapshot_is_saved_and_listed(self):
        out = self.snap("before")
        self.assertIn("snapshot before: 8 regions", out)
        self.assertIn("before", list_snapshots())

    def test_the_same_name_is_refused_unless_replaced(self):
        self.snap("a")
        with self.assertRaisesRegex(SnapshotError, "already exists"):
            self.snap("a")
        self.assertIn("snapshot a", self.snap("a", replace=True))

    def test_bad_names_are_refused(self):
        for name in ("", "../x", "a b", ".hidden", "x" * 65):
            with self.assertRaisesRegex(SnapshotError, "not a snapshot name"):
                self.snap(name)

    def test_an_empty_list_says_so(self):
        self.assertIn("no snapshots yet", list_snapshots())

    def test_taking_one_writes_nothing_to_the_game(self):
        self.snap("a")
        self.assertEqual(self.server.writes, [])


class DiffTest(SnapshotCase):
    def test_identical_snapshots_have_no_differences(self):
        self.snap("a"), self.snap("b")
        self.assertEqual(diff("a", "b"), "no differences")

    def test_fields_are_named_the_aura_of_majesty_case(self):
        self.snap("before")
        put_field(self.mem, BASE, "wizard", 1, "globals", [1 if i == 3 else 0 for i in range(24)])
        put_field(self.mem, BASE, "wizard", 1, "relations", [0, 20, 0, 0, 0, 0])
        put_field(self.mem, BASE, "wizard", 2, "relations", [20, 0, 0, 0, 0, 0])
        put_field(self.mem, BASE, "wizard", 1, "gold", 777)
        self.snap("after")
        out = diff("before", "after")
        self.assertIn("wizard 1 (Jafar) globals.Aura of Majesty: 0 -> 1", out)
        self.assertIn("wizard 1 (Jafar) relations.Freya: 0 -> 20", out)
        self.assertIn("wizard 2 (Freya) relations.Jafar: 0 -> 20", out)
        self.assertIn("wizard 1 (Jafar) gold: 0 -> 777", out)
        self.assertEqual(len(out.splitlines()), 4)

    def test_units_cities_and_the_count(self):
        self.snap("a")
        self.mem[unit_at(1) + 8] = 127                                  # moves left
        struct.pack_into("<I", self.mem, unit_at(1) + 24, 0x20000)      # Flight
        self.mem[layout.CITIES.reference + 20] = 25                     # Blackstone's population
        struct.pack_into("<H", self.mem, layout.UNIT_COUNT_REFERENCE, 5)
        self.snap("b")
        out = diff("a", "b")
        self.assertIn("unit 1 (type 40) moves_left: 0 -> 127", out)
        self.assertIn("unit 1 (type 40) enchantments: 0 -> 131072", out)
        self.assertIn("city 1 (Blackstone) population: 7 -> 25", out)
        self.assertIn("unit count: 4 -> 5", out)

    def test_bytes_the_tables_do_not_name_show_as_offsets(self):
        self.snap("a")
        self.mem[layout.NODES.reference + 5] = 9
        self.snap("b")
        self.assertIn("node 0 +0x05: 00 -> 09", diff("a", "b"))

    def test_the_data_segment_shows_offsets(self):
        self.snap("a")
        struct.pack_into("<2H", self.mem, DGROUP + layout.POINTER_IN_DGROUP, 12, 34)
        self.snap("b")
        self.assertEqual(diff("a", "b"), "data segment +0x78c2: 00 -> 0c\ndata segment +0x78c4: 00 -> 22")

    def test_noise_is_left_out_when_asked(self):
        self.snap("a")
        self.mem[DGROUP + 0x1000] = 1                                   # a "timer" that ticks between any two reads
        self.snap("a2")
        self.mem[DGROUP + 0x1000] = 2
        self.mem[DGROUP + 0x2000] = 7                                   # the real change
        self.snap("b")
        out = diff("a", "b")
        self.assertIn("+0x1000", out)
        self.assertEqual(diff("a", "b", ignore_name="a2"), "data segment +0x2000: 00 -> 07")

    def test_a_long_diff_stops_at_the_limit_unless_all(self):
        self.snap("a")
        for i in range(0, 600, 2):
            self.mem[DGROUP + 0x4000 + i] = 1
        self.snap("b")
        short = diff("a", "b", limit=50)
        self.assertEqual(len(short.splitlines()), 51)
        self.assertIn("250 more lines (--all shows them)", short)
        self.assertEqual(len(diff("a", "b", show_all=True, limit=50).splitlines()), 300)

    def test_a_change_inside_a_table_is_not_also_shown_as_the_data_segment(self):
        # the 64 KiB data segment window also covers the wizard table and the unit count
        self.snap("a")
        put_field(self.mem, BASE, "wizard", 3, "mana", 99)
        struct.pack_into("<H", self.mem, layout.UNIT_COUNT_REFERENCE, 6)
        self.snap("b")
        self.assertEqual(diff("a", "b"), "wizard 3 (Sss'ra) mana: 0 -> 99\nunit count: 4 -> 6")

    def test_missing_and_damaged_snapshots_are_refused(self):
        with self.assertRaisesRegex(SnapshotError, "no snapshot called 'nope'"):
            diff("nope", "nada")
        self.snap("a")
        from mompy.snapshot import _path
        _path("a").write_text("{not json", encoding="utf-8")
        with self.assertRaisesRegex(SnapshotError, "is damaged"):
            diff("a", "a")
        _path("a").write_text(json.dumps({"regions": {"wizards": {"data": "!!!"}}}), encoding="utf-8")
        with self.assertRaisesRegex(SnapshotError, "is damaged"):
            diff("a", "a")


class CommandTest(SnapshotCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_snapshot_and_diff_through_the_command(self):
        url = ["--url", self.server.url]
        self.assertEqual(self.run_cli("snapshot", "a", *url)[0], 0)
        put_field(self.mem, BASE, "wizard", 1, "gold", 5)
        self.assertEqual(self.run_cli("snapshot", "b", *url)[0], 0)
        code, out, _ = self.run_cli("diff", "a", "b")
        self.assertEqual((code, out.strip()), (0, "wizard 1 (Jafar) gold: 0 -> 5"))
        code, out, _ = self.run_cli("snapshot", "--list", *url)
        self.assertEqual(code, 0)
        self.assertIn("a  ", out)

    def test_errors_exit_1(self):
        code, _, err = self.run_cli("snapshot", "--url", self.server.url)
        self.assertEqual(code, 1)
        self.assertIn("name the snapshot", err)
        code, _, err = self.run_cli("diff", "x", "y")
        self.assertEqual(code, 1)
        self.assertIn("no snapshot called 'x'", err)
