import unittest

from zinolib.ritz import _decode_history


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
