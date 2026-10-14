import contextlib
import io
import json
import os
import unittest
from dataclasses import replace

from mompy import fields as F
from mompy import game as gamefile
from mompy import layout, poke as poking
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.poke import PokeError, check_allowed, parse_item, poke, undo

from .fake_dosbox import FakeDosbox, HomeTestCase, game_memory, put_field

BASE = layout.REFERENCE_WIZARD_BASE


def game():
    mem = game_memory()
    put = lambda n, name, v: put_field(mem, BASE, "wizard", n, name, v)
    put(1, "gold", 8293)
    put(1, "mana", 100)
    put(1, "books", [0, 12, 0, 3, 0])
    put(1, "name", "Jafar")
    put(1, "retorts", [1] + [0] * 17)
    put(1, "relations", [0, 0, 0, 0, 0, -81])
    put(1, "treaty_status", [0, 0, 0, 0, 0, 3])
    put(1, "spells", [2] * 5 + [0] * 209)
    put(2, "relations", [0, 0, 0, 0, 0, 0])
    put(2, "treaty_status", [0, 0, 0, 0, 0, 0])
    put(1, "power_base", 1376)
    return mem


class PokeCase(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.mem = game()
        self.server = FakeDosbox(self.mem)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__)
        self.api = DosboxApi(self.server.url)

    def poke(self, number, spec, text, **kw):
        return poke(self.api, number, spec, text, **kw)

    def changed(self, before):
        """Addresses whose byte differs from the snapshot ``before``."""
        return [i for i in range(len(before)) if before[i] != self.mem[i]]

    def field_at(self, number, name, index=0):
        f = F.find("wizard", name)
        start = BASE + (number - 1) * layout.WIZARD_STRIDE + f.offset + index * (f.item_size if f.is_array else 0)
        return start, f

    def value(self, number, name, index=None):
        start, f = self.field_at(number, name, index or 0)
        if index is not None:
            return f.decode_item(bytes(self.mem[start:start + f.item_size]))
        return f.decode(bytes(self.mem[start:start + f.size]))


class WriteTest(PokeCase):
    def test_a_number_changes_only_its_own_bytes(self):
        before = bytes(self.mem)
        self.assertEqual(self.poke(1, "gold", "30000"), "gold: 8293 -> 30000")
        start, _ = self.field_at(1, "gold")
        self.assertEqual(self.changed(before), [start, start + 1])      # 8293 = 0x2065 -> 30000 = 0x7530: both bytes
        self.assertEqual(self.value(1, "gold"), 30000)

    def test_an_element_and_a_whole_array(self):
        before = bytes(self.mem)
        self.assertEqual(self.poke(1, "books.sorcery", "13"), "books.sorcery: 12 -> 13")
        self.assertEqual(len(self.changed(before)), 1)
        self.assertEqual(self.value(1, "books"), [0, 13, 0, 3, 0])
        self.poke(1, "books", "1,2,3,4,5")
        self.assertEqual(self.value(1, "books"), [1, 2, 3, 4, 5])

    def test_a_name_leaves_no_tail_of_the_old_one(self):
        self.poke(1, "name", "Al")
        start, _ = self.field_at(1, "name")
        self.assertEqual(bytes(self.mem[start:start + 20]), b"Al" + b"\0" * 18)
        self.assertEqual(self.poke(1, "name", "  Merlin the Wise  "), "name: Al -> Merlin the Wise")

    def test_flags_and_enum_words(self):
        self.poke(1, "retorts.famous", "on")
        self.assertEqual(self.value(1, "retorts", 13), 1)
        self.poke(1, "retorts.alchemy", "no")
        self.assertEqual(self.value(1, "retorts", 0), 0)
        self.poke(1, "spells.10", "known")
        self.assertEqual(self.value(1, "spells", 9), 2)
        self.poke(1, "spells.11", "on the research list")
        self.assertEqual(self.value(1, "spells", 10), 3)

    def test_unchanged_writes_nothing_and_logs_nothing(self):
        before = bytes(self.mem)
        self.assertEqual(self.poke(1, "gold", "8293"), "gold is already 8293, nothing written")
        self.assertEqual((self.server.writes, bytes(self.mem) == before), ([], True))
        self.assertEqual(poking.read_log(), ([], 0))

    def test_dry_run_writes_and_logs_nothing(self):
        before = bytes(self.mem)
        self.assertEqual(self.poke(1, "gold", "30000", dry_run=True), "(dry run) would write gold: 8293 -> 30000")
        self.assertEqual((self.server.writes, bytes(self.mem) == before), ([], True))
        self.assertEqual(poking.read_log(), ([], 0))


class RefusalTest(PokeCase):
    def refused(self, number, spec, text, pattern, **kw):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, pattern):
            self.poke(number, spec, text, **kw)
        self.assertEqual(bytes(self.mem), before, f"{spec} {text} changed memory")
        self.assertEqual(self.server.writes, [])
        self.assertEqual(poking.read_log(), ([], 0))

    def test_values_out_of_range_or_not_numbers(self):
        self.refused(1, "gold", "30001", "from 0 to 30000")
        self.refused(1, "gold", "=-1", "from 0 to 30000")
        self.refused(1, "gold", "lots", "whole number")
        self.refused(1, "gold", "1.5", "whole number")
        self.refused(1, "books.sorcery", "14", "from 0 to 13")
        self.refused(1, "relations.freya", "101", "from -100 to 100")
        self.refused(1, "retorts.famous", "2", "from 0 to 1")
        self.refused(1, "spells.5", "4", "from 0 to 3")

    def test_names(self):
        self.refused(1, "name", "x" * 20, "1 to 19")
        self.refused(1, "name", "   ", "1 to 19")
        self.refused(1, "name", "Zoë", "no accents")

    def test_unknown_things(self):
        self.refused(1, "goldd", "5", "Fields:")
        self.refused(1, "books.sorcerer", "5", "no element")
        self.refused(1, "gold.1", "5", "single value")
        self.refused(7, "gold", "5", "no wizard 7")
        self.refused(0, "gold", "5", "no wizard 0")

    def test_fields_the_game_does_not_take(self):
        self.refused(1, "power_base", "5", "worked out again")
        self.refused(1, "banner", "2", "not editable")

    def test_whole_arrays_need_the_right_count_and_the_big_ones_are_refused(self):
        self.refused(1, "books", "1,2,3", "5 comma-separated values")
        self.refused(1, "books", "1,2,3,4,15", "from 0 to 13")
        self.refused(1, "spells", ",".join(["2"] * 214), "one element at a time")
        self.refused(1, "relations", "0,0,0,0,0,0", "one element at a time")

    def test_a_wizard_has_no_relation_with_himself(self):
        self.refused(1, "relations.jafar", "10", "himself")
        self.refused(2, "treaty_status.2", "alliance", "himself")

    def test_a_guess_needs_force(self):
        guess = replace(F.find("wizard", "mana"), confidence="guess")
        with self.assertRaisesRegex(PokeError, "only a guess"):
            check_allowed(guess, force=False)
        check_allowed(guess, force=True)                  # no error
        check_allowed(F.find("wizard", "mana"), force=False)

    def test_parse_item_words(self):
        treaty = F.find("wizard", "treaty_status")
        self.assertEqual([parse_item(treaty, w) for w in ("war", "WAR", "alliance", "wizard pact", "wizard_pact",
                                                           "none", "peace", "none (peace)", "2")], [3, 3, 2, 1, 1, 0, 0, 0, 2])
        with self.assertRaises(PokeError):
            parse_item(treaty, "friendship")
        with self.assertRaises(PokeError):
            parse_item(treaty, "4")


class ServerTest(PokeCase):
    def test_the_game_changing_under_us_is_refused(self):
        self.server.race_on_write = True
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "changed gold while mompy was working"):
            self.poke(1, "gold", "30000")
        self.assertEqual(self.changed(before), [self.field_at(1, "gold")[0]])   # only the byte the fake itself changed
        self.assertEqual(poking.read_log(), ([], 0))

    def test_writes_disabled_names_the_setting(self):
        self.server.allow_writes = False
        with self.assertRaisesRegex(PokeError, "webserver_allow_writes"):
            self.poke(1, "gold", "30000")
        self.assertEqual(poking.read_log(), ([], 0))


class MirroredTest(PokeCase):
    def test_a_relation_changes_both_wizards(self):
        out = self.poke(1, "relations.freya", "70")
        self.assertEqual(out, "relations.Freya: 0 -> 70  (and Freya's view of Jafar)")
        self.assertEqual(self.value(1, "relations", 1), 70)
        self.assertEqual(self.value(2, "relations", 0), 70)
        self.poke(3, "treaty_status.jafar", "alliance")                    # from the other side
        self.assertEqual(self.value(3, "treaty_status", 0), 2)
        self.assertEqual(self.value(1, "treaty_status", 2), 2)

    def test_the_neutral_player_has_one_side(self):
        before = bytes(self.mem)
        self.poke(1, "treaty_status.neutral", "none")
        self.assertEqual(len(self.changed(before)), 1)
        self.assertEqual(self.value(1, "treaty_status", 5), 0)

    def test_if_the_second_write_fails_the_first_is_put_back(self):
        before = bytes(self.mem)
        self.server.fail_write_number = 2                                   # the first write is #1
        with self.assertRaisesRegex(PokeError, "first side was put back"):
            self.poke(1, "relations.freya", "70")
        self.assertEqual(bytes(self.mem), before)
        self.assertEqual(poking.read_log(), ([], 0))

    def test_already_equal_on_the_other_side_writes_only_one(self):
        put_field(self.mem, BASE, "wizard", 2, "relations", [70, 0, 0, 0, 0, 0])
        before = bytes(self.mem)
        self.poke(1, "relations.freya", "70")
        self.assertEqual(len(self.changed(before)), 1)
        self.assertEqual(len(poking.read_log()[0][0]["writes"]), 1)


class UndoTest(PokeCase):
    def test_undo_restores_and_removes_the_entry(self):
        before = bytes(self.mem)
        self.poke(1, "gold", "30000")
        self.assertEqual(undo(self.api), "undid: gold 30000 -> 8293")
        self.assertEqual(bytes(self.mem), before)
        self.assertEqual(poking.read_log(), ([], 0))
        self.assertEqual(undo(self.api), "nothing to undo")

    def test_two_pokes_are_undone_in_reverse_order(self):
        self.poke(1, "gold", "100")
        self.poke(1, "gold", "200")
        self.assertEqual(undo(self.api), "undid: gold 200 -> 100")
        self.assertEqual(self.value(1, "gold"), 100)
        self.assertEqual(undo(self.api), "undid: gold 100 -> 8293")
        self.assertEqual(self.value(1, "gold"), 8293)

    def test_a_mirrored_change_is_undone_on_both_sides(self):
        self.poke(1, "relations.freya", "70")
        undo(self.api)
        self.assertEqual((self.value(1, "relations", 1), self.value(2, "relations", 0)), (0, 0))

    def test_undo_refuses_when_the_game_changed_it_since(self):
        self.poke(1, "gold", "30000")
        put_field(self.mem, BASE, "wizard", 1, "gold", 5)                     # the game moved on
        with self.assertRaisesRegex(PokeError, "changed since"):
            undo(self.api)
        self.assertEqual(self.value(1, "gold"), 5)
        self.assertEqual(len(poking.read_log()[0]), 1)                        # the entry is kept

    def test_a_damaged_log_line_is_skipped(self):
        self.poke(1, "gold", "30000")
        with open(os.path.join(self.home, "undo.jsonl"), "a", encoding="utf-8") as f:
            f.write("this is not json\n")
        self.assertEqual(undo(self.api), "undid: gold 30000 -> 8293 (1 unreadable log line skipped)")

    def test_the_log_keeps_the_last_200(self):
        for n in range(205):
            self.poke(1, "gold", str(n + 1))
        entries, bad = poking.read_log()
        self.assertEqual((len(entries), bad), (poking.LOG_LIMIT, 0))
        self.assertEqual(entries[-1]["new"], "205")


class CacheTest(PokeCase):
    def full_reads(self):
        return [r for r in self.server.requests if r[0] == "GET" and r[1].endswith(f"/{16 * 1024 * 1024}")]

    def test_the_second_command_does_not_scan(self):
        from mompy.peek import peek
        peek(self.api, "wizard", 1, "gold")
        first = len(self.full_reads())
        self.assertIn(first, (1, 2))                                          # the wizards, and (once) the spell table when there is none
        peek(self.api, "wizard", 1, "gold")
        self.poke(1, "gold", "5")
        self.assertEqual(len(self.full_reads()), first)                       # remembered, confirmed by a small read
        self.assertTrue(os.path.exists(os.path.join(self.home, "cache.json")))

    def test_a_stale_or_damaged_cache_just_rescans(self):
        cache = os.path.join(self.home, "cache.json")
        with open(cache, "w", encoding="utf-8") as f:
            json.dump({self.api.url: {"base": 0x40000}}, f)                   # nothing there
        self.assertEqual(self.poke(1, "gold", "5"), "gold: 8293 -> 5")
        self.assertIn(len(self.full_reads()), (1, 2))
        with open(cache, encoding="utf-8") as f:
            self.assertEqual(json.load(f)[self.api.url]["base"], BASE)
        junk = ("{not json", "[]", json.dumps({self.api.url: "x"}), json.dumps({self.api.url: {"base": -5}}))
        for n, bad in enumerate(junk):
            with open(cache, "w", encoding="utf-8") as f:
                f.write(bad)
            self.assertEqual(self.poke(1, "gold", str(100 + n)), f"gold: {5 if n == 0 else 99 + n} -> {100 + n}")

    def test_a_cache_pointing_at_a_moved_game_is_not_trusted(self):
        gamefile._remember(self.api.url, 0x3239A)                             # a 0.83 layout, but this game is at BASE
        self.assertEqual(self.poke(1, "gold", "5"), "gold: 8293 -> 5")
        self.assertIn(len(self.full_reads()), (1, 2))


class CliTest(PokeCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv) + ["--url", self.server.url])
        return code, out.getvalue().strip(), err.getvalue().strip()

    def test_poke_dry_run_refusal_and_undo(self):
        self.assertEqual(self.run_cli("poke", "wizard", "1", "gold", "30000"), (0, "gold: 8293 -> 30000", ""))
        code, out, err = self.run_cli("poke", "wizard", "1", "gold", "30001")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("from 0 to 30000", err)
        self.assertEqual(self.run_cli("poke", "wizard", "1", "mana", "5", "--dry-run")[1], "(dry run) would write mana: 100 -> 5")
        self.assertEqual(self.value(1, "mana"), 100)
        self.assertEqual(self.run_cli("undo"), (0, "undid: gold 30000 -> 8293", ""))
        self.assertEqual(self.run_cli("undo"), (0, "nothing to undo", ""))
        self.assertEqual(self.value(1, "gold"), 8293)

    def test_unreachable_is_one_line_on_stderr(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["poke", "wizard", "1", "gold", "5", "--url", "http://127.0.0.1:1"])
        self.assertEqual((code, out.getvalue()), (1, ""))
        self.assertIn("cannot reach", err.getvalue())


if __name__ == "__main__":
    unittest.main()
