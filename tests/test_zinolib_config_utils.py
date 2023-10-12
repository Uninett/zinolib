import os
from pathlib import Path
from tempfile import mkstemp, mkdtemp
from unittest import TestCase

from zinolib.config.utils import find_config_file


def make_file():
    fd, filename = mkstemp(dir=str(Path.cwd()))
    os.write(fd, b"")
    return filename


def delete_file(filename):
    Path(filename).unlink(missing_ok=True)


class FindConfigFileTest(TestCase):
    def test_find_config_file_missing_config_file(self):
        with self.assertRaises(FileNotFoundError):
            find_config_file("bcekjyfbu eyxxgyikyvub iysbiucbcsiu")

    def test_find_config_file_golden_path(self):
        filename = make_file()
        found_filename = find_config_file(filename)
        delete_file(filename)
        self.assertEqual(Path.cwd() / filename, found_filename)

    def test_find_config_file_unusuable_file(self):
        with self.assertRaises(FileNotFoundError):
            filename = mkdtemp(dir=str(Path.cwd()))
            found_filename = find_config_file(filename)
            delete_file(filename)
