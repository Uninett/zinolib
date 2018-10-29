#!/usr/bin/env python3
from ritz import ritz, parse_config, notifier, caseType, Case, caseState
import curses
import curses.textpad
from math import ceil
from time import sleep
from pprint import pprint
from typing import NamedTuple
import logging
from culistbox import listbox, BoxSize, BoxElement
import datetime
import argparse
import sys


log = logging.getLogger("cuRitz")
log.setLevel(logging.DEBUG)
log.addHandler(logging.FileHandler('curitz.log'))

__version__ = "0.2.0"

def interfaceRenamer(s):
    s = s.replace("HundredGigE", "Hu")
    s = s.replace("GigabitEthernet", "Gi")
    s = s.replace("TenGigiabitEthernet", "Te")
    s = s.replace("TenGigE", "Te")
    s = s.replace("FastEthernet", "Fa")
    s = s.replace("Port-channel", "Po")
    s = s.replace("Loopback", "Lo")
    s = s.replace("Tunnel", "Tu")
    s = s.replace("Ethernet", "Eth")
    s = s.replace("Vlan", "Vl")

    return s


def uiShowLogWindow(screen, heading, lines):
    (screen_y, screen_x) = screen.getmaxyx()

    center_x = screen_x // 2
    if center_x < 40:
        center_x = 40
    if screen_y < 30:
        box_h = screen_y - 8
    else:
        box_h = 30
    box = listbox(box_h,
                  80,
                  3,
                  center_x - 40)

    # Display box on the midle of screen
    box.heading = heading
    box.clear()
    for l in lines:
        box.add(l)

    box.draw()

    while True:
        x = screen.getch()
        if x == -1:
            pass
        elif x == curses.KEY_UP:
            # Move up one element in list
            if box.active_element > 0:
                box.active_element -= 1

        elif x == curses.KEY_DOWN:
            # Move down one element in list
            if box.active_element < len(lb) - 1:
                box.active_element += 1
        else:
            return
        box.draw()


def uiShowLog(screen, caseid):
    global cases
    lines = []
    for line in cases[caseid].history:
        lines.append("{} {}".format(line["date"], line["header"][1]))
        if not line["system"]:
            for l in line["log"]:
                lines.append("  {}".format(l))
    uiShowLogWindow(screen, "Case {} - {}".format(caseid, cases[caseid].get("descr", "")), lines)


def strfdelta(tdelta, fmt):
    """
    Snipped from: https://stackoverflow.com/questions/8906926/formatting-python-timedelta-objects/17847006
    """
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def main(screen):
    global lb, session, notifier, cases, table_structure, screen_size

    curses.noecho()
    curses.cbreak()
    curses.start_color()
    screen.keypad(1)
    screen.timeout(10000)

    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(10, curses.COLOR_RED, curses.COLOR_BLACK)

    curses.curs_set(0)

    screen_size = BoxSize(*screen.getmaxyx())
    lb = listbox(screen_size.height - 8, screen_size.length, 1, 0)
    screen.clear()
    screen.refresh()


    table_structure = "{selected:1} {opstate:11} {admstate:8} {age:9} {router:16} {port:14} {description}"

    with ritz(c_server, username=c_user, password=c_secret) as session:
        with notifier(session) as notifier:
            try:
                runner(screen)
            except KeyboardInterrupt:
                pass


def sortCases(casedict, field="lasttrans"):
    cases_sorted = []
    for key in sorted(cases, key=lambda k: cases[k]._attrs[field]):
        cases_sorted.append(key)
    return reversed(cases_sorted)


def create_case_list():
    global cases, visible_cases, lb, cases_selected
    visible_cases = cases.keys()
    sorted_cases = sortCases(cases, field="id")

    lb.clear()
    lb.heading = table_structure.format(
        selected="S",
        opstate="OpState",
        admstate="AdmState",
        router="Router",
        port="Port",
        description="Description",
        age="Age")
    for c in sorted_cases:
        if c in visible_cases:
            case = cases[c]
            try:
                age = datetime.datetime.now() - case.opened
                common = {}
                common['selected'] = "*" if case.id in cases_selected else " "
                common['router'] = case.router
                common['admstate'] = case.state.value[:7]
                common['age'] = strfdelta(age, "{days:2d}d {hours:02}:{minutes:02}")
                common['priority'] = case.priority
                color = []
                if case.type == caseType.PORTSTATE:
                    if case.portstate == 'down' and case.state == caseState.OPEN:
                        color = [curses.color_pair(10)]
                    lb.add(BoxElement(case.id,
                                      table_structure.format(
                                          **common,
                                          opstate="PORT %s" % case.portstate[0:5],
                                          port=interfaceRenamer(case.port),
                                          description=case.get("descr", ""),
                                          ), color))
                elif case.type == caseType.BGP:
                    if case.bgpos == 'down' and case.state == caseState.OPEN:
                        color = [curses.color_pair(10)]
                    lb.add(BoxElement(case.id,
                                      table_structure.format(
                                          **common,
                                          opstate="BGP  %s" % case.bgpos[0:5],
                                          port="AS{}".format(case.remote_as), #str(case.remote_addr),
                                          description=case.get("lastevent", ""),
                                          ), color))
                elif case.type == caseType.BFD:
                    if case.bfdstate == 'down' and case.state == caseState.OPEN:
                        color = [curses.color_pair(10)]
                    lb.add(BoxElement(case.id,
                                    table_structure.format(
                                        **common,
                                        opstate="BFD  %s" % case.bfdstate[0:5],
                                        port=str(case.bfdaddr),
                                        description="{}, {}".format(case.get('neigh_rdns'),
                                                                    case.get('lastevent')),
                                        ), color))
                elif case.type == caseType.REACHABILITY:
                    if case.reachability == 'unrechable' and case.state == caseState.OPEN:
                        color = [curses.color_pair(10)]
                    lb.add(BoxElement(case.id,
                                    table_structure.format(
                                        **common,
                                        opstate=case.reachability,
                                        port="",
                                        description="",
                                        ), color))
                elif case.type == caseType.ALARM:
                    if case.alarm_type == 'red' and case.state == caseState.OPEN:
                        color = [curses.color_pair(10)]
                    lb.add(BoxElement(case.id,
                                      table_structure.format(
                                          **common,
                                          opstate="ALRM {}".format(case.alarm_type),
                                          port="",
                                          description=case.lastevent,
                                          ), color))
                else:
                  log.error("Unable to create table for case {}".format(case.id))
                  log.error(repr(case._attrs))
            except Exception as e:
                log.exception("Exception while createing table entry for case {}".format(case.id))
                log.fatal(repr(case._attrs))
                raise

def runner(screen):
    global cases, cases_selected, screen_size
    # Get all data for the first time
    cases = {}
    cases_selected = []

    draw(screen)
    caselist = session.get_caseids()
    for c in caselist:
        case = session.case(c)
        cases[case.id] = case
        elements = int((len(cases) / len(caselist)) * 20)
        screen.addstr(9, 10,
                      "[{:-<20}] Loaded {} of {} cases".format(
                          "=" * elements,
                          len(cases),
                          len(caselist)))
        screen.refresh()

    create_case_list()
    draw(screen)

    while True:
        x = screen.getch()

        if curses.is_term_resized(*screen_size):
            # Screen is resized
            screen_size = BoxSize(*screen.getmaxyx())
            lb.resize(screen_size.height - 8, screen_size.length)

        screen.addstr(0, screen_size.length - 8, "ch:{:3}".format(x))
        if poll():
            create_case_list()

        if x == -1:
            # Nothing happened, check for changes
            pass

        elif x == ord('q'):
            # Q pressed, Exit application
            return

        elif x == curses.KEY_UP:
            # Move up one element in list
            if lb.active_element > 0:
                lb.active_element -= 1

        elif x == curses.KEY_DOWN:
            # Move down one element in list
            if lb.active_element < len(lb) - 1:
                lb.active_element += 1

        elif x == curses.KEY_NPAGE:
            a = lb.active_element + lb.pagesize
            if a < len(lb) - 1:
                lb.active_element = a
            else:
                lb.active_element = len(lb) - 1

        elif x == curses.KEY_PPAGE:
            a = lb.active_element - lb.pagesize
            if a > 0:
                lb.active_element = a
            else:
                lb.active_element = 0

        elif x == ord('x'):
            # (de)select a element
            if lb.active.id in cases_selected:
                cases_selected.remove(lb.active.id)
            else:
                cases_selected.append(lb.active.id)
            create_case_list()

        elif x == ord('c'):
            # Clear selection
            cases_selected.clear()
            create_case_list()
        elif x == ord('u'):
            # Update selected cases
            if cases_selected:
                uiUpdateCases(screen, cases_selected)
            else:
                uiUpdateCases(screen, [lb.active.id])
        elif x == ord('s'):
            # Update selected cases
            if cases_selected:
                uiSetState(screen, cases_selected)
            else:
                uiSetState(screen, [lb.active.id])
            curses.flash()
        elif x == curses.KEY_ENTER or x == 10 or x == 13:  # [ENTER], CR or LF
            uiShowLog(screen, lb.active.id)

        draw(screen)


def draw(screen):
    screen.addstr(0, 0, "cuRitz version {}  -  {}".format(__version__, c_server))

    screen.addstr(screen_size.height - 1, 0, "q=Quit  x=(de)select  c=Clear sel  s=Set State  u=Update History  <ENTER>=Show history <UP/DOWN> = Navigate"[:screen_size.length - 1])
    lb.draw()


def uiUpdateCases(screen, caseids):
    update = uiUpdateCaseWindow(screen, len(caseids))
    if update:
        for case in caseids:
            cases[case].add_history(update)


def uiSetState(screen, caseids):
    update = uiSetStateWindow(screen, len(caseids))
    if update:
        for case in caseids:
            cases[case].set_state(update)


def uiSetStateWindow(screen, number):
    try:
        box = listbox(9, 62, 4, 9)
        box.heading = "Set state on {} cases".format(number)
        box.add("Open")
        box.add("Working")
        box.add("wAiting")
        box.add("coNfirm-wait")
        box.add("Ignored")
        box.add("Closed")
        box.draw()

        while True:
            x = screen.getch()
            if x == -1:
                pass
            elif x == curses.KEY_UP:
                # Move up one element in list
                if box.active_element > 0:
                    box.active_element -= 1

            elif x == curses.KEY_DOWN:
                # Move down one element in list
                if box.active_element < len(lb) - 1:
                    box.active_element += 1

            elif x == ord('o') or x == ord('O'):
                box.active_element = 0
            elif x == ord('w') or x == ord('W'):
                box.active_element = 1
            elif x == ord('a') or x == ord('A'):
                box.active_element = 2
            elif x == ord('n') or x == ord('N'):
                box.active_element = 3
            elif x == ord('i') or x == ord('I'):
                box.active_element = 4
            elif x == ord('c' or x == ord('C')):
                box.active_element = 5
            elif x == curses.KEY_ENTER or x == 13 or x == 10:
                return box.active.lower()
            elif x == 27:  # ESC
                raise KeyboardInterrupt("ESC pressed")

            box.draw()

    except KeyboardInterrupt:
        box.clear()
    return ""


def uiUpdateCaseWindow(screen, number):
    border = curses.newwin(9, 62, 4, 9)
    textbox = curses.newwin(5, 60, 6, 10)
    border.box()
    border.addstr(0, 1, "Add new history line - ctrl+g=send abort=ctrl+c")
    border.addstr(1, 1, "{} case(s) selected for update".format(number))
    border.refresh()
    p = curses.textpad.Textbox(textbox)
    curses.curs_set(1)
    try:
        text = p.edit()
    except KeyboardInterrupt:
        return ""
    return text


def poll():
    global cases, cases_selected
    update = notifier.poll()
    if update:
        if update.id not in cases:
            if update.type != "state":
                # Update on unknown case thats not a state update
                # We just exit and wait for a state on that object
                return
        if update.type == "state":
            cases[update.id] = session.case(update.id)
        elif update.type == "attr":
            cases[update.id] = session.case(update.id)
        elif update.type == "history":
            pass
        elif update.type == "log":
            pass
        elif update.type == "scavenged":
            cases.pop(update.id, None)
            if update.case in cases_selected:
                cases_selected.remove(update.id)
        else:
            log.debug("unknown notify entry: %s for id %s" % (update.type, update.id))
            return False
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-p', '--profile', default='default',
                        help='use Zino profile')
    parser.add_argument('--profiles', action='store_true',
                        help='List Zino profiles')
    parser.add_argument('-c', '--config', nargs=1, default='~/.ritz.tcl',
                        help='zino config file')
    args = parser.parse_args()


    conf = parse_config("~/.ritz.tcl")


    if args.profile:
      if not args.profile in conf.keys():
        print("List of zino profiles:")
        for profile in conf.keys():
          print("  {}".format(profile))
        sys.exit("Unable to find profile {}".format(args.profile))


    if args.profiles:
      print("List of zino profiles:")
      for profile in conf.keys():
        print("  {}".format(profile))
      sys.exit(0)

    c_server = conf[args.profile]["Server"]
    c_user = conf[args.profile]["User"]
    c_secret = conf[args.profile]["Secret"]
    curses.wrapper(main)
