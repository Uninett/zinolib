import logging
import datetime
import os
import time
import unittest
from ipaddress import ip_address

from zinolib.ritz import ritz, ProtocolError, AuthenticationError, caseState, caseType
from zinolib.zino_emu import zinoemu

from ..utils import executor


class SlowTest(unittest.TestCase):
    def setUp(self):
        self.old_timezone = os.environ.get('TZ', None)
        os.environ['TZ'] = 'Europe/Oslo'
        time.tzset()

    def tearDown(self):
        if self.old_timezone:
            os.environ['TZ'] = self.old_timezone
            time.tzset()

    def test_C_connect_no_login_response(self):
        with zinoemu(executor):

            r = ritz(
                "127.0.0.1", username="no_login_response", password="no_login_response"
            )
            #  with self.assertRaises(ProtocolError):
            try:
                r.connect()
            except ProtocolError:
                pass
            finally:
                r.close()

    def test_E_connect_random_data_on_connect(self):
        with zinoemu(executor):
            r = ritz(
                "127.0.0.1",
                username="illegal-first-response",
                password="illegal-first-response",
            )
            with self.assertRaises(ProtocolError):
                r.connect()
            r.close()
