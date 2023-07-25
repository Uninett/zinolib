"""
Get a live Zino 1 session to use::

    > from zinolib.ritz import ritz, parse_tcl_config
    > conf = parse_tcl_config("~/.ritz.tcl")['default']
    > session = ritz(
        conf['Server'],
        username=conf['User'],
        password=conf['Secret'],
        timeout=30,
    )
    > session.connect()

Now you can use the session when initializing Zino1EventEngine::

    > event_engine = Zino1EventEngine(session)

To get a list of currently available events::

    > event_engine.get_events()

The events are then available as::

    > event_engine.events

This is a dictionary of event_id, event object pairs.

To get history for a specific event::

    > history_list = event_engine.get_history_for_id(INT)

To get the log for a specific event::

    > log_list = event_engine.get_log_for_id(INT)

History can be stored on the correct event with one of::

    > event_engine.set_history_for_event(event, history_list)
    > event_engine.set_history_for_event(INT, history_list)

Log can be stored on the correct event with one of::

    > event_engine.set_log_for_event(event, log_list)
    > event_engine.set_log_for_event(INT, log_list)

Both return the changed event.

"""

from datetime import datetime, timezone
from typing import List, Dict, Union, TypedDict

from .event_types import EventType, Event, EventEngine, HistoryEntry, LogEntry


HistoryDict = TypedDict(
    "HistoryDict",
    {"date": datetime, "user": str, "log": str},
    total=False,
)
LogDict = TypedDict(
    "LogDict",
    {"log": str, "date": datetime},
    total=False,
)


def convert_timestamp(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, timezone.utc)


class EventAdapter:
    FIELD_MAP = {
        "state": "adm_state",
        "bfdAddr": "bfd_addr",
        "bfdDiscr": "bfd_discr",
        "bfdState": "bfd_state",
        "bfdIx": "bfd_ix",
        #"Neigh-rDNS": "Neigh_rDNS",
        "bgpAS": "bgp_AS",
        "bgpOS": "bgp_OS",
        "ifindex": "if_index",
        "portstate": "port_state",
    }
    FIELD_VALUE_CONVERTER_MAP = {
        'ac_down': int,
    }

    @staticmethod
    def get_attrlist(session, event_id: int):
        return session.get_raw_attributes(event_id)

    @classmethod
    def attrlist_to_attrdict(cls, attrlist: List[str]):
        """Translate a wire protocol dump of a single event

        The dump is a list of lines of the format:

            attr:value
        """
        event_dict = {}
        for item in attrlist:
            k, v = item.split(":", 1)
            if '-' in k:
                k = '_'.join(k.split('-'))
            k = cls.FIELD_MAP.get(k, k)
            event_dict[k.strip()] = v.strip()
        return event_dict

    @classmethod
    def convert_values(cls, attrdict):
        "Convert some values that pydantic handles clumsily"
        for field_name, function in cls.FIELD_VALUE_CONVERTER_MAP.items():
            if field_name in attrdict:
                value = function(attrdict[field_name])
                attrdict[field_name] = value
        return attrdict

    @staticmethod
    def set_admin_state(session, event: EventType, state):
        return session.set_state(event.id, state.value)

    @staticmethod
    def get_event_ids(session):
        return session.get_caseids()


class HistoryAdapter:
    SYSTEM_USER = "monitor"

    @staticmethod
    def get_history(session, event_id: int):
        return session.get_raw_history(event_id).data

    @classmethod
    def parse_response(cls, history_data: List[str]):
        """
        Input:

        [
            '1678273372 state change embryonic -> open (monitor)',
            '1678276375 someuser',
            ' manually recorded history message ',
            ' ',
            '1678276378 state change open -> waiting (someuser)',
            '1680265996 someotheruser',
            ' other manually recorded history message ',
            ' ',
            '1680266003 state change waiting -> working (someotheruser)']

        Output:
        [
            {
                "date": datetime,
                "user": user,
                "log": log,
            },
            ..
        ]
        """
        history_list: List[HistoryDict] = []
        for row in history_data:
            if row == " ":  # end of history
                continue
            if row.startswith(" "):  # history
                history_list[-1]["log"] += row.strip()
            else:
                timestamp, body = row.split(" ", 1)
                dt = convert_timestamp(int(timestamp))
                entry: HistoryDict = {"date": dt}
                if " " in body:  # server generated
                    entry["user"] = cls.SYSTEM_USER
                    entry["log"] = body
                else:
                    entry["user"] =  body
                    entry["log"] = ""
                history_list.append(entry)

        return history_list

    @classmethod
    def add(cls, session, message: str, event: EventType):
        success = session.add_history(event.id, message)
        if success:
            # fetch history
            raw_history = cls.get_history(session, event.id)
            parsed_history = cls.parse_response(raw_history)
            event.history = HistoryEntry.create_list(parsed_history)
            return event


class LogAdapter:
    @staticmethod
    def get_log(session, event_id: int):
        return session.get_raw_log(event_id).data

    @staticmethod
    def parse_response(log_data: List[str]) -> List[LogDict]:
        """
        Input:
        [
            '1683159556 some log message',
            '1683218672 some other log message',
        ]

        Output:
        [
            {
                "date": datetime,
                "log": log
            },
            ..
        ]
        """
        log_list: List[LogDict] = []
        for row in log_data:
            timestamp, log = row.split(" ", 1)
            dt = convert_timestamp(int(timestamp))
            log_list.append({"date": dt, "log": log})
        return log_list


class Zino1EventEngine(EventEngine):
    # Easily replaced in order to ease testing
    _event_adapter = EventAdapter
    _history_adapter = HistoryAdapter
    _log_adapter = LogAdapter

    def clear_flapping(self, event: EventType):
        """Clear flapping state of a PortStateEvent

        Usage:
            c = ritz_session.case(123)
            c.clear_clapping()
        """
        if event.type == Event.Type.PortState:
            return self.session.clear_flapping(event.router, event.ifindex)
        return None

    def get_events(self):
        self.check_session()
        for event_id in self._event_adapter.get_event_ids(self.session):
            event = self.create_event_from_id(event_id)
            self.events[event_id] = event

    def create_event_from_id(self, event_id: int):
        self.check_session()
        attrlist = self._event_adapter.get_attrlist(self.session, event_id)
        attrdict = self._event_adapter.attrlist_to_attrdict(attrlist)
        attrdict = self._event_adapter.convert_values(attrdict)
        return Event.create(attrdict)

    def get_history_for_id(self, event_id: int):
        self.check_session()
        raw_history = self._history_adapter.get_history(self.session, event_id)
        parsed_history = self._history_adapter.parse_response(raw_history)
        return HistoryEntry.create_list(parsed_history)

    def get_log_for_id(self, event_id: int):
        self.check_session()
        raw_log = self._log_adapter.get_log(self.session, event_id)
        parsed_log = self._log_adapter.parse_response(raw_log)
        return LogEntry.create_list(parsed_log)
