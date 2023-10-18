from os import environ
from pathlib import Path


DEFAULT_XDG_CONFIG_HOME = Path.home() / '.config'
XDG_CONFIG_HOME = environ.get('XDG_CONFIG_HOME', DEFAULT_XDG_CONFIG_HOME)
VISIBLE_LOCATIONS = [XDG_CONFIG_HOME, Path('/usr/local/etc'), Path('/etc')]
INVISIBLE_LOCATIONS = [Path.cwd(), Path.home()]
CONFIG_DIRECTORIES = INVISIBLE_LOCATIONS + VISIBLE_LOCATIONS


def make_filename_safe(filename):
    return Path(filename).name


def find_config_file(filename, directories=None):
    """
    Look for filename in ``directories`` in order

    The filename is validated. Any prefixed dot is removed, any path-magic (~,
    /, .. etc.) is stripped away.

    If the file isn't found in any of them, raise FileNotFoundError
    """
    if directories is None:
        directories = CONFIG_DIRECTORIES
    tried = []
    filename = filename.lstrip('.')
    filename = make_filename_safe(filename)
    for directory in directories:
        directory = Path(directory)
        if directory in INVISIBLE_LOCATIONS:
            used_filename = f'.{filename}'
        else:
            used_filename = filename
        path = directory / used_filename
        tried.append(path)
        if path.is_file():
            return path
    tried_paths = [str(path) for path in tried]
    raise FileNotFoundError(f"Looked for config in {tried_paths}, none found")
