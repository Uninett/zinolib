from datetime import datetime, timedelta, timezone
from typing import Optional, ClassVar, List, TypeVar, Union, Dict, Generic

from pydantic import ConfigDict, IPvAnyAddress
from pydantic import BaseModel

from .compat import StrEnum


class PropertyBaseModel(BaseModel):
    # Workaround for serializing properties with pydantic until
    # https://github.com/samuelcolvin/pydantic/issues/935
    # is solved, schgeduled for Pydantic v2
    #
    # Copied from https://github.com/pydantic/pydantic/issues/935#issuecomment-1202998566  # noqa: E501
    @classmethod
    def get_properties(cls):
        return [prop for prop in dir(cls) if isinstance(getattr(cls, prop), property)]

    def dict(self, *args, **kwargs):
        self.__dict__.update(
            {prop: getattr(self, prop) for prop in self.get_properties()}
        )
        return super().dict(*args, **kwargs)

    def json(
        self,
        *args,
        **kwargs,
    ) -> str:
        self.__dict__.update(
            {prop: getattr(self, prop) for prop in self.get_properties()}
        )

        return super().json(*args, **kwargs)


def utcnow():
    return datetime.now(timezone.utc)


class AdmState(StrEnum):
    """

    Historic states:

    * "active" was used twice in 1998
    """
    # ACTIVE = "active"

    CLOSED = "closed"
    CONFIRM_WAIT = "confirm-wait"
    IGNORED = "ignored"
    OPEN = "open"
    WAITING = "waiting"
    WORKING = "working"


class FlapState(StrEnum):
    FLAPPING = 'flapping'
    STABLE = 'stable'


class BFDState(StrEnum):
    ADMIN_DOWN = "adminDown"
    DOWN = "down"
    INIT = "init"
    UP = "up"


class ReachabilityState(StrEnum):
    REACHABLE = "reachable"
    NORESPONSE = "no-response"


class PortState(StrEnum):
    """
    Historic states:

    * "testing" was used six times from 2000 to 2001
    * "admin0" was used ten times from 2000 to 2002
    * "flapping" was used 22 times on 2016-07-13T09:55 UTC
    * "notPresent" was used 161 times during 2003
    * "5" was used 389 times from 1998 to 2000
    * "dormant" was used 813 times from 2000 to 2006
    """
    # TESTING = "testing"
    # ADMIN_0 = "admin0"
    # FLAPPING = "flapping"
    # NOT_PRESENT = "notPresent"
    # FIVE = "5"
    # DORMANT = "dormant"

    ADMIN_DOWN = "adminDown"
    DOWN = "down"
    LOWER_LAYER_DOWN = "lowerLayerDown"
    UP = "up"


class LogEntry(BaseModel):
    date: datetime  # epoch
    log: str

    @classmethod
    def create_list(cls, raw_log_list):
        log_list = []
        for entry in raw_log_list:
            obj = cls(**entry)
            log_list.append(obj)
        return log_list


class HistoryEntry(BaseModel):
    log: str
    date: datetime  # epoch
    user: str

    @classmethod
    def create_list(cls, raw_history_list):
        history_list = []
        for entry in raw_history_list:
            obj = cls(**entry)
            history_list.append(obj)
        return history_list


class Event(PropertyBaseModel):
    """
    """
    class Type(StrEnum):
        ALARM = "alarm"
        BFD = "bfd"
        BGP = "bgp"
        PORTSTATE = "portstate"
        REACHABILITY = "reachability"

    id: int
    type: ClassVar[Type]
    adm_state: AdmState
    router: str
    opened: datetime  # epoch

    lastevent: Optional[str]
    lasttrans: Optional[datetime] = None  # epoch
    updated: Optional[datetime]  # epoch
    polladdr: Optional[IPvAnyAddress]
    priority: int = 100

    # Cannot be set here, only per subclass
    # port: str = ""
    # description: str = ""
    # op_state: str = ""

    log: List[LogEntry] = []
    history: List[HistoryEntry] = []
    SUBTYPES: ClassVar[dict] = {}
    model_config = ConfigDict(validate_default=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.SUBTYPES[cls.type.value] = cls

    @classmethod
    def create(cls, attrdict):
        event_type_string = attrdict["type"]
        subtype = Event.SUBTYPES[event_type_string]
        eventobj = subtype(**attrdict)
        return eventobj


EventType = TypeVar('EventType', bound=Event)
EventOrId = Union[EventType, int]


class AlarmEvent(Event):
    type = Event.Type.ALARM
    alarm_count: int
    alarm_type: str
    port: str = ""

    @property
    def op_state(self) -> str:
        return f"ALRM  {self.alarm_type}"

    @property
    def description(self) -> str:
        return self.lastevent


class BFDEvent(Event):
    type = Event.Type.BFD
    bfd_addr: Optional[IPvAnyAddress] = None
    bfd_discr: Optional[int] = None
    bfd_state: BFDState
    bfd_ix: int
    Neigh_rDNS: str = ""  # ?

    @property
    def port(self) -> str:
        return self.bfd_addr if self.bfd_addr else f"ix {self.bfd_ix}"

    @property
    def description(self) -> str:
        return f"{self.Neigh_rDNS}, {self.lastevent}"

    @property
    def op_state(self) -> str:
        return f"BFD  {self.bfd_state[:5]}"


class BGPEvent(Event):
    type = Event.Type.BGP
    bgp_AS: str
    bgp_OS: str
    remote_AS: int
    remote_addr: IPvAnyAddress
    peer_uptime: int
    lastevent: str

    @property
    def port(self) -> str:
        return f"AS{self.remote_AS}"

    @property
    def description(self) -> str:
        # rdns = dns_reverse_resolver(str(cls.remote_addr))
        # rdns = ''
        # return f"{rdns}, {cls.lastevent}"
        return f"{self.remote_addr}, {self.lastevent}"

    @property
    def op_state(self) -> str:
        return f"BGP  {self.bgp_OS[:5]}"


class ReachabilityEvent(Event):
    type = Event.Type.REACHABILITY
    reachability: ReachabilityState
    ac_down: Optional[timedelta] = None  # int
    description: str = ""
    port: str = ""

    @property
    def op_state(self) -> str:
        return self.reachability


class PortStateEvent(Event):
    type = Event.Type.PORTSTATE
    ac_down: Optional[timedelta] = None  # int
    descr: str = ""
    flaps: Optional[int] = None
    flapstate: Optional[FlapState] = None
    if_index: int
    port_state: PortState  # str *
    reason: Optional[str] = None  # *
    port: str = ""

    @property
    def description(self) -> str:
        return self.descr

    @property
    def op_state(self) -> str:
        return f"PORT  {self.port_state[:5]}"

    def get_downtime(self):
        """Calculate downtime on this PortState"""
        # If no transition is detected, use now.
        now = utcnow()
        lasttrans = self.lasttrans or now
        accumulated = self.ac_down or timedelta(seconds=0)

        if self.port_state in [PortState.DOWN, PortState.LOWER_LAYER_DOWN]:
            return accumulated + now - lasttrans
        else:
            return accumulated


class EventEngine:
    """
    Implementation-agnostic controller for events

    A list of already existing events can be manipulated by an instance of
    this class out of the box, but the actual IO is done by subclasses.
    """
    events: Dict[int, Event]

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

    def set_history_for_event(self, event_or_id: EventOrId, history_list: List[HistoryEntry]):
        event = self._get_event(event_or_id)
        event.history = history_list
        self._set_event(event)
        return event

    def set_log_for_event(self, event_or_id: EventOrId, log_list: List[LogEntry]):
        event = self._get_event(event_or_id)
        event.log = log_list
        self._set_event(event)
        return event

    # not finished
    def add_history_for_event(self, event: EventType, history_entry):
        event.history.append(history_entry)
        return event
