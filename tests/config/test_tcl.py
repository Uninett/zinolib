from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from zinolib.config.tcl import parse_tcl_config, normalize, parse

from ..utils import clean_textfile, make_tmptextfile, delete_tmpfile


RITZ_CONFIG = """
    set Secret 0123456789
    set User admin
    set Server example.org
    set Port 8001

    global Sortby
    set Sortby "upd-rev"

    set _Secret(dev-server) 0123456789
    set _User(dev-server) admin
    set _Server(dev-server) example.com
    set _Port(dev-server) 8001
"""


class ParseTclConfigTest(TestCase):
    def test_parse_tcl_config_missing_config_file(self):
        with self.assertRaises(FileNotFoundError):
            parse_tcl_config("cvfgdh vghj vbjhk")

    def test_parse_tcl_config_empty_config_file(self):
        filename = make_tmptextfile("", suffix=".tcl")
        tmp_directory = Path(filename).parent
        with patch("zinolib.config.utils.CONFIG_DIRECTORIES", [tmp_directory]):
            tcl_config_dict = parse_tcl_config(filename)
        delete_tmpfile(filename)
        self.assertEqual(tcl_config_dict, {})

    def test_parse_tcl_config_golden_path(self):
        filename = make_tmptextfile(RITZ_CONFIG, suffix=".tcl")
        tmp_directory = Path(filename).parent
        with patch("zinolib.config.utils.CONFIG_DIRECTORIES", [tmp_directory]):
            tcl_config_dict = parse_tcl_config(filename)
        delete_tmpfile(filename)
        expected = {
            "default": {
                "Port": "8001",
                "Secret": "0123456789",
                "Server": "example.org",
                "Sortby": '"upd-rev"',
                "User": "admin",
            },
            "dev-server": {
                "Port": "8001",
                "Secret": "0123456789",
                "Server": "example.com",
                "User": "admin",
            },
        }
        self.assertEqual(tcl_config_dict, expected)


class ParseNormalizeTest(TestCase):
    def test_normalize_empty_dict(self):
        expected = {"global_options": {}, "connections": {}}
        self.assertEqual(normalize({}), expected)

    def test_normalize_golden_path(self):
        tcl_config_dict = parse(clean_textfile(RITZ_CONFIG))
        expected = {
            "global_options": {"sort_by": '"upd-rev"'},
            "connections": {
                "default": {
                    "secret": "0123456789",
                    "username": "admin",
                    "server": "example.org",
                    "port": "8001",
                },
                "dev_server": {
                    "secret": "0123456789",
                    "username": "admin",
                    "server": "example.com",
                    "port": "8001",
                },
            },
        }
        self.assertEqual(normalize(tcl_config_dict), expected)
