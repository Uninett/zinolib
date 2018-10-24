#!/usr/bin/env python3
from ritz import ritz, parse_config, notifier, caseType, Case
import curses
import curses.textpad
from math import ceil
from time import sleep
from pprint import pprint
from typing import NamedTuple
import logging
from culistbox import listbox, BoxSize, BoxElement
import datetime


log = logging.getLogger("cuRitz")
log.setLevel(logging.DEBUG)
log.addHandler(logging.FileHandler('curitz.log'))




def strfdelta(tdelta, fmt):
    """
    Snipped from: https://stackoverflow.com/questions/8906926/formatting-python-timedelta-objects/17847006
    """
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)




def main(screen):
    global lb, session, notifier, cases, table_structure
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    screen.keypad(1)
    screen.timeout(1000)

    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.curs_set(0)

    screen_size = BoxSize(*screen.getmaxyx())
    lb = listbox(screen_size.height - 8, screen_size.length, 1, 0)
    screen.clear()
    screen.refresh()

    screen.addstr(0, 0, "cuRitz 0.1 Alpha Devel version")
    screen.addstr(screen_size.height - 1, 0, "q = quit  x = (de)select  c=Clear selection  s=sort  f=filter  UP/DOWN = Navigate")

    conf = parse_config("~/.ritz.tcl")
    c_server = conf["default"]["Server"]
    c_user   = conf["default"]["User"]
    c_secret = conf["default"]["Secret"]

    table_structure = "{selected:1} {opstate:10} {state:8} {age:8} {router:16} {port:20} {description}"

    with ritz(c_server, username=c_user, password=c_secret) as session:
        with notifier(session) as notifier:
            runner(screen)


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
        state="AdmState",
        router="Router",
        port="Port",
        description="Description",
        age="Age")
    for c in sorted_cases:
        if c in visible_cases:
            case = cases[c]
            if case.type == caseType.PORTSTATE:
                age = datetime.datetime.now() - case.opened
                log.debug("list of cases: %s" % repr(cases_selected))
                lb.add(BoxElement(case.id,
                                  table_structure.format(
                                      selected="*" if case.id in cases_selected else " ",
                                      opstate="port %s" % case.portstate,
                                      state=case.state.value,
                                      router=case.router,
                                      port=case.port,
                                      description=case.get("descr", ""),
                                      age=strfdelta(age, "{days:2d}d {hours:02}:{minutes:02}"))))


def runner(screen):
    global cases, cases_selected
    # Get all data for the first time
    cases = {}
    cases_selected = []
    for case in session.cases_iter():
        cases[case.id] = case
    create_case_list()
    lb.draw()

    while True:
        x = screen.getch()
        if x == -1:
            # Nothing happened, check for changes
            if poll():
                create_case_list()
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
            updateCase()
            curses.flash()
        elif x == curses.KEY_RESIZE:
            # Resize of window
            screen_size = BoxSize(*screen.getmaxyx())
            lb.resize(screen_size.height - 8, screen_size.length)

        lb.draw()


def updateCase():
    win = curses.newwin(5, 60, 5, 10)
    win.box()
    win.addstr(0, 1, "Add new history line")
    p = curses.textpad.Textbox(win)
    curses.curs_set(1)
    text = p.edit()
    curses.curs_set(0)
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
    curses.wrapper(main)
