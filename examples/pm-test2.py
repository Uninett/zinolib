from ritz import ritz, notifier, parse_tcl_config
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
  conf = parse_tcl_config("~/.ritz.tcl")

  if args.prod:
    c_server = conf["default"]["Server"]
    c_user   = conf["default"]["User"]
    c_secret = conf["default"]["Secret"]
  else:
    c_server = conf["UNINETT-backup"]["Server"]
    c_user   = conf["UNINETT-backup"]["User"]
    c_secret = conf["UNINETT-backup"]["Secret"]
  sess = ritz(c_server)
  sess.connect(c_server)
  sess.authenticate(c_user, c_secret)

  print("List all PMs:")
  pm = sess.pm_list()
  print(pm)
  #for i in pm:
  #  print("canceling %d" % i)
  #  sess.pmCancel(i)

  print("Schedule test pm:")
  pm = sess.pm_add_device(datetime.now()+timedelta(minutes=1),
                          datetime.now()+timedelta(minutes=10),
                          "teknobyen-gw", m_type='str')
  print("Scheduled")

  print("List all PMs:")
  pms = sess.pm_list()
  print(pm)

  print("pmDetails:")
  print(sess.pmDetails(pm))

  print("pmLog:")
  print(sess.pmLog(122))

  print("pmAddLog:")
  sess.pmAddLog(pm, "This is a test log :)")

  print("pmDetails:")
  print(sess.pmDetails(pm))

  print("pmLog:")
  print(sess.pmLog(pm))

  print("pmMatching:")
  print(sess.pmMatching(pm))

  print("pmCancel:")
  print(sess.pmCancel(pm))


  return






if __name__ == "__main__":
  main()
