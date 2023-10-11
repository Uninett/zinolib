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

    def _get_event(self, event_or_id: EventOrId) -> Event:
        if isinstance(event_or_id, Event):
            return event_or_id
        if isinstance(event_or_id, int):
            return self.events[event_or_id]
        raise ValueError("Unknown type")

    def _set_event(self, event: Event):
        self.events[event.id] = event

    def check_session(self):
        if not self.session:
            raise ValueError  # raise correct error

    def set_history_for_event(self, event_or_id: EventOrId, history_list: List[HistoryEntry]) -> EventType:
        event = self._get_event(event_or_id)
        event.history = history_list
        self._set_event(event)
        return event

    def set_log_for_event(self, event_or_id: EventOrId, log_list: List[LogEntry]) -> EventType:
        event = self._get_event(event_or_id)
        event.log = log_list
        self._set_event(event)
        return event
