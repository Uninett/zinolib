import socket
import hashlib
from pprint import pprint
from datetime import datetime
import errno
from time import mktime
import re


# Things to implement
# /local/src/zino/zino/server.tcl
#   user        Authenticate user
#               Status: Implemented

#   nsocket     Outdated, DO NOT IMPLEMENT

#   ntie        Connect to notification socket
#               Status: NOT implemented

#   caseids     Get list of caseids
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


def readcommand(sock, command, recv_buffer=4096, delim='\r\n'):
  # Reads socket buffer until the end of datastructure
  buffer = ''
  data = True
  header = False
  r = []

  sock.send(command)
  while data:
    data = sock.recv(recv_buffer)
    # buffer += data.decode('UTF-8')
    buffer += data.decode('latin-1')

    if not header:
      if buffer.find(delim) != -1:
        line, buffer = buffer.split('\r\n', 1)  # '\r\n' is not a byte
        rawh = line.split(' ', 1)  # ' ' is not a byte
        header = (int(rawh[0]), rawh[1])
        # header = line
        # Crude error detection :)
        if header[0] >= 500:
          raise ProtocolError(header)
        if header[0] == 200:
          return header[1], header
      next

    while buffer.find(delim) != -1:
      line, buffer = buffer.split('\r\n', 1)  # '\r\n' is not a byte
      if line == ".":
        return r, header
      r.append(line)
  return r, header


def decodeHistory(logarray):
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


class ritz():
  """Connect to zino datachannel."""
  def __init__(self,
               server,
               port=8001,
               timeout=10,
               username=None,
               password=None):
    """Initialize."""
    self.s = None
    self.connStatus = False
    self.server = server
    self.port = port
    self.timeout = timeout
    self.username = username
    self.password = password

  def __enter__(self):
    self.connect()
    return self

  def __exit__(self, type, value, traceback):
    pass
    # self.close()

  def connect(self):
    # Opens an connection to the Server
    # To do things you need to authenticate after connection
    self.s = socket.create_connection((self.server, self.port), self.timeout)
    self._buff = self.s.recv(4096)
    rawHeader = self._buff.split(b"\r\n")[0]
    header = rawHeader.split(b" ", 2)
    print("header:'{}'".format(header))
    if header[0] == b"200":
      self.authChallenge = header[1]
      self.connStatus = True
    else:
      raise NotConnectedError("Did not get a status code 200")

    # Automaticly authenticate if username and password is supplied
    if self.username and self.password:
      self.authenticate(self.username, self.password)

  def close(self):
    if self.s:
      pass
    raise NotImplementedError("close is not implemented")

  @property
  def connected(self):
    if self.s and self.connStatus and self.authenticated:
      return True
    return False

  def auth(self, user, password):
    # Authenticate user
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")

    # Combine Password and authChallenge from Ritz to make authToken
    genToken = "%s %s" % (self.authChallenge.decode('UTF-8'), password)
    authToken = hashlib.sha1(genToken.encode('UTF-8')).hexdigest()
    cmd = 'user %s %s  -\r\n' % (user, authToken)
    self.s.send(bytes(cmd.encode('UTF-8')))
    self._buff = self.s.recv(4096)
    if self._buff[0:3] == b"200":
      self.authenticated = True
      return
    raise AuthenticationError("Access Denied while authenticating")

  def caseids(self):
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    data, header = readcommand(self.s, b"caseids\r\n")

    ids = []
    for id in data:
      if id.isdigit():
        ids.append(int(id))

    return ids

  def getattrs(self, caseid):
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    cmd = "getattrs %s\r\n" % caseid
    data, header = readcommand(self.s, cmd.encode('UTF-8'))
    caseinfo = {}
    for d in data:
      v = d.split(b":", 1)
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

    return caseinfo

  def gethist(self, caseid):
    #   gethist     Get Logs from CaseID
    #   Parameters: caseID
    #   Returns a list of historylines (timestamp, message)??
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    data, header = readcommand(self.s, "gethist %s\r\n" % caseid)
    # caseinfo = {}
    # for d in data:
    #   v = d.split(":",1)
    #   caseinfo[v[0].strip()] = v[1].strip()

    return decodeHistory(data)

  def getlog(self, caseid):
    #   getlog      Get Logs from CaseID
    #   Parameters: caseID
    #   Returns a list of loglines (timestamp, message)
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    # self.s.send("getattrs %d\r\n" % caseid)
    # print("Getting %s " % caseid)
    data, header = readcommand(self.s, "getlog %s\r\n" % caseid)
    # caseinfo = {}
    # for d in data:
    #   v = d.split(":",1)
    #   caseinfo[v[0].strip()] = v[1].strip()
    return data

  def addhist(self, caseid, message):
    # ZinoServer:
    # paramters: case-id
    # 302 please provide new history entry, termiate with '.'

    # Start Command
    self.s.send(b"addhist %s  -\r\n" % (caseid))
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "302":
      raise Exception("Unknown return from server: %s" % self._buff)

    # Generate Message to zino
    if isinstance(message, list):
      msg = "\r\n".join(message)
    else:
      msg = message

    # Send message
    self.s.send(b"%b\r\n\r\n.\r\n" % msg.encode())

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == b"200":
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def setstate(self, caseid, state):
    if state not in ["open", "working",
                     "waiting", "confirm-wait",
                     "ignored", "closed"]:
      raise Exception("Illegal state")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    self.s.send(b"setstate %s %s\r\n" % (caseid, state.encode()))

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == b"200":
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def pollrtr(self, router):
    self.s.send(b"pollrtr %s\r\n" % router.encode())

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "200":
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

  def pollintf(self, router, ifindex):
    if not isinstance(ifindex, int):
        raise TypeError("CaseID needs to be an interger")
    self.s.send(b"pollintf %s %s\r\n" % (router.encode(), ifindex))

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == b"200":
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True
    pass

  def ntie(self, key):
    # Tie to notification channel
    # Parameters: key:
    #   key is key reported by notification channel.
    self.s.send(b"ntie %s\r\n" % key)

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == b"200":
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True
    pass

  def pmAddDevice(self, from_t, to_t, device, m_type="exact"):
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
        raise Exception("To timestamp is earlier than From timestamp")
    if m_type not in ("exact", "str", "regexp"):
        raise Exception("Unknown m_type, needs to be exact, str or regexp")

    from_ts = mktime(from_t.timetuple())
    to_ts = mktime(to_t.timetuple())

    data, header = readcommand(self.s, b'pm add %d %d device %s %s\r\n' %
                               (from_ts,
                                to_ts,
                                m_type.encode(),
                                device.encode()))

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)

    data2 = data.split(" ", 3)
    return int(data2[2])

  def pmAddInterface(self, from_t, to_t, device, interface):
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

    data, header = readcommand(self.s, b'pm add %d %d portstate %s %s\r\n' %
                               (from_ts,
                                to_ts,
                                device.encode(),
                                interface.encode()))

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)

    data2 = data.split(" ", 3)
    return int(data2[2])

  def pmList(self):
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

    data, header = readcommand(self.s, b"pm list\r\n")

    ids = []
    for id in data:
      if id.isdigit():
        ids.append(int(id))

    return ids

  def pmCancel(self, id):
    # Cansels a Maintenance period
    # pm cancel
    #    [2] id      - id of pm to cancel
    if not self.connStatus:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    if not isinstance(id, int):
      raise TypeError("ID needs to be an integer")
    data, header = readcommand(self.s, b"pm cancel %d\r\n" % (id))

    # Check returncode
    if not header[0] == 200:
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    else:
      return True

  def pmDetails(self, id):
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

    data, header = readcommand(self.s, b"pm details %d\r\n" % (id))

    data2 = data.split(' ', 5)
    print(data2)

    res = {'id': int(data2[0]),
           'from': datetime.fromtimestamp(int(data2[1])),
           'to': datetime.fromtimestamp(int(data2[2])),
           'type': data2[3],
           'm_type': data2[4],
           'device': data2[5]}

    return res

  def pmMatching(self, id):
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

    data, header = readcommand(self.s, b"pm matching %d\r\n" % id)

    # What to return?
    print(header)
    print(data)
    # raise NotImplementedError("pmMatching not Implemented")

  def pmAddLog(self, id, message):
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

    self.s.send(b"pm addlog %d  -\r\n" % (id))
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "302":
      raise Exception("Unknown return from server: %s" % self._buff)

    # Generate Message to zino
    if isinstance(message, list):
      msg = "\r\n".join(message)
    else:
      msg = message

    # Send message
    self.s.send(b"%s\r\n\r\n.\r\n" % msg.encode())

    # Check returncode
    self._buff = self.s.recv(4096)
    print self._buff

    if not self._buff[0:3] == b"200":
      raise Exception("Not getting 200 OK from server: %s" % self._buff)
    return True

    raise NotImplementedError("pmAddLog not Implemented")

  def pmLog(self, id):
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
    data, header = readcommand(self.s, b"pm log %d\r\n" % id)

    # print(header)
    # print(data)
    return decodeHistory(data)
    # raise NotImplementedError("Not Implemented")


class notifier():
  def __init__(self):
    self.s = None
    self.connStatus = False
    self._buff = ""

  def connect(self, server, port=8002, timeout=30):
    if not self.s:
      self.s = socket.create_connection((server, port), timeout)
      self._buff = self.s.recv(4096)
      self.s.setblocking(False)
      rawHeader = self._buff.split(b"\r\n")[0]
      header = rawHeader.split(b" ", 1)
      # print(len(header[0]))
      if len(header[0]) == 40:
        self.connStatus = True
        self._buff = ''

        return header[0]
      else:
        raise NotConnectedError("Key not found")

  def poll(self):
    try:
      self._buff += self.s.recv(4096)
    except socket.error as e:
      if not (e.args[0] == errno.EAGAIN or e.args[0] == errno.EWOULDBLOCK):
        # a "real" error occurred
        self.s = None
        self.connStatus = False
        raise NotConnectedError("Not connected to server")

    if "\r\n" in self._buff:
      line, self._buff = self._buff.split(b'\r\n', 1)
      return line


if "__main__" == __name__:
    print("This is a library, not a application :)")
