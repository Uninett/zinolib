import unittest
from datetime import datetime, timedelta, timezone

from zinolib.event_types import AdmState, Event, HistoryEntry, LogEntry
from zinolib.controllers.zino1 import EventAdapter, HistoryAdapter, LogAdapter, Zino1EventManager

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
    def get_attrlist(session, event_id: int):
        return raw_attrlist

    @classmethod
    def attrlist_to_attrdict(cls, attrlist):
        return EventAdapter.attrlist_to_attrdict(attrlist)

    @classmethod
    def convert_values(cls, attrdict):
        return EventAdapter.convert_values(attrdict)

    @staticmethod
    def get_event_ids(session):
        return [raw_event_id]


class FakeHistoryAdapter(HistoryAdapter):
    @staticmethod
    def get_history(session, event_id: int):
        return raw_history


class FakeLogAdapter(LogAdapter):
    @staticmethod
    def get_log(session, event_id: int):
        return raw_log


class FakeZino1EventManager(Zino1EventManager):
    _event_adapter = FakeEventAdapter
    _history_adapter = FakeHistoryAdapter
    _log_adapter = FakeLogAdapter

    def __init__(self, session=None):
        super().__init__(session)


class Zino1EventManagerTest(unittest.TestCase):

    def test_get_events(self):
        zino1 = FakeZino1EventManager('foo')
        self.assertEqual(len(zino1.events), 0)
        zino1.get_events()
        self.assertEqual(len(zino1.events), 1)
        self.assertIn(raw_event_id, zino1.events)
        self.assertEqual(zino1.events[raw_event_id].id, raw_event_id)

    def test_get_history_for_id(self):
        zino1 = FakeZino1EventManager('foo')
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
        zino1 = FakeZino1EventManager('foo')
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
