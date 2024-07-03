import unittest
from datetime import datetime, timedelta, timezone

from zinolib.event_types import AdmState, Event, HistoryEntry, LogEntry
from zinolib.controllers.zino1 import EventAdapter, HistoryAdapter, LogAdapter, SessionAdapter, Zino1EventManager, UpdateHandler
from zinolib.controllers.zino1 import RetryError, NotConnectedError
from zinolib.ritz import NotifierResponse

raw_event_id = 139110
raw_attrlist = [
    'state: ignored',
    'router: uninett-tor-sw4',
    'descr: local MC-LAG, tor-sw4.har-04.p.uninett.no',
    'type: portstate',
    'opened: 1677714463',
    'lasttrans: 1686584585',
    'id: 139110',
    'port: ae24',
    'flaps: 1',
    'updated: 1686584585',
    'ac-down: 352952',
    'priority: 100',
    'polladdr: 158.38.129.42',
    'portstate: up',
    'ifindex: 654',
]
raw_history = [
    '1678273372 state change embryonic -> open (monitor)',
    '1678276375 someuser',
    ' manually recorded history message ',
    ' ',
    '1678276378 state change open -> waiting (someuser)',
    '1680265996 someotheruser',
    ' other manually recorded history message ',
    ' ',
    '1680266003 state change waiting -> working (someotheruser)'
]
raw_log = [
    '1683159556 some log message',
    '1683218672 some other log message',
]


class FakeEventAdapter:
    @staticmethod
    def get_attrlist(request, event_id: int):
        return raw_attrlist.copy()

    @classmethod
    def attrlist_to_attrdict(cls, attrlist):
        return EventAdapter.attrlist_to_attrdict(attrlist)

    @staticmethod
    def validate_raw_attrlist(attrlist):
        return True

    @classmethod
    def convert_values(cls, attrdict):
        return EventAdapter.convert_values(attrdict)

    @staticmethod
    def get_event_ids(request):
        return [raw_event_id]


class FakeHistoryAdapter(HistoryAdapter):
    @staticmethod
    def get_history(request, event_id: int):
        return raw_history.copy()


class FakeLogAdapter(LogAdapter):
    @staticmethod
    def get_log(request, event_id: int):
        return raw_log.copy()


class FakeSessionAdapter(SessionAdapter):

    @classmethod
    def _setup_config(cls, config):
        pass

    @staticmethod
    def _setup_request(session, config):
        class FakeSession:
            authenticated = True
            connected = True

        session.request = FakeSession()  # needs to be truthy
        session.push = True  # needs to be truthy
        return session


class FakeZino1EventManager(Zino1EventManager):
    _event_adapter = FakeEventAdapter
    _history_adapter = FakeHistoryAdapter
    _log_adapter = FakeLogAdapter
    _session_adapter = FakeSessionAdapter

    def __init__(self, session=None):
        super().__init__(session)


class Zino1EventManagerTest(unittest.TestCase):

    def init_manager(self):
        zino1 = FakeZino1EventManager.configure(None)
        return zino1

    def test_verify_session_raises_notconnectederror_on_incorrect_manager(self):
        zino1 = FakeZino1EventManager()
        with self.assertRaises(NotConnectedError) as e:
            zino1._verify_session()
            self.assertIn("The request socket have not been set up correctly", e)

    def test_verify_session_raises_notconnectederror_if_not_connected(self):
        zino1 = FakeZino1EventManager.configure(None)
        orig = zino1.session.request.connected
        zino1.session.request.connected = False
        try:
            with self.assertRaises(NotConnectedError) as e:
                zino1._verify_session()
                self.assertIn("Authentication necessary", e)
        finally:
            zino1.session.request.connected = orig

    def test_verify_session_returns_False_if_quieted_on_incorrect_manager(self):
        zino1 = FakeZino1EventManager()
        result = zino1._verify_session(quiet=True)
        self.assertEqual(result, False)

    def test_create_event_from_id_receiving_garbage_admstate_is_safely_handled(self):
        global raw_attrlist
        zino1 = self.init_manager()
        good_attrlist = raw_attrlist[:] # copy
        try:
            raw_attrlist[0] = "state: garbage admstate"
            event = zino1.create_event_from_id(139110)
            self.assertEqual(event.adm_state, AdmState.UNKNOWN)
        finally:
            # reset to known good attrlist for other tests
            raw_attrlist = good_attrlist

    def test_create_event_from_id_may_get_garabage_data(self):
        def falsey(_):
            return False

        zino1 = self.init_manager()
        old = zino1._event_adapter.validate_raw_attrlist
        zino1._event_adapter.validate_raw_attrlist = staticmethod(falsey)
        with self.assertRaises(RetryError):
            zino1.create_event_from_id(139110)
        zino1._event_adapter.validate_raw_attrlist = old

    def test_get_events(self):
        zino1 = self.init_manager()
        self.assertEqual(len(zino1.events), 0)
        zino1.get_events()
        self.assertEqual(len(zino1.events), 1)
        self.assertIn(raw_event_id, zino1.events)
        self.assertEqual(zino1.events[raw_event_id].id, raw_event_id)

    def test_get_history_for_id(self):
        zino1 = self.init_manager()
        history_list = zino1.get_history_for_id(4567)
        expected_history_list = [
            HistoryEntry(
                log='state change embryonic -> open (monitor)',
                date=datetime(2023, 3, 8, 11, 2, 52, tzinfo=timezone.utc),
                user='monitor'),
            HistoryEntry(
                log='manually recorded history message',
                date=datetime(2023, 3, 8, 11, 52, 55, tzinfo=timezone.utc),
                user='someuser'),
            HistoryEntry(
                log='state change open -> waiting (someuser)',
                date=datetime(2023, 3, 8, 11, 52, 58, tzinfo=timezone.utc),
                user='monitor'),
            HistoryEntry(
                log='other manually recorded history message',
                date=datetime(2023, 3, 31, 12, 33, 16, tzinfo=timezone.utc),
                user='someotheruser'),
            HistoryEntry(
                log='state change waiting -> working (someotheruser)',
                date=datetime(2023, 3, 31, 12, 33, 23, tzinfo=timezone.utc),
                user='monitor')
        ]
        self.assertEqual(history_list, expected_history_list)

    def test_get_log_for_id(self):
        zino1 = self.init_manager()
        log_list = zino1.get_log_for_id(4567)
        expected_log_list = [
            LogEntry(
                date=datetime(2023, 5, 4, 0, 19, 16, tzinfo=timezone.utc),
                log='some log message'),
            LogEntry(
                date=datetime(2023, 5, 4, 16, 44, 32, tzinfo=timezone.utc),
                log='some other log message')
        ]
        self.assertEqual(log_list, expected_log_list)


class UpdateHandlerTest(unittest.TestCase):

    def init_manager(self):
        zino1 = FakeZino1EventManager.configure(None)
        return zino1

    def test_cmd_scavenged(self):
        zino1 = self.init_manager()
        zino1.get_events()
        self.assertIn(raw_event_id, zino1.events)
        self.assertNotIn(raw_event_id, zino1.removed_ids)
        updates = UpdateHandler(zino1)
        update = NotifierResponse(raw_event_id, "","")
        ok = updates.cmd_scavenged(update)
        self.assertTrue(ok)
        self.assertNotIn(raw_event_id, zino1.events)
        self.assertIn(raw_event_id, zino1.removed_ids)

    def test_cmd_attr(self):
        zino1 = self.init_manager()
        zino1.get_events()
        old_events = zino1.events.copy()
        old_events[raw_event_id].priority = 500
        updates = UpdateHandler(zino1)
        update = NotifierResponse(raw_event_id, "","")
        ok = updates.cmd_attr(update)
        self.assertTrue(ok)
        self.assertNotEqual(zino1.events[raw_event_id].priority, old_events[raw_event_id].priority)

    def test_cmd_state_is_closed_and_autoremove_is_on(self):
        zino1 = self.init_manager()
        zino1.get_events()
        self.assertNotIn(raw_event_id, zino1.removed_ids)
        self.assertIn(raw_event_id, zino1.events)
        updates = UpdateHandler(zino1, autoremove=True)
        update = NotifierResponse(raw_event_id, "", "X closed")
        ok = updates.cmd_state(update)
        self.assertTrue(ok)
        self.assertIn(raw_event_id, zino1.removed_ids)
        self.assertNotIn(raw_event_id, zino1.events)

    def test_cmd_state_is_closed_and_autoremove_is_off(self):
        zino1 = self.init_manager()
        zino1.get_events()
        old_events = zino1.events.copy()
        old_events[raw_event_id].priority = 500
        updates = UpdateHandler(zino1, autoremove=False)
        update = NotifierResponse(raw_event_id, "","X closed")
        ok = updates.cmd_state(update)
        self.assertTrue(ok)
        self.assertNotEqual(zino1.events[raw_event_id].priority, old_events[raw_event_id].priority)

    def test_cmd_state_is_not_closed(self):
        zino1 = self.init_manager()
        zino1.get_events()
        old_events = zino1.events.copy()
        old_events[raw_event_id].priority = 500
        updates = UpdateHandler(zino1, autoremove=False)
        update = NotifierResponse(raw_event_id, "","x butterfly")
        ok = updates.cmd_state(update)
        self.assertTrue(ok)
        self.assertNotEqual(zino1.events[raw_event_id].priority, old_events[raw_event_id].priority)

    def test_fallback(self):
        zino1 = self.init_manager()
        updates = UpdateHandler(zino1)
        update = NotifierResponse(raw_event_id, "", "")
        with self.assertLogs('zinolib.controllers.zino1', level='WARNING') as cm:
            self.assertFalse(updates.fallback(update))

    def test_handle_new_stateless_event_is_very_special(self):
        zino1 = self.init_manager()
        updates = UpdateHandler(zino1)
        update = NotifierResponse(1337, "", "")
        result = updates.handle_event_update(update)
        self.assertEqual(result, None)

    def test_handle_known_type(self):
        zino1 = self.init_manager()
        zino1.get_events()
        old_events = zino1.events.copy()
        old_events[raw_event_id].priority = 500
        updates = UpdateHandler(zino1)
        update = NotifierResponse(raw_event_id, updates.UpdateType.LOG, "")
        ok = updates.handle_event_update(update)  # will refetch events
        self.assertTrue(ok)
        self.assertNotEqual(zino1.events[raw_event_id].priority, old_events[raw_event_id].priority)

    def test_handle_unknown_type(self):
        zino1 = self.init_manager()
        zino1.get_events()
        updates = UpdateHandler(zino1)
        update = NotifierResponse(raw_event_id, "trout", "")
        with self.assertLogs('zinolib.controllers.zino1', level='WARNING'):
            ok = updates.handle_event_update(update)  # will run fallback
            self.assertFalse(ok)
