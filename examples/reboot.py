import subprocess
import re
import sys
import os
from ritz import ritz
from datetime import datetime, timedelta


def main():
    """
    Script to schedule downtime of interfaces in zino when a server reboots.

    This script tries to detect interface names via LLDP and uses the env
    variables ZINOUSER and ZINOSECRET to connect to zino as as a ritz client.
    """
    if "ZINOUSER" in os.environ and "ZINOSECRET" in os.environ:
        user = os.environ["ZINOUSER"]
        secret = os.environ["ZINOSECRET"]
    else:
        sys.exit("ZINOUSER and/or ZINOSECRET env variable is not set, exiting")

    if "ZINOSERVER" in os.environ:
        server = os.environ["ZINOSERVER"]
    else:
        server = "zino.uninett.no"

    ports = collect_interfaces()
    if ports:
        with ritz(server, username=user, password=secret) as s:
            for device, porttype, port in ports:
                try:
                    id = s.pm_add_interface(datetime.now() + timedelta(seconds=15),
                                            datetime.now() + timedelta(minutes=30),
                                            device,
                                            r"^{}(\.\d+)?$".format(port))
                    print("Scheduled maintenance for %s %s : id %s" % (device, port, id))
                except Exception as e:
                    print("Unable to schedule maintenance for %s %a : %s" (device, port, e))


def collect_interfaces():
    lldp = subprocess.check_output(["lldpctl"])

    portlist = []

    device = ""
    print("Locating interfaces:")
    for line in lldp.decode().split("\n"):
        d = re.search("SysName:(.*)$", line)
        if d:
            device = d.group(1).strip()

        p = re.search("PortID:\W+(\w+)\W+(\S+)$", line)
        if p:
            porttype, port = p.groups()
            if porttype not in ["local", "ifname"]:
                print("Unable to add interface %s %s, Type needs to be ifname, not %s" % (device, port, porttype))
            else:
                portlist.append([device, porttype, port])
                print("Found interface: %s %s" % (device, port))


    return portlist





if __name__ == "__main__":
    main()
