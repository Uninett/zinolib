"""Simple textbox editing widget with Emacs-like keybindings."""

import curses
import curses.ascii

def rectangle(win, uly, ulx, lry, lrx):
    """Draw a rectangle with corners at the provided upper-left
    and lower-right coordinates.
    """
    win.vline(uly+1, ulx, curses.ACS_VLINE, lry - uly - 1)
    win.hline(uly, ulx+1, curses.ACS_HLINE, lrx - ulx - 1)
    win.hline(lry, ulx+1, curses.ACS_HLINE, lrx - ulx - 1)
    win.vline(uly+1, lrx, curses.ACS_VLINE, lry - uly - 1)
    win.addch(uly, ulx, curses.ACS_ULCORNER)
    win.addch(uly, lrx, curses.ACS_URCORNER)
    win.addch(lry, lrx, curses.ACS_LRCORNER)
    win.addch(lry, ulx, curses.ACS_LLCORNER)

class Textbox:
    """Editing widget using the interior of a window object.
     Supports the following Emacs-like key bindings:
    Ctrl-A      Go to left edge of window.
    Ctrl-B      Cursor left, wrapping to previous line if appropriate.
    Ctrl-D      Delete character under cursor.
    Ctrl-E      Go to right edge (stripspaces off) or end of line (stripspaces on).
    Ctrl-F      Cursor right, wrapping to next line when appropriate.
    Ctrl-G      Terminate, returning the window contents.
    Ctrl-H      Delete character backward.
    Ctrl-J      Terminate if the window is 1 line, otherwise insert newline.
    Ctrl-K      If line is blank, delete it, otherwise clear to end of line.
    Ctrl-L      Refresh screen.
    Ctrl-N      Cursor down; move down one line.
    Ctrl-O      Insert a blank line at cursor location.
    Ctrl-P      Cursor up; move up one line.
    Move operations do nothing if the cursor is at an edge where the movement
    is not possible.  The following synonyms are supported where possible:
    KEY_LEFT = Ctrl-B, KEY_RIGHT = Ctrl-F, KEY_UP = Ctrl-P, KEY_DOWN = Ctrl-N
    KEY_BACKSPACE = Ctrl-h
    """
    def __init__(self, win, insert_mode=False):
        self.win = win
        self.insert_mode = insert_mode
        self._update_max_yx()
        self.stripspaces = 1
        self.lastcmd = None
        win.keypad(1)

    def _update_max_yx(self):
        maxy, maxx = self.win.getmaxyx()
        self.maxy = maxy - 1
        self.maxx = maxx - 1

    def _end_of_line(self, y):
        """Go to the location of the first blank on the given line,
        returning the index of the last non-blank character."""
        self._update_max_yx()
        last = self.maxx
        while True:
            if curses.ascii.ascii(self.win.inch(y, last)) != curses.ascii.SP:
                last = min(self.maxx, last+1)
                break
            elif last == 0:
                break
            last = last - 1
        return last

    def _insert_printable_char(self, ch):
        self._update_max_yx()
        (y, x) = self.win.getyx()
        backyx = None
        while y < self.maxy or x < self.maxx:
            if self.insert_mode:
                oldch = self.win.inch()
            # The try-catch ignores the error we trigger from some curses
            # versions by trying to write into the lowest-rightmost spot
            # in the window.
            try:
                self.win.addch(ch)
            except curses.error:
                pass
            if not self.insert_mode or not curses.ascii.isprint(oldch):
                break
            ch = oldch
            (y, x) = self.win.getyx()
            # Remember where to put the cursor back since we are in insert_mode
            if backyx is None:
                backyx = y, x

        if backyx is not None:
            self.win.move(*backyx)

    def do_command(self, ch):
        "Process a single editing command."
        self._update_max_yx()
        (y, x) = self.win.getyx()
        self.lastcmd = ch

        if isinstance(ch, str):
            if ch.isprintable() or ch == 160:  # Permit all unicode printable characters and NonBreakSpace
                # PRINTABLE   Insert printable character
                if y < self.maxy or x < self.maxx:
                    self._insert_printable_char(ch)

            elif ord(ch) == curses.ascii.SOH:
                # CTRL+a HOME / Move to left edge
                self.win.move(y, 0)

            elif ord(ch) == curses.ascii.EOT:
                # CTRL+d Delete under cursor
                self.win.delch()

            elif ord(ch) == curses.ascii.ENQ:
                # CTRL+e
                if self.stripspaces:
                    self.win.move(y, self._end_of_line(y))
                else:
                    self.win.move(y, self.maxx)

            elif ord(ch) == curses.ascii.BEL:
                # CTRL+g  execute action
                return 0

            elif ord(ch) == curses.ascii.NL:
                # CTRL+j  ENTER
                if self.maxy == 0:
                    return 0
                elif y < self.maxy:
                    self.win.move(y+1, 0)

            elif ord(ch) == curses.ascii.VT:
                # CTRL+k
                if x == 0 and self._end_of_line(y) == 0:
                    self.win.deleteln()
                else:
                    # first undo the effect of self._end_of_line
                    self.win.move(y, x)
                    self.win.clrtoeol()

            elif ord(ch) == curses.ascii.FF:
                # CTRL+l Refresh
                self.win.refresh()

            elif ord(ch) == curses.ascii.SI:
                # CTRL+o Insert line after
                self.win.insertln()

            elif ord(ch) == curses.ascii.DLE:
                # CTRL+p
                ch = curses.KEY_UP

            elif ord(ch) == curses.ascii.SO:
                # CTRL+n
                ch = curses.KEY_DOWN

            elif ord(ch) == curses.ascii.STX:
                # CTRL+b
                ch = curses.KEY_LEFT

            elif ord(ch) == curses.ascii.BS:
                # CTRL+h
                ch = curses.KEY_BACKSPACE

            elif ord(ch) == curses.ascii.ACK:
                # CTRL+f
                ch = curses.KEY_RIGHT

        if isinstance(ch, int):
            # We got an Control Caracter
            if ch in (curses.KEY_LEFT,curses.KEY_BACKSPACE): # curses.ascii.BS curses.ascii.STX, missing: CTRL+b
                # MOVE LEFT and delete char
                if x > 0:
                    self.win.move(y, x-1)
                elif y == 0:
                    pass
                elif self.stripspaces:
                    self.win.move(y-1, self._end_of_line(y-1))
                else:
                    self.win.move(y-1, self.maxx)

            if ch in (curses.KEY_RIGHT,): # Missing: curses.ascii.ACK (CTRL+f):
                if x < self.maxx:
                    self.win.move(y, x+1)
                elif y == self.maxy:
                    pass
                else:
                    self.win.move(y+1, 0)

            if ch in (curses.KEY_DOWN,): # Missing CTRL+n
                if y < self.maxy:
                    self.win.move(y+1, x)
                    if x > self._end_of_line(y+1):
                        self.win.move(y+1, self._end_of_line(y+1))

            if ch == curses.KEY_UP:
                if y > 0:
                    self.win.move(y-1, x)
                    if x > self._end_of_line(y-1):
                        self.win.move(y-1, self._end_of_line(y-1))

            elif ch in (curses.KEY_BACKSPACE,):    #missing: curses.ascii.BS BS is treated as str:8,
                self.win.delch()

        return 1

    def gather(self):
        "Collect and return the contents of the window."
        result = ""
        self._update_max_yx()
        for y in range(self.maxy+1):
            self.win.move(y, 0)
            stop = self._end_of_line(y)
            if stop == 0 and self.stripspaces:
                continue
            for x in range(self.maxx+1):
                if self.stripspaces and x > stop:
                    break
                result = result + chr(self.win.inch(y, x))
            if self.maxy > 0:
                result = result + "\n"
        return result

    def edit(self, validate=None):
        "Edit in the widget window and collect the results."
        while 1:
            ch = self.win.get_wch()

            if validate:
                ch = validate(ch)
            if not ch:
                continue
            if not self.do_command(ch):
                break
            self.win.refresh()
        return self.gather()

if __name__ == '__main__':
    def test_editbox(stdscr):
        ncols, nlines = 9, 4
        uly, ulx = 15, 20
        stdscr.addstr(uly-2, ulx, "Use Ctrl-G to end editing.")
        win = curses.newwin(nlines, ncols, uly, ulx)
        rectangle(stdscr, uly-1, ulx-1, uly + nlines, ulx + ncols)
        stdscr.refresh()
        return Textbox(win).edit()

    str = curses.wrapper(test_editbox)
    print('Contents of text box:', repr(str))
