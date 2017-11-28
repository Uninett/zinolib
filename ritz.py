import socket
import hashlib
from pprint import pprint


# Things to implement
# /local/src/zino/zino/server.tcl
# proc ServerCmd { chan line } {
#   user        Authenticate user
#               Status: Login implemented

#   nsocket     doNsocketCmd $chan $l

#   ntie        Connect to notification socket
#               Status: NOT implemented

#   caseids     Get list of caseids
#               Status: caseids implemented

#   clearflap   doClearFlap $chan $l

#   getattrs    Get attributes of CaseID
#               Status: Crude implementation

#   getlog      Get Logs from CaseID
#               Status: Crude implementation

#   gethist     Get History from CaseID
#               Status: Crude implementation

#   addhist     Add history line to CaseID
#               Status: addhist Implemented

#   setstate    Set noe state on caseID
#               Status: setstate implemented

#   community   doCommunityCmd $chan $l
#   pollintf    Poll a router
#               State: implemented but not tested

#   pollrtr     Poll an interface
#               State: implemented but not Testmelding

#   pm          doPM $chan $l
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



class ritz_channel():
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

    return data


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
    if not isinstance(ifindex, int)
    self.s.send("pollintf %s %s\r\n" % (router, ifindex))

    # Check returncode
    self._buff = self.s.recv(4096)
    if not self._buff[0:3] == "200":
      raise Exception("Not getting 200 status from server: %s" % self._buff)
    return True
    pass



if "__main__" == __name__:
    print("This is a library, not a application :)")
