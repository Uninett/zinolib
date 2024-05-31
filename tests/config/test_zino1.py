import unittest
from argparse import ArgumentParser


from zinolib.config.zino1 import ZinoV1Config, _parse_tcl


class ParseTclTest(unittest.TestCase):

    def test_parse_tcl_golden_path(self):
        section = "default"
        config_dict = {
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
        expected_connection = {
            "port": 8001,
            "password": "0123456789",
            "server": "example.org",
            "username": "admin",
        }
        expected_option = {
            "sort_by": '"upd-rev"',
        }
        connection, options = _parse_tcl(config_dict, section)
        self.assertEqual(expected_connection, connection)
        self.assertEqual(expected_option, options)


class ZinoV1ConfigTest(unittest.TestCase):

    example_connection = {
        "port": "8001",
        "password": "0123456789",
        "server": "example.org",
        "username": "admin",
    }

    def manually_create_config(self, connection=None):
        connection = connection or self.example_connection
        _dict = {"connections": {"default": connection}}
        return ZinoV1Config.from_dict(_dict)

    def test_manually_create_config(self):
        config = self.manually_create_config()
        self.assertEqual(config.port, 8001)

    def test_set_userauth(self):
        config = self.manually_create_config()
        self.assertEqual(config.username, "admin")
        config.set_userauth('foo', 'barfybarf')
        self.assertEqual(config.username, "foo")

    def test_update_from_args(self):
        parser = ArgumentParser()
        parser.add_argument("password")
        parser.add_argument("unknown")
        args = parser.parse_args(["x", "y"])
        config = self.manually_create_config()
        self.assertEqual(config.password, "0123456789")
        config.update_from_args(args)
        self.assertEqual(config.password, "x")
        self.assertNotIn("unknown", vars(config))
