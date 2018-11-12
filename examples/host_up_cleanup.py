import subprocess
import logging
import re
import sys
import os
import socket
from ritz import ritz, caseType, caseState
from datetime import datetime, timedelta
import traceback
import re



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

    print("Removing Maintenance on physical interfaces")
    with ritz(server, username=user, password=secret) as s:
        try:
            # Actually searching for ', fqdn.domain.ext'

            ids = s.get_caseids()
            for id in ids:
                try:
                    attr = s.case(id)
                except Exception as e:
                    print(e)
                    #print("Invalid case {id}".format(id=id))
                    continue
                if attr.type not in [caseType.PORTSTATE]:
                    print("case {id} is not a portstate".format(**attr))
                    continue

                #print("Checking case {id}: {descr}".format(**attr))
                #Check if case has a descr
                if not attr.has_key("descr"):
                    continue

                if not re.search(r", {}".format(fqdn.replace(".", r"\.")), attr.descr):
                    print("Did not match: {}".format(attr.descr))
                    continue

                print("Found case {id}: {descr}".format(**attr))
                if attr.portstate == "up" and attr.state in [caseState.IGNORED, caseState.OPEN]:
                  # This case is not tampered with, just close it :)
                  try:
                      s.clear_flapping(attr.router, attr.ifindex)

                      s.add_history(id, "This case is automatically closed by {filename}".format(filename=os.path.basename(__file__)))
                      s.set_state(id, "closed")
                      print("  Closed")
                  except Exception as e:
                    print("  Error closing: %s" % e)

        except Exception as e:
            print("Unable to clean : %s" % (traceback.format_exc()))

if __name__ == "__main__":
    main()
