import unittest
from unittest import mock
from unittest.mock import create_autospec
from datetime import datetime, timedelta

from pydantic import ValidationError

from zinolib.controllers.base import EventManager
from zinolib.event_types import Event, HistoryEntry, LogEntry
from zinolib.event_types import AdmState, BFDState, PortState, ReachabilityState


common_minimal_input = {
    "id": 4576,
    "adm_state": AdmState.OPEN,
    "router": "fghjuy",
    "opened": 1000000000,
}


class EventTest(unittest.TestCase):

    def test_create_event_from_empty_dict_should_complain_about_missing_type(self):
        with self.assertRaises(KeyError) as cm:
            event = Event.create({})
        self.assertEqual(cm.exception.args[0], "type")

    def test_create_event_from_minimal_dict_should_fail(self):
        minimal_input = common_minimal_input.copy()
        minimal_input["type"] = Event.Type.ALARM
        with self.assertRaises(ValidationError):
            event = Event.create(minimal_input)

    def test_create_event_from_subtype_correct_dict_should_succeed(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.ALARM,
            "alarm_count": 1,
            "alarm_type": "apocalypse!!",
        })
        event = Event.create(minimal_input)
        self.assertTrue(isinstance(event, Event.SUBTYPES[Event.Type.ALARM.value]))

    def test_get_downtime_should_fail_noisily_on_non_PortStateEvent(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.ALARM,
            "alarm_count": 1,
            "alarm_type": "apocalypse!!",
        })
        event = Event.create(minimal_input)
        with self.assertRaises(AttributeError):
            event.get_downtime()

    def test_ac_down_field_should_be_timedelta(self):
        # pydantic changes its mind as to what formats are supported
        # so we double check here
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.REACHABILITY,
            "reachability": ReachabilityState.REACHABLE,
            "ac_down": 4564654,
        })
        event = Event.create(minimal_input)
        self.assertTrue(isinstance(event.ac_down, timedelta))

    def test_lasttrans_and_updated_should_be_datetime(self):
        # pydantic changes its mind as to what formats are supported
        # so we double check here
        input = common_minimal_input.copy()
        input.update(**{
            "type": Event.Type.REACHABILITY,
            "reachability": ReachabilityState.REACHABLE,
            "ac_down": 4564654,
            "lasttrans": "1234567890",
            "updated": "1234567890",
        })
        event = Event.create(input)
        self.assertTrue(isinstance(event.lasttrans, datetime))
        self.assertTrue(isinstance(event.updated, datetime))


class AlarmEventTest(unittest.TestCase):

    def test_create_alarm_event_sets_correct_fields(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.ALARM,
            "alarm_count": 1,
            "alarm_type": "apocalypse!!",
            "lastevent": "vfbghj",
        })
        event = Event.create(minimal_input)
        self.assertEqual(event.alarm_count, minimal_input["alarm_count"])
        self.assertEqual(event.alarm_type, minimal_input["alarm_type"])
        self.assertEqual(event.op_state, f"ALRM  {event.alarm_type}")
        self.assertEqual(event.description, event.lastevent)


class BFDEventTest(unittest.TestCase):

    def test_create_bfd_event_sets_correct_fields(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.BFD,
            "bfd_state": BFDState.UP,
            "bfd_ix": 4356,
            "lastevent": "vfbghj",
        })
        event = Event.create(minimal_input)
        self.assertEqual(event.port, f"ix {minimal_input['bfd_ix']}")
        self.assertEqual(event.op_state, f"BFD  {event.bfd_state}"[:10])
        self.assertEqual(event.description, f", {minimal_input['lastevent']}")


class BGPEventTest(unittest.TestCase):

    def test_create_bgp_event_sets_correct_fields(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.BGP,
            "bgp_AS": "vfrgthyj",
            "bgp_OS": "hjkuil",
            "remote_AS": 345,
            "remote_addr": "8.8.8.8",
            "peer_uptime": 4567,
            "lastevent": "ghj",
        })
        event = Event.create(minimal_input)
        self.assertEqual(event.port, f"AS{minimal_input['remote_AS']}")
        self.assertEqual(event.op_state, f"BGP  {event.bgp_OS}"[:10])
        self.assertEqual(event.description, f"{minimal_input['remote_addr']}, {minimal_input['lastevent']}")


class ReachabilityEventTest(unittest.TestCase):

    def test_create_reachability_event_sets_correct_fields(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.REACHABILITY,
            "reachability": ReachabilityState.REACHABLE,
            "ac_down": 567,
        })
        event = Event.create(minimal_input)
        self.assertEqual(event.port, "")
        self.assertEqual(event.op_state, event.reachability)
        self.assertEqual(event.description, "")


class PortStateEventTest(unittest.TestCase):

    def test_create_port_state_event_sets_correct_fields(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.PORTSTATE,
            "if_index": 321,
            "port_state": PortState.UP,
        })
        event = Event.create(minimal_input)
        self.assertEqual(event.port, "")
        self.assertEqual(event.op_state, f"PORT  {event.port_state}"[:11])
        self.assertEqual(event.description, event.descr)

    def test_get_downtime_should_return_a_timedelta(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.PORTSTATE,
            "if_index": 321,
            "port_state": PortState.UP,
        })
        event = Event.create(minimal_input)
        downtime = event.get_downtime()
        self.assertTrue(isinstance(downtime, timedelta))


class HistoryEntryTest(unittest.TestCase):

    def test_create_list_should_return_list_of_history_entries(self):
        dt = datetime.fromisoformat("2023-06-28T10:41:54+00:00")
        history_list = [{
            "date": dt,
            "log": "fhgj",
            "user": "ghj",
        }]
        history = HistoryEntry.create_list(history_list)
        expected_history_entry = HistoryEntry(date=dt, log="fhgj", user="ghj")
        self.assertEqual(history, [expected_history_entry])


class LogEntryTest(unittest.TestCase):

    def test_create_list_should_return_list_of_log_entries(self):
        dt = datetime.fromisoformat("2023-06-28T10:41:54+00:00")
        log_list = [{
            "date": dt,
            "log": "fhgj",
        }]
        log = LogEntry.create_list(log_list)
        expected_log_entry = LogEntry(date=dt, log="fhgj")
        self.assertEqual(log, [expected_log_entry])


class EventManagerTest(unittest.TestCase):

    def setUp(self):
        minimal_input = common_minimal_input.copy()
        minimal_input.update(**{
            "type": Event.Type.ALARM,
            "alarm_count": 1,
            "alarm_type": "apocalypse!!",
            "lastevent": "vfbghj",
        })
        event = Event.create(minimal_input)
        self.event = event

    def test__verify_session_wjen_no_session_should_fail_noisily(self):
        event_manager = EventManager()
        with self.assertRaises(ValueError):
            event_manager._verify_session()

    def test_get_event_with_id_should_succeed(self):
        event = self.event
        event_manager = EventManager()
        event_manager._set_event(event)

        resulting_event = event_manager._get_event(event.id)
        self.assertEqual(self.event, resulting_event)

    def test_set_history_for_event(self):
        event = self.event
        event_manager = EventManager()
        event_manager._set_event(event)
        self.assertFalse(event_manager.events[event.id].history)
        dt = datetime.fromisoformat("2023-06-28T10:41:54+00:00")
        history_list = [{
            "date": dt,
            "log": "fhgj",
            "user": "ghj",
        }]
        updated_event = event_manager.set_history_for_event(event, history_list)
        self.assertTrue(event_manager.events[event.id].history)

    def test_set_log_for_event(self):
        event = self.event
        event_manager = EventManager()
        event_manager._set_event(event)
        self.assertFalse(event_manager.events[event.id].log)
        dt = datetime.fromisoformat("2023-06-28T10:41:54+00:00")
        log_list = [{
            "date": dt,
            "log": "fhgj",
        }]
        updated_event = event_manager.set_log_for_event(event, log_list)
        self.assertTrue(event_manager.events[event.id].log)


class AdmStateTest(unittest.TestCase):

    def test_golden_path(self):
        for state in AdmState:
            enum_state = AdmState(state)
            self.assertEqual(enum_state.value, state)

    def test_garbage_input_should_be_converted_to_UNKNOWN(self):
        value = AdmState("random garbage")
        self.assertEqual(value, AdmState.UNKNOWN)
