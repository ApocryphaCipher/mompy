import contextlib
import io
import json
import struct

from mompy import layout
from mompy.cli import main
from mompy.peek import PeekError, peek
from mompy.poke import PokeError, poke, undo
from mompy.where import where

from .test_summon import SummonCase

LAIR_AT = layout.ENCOUNTERS.reference
NODE_AT = layout.NODES.reference


def put_lair(mem, index, x, y, plane, kind, intact=1, guards=(), gold=0, mana=0):
    at = LAIR_AT + index * 24
    rec = bytearray(24)
    rec[0:5] = bytes([x, y, plane, intact, kind])
    for slot, (unit_type, count) in enumerate(guards):
        rec[5 + 2 * slot] = unit_type
        rec[6 + 2 * slot] = count
    struct.pack_into("<hh", rec, 10, gold, mana)
    mem[at:at + 24] = rec


def put_node(mem, index, x, y, plane, owner, kind, power=7):
    at = NODE_AT + index * 48
    rec = bytearray(48)
    rec[0:5] = bytes([x, y, plane, owner & 0xFF, power])
    rec[45] = kind
    mem[at:at + 48] = rec


class SiteCase(SummonCase):
    def setUp(self):
        super().setUp()
        for i in range(2):                                   # the plain fake game has two nodes: start from none
            self.mem[NODE_AT + i * 48:NODE_AT + i * 48 + 48] = bytes(48)
        put_node(self.mem, 3, 51, 17, 0, -1, 0)              # an unowned Sorcery node on Arcanus
        put_node(self.mem, 4, 20, 9, 1, 0, 2)                # a Chaos node on Myrror melded by wizard 1
        put_lair(self.mem, 7, 51, 17, 0, 3, guards=[(179, 0x33), (180, 0x22)])           # the Sorcery node's guardians
        put_lair(self.mem, 12, 8, 30, 1, 4, guards=[(180, 0x21)], gold=100, mana=25)     # a cave
        put_lair(self.mem, 20, 20, 9, 1, 2, intact=0, guards=[(179, 0x40)])               # cleared Chaos node guardians (kind 2 on purpose)


class PeekTest(SiteCase):
    def test_a_lair_with_its_monsters_in_words(self):
        out = peek(self.api, "lair", 12, None)
        self.assertTrue(out.startswith("lair 12 (Cave, Myrror (8, 30), not cleared)"))
        for line in ("kind = 4 (Cave)", "guard1_type = Sprites (180)", "guard1_count = 1 left of 2 (0x21)", "guard2_type = none",
                     "guard2_count = none", "gold = 100", "mana = 25", "intact = 1 (not cleared)"):
            self.assertIn("  " + line, out)

    def test_a_node_shows_its_guardians_from_the_encounter_at_its_tile(self):
        out = peek(self.api, "node", 3, None)
        self.assertTrue(out.startswith("node 3 (Sorcery, Arcanus (51, 17), nobody)"))
        self.assertIn("  owner = nobody", out)
        self.assertIn("  guardians (lair 7, not cleared): War Bears 3 of 3, Sprites 2 of 2", out)
        self.assertIn("  owner = Jafar", peek(self.api, "node", 4, None))

    def test_a_node_without_an_encounter_says_so(self):
        put_node(self.mem, 5, 1, 1, 0, -1, 1)
        self.assertIn("guardians: none recorded", peek(self.api, "node", 5, None))

    def test_empty_slots_and_numbers_out_of_range(self):
        with self.assertRaisesRegex(PeekError, "no lair 50: that slot is empty"):
            peek(self.api, "lair", 50, None)
        with self.assertRaisesRegex(PeekError, r"no lair 102 \(0 to 101\)"):
            peek(self.api, "lair", 102, None)
        with self.assertRaisesRegex(PeekError, r"no node 30 \(0 to 29\)"):
            peek(self.api, "node", 30, None)

    def test_where_names_the_node_and_the_monsters_on_a_tile(self):
        self.assertEqual(where(self.api, "51,17,arcanus"),
                         "Arcanus (51, 17)\n  Sorcery node #3, nobody's\n"
                         "  Sorcery node guardians (lair #7, not cleared): guards War Bears 3 of 3, Sprites 2 of 2")
        self.assertIn("Cave (lair #12, not cleared): guards Sprites 1 of 2; reward 100 gold, 25 mana", where(self.api, "8,30,myrror"))
        data = json.loads(where(self.api, "8,30,myrror", as_json=True))
        self.assertEqual(data["sites"][0]["guards"], [{"type": "Sprites", "left": 1, "started": 2}])
        self.assertIsNone(data["node"])


class PokeTest(SiteCase):
    def test_gold_mana_and_cleared_change_only_their_bytes(self):
        before = bytes(self.mem)
        self.assertEqual(poke(self.api, 12, "gold", "777", block_name="lair"), "lair 12 gold: 100 -> 777")
        poke(self.api, 12, "mana", "0", block_name="lair")
        poke(self.api, 12, "intact", "0", block_name="lair")
        changed = self.differing(before)
        self.assertEqual(sorted(set(changed) - {LAIR_AT + 12 * 24 + k for k in (3, 10, 11, 12, 13)}), [])
        self.assertEqual(struct.unpack_from("<h", self.mem, LAIR_AT + 12 * 24 + 10)[0], 777)

    def test_guards_by_name_and_friendly_counts(self):
        poke(self.api, 12, "guard2_type", "war_bears", block_name="lair")
        out = poke(self.api, 12, "guard2_count", "5", block_name="lair")
        self.assertEqual(out, "lair 12 guard2_count: none -> 5 left of 5 (0x55)")
        self.assertEqual(self.mem[LAIR_AT + 12 * 24 + 7:LAIR_AT + 12 * 24 + 9], bytes([179, 0x55]))
        self.assertIn("2 left of 3 (0x32)", poke(self.api, 12, "guard1_count", "2/3", block_name="lair"))
        self.assertIn("(0x44)", poke(self.api, 12, "guard1_count", "0x44", block_name="lair"))
        self.assertIn("-> none", poke(self.api, 12, "guard2_type", "none", block_name="lair"))

    def test_bad_guards_and_rewards_write_nothing(self):
        before = bytes(self.mem)
        for field, value, pattern in (("guard1_count", "3/2", "left/started"), ("guard1_count", "2/16", "left/started"),
                                      ("guard1_count", "lots", "left/started"), ("guard1_count", "256", "whole number"),
                                      ("guard1_type", "198", "whole number"), ("guard1_type", "dragon", "no unit is called"),
                                      ("gold", "30001", "whole number"), ("gold", "=-1", "whole number"),
                                      ("kind", "5", "not editable"), ("x", "5", "not editable")):
            with self.assertRaisesRegex(PokeError, pattern):
                poke(self.api, 12, field, value, block_name="lair")
        with self.assertRaisesRegex(PokeError, "Swordsmen exists for several races"):
            poke(self.api, 12, "guard1_type", "swordsmen", block_name="lair")
        self.assertEqual(bytes(self.mem), before)

    def test_a_node_owner_by_name_or_nobody(self):
        self.assertEqual(poke(self.api, 3, "owner", "freya", block_name="node"), "node 3 owner: nobody -> Freya")
        self.assertEqual(self.mem[NODE_AT + 3 * 48 + 3], 1)
        self.assertEqual(poke(self.api, 3, "owner", "nobody", block_name="node"), "node 3 owner: Freya -> nobody")
        self.assertEqual(self.mem[NODE_AT + 3 * 48 + 3], 0xFF)
        with self.assertRaisesRegex(PokeError, "whole number from -1 to 4"):
            poke(self.api, 3, "owner", "7", block_name="node")
        with self.assertRaisesRegex(PokeError, "not editable"):
            poke(self.api, 3, "type", "1", block_name="node")
        with self.assertRaisesRegex(PokeError, "only a guess"):
            poke(self.api, 3, "flags", "1", block_name="node")

    def test_undo_and_dry_run(self):
        before = bytes(self.mem)
        self.assertEqual(poke(self.api, 12, "gold", "5", dry_run=True, block_name="lair"), "(dry run) would write lair 12 gold: 100 -> 5")
        self.assertEqual(bytes(self.mem), before)
        poke(self.api, 12, "guard1_count", "4", block_name="lair")
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)

    def test_the_commands(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["poke", "lair", "12", "guard1_type", "war_bears", "--url", self.server.url]), 0)
            self.assertEqual(main(["peek", "lair", "12", "guard1_type", "--url", self.server.url]), 0)
            self.assertEqual(main(["peek", "node", "3", "--url", self.server.url]), 0)
            self.assertEqual(main(["fields", "lair"]), 0)
            self.assertEqual(main(["peek", "lair", "99", "--url", self.server.url]), 1)
        text = out.getvalue()
        self.assertIn("lair 12 guard1_type: Sprites (180) -> War Bears (179)", text)
        self.assertIn("guard1_type = War Bears (179)", text)
        self.assertIn("guardians (lair 7", text)
        self.assertIn("that slot is empty", err.getvalue())
