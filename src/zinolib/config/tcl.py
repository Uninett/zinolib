from pathlib import Path
import re

from .utils import find_config_file


TCL_FILENAME = ".ritz.tcl"


def load(filename):
    """Get the contents of a .ritz.tcl config file

    .ritz.tcl is formatted as a tcl file.
    """
    path = Path(filename).expanduser()
    with path.open("r") as f:
        # normalize lineends just in case
        lines = [line.strip() for line in f.readlines()]
    text = "\n".join(lines)
    return text


def parse(text):
    """
    Parse the text of a .ritz.tcl config file

    .ritz.tcl is formatted as a tcl file.

    A config-file with the following contents:

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

    Results in the following dict:

    {
        "default": {
            "Secret": "0123456789",
            "User": "admin",
            "Server": "example.org",
            "Port": "8001",
            "Sortby": "upd-rev",
        },
        "dev-server": {
            "Secret": "0123456789",
            "User": "admin",
            "Server": "example.com",
            "Port": "8001",
        },
    }
    """
    lines = text.split("\n")
    config = {}
    for line in lines:
        match = re.fullmatch(r"\s?set _?([a-zA-Z0-9]+)(?:\((.*)\))? (.*)", line)
        if match:
            key, group, value = match.groups()
            if not group:
                group = "default"

            if group not in config:
                config[group] = {}

            config[group][key] = value
    return config


def normalize(tcl_config_dict):
    """
    Standardize on snake-case key-names and break out global options

    Usage::

        > config_dict = Normalizer.normalize(tcl_config_dict)

    A config-dict with the following contents::

        {
            "default": {
                "Secret": "0123456789",
                "User": "admin",
                "Server": "example.org",
                "Port": "8001",
                "Sortby": "upd-rev",
            },
            "dev-server": {
                "Secret": "0123456789",
                "User": "admin",
                "Server": "example.com",
                "Port": "8001",
            },
        }

    Results in a dict with the following contents::

        {
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
            "global_options": {
                "sort_by": "upd-rev",
            },
        }
    """
    KEYMAP = {"Sortby": "sort_by", "User": "username"}
    CONNECTION_KEYS = set(("username", "secret", "server", "port"))
    connections = {}
    global_options = {}
    for name in tcl_config_dict:
        connection = {}
        for key, value in tcl_config_dict[name].items():
            key = KEYMAP.get(key, key.lower())
            key = "_".join(key.split("-"))
            if key not in CONNECTION_KEYS:
                global_options[key] = value
            else:
                connection[key] = value
        name = "_".join(name.split("-"))
        connections[name] = connection
    return {"global_options": global_options, "connections": connections}


# legacy
def parse_tcl_config(filename=None):
    if filename is None:
        filename = TCL_FILENAME
    filename = find_config_file(filename)
    contents = load(filename)
    config = parse(contents)
    return config
