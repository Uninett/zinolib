import logging
import datetime
import os
import time
import unittest
from ipaddress import ip_address

from zinolib.ritz import ritz, ProtocolError, AuthenticationError, caseState, caseType
from zinolib.zino_emu import zinoemu


ritzlog = logging.getLogger("ritz")
ritzlog.setLevel(logging.DEBUG)
ritzlog.addHandler(logging.FileHandler("test1.log"))


def executor(client):
    d = {
        "user testuser 7f53cac4ffa877616b8472d3b33a44cbba1907ad  -\r\n": ["200 ok\r\n"],
        "user auth-failure 7f53cac4ffa877616b8472d3b33a44cbba1907ad  -\r\n": [
            "500 Authentication failure\r\n"
        ],
        "user illegal-first-response 85970fa23a2f5aa06c22b60f04013fe072319ebd  -\r\n": [
            "something-gurba-happened"
        ],
        "user no_login_response 87101b4944f4200fce90f519ddae5eacffeeadf6  -\r\n": [""],
        "caseids\r\n": [
            "304 list of active cases follows, terminated with '.'\r\n",
            "32802\r\n34978\r\n.\r\n",
        ],
        "getattrs 32802\r\n": [
            "303 simple attributes follow, terminated with '.'\r\n",
            "state: working\r\nrouter: uninett-gsw2\r\ntype: bgp\r\nopened: 1524465142\r\nremote-addr: 2001:700:0:4515::5:11\r\nid: 32802\r\npeer-uptime: 0\r\nupdated: 1533116751\r\npolladdr: 127.0.0.1\r\npriority: 100\r\nbgpOS: down\r\nbgpAS: halted\r\nremote-AS: 64666\r\nlastevent: peer is admin turned off\r\n.\r\n",
        ],
        "getattrs 34978\r\n": [
            "303 simple attributes follow, terminated with '.'\r\n",
            "router: bergen-sw1\r\nstate: working\r\ntype: alarm\r\nalarm-count: 1\r\nopened: 1529156235\r\nalarm-type: yellow\r\nid: 34978\r\nupdated: 1529156235\r\npolladdr: 127.0.0.1\r\npriority: 100\r\nlastevent: alarms went from 0 to 1\r\n.\r\n",
        ],
        "getattrs 40959\r\n": [
            "303 simple attributes follow, terminated with '.'\r\n",
            "state: open\r\nrouter: oslo-gw1\r\ntype: bgp\r\nopened: 1539480952\r\nremote-addr: 193.108.152.34\r\nid: 40959\r\npeer-uptime: 503\r\nupdated: 1539485757\r\npolladdr: 128.39.0.1\r\npriority: 500\r\nbgpOS: established\r\nremote-AS: 21357\r\nbgpAS: running\r\nlastevent: peer was reset (now up)\r\n.\r\n",
        ],
        "gethist 40959\r\n": [
            "301 history follows, terminated with '.'\r\n",
            "1539480952 state change embryonic -> open (monitor)\r\n1539509123 runarb\r\n Testmelding ifra pyRitz\r\n \r\n.\r\n",
        ],
        "getlog 40959\r\n": [
            "300 log follows, terminated with '.'\r\n",
            "1539480952 oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)\r\n1539484557 oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)\r\n1539485757 oslo-gw1 peer 193.108.152.34 AS 21357 was reset (now up)\r\n.\r\n",
        ],
        "addhist 40959  -\r\n": [
            "302 please provide new history entry, termiate with '.'\r\n"
        ],
        "Testmelding ifra pyRitz\r\n\r\n.\r\n": ["200 ok\r\n"],
        "setstate 40959 open\r\n": ["200 ok\r\n"],
        "setstate 40959 working\r\n": ["200 ok\r\n"],
        "setstate 40959 waiting\r\n": ["200 ok\r\n"],
        "setstate 40959 confirm-wait\r\n": ["200 ok\r\n"],
        "setstate 40959 ignored\r\n": ["200 ok\r\n"],
        "setstate 40959 closed\r\n": ["200 ok\r\n"],
        "setstate 40960 open\r\n": ["500 Cannot reopen closed event 40960\r\n"],
        "clearflap uninett-tor-sw3 707\r\n": ["200 ok\r\n"],
        "pollrtr uninett-tor-sw3": ["200 ok\r\n"],
        "pollintf uninett-tor-sw3 707": ["200 ok\r\n"],
        "ntie 909e90c2eda89a09819ee7fe9b3f67cadb31449f\r\n": ["200 ok\r\n"],
        "ntie xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\r\n": [
            "500 Could not find your notify socket\r\n"
        ],
    }

    client.send("200 2f88fe9d496b1c1a33a8d69f5c3ff7e8c34a1069 Hello, there\r\n")
    client.executor(d)


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

    def test_D_connect_authentication_failed(self):
        with zinoemu(executor):
            r = ritz("127.0.0.1", username="auth-failure", password="test")
            with self.assertRaises(AuthenticationError):
                r.connect()
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

    def test_F_with(self):
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                self.assertTrue(sess)

    def test_G_clean_attributes(self):
        self.maxDiff = None
        with zinoemu(executor):
            with ritz("127.0.0.1", username="testuser", password="test") as sess:
                caseids = sess.get_caseids()
                self.assertTrue(32802 in caseids)
                self.assertTrue(34978 in caseids)
                self.assertFalse(999 in caseids)
                expected_result = {
                    "ac_down": None,
                    "alarm_count": None,
                    "bfddiscr": None,
                    "bfdix": None,
                    "bgpas": "halted",
                    "bgpos": "down",
                    "flaps": None,
                    "id": 32802,
                    "ifindex": None,
                    "lastevent": "peer is admin turned off",
                    "lasttrans": None,
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
                raw_attrs = sess.get_attributes(32802)
                cleaned_attrs = sess.clean_attributes(raw_attrs)
                self.assertEqual(cleaned_attrs, expected_result)

                expected_result = {
                    "ac_down": None,
                    "alarm_count": 1,
                    "bfddiscr": None,
                    "bfdix": None,
                    "flaps": None,
                    "alarm_type": "yellow",
                    "id": 34978,
                    "ifindex": None,
                    "lastevent": "alarms went from 0 to 1",
                    "lasttrans": None,
                    "peer_uptime": None,
                    "opened": datetime.datetime(2018, 6, 16, 15, 37, 15),
                    "polladdr": ip_address("127.0.0.1"),
                    "priority": 100,
                    "remote_as": None,
                    "router": "bergen-sw1",
                    "state": caseState.WORKING,
                    "type": caseType.ALARM,
                    "updated": datetime.datetime(2018, 6, 16, 15, 37, 15),
                }
                raw_attrs = sess.get_attributes(34978)
                cleaned_attrs = sess.clean_attributes(raw_attrs)
                self.assertEqual(cleaned_attrs, expected_result)

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
