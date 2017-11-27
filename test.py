from ritz import ritz_channel
from pprint import pprint
from os.path import expanduser
import re

def importconf(file):
  config = {}
  with open(expanduser(file), "r") as f:
    for line in f.readlines():
      sets = re.findall("^\s?set\s+(\S+)\s+(.*)$", line)
      if sets:
        config[sets[0][0]] = sets[0][1]
  return config

def main():
  sess = ritz_channel()
  conf = importconf("~/.ritz.tcl")
  pprint(conf)
  sess.connect(conf["_Server(UNINETT-backup)"])
  sess.auth(conf["_User(UNINETT-backup)"], conf["_Secret(UNINETT-backup)"])
  caseids = sess.caseids()
  for i in caseids:
    print("Case: %s" % i)
    pprint(sess.getattrs(int(i)))
  print("Get History: 23936")
  pprint(sess.gethist(23936))
  print("Get Log: 23936")
  pprint(sess.getlog(23936))

if __name__ == "__main__":
  main()
