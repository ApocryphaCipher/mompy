import re
import tomllib
import unittest
from importlib import resources
from pathlib import Path

import mompy
from mompy import cli

ROOT = Path(__file__).resolve().parent.parent
GAME_FILE = re.compile(r"\.(lbx|gam|exe|fon|bin)$", re.IGNORECASE)      # the game's own files must never be in this repository


class PackagingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    def test_the_version_is_the_same_everywhere(self):
        self.assertEqual(self.meta["project"]["version"], mompy.__version__)

    def test_a_licence_is_declared_and_shipped(self):
        project = self.meta["project"]
        self.assertEqual(project["license"], "MIT")
        self.assertEqual(project["license-files"], ["LICENSE"])
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text(encoding="utf-8"))

    def test_there_are_no_dependencies_and_python_is_3_12_or_newer(self):
        self.assertEqual(self.meta["project"]["dependencies"], [])
        self.assertEqual(self.meta["project"]["requires-python"], ">=3.12")

    def test_the_command_is_wired_to_a_real_function(self):
        target = self.meta["project"]["scripts"]["mompy"]
        self.assertEqual(target, "mompy.cli:main")
        self.assertTrue(callable(cli.main))

    def test_the_field_table_ships_with_the_package(self):
        self.assertIn("fields.toml", self.meta["tool"]["setuptools"]["package-data"]["mompy"])
        self.assertTrue(resources.files("mompy").joinpath("fields.toml").is_file())

    def test_only_the_code_and_the_field_table_are_packaged(self):
        self.assertEqual(self.meta["tool"]["setuptools"]["packages"], ["mompy"])
        shipped = {p.name for p in (ROOT / "mompy").iterdir() if p.is_file()}
        self.assertEqual({n for n in shipped if not n.endswith(".py")}, {"fields.toml"})

    def test_no_game_file_is_anywhere_in_the_repository(self):
        found = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
                 if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts and GAME_FILE.search(p.name)]
        self.assertEqual(found, [], "the game's files are copyrighted and must never be committed")
