# from __future__ import annotations

import logging
import socket
import hashlib
import enum
import ipaddress
from pprint import pprint
from datetime import datetime, timedelta
import errno
from time import mktime
import re
from os.path import expanduser
from typing import NamedTuple
import codecs
import select

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Things to implement
# /local/src/zino/zino/server.tcl
#   user        Authenticate user
#               Status: Implemented

#   nsocket     Outdated, DO NOT IMPLEMENT

#   ntie        Connect to notification socket
#               Status: NOT implemented

#   caseids     Get list of get_caseids
#               Status: Implemented

#   clearflap   doClearFlap $chan $l

#   getattrs    Get attributes of CaseID
#               Status: Crude implementation

#   getlog      Get Logs from CaseID
#               Status: Crude implementation

#   gethist     Get History from CaseID
#               Status: Crude implementation

#   addhist     Add history line to CaseID
#               Status: Implemented

#   setstate    Set noe state on caseID
#               Status: Implemented

#   community   Returns SNMP Community to comm. with device
#               uses router name as parameter
#               State: not Implemented

#   pollintf    Poll a router
#               State: implemented but not tested

#   pollrtr     Poll an interface
#               State: implemented but not Testmelding

#   pm          Preventive Maintenance
#               has a bid tree of sob commands,
#                 pm add      - Scheduled a PM
#                   State: Crude implementation
#                 pm list     - List all PMs
#                   State: Crude implementation
#                 pm cancel   - Cancel a PM
#                   State: Implemented
#                 pm details  - Details of a PM
#                   State: Crude implementation
#                 pm matching - Get ports and devices matching a PM
#                   State: Crude implementation not tested
#                 pm addlog   - Add a log entry to a PM
#                   State: Not Implemented
#                 pm log      - Get log of a PM
#                   State: Not Implemented
#                 pm help     - Get help... wil not implement
#                  State: NOT implemented
#
#   quit        doQuitCmd $chan $l
#   help        doHelpCmd $chan $l
#   version     doVersionCmd $chan $l


class AuthenticationError(Exception):
  pass


class NotConnectedError(Exception):
  pass


class ProtocolError(Exception):
  pass


notifierEntry = NamedTuple("notifierEntry", [('id', int),
                                             ('type', str),
                                             ('info', str)])

zinoDataEntry = NamedTuple("zinoDataEntry", [('data', str),
                                             ('header',str)])


def windows_codepage_cp1251(error):
    """Windows Codepage 1251 decoder fallback

    This function could be used as a failback for UnicodeEncodeError to fail
    back to windows codepage 1251 decoding when eg. utf-8 failes

    All valid windows codepage 1251 elements will be returned with their
    representative unicode characters and failes back to unicode unknown char
    when no valid character is found

    All illegal characters are replaced with unicode 0xFFFD
    """

    # This only works on UnicodeDecodeError, will not work on encoding
    if not isinstance(error, UnicodeDecodeError):
        raise error

    # 0xFFFD is the unicode char for illegal character.
    # these characters are not an valid printable cp1251 character

    cp1251_map = [
        0x20AC, 0xFFFD, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021, #0x80-0x87
        0x02c6, 0x2030, 0x0160, 0x2039, 0x0152, 0xFFFD, 0x017d, 0xFFFD, #0x88-0x8F
        0xFFFD, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014, #0x90-0x97
        0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0xFFFD, 0x017E, 0x0178  #0x98-0x9F
    ]

    result = []
    for i in range(error.start, error.end):
        byte = error.object[i]

        if byte >= 0x80 and byte <= 0x9F:
            # We try to use windows codepage 1251 on this char
            result.append(chr(cp1251_map[byte - 0x80]))

        else:
            # This looks like a valid latin-1 char
            # It correspons to the same unicode char
            result.append(chr(0x00 + byte))

    return ''.join(result), error.end


codecs.register_error("windows_codepage_cp1251", windows_codepage_cp1251)

class caseState(enum.Enum):
    """State field of a ritz.Case object"""
    OPEN = 'open'
    WORKING = 'working'
    WAITING = 'waiting'
    CONFIRM = 'confirm-wait'
    IGNORED = 'ignored'
    CLOSED = 'closed'


class caseType(enum.Enum):
    """Type field of a ritz.Case object"""
    PORTSTATE = 'portstate'
    BGP = 'bgp'
    BFD = 'bfd'
    REACHABILITY = 'reachability'
    ALARM = 'alarm'


def _decode_history(logarray):
  """Decode history

  Decodes a history "object" from the tcp socket and returns a list with history dict objects
  Input is a list of lines recieved from zino history or log command
  Output is a list with log/history entries
  """
  ret = []
  curr = {}
  for log in logarray:
    if not log[0] == " ":
      # This is a header line
      curr = {}
      curr["log"] = []

      header = log.split(" ", 1)
      # curr["raw_line"] = log
      # curr["raw_header"] = header
      curr["date"] = datetime.fromtimestamp(int(header[0]))
      curr["header"] = header[1]

      if header[1].count(" ") != 0:
        # this is a short system log
        curr["log"] = []
        curr["user"] = "system"  # re.match(".*\((\w+)\)$", header[1]).group(1)
        ret.append(curr)
      else:
        curr["user"] = header[1]

    elif log == " ":
      # End entry, empty line with one space
      ret.append(curr)
    else:
      # Append log line
      curr["log"].append(log[1::])
  return ret


# def parse_tcl_config(filename: str | Path):
def parse_tcl_config(filename):
  """Parse a .ritz.tcl config file

  Used to fetch a users connection information to connect to zino
  .ritz.tcl is formatted as a tcl file.
  """
  config = {}
  with open(expanduser(filename), 'r') as f:
    for line in f.readlines():
      _set = re.findall(r'^\s?set _?([a-zA-Z0-9]+)(?:\((.*)\))? (.*)$', line)
      if _set:
        group = _set[0][1] if _set[0][1] != '' else 'default'
        key = _set[0][0]
        value = _set[0][2]

        if group not in config:
          config[group] = {}

        config[group][key] = value
  return config


class Case():
  """Zino case element

  Returns a case object with all attributes and functions of the zino case object

  Usage:
      c = ritz_session.case(123)
  or
      c = Case(ritz_session, 123)
  """

  def __init__(self, zino, caseid):
    self._zino = zino
    self._caseid = caseid
    self._attrs = self._zino.get_attributes(caseid)

  def __repr__(self):
    return "%s(%s)" % (str(self.__class__), self._caseid)

  def clear_flapping(self):
    """Clear flapping state if this case object

    Usage:
        c = ritz_session.case(123)
        c.clear_clapping()
    """
    if self.type == caseType.PORTSTATE:
      return self._zino.clear_flapping(self._attrs["router"],
                                       self._attrs["ifindex"])
    else:
      raise AttributeError("clear_flapping is only supported when type is portstate")

  def add_history(self, message):
    """Add a history line to this case object

    Usage:
        c = ritz_session.case(123)
        c.add_history("Test message")
    """
    return self._zino.add_history(self._caseid, message)

  def set_state(self, state):
    """Set case to new state

    state is a object of class(enum) caseState
    Usage:
        c = ritz_session.case(123)
        c.set_state(caseState.WAITING)
    """
    return self._zino.set_state(self._caseid, state)

  def poll(self):
      """Poll interface or device immediately

      Usage:
          c = ritz_session.case(123)
          c.poll()
      """
      if self.type == caseType.PORTSTATE:
          return self._zino.poll_interface(self._attrs["router"],
                                           self._attrs["ifindex"])
      else:
          return self._zino.poll_router(self._attrs["router"])

  def __getattr__(self, name):
    """Wrapper to get all attributbutes of the object as python attributes
    Usage:
        c = ritz_session.case(123)
        print(c.id)
    """
    if name in self._attrs:
      return self._attrs[name]
    elif 'history' == name:
      return self._zino.get_history(self._caseid)
    elif 'log' == name:
      return self._zino.get_log(self._caseid)
    elif 'downtime' == name:
        return self.get_downtime()
    else:
      self.__getattribute__(name)
      # raise AttributeError("%s instance of type %s has no attribute '%s'" % (self.__class__, self._attrs["type"], name))
    return self

  def __getitem__(self, key):
      """Wrapper to dict

      Makes the object act as a dict object, used when the key is a string
      Usage:
          c = ritz_session.case(123)
          print(c["id"])
      """
      return self.__getattr__(key)

  def get(self, key, default=None):
      return self._attrs.get(key, default)

  def get_downtime(self):
      """Calculate downtime on this object

      This is only supported on portstate
      """
      if self.type is not caseType.PORTSTATE:
          raise TypeError("get_downtime is not supported under case type '%s'" % str(self.attr["type"]))

      # If no transition is detected, use now.
      lasttrans = self._attrs.get("lasttrans", datetime.now())
      # Return timedelta 0 if ac_down is non_existant
      accumulated =  self._attrs.get("ac_down", timedelta(seconds=0))

      if self.portstate in ["lowerLayerDown", "down"]:
          return accumulated + datetime.now() - lasttrans
      else:
          return accumulated



  def keys(self):
      """List keys of this object

      This wil mimmic the keys attribyte of a dict, returns all attributes available
      """
      k = [k for k in self._attrs.keys()]
      k.append('history')
      k.append('log')
      if self.type == caseType.PORTSTATE:
          k.append('downtime')
      return k

  def has_key(self, k):
              return k in self._attrs


class ritz():
  """Connect to zino datachannel.
  Usage:
      from ritz import ritz
      ritz_session = ritz(c_server, username="123", password="123")
      ritz_session.connect()
  or
      from ritz import ritz
      with ritz(c_server, username="123", password="123") as ritz_session:
          ...
  """
  def __init__(self,
               server,
               port=8001,
               timeout=10,
               username=None,
               password=None):
    """Initialize"""
    global logger

    self._sock = None
    self.connStatus = False
    self.server = server
    self.port = port
    self.timeout = timeout
    self.username = username
    self.password = password
    self._buff = ''

  def __enter__(self):
    """Wrapper for with to automaticly connect to zino"""
    self.connect()
    return self

  def __exit__(self, type, value, traceback):
    """Wrapper for with to close zino connection"""
    self.close()

  def __del__(self):
    """Zino object deletion"""
    self.close()

  def _read_command(self, command, recv_buffer=4096, delim='\r\n'):
    """Read a command from the ritz TCP socket

    This code needs a rewrite, maby use socket file object?
    everything is \r\n terminated
    """
    global logger
    buffer = ''
    data = True
    header = False
    r = []
    logger.debug("send: %s" % command.__repr__())
    if command:
      self._sock.send(command)
    while data:
      try:
          data = self._sock.recv(recv_buffer)
      except socket.timeout:
          raise TimeoutError("Timed out waiting for data. command: %s buffer: %s" % (repr(command), repr(buffer)))
      logger.debug("recv: %s" % data.__repr__())

      buffer += data.decode('UTF-8', errors='windows_codepage_cp1251')

      if not header:
        if buffer.find(delim) != -1:
          try:
            line, buffer = buffer.split('\r\n', 1)  # '\r\n' is not a byte
            rawh = line.split(' ', 1)  # ' ' is not a byte
            header = (int(rawh[0]), rawh[1])
          except ValueError:
              raise ProtocolError("Illegal response from server detected: %s" % repr(buffer))
          # header = line
          # Crude error detection :)
          if header[0] >= 500:
            # Die on Error codes
            return zinoDataEntry(header[1], header)
            # raise ProtocolError("Errorcode '%s %s' reported from server" % (header[0], header[1]))
          if header[0] == 200:
            # Return to user on 200, 200 doesent add more data
            return zinoDataEntry(header[1], header)
          if header[0] == 302:
            # Return to user on 302, wee need more data
            return zinoDataEntry(header[1], header)
        next

      while buffer.find(delim) != -1:
        line, buffer = buffer.split('\r\n', 1)  # '\r\n' is not a byte
        if line == ".":
          return zinoDataEntry(r, header)
        r.append(line)
    if not header:
        raise ProtocolError("No header info detected for command %s, buffer %s" % (repr(command), repr(buffer)))
    return zinoDataEntry(r, header)

  def connect(self):
    """Connect to zino datachannel

    Opens the tcp socket to the zino data channel
    Usage:
        zino_session = ritz(.....)
        zino_session.connect()
    """
    # Opens an connection to the Server
    # To do things you need to authenticate after connection
    try:
        self._sock = socket.create_connection((self.server, self.port), self.timeout)
    except socket.gaierror as E:
        raise NotConnectedError(E)
    response = self._read_command(None)
    if response.header[0] == 200:
      self.authChallenge = response.header[1].split(' ', 1)[0]
      self.connStatus = True
    else:
      raise NotConnectedError("Did not get a status code 200")

    # Automaticly authenticate if username and password is supplied
    if self.username and self.password:
      self.authenticate(self.username, self.password)

  def close(self):
    """Disconnect zino datachennel"""
    if self._sock:
      self._sock.close()
      self._sock = None
      self.connStatus = False
      self.authenticated = False

  @property
  def connected(self):
    """Returns True when datachannel is connected"""
    if self._sock and self.connStatus and self.authenticated:
      return True
    return False

  def authenticate(self, user, password):
    """Authenticate a user on the zino datachannel

    Automaticlly started by connect() if username and password is specified at
    object creation time, if not the user needs to execute this command to
    authenticate the session against the zino Server

    Usage:
        ritz_session = ritz(server)
        ritz_session.connect()
        ritz_session.authenticate("username","password")
    """
    # Authenticate user
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")

    # Combine Password and authChallenge from Ritz to make authToken
    genToken = "%s %s" % (self.authChallenge, password)
    authToken = hashlib.sha1(genToken.encode('UTF-8')).hexdigest()
    cmd = 'user %s %s  -\r\n' % (user, authToken)
    #  try:
    try:
      response = self._read_command(cmd.encode('UTF-8'))
    #  except ProtocolError as e:
    #    raise AuthenticationError(e)
      if response.header[0] == 200:
        self.authenticated = True
        return
      else:
          raise AuthenticationError("Unable to authenticate user, '%s'" % repr(response.header))
    except TypeError:
      raise ProtocolError("Got an illegal response from the server")

  def case(self, id):
    """Get a zino Case object

    Usage:
        case = ritz_session.case(id)"""
    return Case(self, id)

  def cases(self):
    """Get a list with all cases in zino

    Usage:
        for case in ritz_session.cases():
            print(case.id)
    """
    return list(self.cases_iter())

  def cases_iter(self):
    """Return list with cases from zino as a iter

    Usage:
        for case in ritz_session.cases_iter():
            print(case.id)
    """
    for k in self.get_caseids():
      yield Case(self, k)

  def get_caseids(self):
    """Get list of CaseID's that exists in zino

    Usage:
        ids = ritz_session.get_caseids()
        print(ids)
          [123,234,345,456,567,678,789]
        """
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    response = self._read_command(b"caseids\r\n")

    ids = []
    for id in response.data:
      if id.isdigit():
        ids.append(int(id))

    return ids

  def get_attributes(self, caseid):
    """Collect all attributes of a zino CaseID object

    Returns a dict of all attributes registred on this case in zino
    also does formatting of fields for known attributes

    Usage:
        attrs = ritz_session.get_attributes(123)
    """
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    cmd = "getattrs %s\r\n" % caseid
    response = self._read_command(cmd.encode('UTF-8'))
    if response.header[0]>=500:
        raise ProtocolError(response.header)
    caseinfo = {}
    for d in response.data:
      v = d.split(":", 1)
      caseinfo[v[0].strip().lower().replace("-", "_")] = v[1].strip()

    caseinfo['id'] = int(caseinfo['id'])
    caseinfo['opened'] = datetime.fromtimestamp(int(caseinfo['opened']))
    caseinfo['updated'] = datetime.fromtimestamp(int(caseinfo['updated']))
    caseinfo['priority'] = int(caseinfo['priority'])

    if 'ifindex' in caseinfo:
      caseinfo['ifindex'] = int(caseinfo['ifindex'])
    if 'lasttrans' in caseinfo:
      caseinfo['lasttrans'] = datetime.fromtimestamp(int(caseinfo['lasttrans']))
    if 'flaps' in caseinfo:
      caseinfo['flaps'] = int(caseinfo['flaps'])
    if 'ac_down' in caseinfo:
      caseinfo['ac_down'] = timedelta(seconds=int(caseinfo['ac_down']))
    if 'state' in caseinfo:
      caseinfo['state'] = caseState(caseinfo['state'])
    if 'type' in caseinfo:
      caseinfo['type'] = caseType(caseinfo['type'])
    if 'polladdr' in caseinfo:
      caseinfo['polladdr'] = ipaddress.ip_address(caseinfo['polladdr'])
    if 'remote_addr' in caseinfo:
      caseinfo['remote_addr'] = ipaddress.ip_address(caseinfo['remote_addr'])
    if 'remote_as' in caseinfo:
      caseinfo['remote_as'] = int(caseinfo["remote_as"])
    if 'peer_uptime' in caseinfo:
      caseinfo['peer_uptime'] = int(caseinfo['peer_uptime'])
    if 'alarm_count' in caseinfo:
      caseinfo['alarm_count'] = int(caseinfo['alarm_count'])
    if 'bfdix' in caseinfo:
      caseinfo['bfdix'] = int(caseinfo['bfdix'])
    if 'bfddiscr' in caseinfo:
      caseinfo['bfddiscr'] = int(caseinfo['bfddiscr'])
    if 'bfdaddr' in caseinfo:
      caseinfo['bfdaddr'] = ipaddress.ip_address(caseinfo['bfdaddr'])


    return caseinfo

  def get_history(self, caseid):
    """Return all history elements of a CaseID

    Usage:
        case_history = ritz_session.get_history(123)
    """
    #   gethist     Get Logs from CaseID
    #   Parameters: caseID
    #   Returns a list of historylines (timestamp, message)??
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    response = self._read_command(b"gethist %d\r\n" % caseid)

    return _decode_history(response.data)

  def get_log(self, caseid):
    """Return all log elements of a CaseID

    Usage:
        case_logs = ritz_session.get_log(123)
    """
    #   getlog      Get Logs from CaseID
    #   Parameters: caseID
    #   Returns a list of loglines (timestamp, message)
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")

    response = self._read_command(b"getlog %d\r\n" % caseid)

    return _decode_history(response.data)

  def add_history(self, caseid, message):
    """Add a history element on a CaseID

    Usage:
        ritz_session.add_history(123, "Test message")
    """
    # ZinoServer:
    # paramters: case-id
    # 302 please provide new history entry, termiate with '.'

    # Generate Message to zino
    if isinstance(message, list):
      msg = "\r\n".join(message)
    else:
      msg = message

    # Start Command
    response = self._read_command(b"addhist %d  -\r\n" % (caseid))
    if not response.header[0] == 302:
      raise ProtocolError("Unknown return from server: %s" % response.data)

    # Send message
    response = self._read_command(b"%s\r\n\r\n.\r\n" % msg.encode())
    if not response.header[0] == 200:
      raise ProtocolError("Not getting 200 OK from server: %s" % response.data)
    return True

  def set_state(self, caseid, state):
    """Change state of a CaseID

    Inputs a caseSession object(enum)
    Usage:
        ritz_session.set_state(caseState.WORKING)
    """
    if isinstance(state, str):
      state = caseState(state)
    elif isinstance(state, caseState):
      pass
    else:
      raise TypeError("State needs to be a string or caseState")

    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")

    response = self._read_command(b"setstate %d %s\r\n" % (caseid, state.value.encode()))

    # Check returncode
    if not response.header[0] == 200:
      raise ValueError("Unable to change state on %d to %s. error: %s" % (caseid, state, repr(response.header)))
    return True

  def clear_flapping(self, router, ifindex):
    """Clear port flapping information on a interface

    Usage:
        ritz_session("routername","interfacename")
    """
    if not isinstance(ifindex, int):
      raise TypeError("CaseID needs to be an integer")

    response = self._read_command(b"clearflap %s %d\r\n" % (router.encode(), ifindex))

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def poll_router(self, router):
    """Poll a router for new data

    Usage:
        zino_session.poll_router("routername")
    """
    response = self._read_command(b"pollrtr %s\r\n" % router.encode())

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def poll_interface(self, router, ifindex):
    """Poll interface for new information

    Inputs is a string containing a router name in zino and the ifindex to be polled.
    Usage:
        zino_session.poll_interface("routername", 9999)
    """
    if not isinstance(ifindex, int):
        raise TypeError("CaseID needs to be an interger")
    response = self._read_command(b"pollintf %s %d\r\n" % (router.encode(), ifindex))

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def ntie(self, key):
    """Tie to notification notification channel

    Connect datachannel and notification channel together,
    used by connect function on the notifier() object

    Usage:
        notify_session = notifier(ritz_session)
    or
        notify_session = notifier()
        key = notify_session.connect("servername")
        ritz_session.ntie(key)
    or
        with notifier(ritz_session) as notif:
            ....
    """
    # Tie to notification channel
    # Parameters: key:
    #   key is key reported by notification channel.
    if isinstance(key, str):
      key = key.encode()
    elif isinstance(key, bytes):
      pass
    else:
      raise ValueError("key needs to be string or bytes")
    response = self._read_command(b"ntie %s\r\n" % key)

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % response.header.__repr__())
    return True

  def pm_add_device(self, from_t, to_t, device, m_type="exact"):
    """Add Maintenance window on a device level

    m_type:
      exact: excact match on one device

    """
    # Adds a Maintenance period
    # pm add
    #    [2] from_t   -  start timestamp  (unixtime)
    #    [3] to_t     -  stop  timestamp  (unixtime)
    #    [4] type     -  "device"
    #    [5] m_type   -  could be "regexp", "str", "exact"
    #                    str: allows ? or * for single or multicaracter wildcard
    #    [6] m_expr   -  device_regex
    #  Returns 200 with id on PM on sucessfull pm add
    #  Function returns id of added PM
    # str: matcher mot device-name, kan bruke ? - en char * - flere char
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    if not isinstance(from_t, datetime):
        raise TypeError("from_t is not a datetime")
    if not isinstance(to_t, datetime):
        raise TypeError("to_t is not a datetime")
    if from_t > to_t:
        raise ValueError("To timestamp is earlier than From timestamp")
    if m_type not in ("exact", "str", "regexp"):
        raise Exception("Unknown m_type, needs to be exact, str or regexp")

    from_ts = mktime(from_t.timetuple())
    to_ts = mktime(to_t.timetuple())

    response = self._read_command(b'pm add %d %d device %s %s\r\n' %
                                      (from_ts,
                                       to_ts,
                                       m_type.encode(),
                                       device.encode()))

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)

    data2 = response.data.split(" ", 3)
    return int(data2[2])

  def pm_add_interface(self, from_t, to_t, device, interface):
      self.pm_add_interface_byname(from_t, to_t, device, interface)

  def pm_add_interface_byname(self, from_t, to_t, device, interface):
    """Adds Maintenance window for interfaces based on interface name

    Does a regex match on interfaces on a device
    from_t:    from timestamp
    to_t:      to_timestamp
    device:    exact device name
    interface: regex on interface names
    """
    # Adds a Maintenance period
    # pm add
    #    [2] from_t   -  start timestamp (unixtime)
    #    [3] to_t     -  stop  timestamp   (unixtime)
    #    [4] type     -  "portstate"
    #    [5] m_type   -  "intf-regexp"
    #    [6] m_dev    -  device excact name
    #    [7] m_expr   -  interface regexp

    #  Returns 200 with id on PM on sucessfull pm add
    #  Function returns id of added PM
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    if not isinstance(from_t, datetime):
        raise TypeError("from_t is not a datetime")
    if not isinstance(to_t, datetime):
        raise TypeError("to_t is not a datetime")
    if from_t > to_t:
        raise Exception("To timestamp is earlier than From timestamp")

    from_ts = mktime(from_t.timetuple())
    to_ts = mktime(to_t.timetuple())

    response = self._read_command(b'pm add %d %d portstate intf-regexp %s %s\r\n' %
                                      (from_ts,
                                       to_ts,
                                       device.encode(),
                                       interface.encode()))

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)

    data2 = response.data.split(" ", 3)
    return int(data2[2])

  def pm_add_interface_bydescr(self, from_t, to_t, description):
    """ Add Maintenance window on interface level by interface description

    Does a regex global match on all interfaces in zino
    from_t:   from timestamp
    to_t:     to timestamp
    description: interface description regex
    """

    # Adds a Maintenance period
    # pm add
    #    [2] from_t   -  start timestamp (unixtime)
    #    [3] to_t     -  stop  timestamp   (unixtime)
    #    [4] type     -  "portstate"
    #    [5] m_type   -  "regexp"
    #    [6] m_expr   -  interface regexp

    #  Returns 200 with id on PM on sucessfull pm add
    #  Function returns id of added PM
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    if not isinstance(from_t, datetime):
        raise TypeError("from_t is not a datetime")
    if not isinstance(to_t, datetime):
        raise TypeError("to_t is not a datetime")
    if from_t > to_t:
        raise Exception("To timestamp is earlier than From timestamp")

    from_ts = mktime(from_t.timetuple())
    to_ts = mktime(to_t.timetuple())

    response = self._read_command(b'pm add %d %d portstate regexp %s\r\n' %
                                      (from_ts,
                                       to_ts,
                                       description.encode()))

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)

    data2 = response.data.split(" ", 3)
    return int(data2[2])

  def pm_list(self):
    """List ID of all active Maintenance windows"""
    # Lists all Maintenance periods registrered
    # pm list
    # returns 300 with list of all scheduled PM's, exits with ^.$
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    response = self._read_command(b"pm list\r\n")

    ids = []
    for id in response.data:
      if id.isdigit():
        ids.append(int(id))

    return ids

  def pm_cancel(self, id):
    """Cancel a Maintenance window"""
    # Cansels a Maintenance period
    # pm cancel
    #    [2] id      - id of pm to cancel
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    if not isinstance(id, int):
      raise TypeError("ID needs to be an integer")
    response = self._read_command(b"pm cancel %d\r\n" % (id))

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    else:
      return True

  def pm_get_details(self, id):
    """Get details of a Maintenance window"""
    # Get details of a Maintenance period
    # pm details
    #    [2] id      - id of pm
    # returns 200 with details. need testing
    if not self.connStatus:
        raise NotConnectedError("Not connected to device")
    if not self.authenticated:
        raise AuthenticationError("User not authenticated")

    if not isinstance(id, int):
      raise TypeError("ID needs to be an integer")

    response = self._read_command(b"pm details %d\r\n" % (id))

    data2 = response.data.split(' ', 5)
    # print(data2)

    res = {'id': int(data2[0]),
           'from': datetime.fromtimestamp(int(data2[1])),
           'to': datetime.fromtimestamp(int(data2[2])),
           'type': data2[3],
           'm_type': data2[4],
           'device': data2[5]}

    return res

  def pm_get_matching(self, id):
    """Get elements matching a Maintenance window"""
    # TODO: OUTPUT NEEDS A REWRITE!
    # Get list of all ports and devices matching a Maintenance id
    # pm matching
    #    [2] id       - id of pm
    # returns 300 with ports and devices matching id, exits with ^.$
    if not self.connStatus:
        raise NotConnectedError("Not connected to device")
    if not self.authenticated:
        raise AuthenticationError("User not authenticated")
    if not isinstance(id, int):
        raise TypeError("ID needs to be an integer")

    response = self._read_command(b"pm matching %d\r\n" % id)

    # Return list with element 1: "device"portstate,
    #                          2: device
    #                          or
    #                          1: portstate,
    #                          2: device,
    #                          3: interface ifindex,
    #                          4: interface name,
    #                          5: interface descr
    return [d.split(" ", 5)[1::] for d in response.data]

  def pm_add_log(self, id, message):
    """Add log entry to a Maintenance window"""
    # Adds a log message on this PM
    # pm addlog
    #   [2] id        -  id of PM
    # returns 302 please provide new PM log entry, terminate with '.'
    #   <message here>
    # .
    # returns 200? need verification
    if not self.connStatus:
        raise NotConnectedError("Not connected to device")
    if not self.authenticated:
        raise AuthenticationError("User not authenticated")

    if not isinstance(id, int):
        raise TypeError("ID needs to be an integer")

    response = self._read_command(b"pm addlog %d  -\r\n" % (id))

    if not response.header[0] == 302:
      raise Exception("Unknown return from server: %s" % self._buff)

    # Generate Message to zino
    if isinstance(message, list):
      msg = "\r\n".join(message)
    else:
      msg = message

    # Send message
    response = self._read_command(b"%s\r\n\r\n.\r\n" % msg.encode())

    # Check returncode
    if not response.header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def pm_get_log(self, id):
    """List all log entries of a Maintenance window"""
    # Get log of a PM
    # pm log
    #   [2] id       -  ID of pm to gat log from
    # returns 300 log follows, exits with ^.$
    #

    if not isinstance(id, int):
      raise TypeError("ID needs to be a integer")
    if not self.connStatus:
        raise NotConnectedError("Not connected to device")
    if not self.authenticated:
        raise AuthenticationError("User not authenticated")
    self._sock.settimeout(30)
    response = self._read_command(b"pm log %d\r\n" % id)

    # print(header)
    # print(data)
    return _decode_history(response.data)
    # raise NotImplementedError("Not Implemented")

  def init_notifier(self):
      notif = notifier(self)
      notif.connect()
      return notif


class notifier:
  """Zino notifier socket
  Usage:
      notify_session = notifier(ritz_session)
      notify_session.connect()
  or
      with notifier(ritz_session) as notify_session:
          ....
  """
  def __init__(self, zino_session, port=8002, timeout=30):
    self._sock = None
    self.connStatus = False
    self._buff = ""
    self.zino_session = zino_session
    self.port = port
    self.timeout = timeout

  def __enter__(self):
      self.connect()
      return self

  def __exit__(self, type, value, traceback):
      pass

  def connect(self):
    """Connect to notifier socket

    This is automatically executed when using the while statement,
    otherwise the user needs to execute it manually to connect the socket
    Usage:
      notify_session = notifier(ritz_session)
      notify_session.connect()
    """
    if not self._sock:
        self._sock = socket.create_connection((self.zino_session.server, self.port), self.timeout)
        self._buff = self._sock.recv(4096)
        self._sock.setblocking(False)
        rawHeader = self._buff.split(b"\r\n")[0]
        header = rawHeader.split(b" ", 1)
        # print(len(header[0]))
        if len(header[0]) == 40:
            self.connStatus = True
            self._buff = ''

            self.zino_session.ntie(header[0])
        else:
            raise NotConnectedError("Key not found")

  def poll(self, timeout=0):
    """Poll the notifier socket for new data

    Returns a notifier object when data is waiting, otherwise None
    Usage:
        n = notify_socket.poll()
        if n:
            ....
    """

    if not "\r\n" in self._buff:
        # Only check for new messages if no message is waiting for processing
        r, _, _ = select.select([self._sock], [], [], timeout)
        if r:
            try:
                self._buff += self._sock.recv(4096).decode()
            except socket.error as e:
                if not (e.args[0] == errno.EAGAIN or e.args[0] == errno.EWOULDBLOCK):
                    # a "real" error occurred
                    self._sock = None
                    self.connStatus = False
                    raise NotConnectedError("Not connected to server")

    if "\r\n" in self._buff:
        try:
            line, self._buff = self._buff.split('\r\n', 1)
            element = line.split(" ", 2)
            id = int(element[0])
            type = element[1]
            try:
                text = element[2]
            except IndexError:
                text = ""
            return notifierEntry(id, type, text)
        except Exception:
            raise ProtocolError("line: {} , _buff: {}".format(line, self._buff))


if "__main__" == __name__:
    print("This is a library, not an application :)")
