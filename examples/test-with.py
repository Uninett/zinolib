from ritz import ritz, notifier, parse_tcl_config
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

def main():
  parser = argparse.ArgumentParser(description='Process some integers.')

  parser.add_argument('CaseID', metavar='N', type=int,
                      help='CaseID to test with')
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
  with ritz(c_server, username=c_user, password=c_secret) as sess:
    get_caseids = sess.get_caseids()
    if args.CaseID == 0:
      for i in get_caseids:
        print("Case: %i" % i)
        pprint(sess.get_attributes(i))
    elif args.CaseID == 1:
      notif = notifier()
      key = notif.connect(c_server)
      sess.ntie(key)
      while True:
        n = notif.poll()
        if n:
          print n
          p = n.split(' ',2)
          if "attr" in p[1]:
            pprint(sess.get_attributes(int(p[0])))
          elif "log" in p[1]:
            pprint(sess.get_log(int(p[0])))
          elif "state" in p[1]:
            v = p[2].split(' ', 1)
            print("State on %s changed from %s to %s" % (p[0],v[0],v[1]))
          else:
            print("UNKNOWN!!!!  : %s" % n)

          print()
        sleep(1)
    else:
      if args.CaseID not in get_caseids:
        print(get_caseids)
        print("CaseID %i is not in database" % args.CaseID)
        sys.exit(1)

      pprint(sess.get_attributes(args.CaseID))
      print("Get History: %i" % args.CaseID)
      pprint(sess.get_history(args.CaseID))
      print("Get Log: %i" % args.CaseID)
      pprint(sess.get_log(args.CaseID))
      #print("Add test message to log: 24014")
      #pprint(sess.add_history(24014, "Testmelding ifra pyRitz"))
      #print("set_state 'open': %i" % args.CaseID)
      #pprint(sess.set_state(args.CaseID, "open"))
if __name__ == "__main__":
  main()
