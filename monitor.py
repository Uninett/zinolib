from ritz import ritz, notifier, parse_config
from pprint import pprint
from os.path import expanduser
from time import sleep
from termcolor import cprint
import re
import argparse
import sys
import logging
import sys


cases = {}



def show():
  # print(chr(27) + "[2J")      # Clear screen
  print("\033c")              #Clear screen
  for c in cases:
    case = cases[c]
    if case["state"] in ("ignored","working", "waiting","closed"):
        continue
    if "portstate" in case["type"]:
      # LowerLayerDown state is quite long... shorten it
      if "lowerLayerDown" in case["portstate"]:
        portState = "LowerDown"
      else:
        portState = case["portstate"]

      cprint("%-10s %-8s %-15s %-24s %-s" % (
            portState, case["state"], case["router"],
            case["port"], case["descr"] if "descr" in case else "---"),"yellow")

    elif "reachability" in case["type"]:
      cprint(" DEVICE DOWN: %s" % case["router"], "red")

def main():
  parser = argparse.ArgumentParser(description='Process some integers.')

  parser.add_argument('--prod', action='store_true')

  args = parser.parse_args()
  conf = parse_config("~/.ritz.tcl")

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
  print("Collecting cases:")
  for i in get_caseids:
    sys.stdout.write(" %i" % i)
    sys.stdout.flush()
    cases[i] = sess.get_attributes(i)

  sys.stdout.write("\n\n")
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
        case = int(p[0])
        cases[case] = sess.get_attributes(case)
        #pprint(sess.get_attributes(int(p[0])))
      #elif "log" in p[1]:
      #  pprint(sess.get_log(int(p[0])))
      elif "state" in p[1]:
        v = p[2].split(' ', 1)
        print("State on %s changed from %s to %s" % (p[0], v[0], v[1]))
      else:
        print("UNKNOWN EVENT !!!!  : %s" % n)

      print()
    sleep(1)



if __name__ == "__main__":
  main()
