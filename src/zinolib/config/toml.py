"""
Expected format of toml-file::

    [connections.default]
    server = "SERVERNAME"
    port = PORT
    username = "SOMEUSERNAME"  # [A-Za-z][A-Za-z0-9]+
    password = "PASSWORD"

    [options]
    timeout = 30
    autoremove = false

This is parsed into a dict of the format::

    {
        "connections": {
            "default": {
                "server": "SERVERNAME",
                "port: PORT,
                "username": "SOMEUSERNAME"
                "password": "PASSWORD"
            },
        },
        "options": {
            "timeout": 30,
            "autoremove": False,
        },
    }
"""

from zinolib.compat import tomlload
from zinolib.config.utils import find_config_file


def parse_toml_config(filename=None):
    full_filename = find_config_file(filename)
    if full_filename:
        with open(full_filename, "rb") as TF:
            toml = tomlload(TF)
            return toml
