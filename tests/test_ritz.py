import unittest

from zinolib.ritz import Case, _decode_history


class CaseTest(unittest.TestCase):
    class FakeZino:
        def __init__(self, attrs=None):
            if attrs:
                self.attrs = attrs
            else:
                self.attrs = {}

        def get_attributes(self, caseid):
            return self.attrs

    def test_golden_path_attribute_access(self):
        zino = self.FakeZino({'foo': 'bar'})
        case = Case(zino, 1)
        self.assertTrue(case._attrs)
        self.assertEqual(case.foo, 'bar')

    def test_accessing_missing_attribute_should_fail_with_extra_info(self):
        zino = self.FakeZino({'foo': 'bar'})
        case = Case(zino, 1)
        expected_msg = "<class 'zinolib.ritz.Case'>(1) of type UNKNOWN has no attribute 'xux'"
        with self.assertRaises(AttributeError) as cm:
            case.xux
        self.assertEqual(cm.exception.args[0], expected_msg)


class DecodeHistoryTest(unittest.TestCase):
    def test_when_entry_does_not_end_in_empty_line_it_should_not_be_ignored(self):
        raw_history = [
            "1753277115 state change embryonic -> open (monitor)",
            "1753277215 ford",
            " the world's about to end",
            "1753277415 ford",
            " time is an illusion,",
            " lunchtime doubly so",
            " ",
        ]
        history = _decode_history(raw_history)
        self.assertEquals(len(history), 3, "Should have decoded 3 history entries")

    def test_when_entry_contains_empty_lines_it_should_not_be_duplicated(self):
        raw_history = [
            "1753277415 ford",
            " time is an illusion,",
            " ",
            " lunchtime doubly so",
            " ",
        ]
        history = _decode_history(raw_history)
        self.assertEquals(len(history), 1, "Should have decoded only 1 history entry")
