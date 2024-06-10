import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, ClassVar, List, TypeVar, Union, Dict, Generic, Set
from typing_extensions import Annotated

from pydantic import ConfigDict, IPvAnyAddress, ValidationError, ValidationInfo
from pydantic import BaseModel, computed_field, field_validator
from pydantic.functional_validators import BeforeValidator

from .compat import StrEnum
from .utils import log_exception_with_params


LOG = logging.getLogger(__name__)


def unknown(v: Optional[str]) -> Optional[str]:
    if v:
        if 'unknown' in v:
            return None
        return v
    return None


# Must be after "unknown"
OptionalIpAnyAddress = Annotated[Optional[IPvAnyAddress], BeforeValidator(unknown)]


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
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        # Python 3.12: "if not value in cls:"
        if not value in cls._value2member_map_:
            return cls.UNKNOWN


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


class Event(BaseModel):
    """
    Base-class with common fields for all events.

    Here there be dragons!
    The following cannot be set here, only per subclass::

        port: str = ""
        description: str = ""
        op_state: str = ""

    For that reason, never ``Event()``, always ``Event.create()``!
    """
    class Type(StrEnum):
        ALARM = "alarm"
        BFD = "bfd"
        BGP = "bgp"
        PORTSTATE = "portstate"
        REACHABILITY = "reachability"

    id: int
    type: Union[Type, str]
    adm_state: AdmState
    router: str
    opened: datetime  # epoch

    lastevent: Optional[str] = ''
    lasttrans: Optional[datetime] = None  # epoch
    updated: Optional[datetime] = None # epoch
    polladdr: Optional[IPvAnyAddress] = None
    priority: int = 100

    log: List[LogEntry] = []
    history: List[HistoryEntry] = []

    EXTRAS: ClassVar[Set[str]] = set()
    SUBTYPES: ClassVar[dict] = {}

    model_config = ConfigDict(validate_default=True)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.SUBTYPES[cls.type.value] = cls

    @classmethod
    @log_exception_with_params(LOG)
    def create(cls, attrdict):
        event_type_string = attrdict["type"]
        subtype = Event.SUBTYPES[event_type_string]
        eventobj = subtype(**attrdict)
        return eventobj

    def is_down(self):
        raise NotImplementedError("Abstract method was called, can not calculate is_down status without event type.")


EventType = TypeVar('EventType', bound=Event)
EventOrId = Union[EventType, int]


class AlarmEvent(Event):
    type: str = Event.Type.ALARM
    alarm_count: int
    alarm_type: str
    port: str = ""

    @computed_field  # type: ignore
    @property
    def op_state(self) -> str:
        return f"ALRM  {self.alarm_type}"

    @computed_field  # type: ignore
    @property
    def description(self) -> Optional[str]:
        return self.lastevent

    def is_down(self) -> bool:
        return self.alarm_count > 0


class BFDEvent(Event):
    type: str = Event.Type.BFD
    bfd_addr: OptionalIpAnyAddress = None
    bfd_discr: Optional[int] = None
    bfd_state: BFDState
    bfd_ix: int
    Neigh_rDNS: str = ""  # ?

    @computed_field  # type: ignore
    @property
    def port(self) -> str:
        return str(self.bfd_addr) if self.bfd_addr else f"ix {self.bfd_ix}"

    @computed_field  # type: ignore
    @property
    def description(self) -> str:
        return f"{self.Neigh_rDNS}, {self.lastevent}"

    @computed_field  # type: ignore
    @property
    def op_state(self) -> str:
        return f"BFD  {self.bfd_state[:5]}"

    def is_down(self) -> bool:
        return self.bfd_state == BFDState.DOWN


class BGPEvent(Event):
    type: str = Event.Type.BGP
    bgp_AS: str
    bgp_OS: str
    remote_AS: int
    remote_addr: IPvAnyAddress
    peer_uptime: int
    lastevent: str

    @computed_field  # type: ignore
    @property
    def port(self) -> str:
        return f"AS{self.remote_AS}"

    @computed_field  # type: ignore
    @property
    def description(self) -> str:
        # rdns = dns_reverse_resolver(str(cls.remote_addr))
        # rdns = ''
        # return f"{rdns}, {cls.lastevent}"
        return f"{self.remote_addr}, {self.lastevent}"

    @computed_field  # type: ignore
    @property
    def op_state(self) -> str:
        return f"BGP  {self.bgp_OS[:5]}"

    def is_down(self) -> bool:
        return self.bgp_OS == "down"


class ReachabilityEvent(Event):
    type: str = Event.Type.REACHABILITY
    reachability: ReachabilityState
    ac_down: Optional[timedelta] = None  # int
    description: str = ""
    port: str = ""

    @computed_field  # type: ignore
    @property
    def op_state(self) -> str:
        return self.reachability

    def is_down(self) -> bool:
        return self.reachability == ReachabilityState.NORESPONSE


class PortStateEvent(Event):
    type: str = Event.Type.PORTSTATE
    ac_down: Optional[timedelta] = None  # int
    descr: str = ""
    flaps: Optional[int] = None
    flapstate: Optional[FlapState] = None
    if_index: int
    port_state: PortState  # str *
    reason: Optional[str] = None  # *
    port: str = ""

    EXTRAS: ClassVar[Set[str]] = {"clear_flapping", "get_downtime"}

    @computed_field  # type: ignore
    @property
    def description(self) -> str:
        return self.descr

    @computed_field  # type: ignore
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

    def is_down(self) -> bool:
        return self.port_state in [PortState.DOWN, PortState.LOWER_LAYER_DOWN]
