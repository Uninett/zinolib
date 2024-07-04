"""
Get a live Zino 1 session to use::

    > from zinolib.config.zino1 import ZinoV1Config
    > from zinolib.controllers.zino1 import Zino1EventManager
    > config = ZinoV1Config.from_tcl('.ritz.tcl', 'default')
    > event_manager = Zino1EventManager.configure(config)
    > event_manager.connect()

The configuration can also be stored in a toml-file::

    > config = ZinoV1Config.from_toml('.ritz.toml', 'default')

.. or in a dict with the format::

    > config_dict = {"connections": "default": { "server": ACTUAL CONFIG .. }}
    > config = ZinoV1Config.from_dict(config_dict, 'default')

Do not initialize ZinoV1Config directly, avoid ``ZinoV1Config(**dict)``.

Authenticate using a username and password from the config-file::

    > event_manager.authenticate()

Explicitly autenticate with a username and password::

    > event_manager.authenticate(username, password)

To get a list of currently available events::

    > event_manager.get_events()

The events are then available as::

    > event_manager.events

This is a dictionary of event_id, event object pairs.

To get a set of removed event ids::

    > event_manager.removed_ids

For updates, either regularly use ``get_events()`` or utilize the UpdateHandler::

    > updater = UpdateHandler(event_manager)
    > updater.connect()
    > updated = updater.get_event_update()

The updater is unique per authenticated user and is only available after login.

``updater.get_event_update()`` updates ``event_manager.events`` and
``event_manager.removed_ids`` and returns the id of a changed event on any
change, falsey otherwise. Check the id against the removed_id's set to see if
it has been removed from the server.

To get history for a specific event::

    > history_list = event_manager.get_history_for_id(INT)

To get the log for a specific event::

    > log_list = event_manager.get_log_for_id(INT)

History can be stored on the correct event with one of::

    > event_manager.set_history_for_event(event, history_list)
    > event_manager.set_history_for_event(INT, history_list)

Log can be stored on the correct event with one of::

    > event_manager.set_log_for_event(event, log_list)
    > event_manager.set_log_for_event(INT, log_list)

Both return the changed event.

The adapters are not meant to be used directly.
"""

from datetime import datetime, timezone
from typing import Dict, Iterable, List, TypedDict, Optional, Set
import logging

from .base import EventManager, EventOrId
from ..compat import StrEnum
from ..event_types import EventType, Event, HistoryEntry, LogEntry, AdmState
from ..ritz import ZinoError, ProtocolError, ritz, notifier, NotConnectedError
from ..utils import log_exception_with_params


__all__ = [
    'Zino1EventManager',
]


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


DEFAULT_TIMEOUT = 30
LOG = logging.getLogger(__name__)


class Zino1Error(ZinoError):
    pass


class RetryError(Zino1Error):
    pass


class EventClosedError(Zino1Error):
    pass


class LostConnectionError(NotConnectedError):
    pass


def convert_timestamp(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, timezone.utc)


class UpdateHandler:
    class UpdateType(StrEnum):
        STATE = "state"
        ATTR = "attr"
        HISTORY = "history"
        LOG = "log"
        SCAVENGED = "scavenged"

    class UpdateError(Zino1Error):
        pass

    class SocketError(UpdateError):
        pass

    def __init__(self, manager, autoremove=False):
        self._connected = False
        if not manager.is_authenticated:
            msg = "Cannot initiate update handler, not authenticated"
            raise self.UpdateError(msg)
        self.manager = manager
        self.events = manager.events
        self.autoremove = autoremove

    def connect(self):
        if not self.manager.session.push:
            self.manager.connect_push_channel()
        self.check_connection()

    def check_connection(self):
        self.manager._verify_session()
        if self.manager.session.push._sock.fileno() >= 0:
            self._connected = True
            return True
        self._connected = False
        raise self.SocketError("Push socket reports failure, fileno = -1")

    def get_event_update(self):
        """
        Fetches one update for a single event and runs the appropriate handler

        Attributes on the update object:

        id: event id
        type: update type, triggers the correct handler
        info: a type-specific string with the actual change

        Run in a loop/every N seconds for a lightweight way to update the event
        list
        """
        self.check_connection()
        update = self.manager.session.push.poll()
        if not update:
            return False
        return self.handle_event_update(update)

    def update(self, event_id: int):
        "Refresh an event from the server, refreshing everything"
        event = self.manager.get_updated_event_for_id(event_id)
        self.manager._set_event(event)
        LOG.debug("Updated event #%i", event_id)

    def remove(self, event_id: int):
        "Remove an event from our local copy of the events list"
        self.manager.remove_event(event_id)
        LOG.debug("Removed event #%i", event_id)

    def handle_event_update(self, update):
        """Call the right handle on the update object depending on type

        If the update is about a locally unknown id and the update type is not
        UpdateType.STATE it is a new, incomplete event so we return nothing.

        Otherwise call the right handler on the update data.
        """
        if update.id not in self.events and update.type != self.UpdateType.STATE:
            # unknown event that don't have a state (yet), wait for new update
            return None
        if update.type in tuple(self.UpdateType):
            method = getattr(self, f"cmd_{update.type}")
            return method(update)
        return self.fallback(update)

    def cmd_state(self, update):
        """State has been changed

        Removes a now closed state if the setting "autoremove" is True,
        otherwise refreshes the event from the server.
        """
        states = update.info.split(" ")
        if states[1] == "closed" and self.autoremove:
            LOG.debug('Autoremoving "%s"', update.id)
            self.remove(update.id)
        else:
            self.update(update.id)
        return update.id

    def cmd_attr(self, update):
        """Attributes has been changed

        Refresh the event from the server.
        """
        self.update(update.id)
        return update.id

    cmd_history = cmd_attr
    cmd_log = cmd_attr

    def cmd_scavenged(self, update):
        """The event has been removed from the server

        Remove it from our local copy of the events list.
        """
        self.remove(update.id)
        return update.id

    def fallback(self, update):
        """There's an unknown update type

        Log it and do nothing.
        """
        LOG.warning('Unknown update type: "%s" for id %s' % (update.type, update.id))
        return False


class SessionAdapter:

    class _Session:
        push = None
        request = None

    @classmethod
    def create_session(cls, config):
        session = cls._setup_request(cls._Session, config)
        return session

    @staticmethod
    def _setup_request(session, config):
        if not session.request:
            session.request = ritz(
                config.server,
                username=config.username,
                password=config.password,
                timeout=config.timeout,
            )
        return session

    @classmethod
    def connect_session(cls, session):
        session.request.connect()
        return cls.connect_push_channel(session)

    @staticmethod
    def connect_push_channel(session):
        if session.request.connected and session.request.authenticated:
            session.push = notifier(session.request)
            session.push.connect()  # ntie
        return session

    @staticmethod
    def authenticate(session, username=None, password=None):
        username = username if username else session.request.username
        password = password if password else session.request.password
        if not username and password:
            raise ValueError("Both username and password must be set and truthy")
        session.request.authenticate(username, password)
        return session

    @staticmethod
    def close_push_channel(session):
        if hasattr(session.push, '_sock'):
            session.push._sock.close()
        session.push = None

    @classmethod
    def close_session(cls, session):
        cls.close_push_channel(session)
        session.request.close()
        session.request = None
        return None


class EventAdapter:
    FIELD_MAP = {
        "state": "adm_state",
        "bfdAddr": "bfd_addr",
        "bfdDiscr": "bfd_discr",
        "bfdState": "bfd_state",
        "bfdIx": "bfd_ix",
        # "Neigh-rDNS": "Neigh_rDNS",
        "bgpAS": "bgp_AS",
        "bgpOS": "bgp_OS",
        "ifindex": "if_index",
        "portstate": "port_state",
    }
    FIELD_VALUE_CONVERTER_MAP = {
        'ac_down': int,
    }

    @staticmethod
    def get_attrlist(request, event_id: int):
        return request.get_raw_attributes(event_id)

    @staticmethod
    def validate_raw_attrlist(attrlist):
        for item in attrlist:
            if ':' not in item:
                LOG.error('"getattrs" is spewing garbage: %s', attrlist)
                return False
        return True

    @classmethod
    @log_exception_with_params(LOG)
    def attrlist_to_attrdict(cls, attrlist: Iterable[str]) -> Dict[str, str]:
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
    def set_admin_state(request, event: EventType, state: AdmState) -> bool:
        return request.set_state(event.id, state.value)

    @staticmethod
    def get_event_ids(request):
        try:
            return request.get_caseids()
        except ProtocolError as e:
            raise RetryError('Zino 1 failed to send a correct response header, retry') from e
        except BrokenPipeError as e:
            raise LostConnectionError('Lost connection to Zino 1 server') from e

    @staticmethod
    def poll(request, event: EventType) -> bool:
        if event.type == Event.Type.PORTSTATE:
            return request.poll_interface(event.router, event.if_index)
        else:
            return request.poll_router(event.router)


class HistoryAdapter:
    SYSTEM_USER = "monitor"

    @staticmethod
    def get_history(request, event_id: int):
        return request.get_raw_history(event_id).data

    @classmethod
    @log_exception_with_params(LOG)
    def parse_response(cls, history_data: Iterable[str]) -> list[HistoryDict]:
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
                history_list[-1]["log"] += row.strip() + ' '
            else:
                timestamp, body = row.split(" ", 1)
                dt = convert_timestamp(int(timestamp))
                entry: HistoryDict = {"date": dt}
                if " " in body:  # server generated
                    entry["user"] = cls.SYSTEM_USER
                    entry["log"] = body
                else:
                    entry["user"] = body
                    entry["log"] = ""
                history_list.append(entry)
        for entry in history_list:
            entry["log"] = entry["log"].strip()

        return history_list

    @classmethod
    def add(cls, request, message: str, event: EventType) -> Optional[EventType]:
        success = request.add_history(event.id, message)
        if success:
            # fetch history
            raw_history = cls.get_history(request, event.id)
            parsed_history = cls.parse_response(raw_history)
            new_history = HistoryEntry.create_list(parsed_history)
            if new_history != event.history:
                event.history = new_history
            return event
        return None


class LogAdapter:
    @staticmethod
    def get_log(request, event_id: int) -> list[str]:
        return request.get_raw_log(event_id).data

    @staticmethod
    @log_exception_with_params(LOG)
    def parse_response(log_data: Iterable[str]) -> list[LogDict]:
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
            try:
                timestamp = int(timestamp)
            except ValueError as e:
                raise RetryError('Zino 1 did not send a log, retry') from e
            dt = convert_timestamp(timestamp)
            log_list.append({"date": dt, "log": log})
        return log_list


class Zino1EventManager(EventManager):
    # Easily replaced in order to ease testing
    _session_adapter = SessionAdapter
    _event_adapter = EventAdapter
    _history_adapter = HistoryAdapter
    _log_adapter = LogAdapter
    removed_ids: Set[int] = set()
    config = None

    @property
    def is_authenticated(self):
        session_ok = self._verify_session(quiet=True)
        return self.session.request.authenticated if session_ok else False

    @property
    def is_connected(self):
        session_ok = self._verify_session(quiet=True)
        return self.session.request.connected if session_ok else False

    def rename_exception(self, function, *args):
        "Replace the original exception with our own"
        try:
            return function(*args)
        except (NotConnectedError, LostConnectionError) as e:
            raise
        except ZinoError as e:
            raise self.ManagerException(e) from e

    def _verify_session(self, quiet=False):
        if not getattr(self.session, 'request', None):
            if quiet:
                return False
            raise NotConnectedError("The request socket have not been set up correctly. Reconnect necessary.")
        if not self.session.request.connected:
            if quiet:
                return False
            raise NotConnectedError("Authentication necessary")
        return True

    @classmethod
    def configure(cls, config):
        session = cls._session_adapter.create_session(config)
        classobj = cls(session)
        classobj.config = config
        return classobj

    def connect(self):
        if not self._verify_session(quiet=True):
            self.session =  self._session_adapter.create_session(self.config)
        self.session = self._session_adapter.connect_session(self.session)

    def connect_push_channel(self):
        self.session = self._session_adapter.connect_push_channel(self.session)

    def authenticate(self, username=None, password=None):
        try:
            self.session = self._session_adapter.authenticate(self.session, username, password)
        except (ZinoError, ValueError) as e:
            raise self.ManagerException(e)

    def disconnect(self):
        session_ok = self._verify_session(quiet=True)
        if session_ok:
            self.session = self._session_adapter.close_session(self.session)
        else:
            self._session_adapter.close_push_channel(self.session)

    def clear_flapping(self, event_or_id: EventOrId):
        """Clear flapping state of a PortStateEvent

        Usage:
            c = ritz_session.case(123)
            c.clear_flapping()
        """
        event = self._get_event(event_or_id)
        if event.type == Event.Type.PORTSTATE:
            return self.session.request.clear_flapping(event.router, event.if_index)
        return None

    def poll(self, event_or_id: EventOrId):
        """Ask the server to refresh data for the event

        If there are any changes they will be available through the update
        handler in a bit
        """
        event = self._get_event(event_or_id)
        return self._event_adapter.poll(self.session.request, event)

    def get_events(self):
        self._verify_session()
        for event_id in self._event_adapter.get_event_ids(self.session.request):
            try:
                event = self.create_event_from_id(event_id)
            except self.ManagerException:
                self.remove_event(event_id)
                continue
            self.events[event_id] = event

    def test_connection(self):
        """Try fetching info about a non-existing event

        If the connection is up, we get a ProtocolError due to the
        non-existent event. Do nothing.

        If the connection is down we will pass on a TimeoutError.
        """
        try:
            self._event_adapter.get_attrlist(self.session.request, 0)
        except ProtocolError:
            pass

    def create_event_from_id(self, event_id: int):
        self._verify_session()
        attrlist = self.rename_exception(self._event_adapter.get_attrlist, self.session.request, event_id)
        if not self._event_adapter.validate_raw_attrlist(attrlist):
            raise RetryError('Zino 1 did not send event attributes, retry')
        attrdict = self._event_adapter.attrlist_to_attrdict(attrlist)
        attrdict = self._event_adapter.convert_values(attrdict)
        return Event.create(attrdict)

    def get_updated_event_for_id(self, event_id):
        event = self.create_event_from_id(event_id)
        history_list = self.get_history_for_id(event.id)
        self.set_history_for_event(event, history_list)
        log_list = self.get_log_for_id(event.id)
        self.set_log_for_event(event, log_list)
        return event

    def change_admin_state_for_id(self, event_id, admin_state: AdmState) -> Optional[Event]:
        self._verify_session()
        event = self._get_event(event_id)
        try:
            success = self._event_adapter.set_admin_state(self.session.request, event, admin_state)
        except ValueError as e:
            if 'reopen' in str(e):
                raise EventClosedError("Cannot set state on closed event")
            else:
                raise
        if success:
            event = self.get_updated_event_for_id(event_id)
            self._set_event(event)
            return event
        return None

    def get_history_for_id(self, event_id: int) -> list[HistoryEntry]:
        self._verify_session()
        raw_history = self.rename_exception(self._history_adapter.get_history, self.session.request, event_id)
        parsed_history = self._history_adapter.parse_response(raw_history)
        return HistoryEntry.create_list(parsed_history)

    def add_history_entry_for_id(self, event_id: int, message) -> Optional[Event]:
        self._verify_session()
        event = self._get_event(event_id)
        success = self._history_adapter.add(self.session.request, message, event)
        if success:
            event = self.get_updated_event_for_id(event_id)
            self._set_event(event)
            return event
        return None

    def get_log_for_id(self, event_id: int) -> list[LogEntry]:
        self._verify_session()
        raw_log = self.rename_exception(self._log_adapter.get_log, self.session.request, event_id)
        parsed_log = self._log_adapter.parse_response(raw_log)
        return LogEntry.create_list(parsed_log)
