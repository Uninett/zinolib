from ritz import ritz,notifier
from pprint import pprint
from os.path import expanduser
from time import sleep
import re
import argparse
import sys
from datetime import datetime, timedelta


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

  parser.add_argument('--prod', action='store_true')
  parser.add_argument('--remove-all-pms', action='store_true')

  args = parser.parse_args()
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
  sess = ritz(c_server)
  sess.connect()
  sess.authenticate(c_user, c_secret)

  return sess


  return






if __name__ == "__main__":
  s = main()
