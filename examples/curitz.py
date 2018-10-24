#!/usr/bin/env python3
from ritz import ritz, parse_config, notifier, caseType, Case
import curses
from math import ceil
from time import sleep
from pprint import pprint
from collections import namedtuple

from culistbox import listbox




def drawMainWindow(screen):
    global strings, position, page, pages, max_row, row_num, rows, Last_key
    highlightText = curses.color_pair(1)
    normalText = curses.A_NORMAL

    size_h, size_l  = screen.getmaxyx()
    box = curses.newwin(size_h-8 , size_l, 0, 0 )

    box_h, box_l = box.getmaxyx()
    max_row = box_h - 2 #max number of rows

    screen.clear()
    box.box()

    row_num = len(strings)

    pages = int( ceil( row_num / max_row ) )


    box.addstr(0, 2, "cuRitz")

    for i in range( 1 + ( max_row * ( page - 1 ) ), max_row + 1 + ( max_row * ( page - 1 ) ) ):
        if row_num == 0:
            box.addstr( 1, 1, "There aren't strings", highlightText )
        else:
            if ( i + ( max_row * ( page - 1 ) ) == position + ( max_row * ( page - 1 ) ) ):
                box.addstr( i - ( max_row * ( page - 1 ) ), 2, ("%2d - %s" % (i, strings[ i - 1 ]) )[0:box_l-4], highlightText )
            else:
                box.addstr( i - ( max_row * ( page - 1 ) ), 2, ("%2d - %s" % (i, strings[ i - 1 ]) )[0:box_l-4], normalText )
            if i == row_num:
                break

    rows = i

    box.addstr(box_h-1, 2, "%d selected, current pos %d page %d" % (len(cases_selected), position, page))

    screen.refresh()
    box.refresh()


def FetchAllCases():
    global sess, cases, cases_visible, cases_selected

    cases = {}
    for case in sess.cases_iter():
        cases[case.id] = case

    cases_visible.clear()
    cases_visible.append(case.id)

def filterCases():
    global cases_visible, cases
    cases_visible = cases.keys()

def sortCases(field="id"):
    global cases_visible, cases_sorted, cases
    cases_sorted = []
    for key in sorted(cases, key=lambda k: cases[k]._attrs[field]):
        if key in cases_visible:
            cases_sorted.append(key)
        #print("%s" % (key))



def main(screen):
    # Initiate Curses
    global cases, cases_visible, cases_selected, conf, sess, cases_sorted
    global strings, position, page, pages, max_row, row_num, rows

    #Initiate global variables
    # All case objects from pyRitz
    cases = {}          # Type: dict[int,ritz.Case]
    # All visible objects in curitz, ordered by order in list
    cases_visible = []  # Type: int
    # All selected case id's
    cases_selected = [] # Type: int
    # All visible objects sorted
    cases_sorted = []

    # Cursor position
    position = 1
    page = 1

    last_key = 0


    curses.noecho()
    curses.cbreak()
    curses.start_color()
    screen.keypad(1)
    #screen.nodelay(1)
    screen.timeout(1000)

    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)

    curses.curs_set(0)



    # Load Config from ritz config file
    conf = parse_config("~/.ritz.tcl")
    c_server = conf["default"]["Server"]
    c_user   = conf["default"]["User"]
    c_secret = conf["default"]["Secret"]

    # Start session with ritz
    sess = ritz(c_server, username=c_user, password=c_secret)
    sess.connect()

    for case in sess.cases_iter():
        cases[case.id] = case
    filterCases()
    sortCases("id")


    strings = []
    for case in cases_sorted:
        c = cases[case]
        strings.append("{state:8} {router:15} {descr}  ".format(id=c.id,
                                                    router=c.get("router", ""),
                                                    descr=c.get("descr", ""),
                                                    state=c.state.value))
    drawMainWindow(screen)



    while True:
      x = screen.getch()
      if x == -1:
          pass
      elif x == curses.KEY_DOWN:
        if page == 1:
            if position < rows:
                position = position + 1
            else:
                if pages > 1:
                    page = page + 1
                    position = 1 + ( max_row * ( page - 1 ) )
        elif page == pages:
            if position < row_num:
                position = position + 1
        else:
            if position < max_row + ( max_row * ( page - 1 ) ):
                position = position + 1
            else:
                page = page + 1
                position = 1 + ( max_row * ( page - 1 ) )
      elif x == "q":
          return

      drawMainWindow(screen)

    #strings = [ "a", "b", "c", "d", "e", "f", "g", "h", "i", "l", "m", "n" ] #list of strings
    #strings.append("Heigth: %s" % size_h)
    #strings.append("Length: %s" % size_l)



if __name__ == "__main__":
    curses.wrapper(main)
