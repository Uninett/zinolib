from pathlib import Path
import unittest
from unittest.mock import patch

from zinolib.config.toml import parse_toml_config

from ..utils import make_tmptextfile, delete_tmpfile


CONFIG = """
    [connections.default]
    server = "example.org"
    port = 8001
    username = "froofroo"
    password = "fghfgh"

    [options]
    autoremove = true
"""


class ParseTomlConfig(unittest.TestCase):

    def test_parse_toml_config_missing_config_file(self):
        with self.assertRaises(FileNotFoundError):
            parse_toml_config("hghjgjh jhgjhkjk ")

    def test_parse_toml_config_empty_config_file(self):
        filename = make_tmptextfile("", suffix=".toml")
        tmp_directory = Path(filename).parent
        with patch("zinolib.config.utils.CONFIG_DIRECTORIES", [tmp_directory]):
            toml_config_dict = parse_toml_config(filename)
        self.assertEqual(toml_config_dict, {})
        delete_tmpfile(filename)

    def test_parse_toml_config_golden_path(self):
        filename = make_tmptextfile(CONFIG, ".toml")
        tmp_directory = Path(filename).parent
        with patch("zinolib.config.utils.CONFIG_DIRECTORIES", [tmp_directory]):
            toml_config_dict = parse_toml_config(filename)
        expected = {
           "connections": {
               "default": {
                   "port": 8001,
                   "password": "fghfgh",
                   "server": "example.org",
                   "username": "froofroo",
               },
           },
           "options": {
               "autoremove": True,
           },
        }
        self.assertEqual(toml_config_dict, expected)
        delete_tmpfile(filename)
