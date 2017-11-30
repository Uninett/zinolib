import socket
import hashlib
from pprint import pprint
from datetime import datetime
import errno


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
#                 pm add from_timestamp to_timestamp type m_type
#                 pm lits $$
#                 pm cancel $$
#                 pm details $$
#                 pm matching $$
#                 pm addlog $$
#                 pm log $$
#                 pm help
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
    buffer += data

    if not header:
      if buffer.find(delim) != -1:
        line, buffer = buffer.split('\r\n', 1)
        rawh = line.split(' ', 1)
        header = (int(rawh[0]), rawh[1])
        #header = line
        # Crude error detection :)
        if header[0] >= 500:
          raise ProtocolError(header)
        if header[0] == 200:
          return header[1], header
      next

    while buffer.find(delim) != -1:
      line, buffer = buffer.split('\r\n', 1)
      if line == ".":
        return r,header
      r.append(line)
  return r,header



class ritz():
  def __init__(self):
    self.s = None
    self.connected = None

  def connect(self, server, port=8001, timeout=10):
    # Opens an connection to the Server
    # To do things you need to authenticate after connection
    self.s = socket.create_connection((server, port), timeout)
    self._buff = self.s.recv(4096)
    rawHeader = self._buff.split("\r\n")[0]
    header = rawHeader.split(" ", 2)
    if header[0] == "200":
      self.authChallenge = header[1]
      self.connected = True
    else:
      raise NotConnectedError("Did not get a status code 200")


  def close(self):
    if self.s:
      pass


  @property
  def connected(self):
    if self.s and self.connected and self.authenticated:
      return True;
    return False




  def auth(self, user, password):
    # Authenticate user
    if not self.connected:
      raise NotConnectedError("Not connected to device")

    # Combine Password and authChallenge from Ritz to make authToken
    authToken = hashlib.sha1("%s %s" % (self.authChallenge, password)).hexdigest()

    self.s.send("user %s %s  -\r\n" % (user, authToken))
    self._buff = self.s.recv(4096)
    if self._buff[0:3] == "200":
      self.authenticated = True
      return
    raise AuthenticationError("Access Denied while authenticating")


  def caseids(self):
    if not self.connected:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")

    data,header = readcommand(self.s, "caseids\r\n")

    ids = []
    for id in data:
      if id.isdigit():
        ids.append(int(id))

    return ids


  def getattrs(self, caseid):
    if not self.connected:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    data, header = readcommand(self.s, "getattrs %s\r\n" % caseid)
    caseinfo = {}
    for d in data:
      v = d.split(":",1)
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
    if not self.connected:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    data, header = readcommand(self.s, "gethist %s\r\n" % caseid)
    caseinfo = {}
    #for d in data:
    #  v = d.split(":",1)
    #  caseinfo[v[0].strip()] = v[1].strip()
    return data


  def getlog(self, caseid):
    #   getlog      Get Logs from CaseID
    #   Parameters: caseID
    #   Returns a list of loglines (timestamp, message)
    if not self.connected:
      raise NotConnectedError("Not connected to device")
    if not self.authenticated:
      raise AuthenticationError("User not authenticated")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    #self.s.send("getattrs %d\r\n" % caseid)
    #print "Getting %s " % caseid
    data, header = readcommand(self.s, "getlog %s\r\n" % caseid)
    caseinfo = {}
    #for d in data:
    #  v = d.split(":",1)
    #  caseinfo[v[0].strip()] = v[1].strip()
    return data


  def addhist(self, caseid, message):
    # ZinoServer:
    # paramters: case-id
    # 302 please provide new history entry, termiate with '.'

    # Start Command
    self.s.send("addhist %s  -\r\n" % (caseid))
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "302":
      raise Exception("Unknown return from server: %s" % self._buff)

    # Generate Message to zino
    if isinstance(message, list):
      msg = "\r\n".join(message)
    else:
      msg = message

    # Send message
    self.s.send("%s\r\n\r\n.\r\n" % msg)

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "200":
      raise Exception("Not getting 200 status from server: %s" % self._buff)
    return True


  def setstate(self, caseid, state):
    if state not in ["open", "working",
                     "waiting", "confirm-wait",
                     "ignored", "closed"]:
      raise Exception("Illegal state")
    if not isinstance(caseid, int):
      raise TypeError("CaseID needs to be an integer")
    self.s.send("setstate %s %s\r\n" % (caseid, state))

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "200":
      raise Exception("Not getting 200 status from server: %s" % self._buff)
    return True


  def pollrtr(self, router):
    self.s.send("pollrtr %s\r\n" % router)

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "200":
      raise Exception("Not getting 200 status from server: %s" % self._buff)
    return True


  def pollintf(self, router, ifindex):
    if not isinstance(ifindex, int):
        raise TypeError("CaseID needs to be an interger")
    self.s.send("pollintf %s %s\r\n" % (router, ifindex))

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "200":
      raise Exception("Not getting 200 status from server: %s" % self._buff)
    return True
    pass


  def ntie(self, key):
    # Tie to notification channel
    # Parameters: key:
    #   key is key reported by notification channel.
    self.s.send("ntie %s\r\n" % key)

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "200":
      raise Exception("Not gettingstatus from server: %s" % self._buff)
    return True
    pass


    def pmAdd(self):
      #pm add from_timestamp to_timestamp type m_type
      raise NotImplementedError("pmAdd not Implemented")


    def pmlist(self):
      #pm list
      raise NotImplementedError("pmList not Implemented")


    def pmCancel(self):
      #pm cancel
      raise NotImplementedError("pmCancel not Implemented")


    def pmDetails(self):
      #pm details
      raise NotImplementedError("pmDetails not Implemented")


    def pmMatching(self):
      #pm matching
      raise NotImplementedError("pmMatching not Implemented")


    def pmAddLog(self):
      #pm addlog
      raise NotImplementedError("pmAddLog not Implemented")


    def pmLog(self):
      #pm log
      raise NotImplementedError("Not Implemented")



class notifier():
  def __init__(self):
    self.s = None
    self.connected = False
    self._buff = ""

  def connect(self, server, port = 8002, timeout = 30):
    if not self.s:
      self.s = socket.create_connection((server, port), timeout)
      self._buff = self.s.recv(4096)
      self.s.setblocking(False)
      rawHeader = self._buff.split("\r\n")[0]
      header = rawHeader.split(" ", 1)
      #print len(header[0])
      if len(header[0]) == 40:
        self.connected = True
        self._buff = ''

        return header[0]
      else:
        raise NotConnectedError("Key not found")


  def poll(self):
    try:
      self._buff += self.s.recv(4096)
    except socket.error, e:
      if not (e.args[0] == errno.EAGAIN or e.args[0] == errno.EWOULDBLOCK):
        # a "real" error occurred
        self.s = None
        self.connected = False
        raise NotConnectedError("Not connected to server")

    if "\r\n" in self._buff:
      line, self._buff = self._buff.split('\r\n', 1)
      return line




if "__main__" == __name__:
    print("This is a library, not a application :)")
