from os import environ
from pathlib import Path


DEFAULT_XDG_CONFIG_HOME = Path.home() / '.config'
XDG_CONFIG_HOME = environ.get('XDG_CONFIG_HOME', DEFAULT_XDG_CONFIG_HOME)
VISIBLE_LOCATIONS = [XDG_CONFIG_HOME, Path('/usr/local/etc'), Path('/etc')]
INVISIBLE_LOCATIONS = [Path.cwd(), Path.home()]
CONFIG_DIRECTORIES = INVISIBLE_LOCATIONS + VISIBLE_LOCATIONS


def find_config_file(filename, directories=CONFIG_DIRECTORIES):
    """
    Look for filename in ``directories`` in order

    Looks for filenames both with and without a prefixed dot.

    If the file isn't found in any of them, raise FileNotFoundError
    """
    tried = []
    if filename.startswith('.'):
        filename = filename[1:]
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
