from os.path import expanduser
import re

TOML = False
try:
    from tomllib import load as tomlload
    TOML = True
except ImportError:
    try:
        from tomli import load as tomlload
        TOML = True
    except ImportError:
        def tomlload(*args, **kwargs):
            raise Exception("TOML library not available, TOML configuration impossible")


__all__ = [
    "parse_tcl_config",
    "parse_toml_config",
]


# def parse_tcl_config(filename: str | Path):
def parse_tcl_config(filename):
    """Parse a .ritz.tcl config file

    Used to fetch a users connection information to connect to zino
    .ritz.tcl is formatted as a tcl file.
    """
    config = {}
    with open(expanduser(filename), "r") as f:
        for line in f.readlines():
            _set = re.findall(r"^\s?set _?([a-zA-Z0-9]+)(?:\((.*)\))? (.*)$", line)
            if _set:
                group = _set[0][1] if _set[0][1] != "" else "default"
                key = _set[0][0]
                value = _set[0][2]

                if group not in config:
                    config[group] = {}

                config[group][key] = value


def parse_toml_config(filename):
    with open(expanduser(filename), "rb") as TF:
        toml = tomlload(TF)
