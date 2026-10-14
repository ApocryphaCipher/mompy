import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("make_wiki", ROOT / "scripts" / "make_wiki.py")
make_wiki = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(make_wiki)

# names that exist only in the game's own spell and unit tables: never in the published tables (mompy reads them from the running game).
# Not in this list: the 24 global enchantments (Time Stop...), whose names are in the field table, and names used as examples in field notes.
GAME_NAMES = ("Earth Lore", "Spell of Mastery", "Magic Spirit", "Sky Drake", "War Bears", "Halberdiers", "Fire Elemental", "Phantom Warriors", "Storm Giant", "Disenchant Area", "Giant Spiders")


class WikiTest(unittest.TestCase):
    def test_the_pages_in_the_repository_match_the_field_table(self):
        files = make_wiki.build()
        for name, text in files.items():
            path = ROOT / "docs" / "wiki" / name
            self.assertTrue(path.is_file(), f"{name} is missing: run python3 scripts/make_wiki.py")
            self.assertEqual(path.read_text(encoding="utf-8"), text, f"{name} is out of date: run python3 scripts/make_wiki.py")
        self.assertEqual({p.name for p in (ROOT / "docs" / "wiki").glob("*.md")}, set(files))

    def test_every_field_of_every_block_is_in_its_page(self):
        from mompy import fields as F
        for title, block, _, _ in make_wiki.PAGES:
            page = make_wiki.build()[f"{title}.md"]
            for f in F.all_fields(block):
                self.assertIn(f"| `{f.name}` |", page, f"{block}.{f.name}")

    def test_the_elements_the_game_names_by_hand_are_listed_but_not_the_game_files_names(self):
        wizard = make_wiki.build()["Wizard.md"]
        for name in ("Aura of Majesty", "Alchemy", "sorcery"):
            self.assertIn(name, wizard)                              # globals, retorts and realms: already in the field table
        self.assertIn("`<spell name>`", wizard)
        for text in make_wiki.build().values():
            for secret in GAME_NAMES:
                self.assertNotIn(secret, text, f"{secret} is a name from the game's files")

    def test_check_mode_says_nothing_when_everything_is_current(self):
        self.assertEqual(make_wiki.main(["--check"]), 0)

    def test_the_wiki_copy_has_links_without_the_md_suffix(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(make_wiki.main(["--wiki-links", "--out", tmp]), 0)
            home = (Path(tmp) / "Home.md").read_text(encoding="utf-8")
        self.assertIn("[Wizard](Wizard)", home)
        self.assertNotIn(".md)", home.split("[Back to the README]")[0])
        self.assertIn("[Wizard](Wizard.md)", make_wiki.build()["Home.md"])
