from ritz import ritz, notifier, parse_tcl_config
from pprint import pprint
from time import sleep
import re
import argparse
import sys
from datetime import datetime, timedelta
import logging

def main():
  parser = argparse.ArgumentParser(description='Process some integers.')

  parser.add_argument('--prod', action='store_true')
  parser.add_argument('--remove-all-pms', action='store_true')

  args = parser.parse_args()
  conf = parse_tcl_config("~/.ritz.tcl")
  pprint(conf)

  if args.prod:
    c_server = conf["default"]["Server"]
    c_user   = conf["default"]["User"]
    c_secret = conf["default"]["Secret"]
  else:
    c_server = conf["UNINETT-backup"]["Server"]
    c_user   = conf["UNINETT-backup"]["User"]
    c_secret = conf["UNINETT-backup"]["Secret"]

  logging.basicConfig()
  logging.getLogger().setLevel(logging.DEBUG)
  requests_log = logging.getLogger("socket")
  requests_log.setLevel(logging.DEBUG)
  requests_log.propagate = True






  sess = ritz(c_server)
  sess.connect()
  sess.authenticate(c_user, c_secret)

  print("List all PMs:")
  pm = sess.pm_list()
  print(pm)
  #for i in pm:
  #  print("canceling %d" % i)
  #  sess.pm_cancel(i)

  print("Schedule test pm:")
  pm = sess.pm_add_device(datetime.now()+timedelta(minutes=1),
                          datetime.now()+timedelta(minutes=2),
                          "teknobyen-gw*", m_type='str')
  print("Scheduled")

  print("List all PMs:")
  pms = sess.pm_list()
  print(pm)

  print("pm_get_details:")
  print(sess.pm_get_details(pm))

  print("pm_get_log:")
  print(sess.pm_get_log(pm))

  print("pm_add_log:")
  sess.pm_add_log(pm, "This is a test log :)")

  print("pm_get_details:")
  print(sess.pm_get_details(pm))

  print("pm_get_log:")
  print(sess.pm_get_log(pm))

  print("pm_get_matching:")
  print(sess.pm_get_matching(pm))

  print("pm_cancel:")
  print(sess.pm_cancel(pm))


  return






if __name__ == "__main__":
  main()
