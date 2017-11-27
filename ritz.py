import socket
import hashlib
from pprint import pprint

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
    self.s = socket.create_connection((server, port), timeout)
    self._buff = self.s.recv(4096)
    rawHeader = self._buff.split("\r\n")[0]
    header = rawHeader.split(" ", 2)
    if header[0] == "200":
      self.authChallenge = header[1]
      self.connected = True
    else:
      raise NotConnectedError("Did not get a status code 200")

  def auth(self, user, password):
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

  def close(self):
    if self.s:
      pass


if "__main__" == __name__:
    print("This is a library, not a application :)")
