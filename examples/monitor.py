from ritz import ritz, notifier, parse_tcl_config, caseType
from pprint import pprint
from os.path import expanduser
from time import sleep
import re
import argparse
import sys
import logging


cases = {}



def show():
  print(chr(27) + "[2J")      # Clear screen
  for c in cases:
    case = cases[c]
    if case["type"] == caseType.PORTSTATE:
      # LowerLayerDown state is quite long... shorten it
      if "lowerLayerDown" in case["portstate"]:
        portState = "LowerDown"
      else:
        portState = case["portstate"]

      print("%-10s %-8s %-15s %-24s %-s" % (
            portState, case["state"], case["router"],
            case["port"], case["descr"] if "descr" in case else "---"))

def main():
  parser = argparse.ArgumentParser(description='Process some integers.')

  parser.add_argument('--prod', action='store_true')

  args = parser.parse_args()
  conf = parse_tcl_config("~/.ritz.tcl")

  if args.prod:
    c_server = conf["default"]["Server"]
    c_user   = conf["default"]["User"]
    c_secret = conf["default"]["Secret"]
  else:
    c_server = conf["UNINETT-backup"]["Server"]
    c_user   = conf["UNINETT-backup"]["User"]
    c_secret = conf["UNINETT-backup"]["Secret"]

  ritzlog = logging.getLogger("ritz")
  ritzlog.setLevel(logging.DEBUG)
  ritzlog.addHandler(logging.FileHandler('comm.log'))
  sess = ritz(c_server)
  sess.connect()
  sess.authenticate(c_user, c_secret)
  get_caseids = sess.get_caseids()

  for i in get_caseids:
    print("Case: %i" % i)
    cases[i] = sess.get_attributes(i)

  show()

  pass
  notif = notifier(sess)
  notif.connect()
  while True:
    n = notif.poll()
    if n:
      print(n)
      p = n.split(' ', 2)
      if "attr" in p[1]:
        pprint(sess.get_attributes(int(p[0])))
      elif "log" in p[1]:
        pprint(sess.get_log(int(p[0])))
      elif "state" in p[1]:
        v = p[2].split(' ', 1)
        print("State on %s changed from %s to %s" % (p[0], v[0], v[1]))
      else:
        print("UNKNOWN!!!!  : %s" % n)

      print()
    sleep(1)


  if args.CaseID not in get_caseids:
    print(get_caseids)
    print("CaseID %i is not in database" % args.CaseID)
    sys.exit(1)

  pprint(sess.get_attributes(args.CaseID))
  print("Get History: %i" % args.CaseID)
  pprint(sess.gethist(args.CaseID))
  print("Get Log: %i" % args.CaseID)
  pprint(sess.get_log(args.CaseID))
  # print("Add test message to log: 24014")
  # pprint(sess.add_history(24014, "Testmelding ifra pyRitz"))
  # print("set_state 'open': %i" % args.CaseID)
  # pprint(sess.set_state(args.CaseID, "open"))


if __name__ == "__main__":
  main()
