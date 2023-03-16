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



  with ritz(c_server, username=c_user, password=c_secret) as sess:
    print("List all PMs:")
    pm = sess.pm_list()
    print(pm)
    for i in pm:
      print("canceling %d" % i)
      sess.pm_cancel(i)

    print("Schedule test pm:")
    pm = sess.pm_add_device(datetime.now() + timedelta(minutes=1),
                            datetime.now() + timedelta(minutes=2),
                            "teknobyen-gw4")
    print("sheduled: %s" % pm)
    pm2 = sess.pm_add_interface(datetime.now() + timedelta(minutes=1),
                                datetime.now() + timedelta(minutes=2),
                                "uninett-tor-sw3",
                                "xe-0/0/19")
    print("sheduled: %s" % pm2)

    print("List all PMs:")
    pms = sess.pm_list()
    print(pm)

    print("pm_get_details %s:" % pm)
    p = sess.pm_get_details(pm)
    for k in p.keys():
      print("%-10s %-s" % (k, p[k]))

    print("pm_get_details %s:" % pm2)
    p = sess.pm_get_details(pm2)
    for k in p.keys():
      print("%-10s %-s" % (k, p[k]))

    print("pm_get_matching: %s" % pm)
    for p in sess.pm_get_matching(pm):
      print(p)

    print("pm_get_matching:%s" % pm2)
    for p in sess.pm_get_matching(pm2):
      print(p)

    print("pm_cancel:")
    print(sess.pm_cancel(pm))
    print(sess.pm_cancel(pm2))

  return






if __name__ == "__main__":
  main()
