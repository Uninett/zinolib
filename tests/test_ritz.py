import unittest

from zinolib.ritz import Case


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
