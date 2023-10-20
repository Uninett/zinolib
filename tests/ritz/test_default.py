import logging
import datetime
import os
import time
import unittest
from ipaddress import ip_address

from zinolib.ritz import ritz, ProtocolError, AuthenticationError, caseState, caseType
from zinolib.zino_emu import zinoemu

from ..utils import executor


class DefaultTest(unittest.TestCase):
    def setUp(self):
        self.old_timezone = os.environ.get('TZ', None)
        os.environ['TZ'] = 'Europe/Oslo'
        time.tzset()

    def tearDown(self):
        if self.old_timezone:
            os.environ['TZ'] = self.old_timezone
            time.tzset()

    def test_A_connect_imediate_disconnect(self):
        def client(client):
            pass

        with zinoemu(client):
            r = ritz("127.0.0.1", username="disconnect-on-connect", password="test")
            with self.assertRaises(ProtocolError):
                r.connect()
            r.close()

    def test_B_connect_illegal_first_response(self):
        def client(client):
            client.send("This will crash.. :)")

        with zinoemu(client):
            r = ritz(
                "127.0.0.1",
                username="illegal-first-response",
                password="illegal-first-response",
            )
            with self.assertRaises(ProtocolError):
                r.connect()
            r.close()

    def test_D_connect_authentication_failed(self):
        with zinoemu(executor):
            r = ritz("127.0.0.1", username="auth-failure", password="test")
            with self.assertRaises(AuthenticationError):
                r.connect()
            r.close()

    def test_F_with(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                self.assertTrue(sess)


    def test_G_get_attributes(self):
        self.maxDiff = None
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                caseids = sess.get_caseids()
                self.assertTrue(32802 in caseids)
                self.assertTrue(34978 in caseids)
                self.assertFalse(999 in caseids)
                expected_result = {
                    "bgpas": "halted",
                    "bgpos": "down",
                    "id": 32802,
                    "lastevent": "peer is admin turned off",
                    "opened": datetime.datetime(2018, 4, 23, 8, 32, 22),
                    "peer_uptime": 0,
                    "polladdr": ip_address("127.0.0.1"),
                    "priority": 100,
                    "remote_as": 64666,
                    "remote_addr": ip_address("2001:700:0:4515::5:11"),
                    "router": "uninett-gsw2",
                    "state": caseState.WORKING,
                    "type": caseType.BGP,
                    "updated": datetime.datetime(2018, 8, 1, 11, 45, 51),
                }
                self.assertEqual(sess.get_attributes(32802), expected_result)

                expected_result = {
                    "alarm_count": 1,
                    "alarm_type": "yellow",
                    "id": 34978,
                    "lastevent": "alarms went from 0 to 1",
                    "opened": datetime.datetime(2018, 6, 16, 15, 37, 15),
                    "polladdr": ip_address("127.0.0.1"),
                    "priority": 100,
                    "router": "bergen-sw1",
                    "state": caseState.WORKING,
                    "type": caseType.ALARM,
                    "updated": datetime.datetime(2018, 6, 16, 15, 37, 15),
                }
                self.assertEqual(sess.get_attributes(34978), expected_result)

    def test_H_get_history(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                hist = sess.get_history(40959)
                test = {
                    "date": datetime.datetime(2018, 10, 14, 3, 35, 52),
                    "header": "state change embryonic -> open (monitor)",
                    "user": "system",
                    "log": [],
                }
                self.assertEqual(hist[0], test)

                test = {
                    "date": datetime.datetime(2018, 10, 14, 11, 25, 23),
                    "header": "runarb",
                    "user": "runarb",
                    "log": ["Testmelding ifra pyRitz"],
                }
                self.assertEqual(hist[1], test)

    def test_I_add_history(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                self.assertTrue(sess.add_history(40959, "Testmelding ifra pyRitz"))

    def test_J_get_log(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                test = [
                    {
                        "user": "system",
                        "header": "oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)",
                        "date": datetime.datetime(2018, 10, 14, 3, 35, 52),
                        "log": [],
                    },
                    {
                        "user": "system",
                        "header": "oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)",
                        "date": datetime.datetime(2018, 10, 14, 4, 35, 57),
                        "log": [],
                    },
                    {
                        "user": "system",
                        "header": "oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)",
                        "date": datetime.datetime(2018, 10, 14, 4, 55, 57),
                        "log": [],
                    },
                ]
                self.assertTrue(sess.get_log(40959) == test)

    def test_K_set_state(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                self.assertTrue(sess.set_state(40959, "open"))
                self.assertTrue(sess.set_state(40959, "working"))
                self.assertTrue(sess.set_state(40959, "waiting"))
                self.assertTrue(sess.set_state(40959, "confirm-wait"))
                self.assertTrue(sess.set_state(40959, "ignored"))
                self.assertTrue(sess.set_state(40959, "closed"))
                with self.assertRaises(ValueError):
                    sess.set_state(40960, "open")

    def test_L_clear_flap(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                sess.clear_flapping("uninett-tor-sw3", 707)

    def test_M_poll_router(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                sess.poll_router("uninett-tor-sw3")

    def test_N_poll_interface(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                sess.poll_interface("uninett-tor-sw3", 707)

    def test_N_ntie(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                self.assertTrue(sess.ntie("909e90c2eda89a09819ee7fe9b3f67cadb31449f"))
                self.assertTrue(sess.ntie(b"909e90c2eda89a09819ee7fe9b3f67cadb31449f"))
                with self.assertRaises(ValueError):
                    sess.ntie(123456789)


if __name__ == "__main__":
    unittest.main()
