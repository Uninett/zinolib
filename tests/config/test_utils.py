import os
from pathlib import Path
from tempfile import mkstemp, mkdtemp
from unittest import TestCase

from zinolib.config.utils import find_config_file, make_filename_safe

from ..utils import make_tmptextfile, delete_tmpfile


class MakeFilenameSafeTest(TestCase):

    def test_if_no_evil_return_input(self):
        filename = 'foo.bar.xux'
        result = make_filename_safe(filename)
        self.assertEqual(filename, result)

    def test_chop_away_path_bits(self):
        filename = '/etc/otherprogram/foo.bar.xux'
        result = make_filename_safe(filename)
        self.assertEqual(result, 'foo.bar.xux')


class FindConfigFileTest(TestCase):
    def test_find_config_file_missing_config_file(self):
        with self.assertRaises(FileNotFoundError):
            find_config_file("bcekjyfbu eyxxgyikyvub iysbiucbcsiu")

    def test_find_config_file_golden_path(self):
        filename = make_tmptextfile("", None)
        tmp_directory = Path(filename).parent
        found_filename = find_config_file(filename, directories=[tmp_directory])
        delete_tmpfile(filename)
        self.assertEqual(Path.cwd() / filename, found_filename)
