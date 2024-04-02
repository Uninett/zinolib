from typing import List, Union, Dict

from ..event_types import EventType, Event, HistoryEntry, LogEntry


EventOrId = Union[EventType, int]


class EventManager:
    """
    Implementation-agnostic controller for events

    A list of already existing events can be manipulated by an instance of
    this class out of the box, but the actual IO is done by subclasses.
    """
    events: Dict[int, Event]

    class ManagerException(Exception):
        pass

    def __init__(self, session=None):
        self.session = session
        self.events = {}
        self.removed_ids = set()

    def _get_event(self, event_or_id: EventOrId) -> Event:
        if isinstance(event_or_id, Event):
            return event_or_id
        if isinstance(event_or_id, int):
            return self.events[event_or_id]
        raise ValueError("Unknown type")

    def _get_event_id(self, event_or_id: EventOrId) -> int:
        if isinstance(event_or_id, int):
            return event_or_id
        if isinstance(event_or_id, Event):
            return event_or_id.id
        raise ValueError("Unknown type")

    def _set_event(self, event: Event):
        self.events[event.id] = event

    def remove_event(self, event_or_id: EventOrId):
        event_id = self._get_event_id(event_or_id)
        self.events.pop(event_id, None)
        self.removed_ids.add(event_id)

    def _verify_session(self, quiet=False):
        if not self.session:
            if quiet:
                return False
            raise ValueError  # raise correct error
        return True

    def set_history_for_event(self, event_or_id: EventOrId, history_list: List[HistoryEntry]) -> Event:
        event = self._get_event(event_or_id)
        event.history = history_list
        self._set_event(event)
        return event

    def set_log_for_event(self, event_or_id: EventOrId, log_list: List[LogEntry]) -> Event:
        event = self._get_event(event_or_id)
        event.log = log_list
        self._set_event(event)
        return event
