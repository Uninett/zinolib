import subprocess
import logging
import re
import sys
import os
import socket
from ritz import ritz
from datetime import datetime, timedelta




def main():
    """
    Script to schedule downtime of interfaces in zino when a server reboots.

    This script tries to detect interface names via LLDP and uses the env
    variables ZINOUSER and ZINOSECRET to connect to zino as as a ritz client.
    """
    if "ZINODEBUG" in os.environ:
        ritzlog = logging.getLogger("ritz")
        ritzlog.setLevel(logging.DEBUG)
        ritzlog.addHandler(logging.FileHandler('comm.log'))

    if "ZINOUSER" in os.environ and "ZINOSECRET" in os.environ:
        user = os.environ["ZINOUSER"]
        secret = os.environ["ZINOSECRET"]
    else:
        sys.exit("ZINOUSER and/or ZINOSECRET env variable is not set, exiting")

    if "ZINOSERVER" in os.environ:
        server = os.environ["ZINOSERVER"]
    else:
        server = "zino.uninett.no"
    if "ZINOHOSTNAME" in os.environ:
        fqdn = os.environ["ZINOHOSTNAME"]
    else:
        fqdn = socket.getfqdn()

    if not fqdn.endswith(".uninett.no"):
        sys.exit("Wooth? sysname does not end with uninett.no?")

    print("Creating Maintenance on physical interfaces")
    with ritz(server, username=user, password=secret) as s:
        try:
            # Actually searching for ', fqdn.domain.ext'
            pm1 = s.pm_add_interface_bydescr(datetime.now() + timedelta(seconds=5),
                                             datetime.now() + timedelta(minutes=30),
                                             r',\s%s' % fqdn.replace(r'.',r'\.'))
            pm1matching = s.pm_get_matching(pm1)

            for i in pm1matching:
                print("Scheduled maintenance for %s %s %s" % (i[1], i[3], pm1))
        except Exception as e:
            print("Unable to schedule maintenance: %s" % (e))

if __name__ == "__main__":
    main()
