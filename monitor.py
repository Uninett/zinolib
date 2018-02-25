from ritz import ritz, notifier
from pprint import pprint
from os.path import expanduser
from time import sleep
import re
import argparse
import sys


def importconf(file):
  config = {}
  with open(expanduser(file), "r") as f:
    for line in f.readlines():
      sets = re.findall("^\s?set\s+(\S+)\s+(.*)$", line)
      if sets:
        config[sets[0][0]] = sets[0][1]
  return config


cases = {}



def show():
  print(chr(27) + "[2J")      # Clear screen
  for c in cases:
    case = cases[c]
    if "portstate" in case["type"]:
      # LowerLayerDown state is quite long... shorten it
      if "lowerLayerDown" in case["portstate"]:
        portState = "LowerDown"
      else:
        portState = case["portstate"]

      print("%-10s %-8s %-15s %-24s %-s" % (
            portState, case["state"], case["router"],
            case["port"], case["descr"]))

def main():
  parser = argparse.ArgumentParser(description='Process some integers.')

  parser.add_argument('--prod', action='store_true')

  args = parser.parse_args()
  sess = ritz()
  conf = importconf("~/.ritz.tcl")
  pprint(conf)
  if args.prod:
    c_server = conf["_Server(UNINETT)"]
    c_user   = conf["_User(UNINETT)"]
    c_secret = conf["_Secret(UNINETT)"]
  else:
    c_server = conf["_Server(UNINETT-backup)"]
    c_user   = conf["_User(UNINETT-backup)"]
    c_secret = conf["_Secret(UNINETT-backup)"]
  sess.connect(c_server)
  sess.auth(c_user, c_secret)
  caseids = sess.caseids()

  for i in caseids:
    print("Case: %i" % i)
    cases[i] = sess.getattrs(i)

  show()

  pass
  notif = notifier()
  key = notif.connect(c_server)
  sess.ntie(key)
  while True:
    n = notif.poll()
    if n:
      print(n)
      p = n.split(' ', 2)
      if "attr" in p[1]:
        pprint(sess.getattrs(int(p[0])))
      elif "log" in p[1]:
        pprint(sess.getlog(int(p[0])))
      elif "state" in p[1]:
        v = p[2].split(' ', 1)
        print("State on %s changed from %s to %s" % (p[0], v[0], v[1]))
      else:
        print("UNKNOWN!!!!  : %s" % n)

      print()
    sleep(1)


  if args.CaseID not in caseids:
    print(caseids)
    print("CaseID %i is not in database" % args.CaseID)
    sys.exit(1)

  pprint(sess.getattrs(args.CaseID))
  print("Get History: %i" % args.CaseID)
  pprint(sess.gethist(args.CaseID))
  print("Get Log: %i" % args.CaseID)
  pprint(sess.getlog(args.CaseID))
  # print("Add test message to log: 24014")
  # pprint(sess.addhist(24014, "Testmelding ifra pyRitz"))
  # print("Setstate 'open': %i" % args.CaseID)
  # pprint(sess.setstate(args.CaseID, "open"))


if __name__ == "__main__":
  main()
