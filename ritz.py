import logging
import socket
import hashlib
import enum
import ipaddress
from pprint import pprint
from datetime import datetime
import errno
from time import mktime
import re
from os.path import expanduser

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

def _read_command(sock, command, recv_buffer=4096, delim='\r\n'):
  """Read a command from the ritz TCP socket

  This code neds a rewrite, maby use socket file object?
  everything is \r\n terminated
  """
  global logger
  buffer = ''
  data = True
  header = False
  r = []
  logger.debug("send: %s" % command.__repr__())
  if command:
    sock.send(command)
  while data:
    try:
        data = sock.recv(recv_buffer)
    except socket.timeout as e:
        raise TimeoutError("Timed out waiting for data. command: %s buffer: %s" % (repr(command), repr(buffer)))
    logger.debug("recv: %s" % data.__repr__())
    # buffer += data.decode('UTF-8')
    buffer += data.decode('latin-1')

    if not header:
      if buffer.find(delim) != -1:
        try:
          line, buffer = buffer.split('\r\n', 1)  # '\r\n' is not a byte
          rawh = line.split(' ', 1)  # ' ' is not a byte
          header = (int(rawh[0]), rawh[1])
        except ValueError as e:
            raise ProtocolError("Illegal response from server detected: %s" % repr(line))
        # header = line
        # Crude error detection :)
        if header[0] >= 500:
          # Die on Error codes
          return header[1], header
          # raise ProtocolError("Errorcode '%s %s' reported from server" % (header[0], header[1]))
        if header[0] == 200:
          # Return to user on 200, 200 doesent add more data
          return header[1], header
        if header[0] == 302:
          # Return to user on 302, wee need more data
          return header[1], header
      next

    while buffer.find(delim) != -1:
      line, buffer = buffer.split('\r\n', 1)  # '\r\n' is not a byte
      if line == ".":
        return r, header
      r.append(line)
  if not header:
      raise ProtocolError("No header info detected for command %s, buffer %s" % (repr(command), repr(buffer)))
  return r, header


def _decode_history(logarray):
  """Decode history

  Decodes a history "object" from the tcp socket and returns a list with history dict objects
  """
  ret = []
  curr = {}
  for log in logarray:
    if not log[0] == " ":
      # This is a header line
      curr = {}
      curr["log"] = []

      header = log.split(" ", 1)
      curr["header"] = header
      curr["date"] = datetime.fromtimestamp(int(header[0]))

      if header[1].count(" ") is not 0:
        # this is a short system log
        curr["log"] = [header[1]]
        curr["user"] = re.match(".*\((\w+)\)$", header[1]).group(1)
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


def parse_config(file):
  """Parse a .ritz.tcl config file

  Used to fetch a users connection information to connect to zino
  """
  config = {}
  with open(expanduser(file), 'r') as f:
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
  """

  def __init__(self, zino, caseid):
    self._zino = zino
    self._caseid = caseid
    self._attrs = self._zino.get_attributes(caseid)

  def __repr__(self):
    return "%s(%s)" % (str(self.__class__), self._caseid)

  def clear_flapping(self):
    """Clear flapping state if this case object"""
    if self.type == "portstate":
      return self._zino.clear_flapping(self._attrs["router"],
                                       self._attrs["ifindex"])
    else:
      raise AttributeError("clear_flapping is only supported when type is portstate")

  def add_history(self, message):
    """Add a history line to this case object"""
    return self._zino.add_history(self._caseid, message)

  def set_state(self, state):
    """Set case to new state"""
    return self._zino.set_state(self._caseid, state)

  def poll(self):
      if self.type == caseType.PORTSTATE:
          return self._zino.poll_interface(self._attrs["router"],
                                           self._attr["ifindex"])
      elif self.type == [caseType.RECABILITY, caseType.ALARM, caseType.BGP]:
          return self._zino_poll_device(self._attrs["router"])
      else:
          raise TypeError("poll_interface is not supported under case type '%s'" % str(self._attr["type"]))

  def __getattr__(self, name):
    """Wrapper to get all attributbutes of the object as python attributes"""
    if name in self._attrs:
      return self._attrs[name]
    elif 'history' == name:
      return self._zino.get_history(self._caseid)
    elif 'log' == name:
      return self._zino.get_log(self._caseid)
    else:
      raise AttributeError("%s instance of type %s has no attribute '%s'" % (self.__class__, self._attrs["type"], name))
    return self

  def __getitem__(self, key):
      """Wrapper to dict

      Makes the object act as a dict object, used when the key is a string
      """
      return self.__getattr__(key)

  def keys(self):
      k = [k for k in self._attrs.keys()]
      k.append('history')
      k.append('log')
      return k

  def has_key(self, k):
              return k in self._attrs


class ritz():
  """Connect to zino datachannel."""
  def __init__(self,
               server,
               port=8001,
               timeout=10,
               username=None,
               password=None):
    """Initialize"""
    global logger

    self.s = None
    self.connStatus = False
    self.server = server
    self.port = port
    self.timeout = timeout
    self.username = username
    self.password = password

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

  def connect(self):
    """Connect to zino datachannel"""
    # Opens an connection to the Server
    # To do things you need to authenticate after connection
    self.s = socket.create_connection((self.server, self.port), self.timeout)
    data, header = _read_command(self.s, None)
    if header[0] == 200:
      self.authChallenge = header[1].split(' ', 1)[0]
      self.connStatus = True
    else:
      raise NotConnectedError("Did not get a status code 200")

    # Automaticly authenticate if username and password is supplied
    if self.username and self.password:
      self.authenticate(self.username, self.password)

  def close(self):
    """Disconnect zino datachennel"""
    if self.s:
      self.s.close()
      self.s = None
      self.connStatus = False
      self.authenticated = False

  @property
  def connected(self):
    """Returns True when datachannel is connected"""
    if self.s and self.connStatus and self.authenticated:
      return True
    return False

  def authenticate(self, user, password):
    """Authenticate a user on the zino datachannel"""
    # Authenticate user
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")

    # Combine Password and authChallenge from Ritz to make authToken
    genToken = "%s %s" % (self.authChallenge, password)
    authToken = hashlib.sha1(genToken.encode('UTF-8')).hexdigest()
    cmd = 'user %s %s  -\r\n' % (user, authToken)
    #  try:
    try:
      data, header = _read_command(self.s, cmd.encode('UTF-8'))
    #  except ProtocolError as e:
    #    raise AuthenticationError(e)
      if header[0] == 200:
        self.authenticated = True
        return
      else:
          raise AuthenticationError("Unable to authenticate user, '%s'" % repr(header))
    except TypeError as e:
      raise ProtocolError("Got an illegal response from the server")

  def case(self, id):
    """Get a zino Case object"""
    return Case(self, id)

  def cases(self):
    """Get a list with all cases in zino"""
    return list(self.cases_iter())

  def cases_iter(self):
    """Return list with cases from zino as a iter"""
    for k in self.get_caseids():
      yield Case(self, k)

  def get_caseids(self):
    """Get list of CaseID's that exists in zino"""
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    data, header = _read_command(self.s, b"caseids\r\n")

    ids = []
    for id in data:
      if id.isdigit():
        ids.append(int(id))

    return ids

  def get_attributes(self, caseid):
    """Collect all attributes of a zino CaseID object"""
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    cmd = "getattrs %s\r\n" % caseid
    data, header = _read_command(self.s, cmd.encode('UTF-8'))
    caseinfo = {}
    for d in data:
      v = d.split(":", 1)
      caseinfo[v[0].strip()] = v[1].strip()

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
    if 'ac-down' in caseinfo:
      caseinfo['ac-down'] = int(caseinfo['ac-down'])
    if 'state' in caseinfo:
      caseinfo['state'] = caseState(caseinfo['state'])
    if 'type' in caseinfo:
      caseinfo['type'] = caseType(caseinfo['type'])
    if 'polladdr' in caseinfo:
      caseinfo['polladdr'] = ipaddress.ip_address(caseinfo['polladdr'])
    if 'remote-addr' in caseinfo:
      caseinfo['remote-addr'] = ipaddress.ip_address(caseinfo['remote-addr'])

    return caseinfo

  def get_history(self, caseid):
    """Return all history elements of a CaseID"""
    #   gethist     Get Logs from CaseID
    #   Parameters: caseID
    #   Returns a list of historylines (timestamp, message)??
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    data, header = _read_command(self.s, b"gethist %d\r\n" % caseid)
    # caseinfo = {}
    # for d in data:
    #   v = d.split(":",1)
    #   caseinfo[v[0].strip()] = v[1].strip()

    return _decode_history(data)

  def get_log(self, caseid):
    """Return all log elements of a CaseID"""
    #   getlog      Get Logs from CaseID
    #   Parameters: caseID
    #   Returns a list of loglines (timestamp, message)
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")

    data, header = _read_command(self.s, b"getlog %d\r\n" % caseid)

    return data

  def add_history(self, caseid, message):
    """Add a history element on a CaseID"""
    # ZinoServer:
    # paramters: case-id
    # 302 please provide new history entry, termiate with '.'

    # Generate Message to zino
    if isinstance(message, list):
      msg = "\r\n".join(message)
    else:
      msg = message

    # Start Command
    data, header = _read_command(self.s, b"addhist %d  -\r\n" % (caseid))
    if not header[0] == 302:
      raise ProtocolError("Unknown return from server: %s" % data)

    # Send message
    data, header = _read_command(self.s, b"%s\r\n\r\n.\r\n" % msg.encode())
    if not header[0] == 200:
      raise ProtocolError("Not getting 200 OK from server: %s" % data)
    return True

  def set_state(self, caseid, state):
    if state not in ["open", "working",
                     "waiting", "confirm-wait",
                     "ignored", "closed"]:
      raise TypeError("Illegal state")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")

    data, header = _read_command(self.s, b"setstate %d %s\r\n" % (caseid, state.encode()))

    # Check returncode
    if not header[0] == 200:
      raise ValueError("Unable to change state on %d to %s. error: %s" % (caseid, state, repr(header)))
    return True

  def clear_flapping(self, router, ifindex):
    """Clear port flapping information on a interface"""
    if not isinstance(ifindex, int):
      raise TypeError("CaseID needs to be an integer")

    data, header = _read_command(self.s, b"clearflap %s %d\r\n" % (router.encode(), ifindex))

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def poll_router(self, router):
    """Poll a router for new data"""
    data, header = _read_command(self.s, b"pollrtr %s\r\n" % router.encode())

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def poll_interface(self, router, ifindex):
    """Poll interface for new information"""
    if not isinstance(ifindex, int):
        raise TypeError("CaseID needs to be an interger")
    data, header = _read_command(self.s, b"pollintf %s %d\r\n" % (router.encode(), ifindex))

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True
    pass

  def ntie(self, key):
    """Tie to notification notification channel

    Connect datachannel and notification channel together,
    used by connect function on the notifier() object
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
    data, header = _read_command(self.s, b"ntie %s\r\n" % key)

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % header.__repr__())
    return True
    pass

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

    data, header = _read_command(self.s, b'pm add %d %d device %s %s\r\n' %
                                 (from_ts,
                                  to_ts,
                                  m_type.encode(),
                                  device.encode()))

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)

    data2 = data.split(" ", 3)
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

    data, header = _read_command(self.s, b'pm add %d %d portstate intf-regexp %s %s\r\n' %
                                 (from_ts,
                                  to_ts,
                                  device.encode(),
                                  interface.encode()))

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)

    data2 = data.split(" ", 3)
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

    data, header = _read_command(self.s, b'pm add %d %d portstate regexp %s\r\n' %
                                 (from_ts,
                                  to_ts,
                                  description.encode()))

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)

    data2 = data.split(" ", 3)
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

    data, header = _read_command(self.s, b"pm list\r\n")

    ids = []
    for id in data:
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
    data, header = _read_command(self.s, b"pm cancel %d\r\n" % (id))

    # Check returncode
    if not header[0] == 200:
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

    data, header = _read_command(self.s, b"pm details %d\r\n" % (id))

    data2 = data.split(' ', 5)
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

    data, header = _read_command(self.s, b"pm matching %d\r\n" % id)

    # Return list with element 1: "device"portstate,
    #                          2: device
    #                          or
    #                          1: portstate,
    #                          2: device,
    #                          3: interface ifindex,
    #                          4: interface name,
    #                          5: interface descr
    return [d.split(" ", 5)[1::] for d in data]

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

    data, header = _read_command(self.s, b"pm addlog %d  -\r\n" % (id))

    if not header[0] == 302:
      raise Exception("Unknown return from server: %s" % self._buff)

    # Generate Message to zino
    if isinstance(message, list):
      msg = "\r\n".join(message)
    else:
      msg = message

    # Send message
    data, header = _read_command(self.s, b"%s\r\n\r\n.\r\n" % msg.encode())

    # Check returncode
    if not header[0] == 200:
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
    self.s.settimeout(30)
    data, header = _read_command(self.s, b"pm log %d\r\n" % id)

    # print(header)
    # print(data)
    return _decode_history(data)
    # raise NotImplementedError("Not Implemented")


class notifier:
  """Zino notifier socket"""
  def __init__(self, zino_session, port=8002, timeout=30):
    self.s = None
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
    if not self.s:
        self.s = socket.create_connection((self.zino_session.server, self.port), self.timeout)
        self._buff = self.s.recv(4096)
        self.s.setblocking(False)
        rawHeader = self._buff.split(b"\r\n")[0]
        header = rawHeader.split(b" ", 1)
        # print(len(header[0]))
        if len(header[0]) == 40:
            self.connStatus = True
            self._buff = ''

            self.zino_session.ntie(header[0])
        else:
            raise NotConnectedError("Key not found")

  def poll(self):
    """Poll the notifier socket for new data"""
    try:
        self._buff += self.s.recv(4096).decode()
    except socket.error as e:
        if not (e.args[0] == errno.EAGAIN or e.args[0] == errno.EWOULDBLOCK):
            # a "real" error occurred
            self.s = None
            self.connStatus = False
            raise NotConnectedError("Not connected to server")

    if "\r\n" in self._buff:
        line, self._buff = self._buff.split('\r\n', 1)
        return line



if "__main__" == __name__:
    print("This is a library, not an application :)")
