import hashlib
import unittest

from zinolib.utils import generate_authtoken


class GenerateAuthtokenTest(unittest.TestCase):

    def test_generate_authtoken(self):
        challenge = "ababp"
        password = "fillifjonka"
        expected = "84f9c302c392488f3f04f69f4c87994e10511892"
        result = generate_authtoken(challenge, password)
        self.assertEqual(expected, result)
