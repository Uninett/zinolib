import os
from pathlib import Path
from tempfile import mkstemp
from unittest import TestCase

from zinolib.config.tcl import parse_tcl_config, normalize, parse


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


def clean_config(configtext):
    config = "\n".join(line.strip() for line in configtext.split("\n"))
    return config


def make_configfile(text):
    config = clean_config(text)
    fd, filename = mkstemp(text=True, suffix=".tcl")
    os.write(fd, bytes(config, encoding="ascii"))
    return filename


def delete_configfile(filename):
    Path(filename).unlink(missing_ok=True)


class ParseTclConfigTest(TestCase):
    def test_parse_tcl_config_missing_config_file(self):
        with self.assertRaises(FileNotFoundError):
            parse_tcl_config("cvfgdh vghj vbjhk")

    def test_parse_tcl_config_empty_config_file(self):
        filename = make_configfile("")
        tcl_config_dict = parse_tcl_config(filename)
        self.assertEqual(tcl_config_dict, {})
        delete_configfile(filename)

    def test_parse_tcl_config_golden_path(self):
        filename = make_configfile(RITZ_CONFIG)
        tcl_config_dict = parse_tcl_config(filename)
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
        delete_configfile(filename)


class ParseNormalizeTest(TestCase):
    def test_normalize_empty_dict(self):
        expected = {"globals": {}, "connections": {}}
        self.assertEqual(normalize({}), expected)

    def test_normalize_golden_path(self):
        tcl_config_dict = parse(clean_config(RITZ_CONFIG))
        expected = {
            "globals": {"sort_by": '"upd-rev"'},
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
