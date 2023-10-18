import os
from pathlib import Path
from tempfile import mkstemp, mkdtemp
from unittest import TestCase

from zinolib.config.utils import find_config_file

from .utils import make_tmptextfile, delete_tmpfile


class FindConfigFileTest(TestCase):
    def test_find_config_file_missing_config_file(self):
        with self.assertRaises(FileNotFoundError):
            find_config_file("bcekjyfbu eyxxgyikyvub iysbiucbcsiu")

    def test_find_config_file_golden_path(self):
        filename = make_tmptextfile("", None)
        found_filename = find_config_file(filename)
        delete_tmpfile(filename)
        self.assertEqual(Path.cwd() / filename, found_filename)
