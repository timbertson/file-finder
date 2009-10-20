#!/usr/bin/env python
import curses
from curses import ascii
import threading
from FileFinder import FileFinder
from PathFilter import PathFilter
from Highlight import Highlight

import logging
logging.basicConfig(level=logging.DEBUG, filename='/tmp/file-finder.log')
logging.info("start..")

MAX_RESULTS = 50
END = object()
START = object()
PREVIOUS = -1
NEXT = 1

A_FILENAME = None
A_PATH = None
A_INPUT = None
A_HIGHLIGHT = None

QUITTING_TIME = threading.Event()

class CursesUI(object):
	def run(self):
		def _doit():
			self.base_path = '.'
			self.path_filter = PathFilter()
			self.finder = FileFinder(self.base_path, path_filter=self.path_filter, quit_indicator=QUITTING_TIME)
			logging.info("getting file list...")
			self.finder.populate(watch=False)
			curses.wrapper(self._run)

		work_thread = threading.Thread(target=_doit)
		work_thread.start()
		# the main thread is just going to wait till someone tells it to quit
		try:
			QUITTING_TIME.wait()
		except KeyboardInterrupt:
			# somehow the main thread fails to exit when it is the one
			# to receive KeyboardInterrupt !
			pass
	
	def _run(self, mainscr):
		self.mainscr = mainscr
		self._init_colors()
		self._init_screens()
		self._init_input()
		self.update()
		self._input_loop()
	
	def _init_colors(self):
		global A_INPUT, A_FILENAME, A_PATH, A_HIGHLIGHT
		curses.use_default_colors()
		A_INPUT = curses.A_REVERSE

		n_filename = 1
		n_path = 2
		n_hi = 3
		curses.init_pair(n_filename, curses.COLOR_WHITE, -1)
		curses.init_pair(n_path, curses.COLOR_BLACK, -1)
		curses.init_pair(n_hi, curses.COLOR_CYAN, -1)

		A_FILENAME = curses.color_pair(n_filename)
		A_PATH = curses.color_pair(n_path)
		A_HIGHLIGHT = curses.color_pair(n_hi) | curses.A_BOLD

	def _init_screens(self):
		self.win_height, self.win_width = self.mainscr.getmaxyx()
		self.input_win = curses.newwin(1, self.win_width, 0, 0)
		self.results_win = curses.newpad(MAX_RESULTS, self.win_width)
		self.status_win = curses.newwin(1, self.win_width, self.win_height-1, 0)
		self.screens = (self.input_win, self.results_win, self.status_win)

	
	def _init_input(self):
		self.set_query("")
		self.results = []
		self.selected = 0
		self.results_scroll = 0
	
	def update(self):
		self.draw_input()
		self.draw_results()
		self._redraw()
	
	def draw_input(self):
		self.input_win.clear()
		find_text = "Find: "

		self.input_win.addnstr(0,0, find_text, self.win_width)
		self.input_win.addnstr(0, len(find_text), self.query, self.win_width, A_INPUT)
		
	def draw_results(self):
		linepos = 0
		indent_width = 6
		filename_len = min(int(self.win_width / 1.5), 30)
		path_len = self.win_width - filename_len - 1 - indent_width

		self.results_win.clear()
		for file, path in self.results:
			drawn_chars = 0
			remaining_chars = filename_len
			for highlighted, segment in self.highlight(file):
				attrs = A_FILENAME | A_HIGHLIGHT if highlighted else A_FILENAME
				logging.debug("writing segment: %s (%s)" % (segment, 'HIGHLIGHTED' if highlighted else 'normal'))
				self.results_win.insnstr(linepos, indent_width + drawn_chars, segment, remaining_chars, attrs)
				drawn_chars += len(segment)
				remaining_chars -= len(segment)
				if remaining_chars <= 0:
					break
			self.results_win.insnstr(linepos, indent_width + filename_len + 1, path, path_len, A_PATH)
			linepos += 1
	
	def do_search(self):
		if len(self.query) == 0:
			self.results = []
			return
		self.set_results(self.finder.find(self.query))
	
	def open_selected(self):
		pass
	
	def select(self, amount):
		pass
	
	def set_query(self, new_query):
		self.query = new_query
		self.highlight = Highlight(new_query)
		self.input_win.move(0, len(new_query))
		self.input_win.cursyncup()
		self.do_search()
	
	def set_results(self, results):
		self.results = list(results)

	def add_char(self, ch):
		self.set_query(self.query + ch)
		logging.debug("query = %s" % (self.query, ))
	
	def remove_char(self):
		self.set_query(self.query[:-1])

	def _redraw(self, *screens):
		logging.debug("redrawing...")
		if len(screens) == 0:
			screens = self.screens
		for scr in screens:
			if scr is self.results_win:
				scr.noutrefresh(
					self.results_scroll, 0, 1, 0,
					self.win_height-2, self.win_width)
			else:
				scr.noutrefresh()
		curses.doupdate()
	
	def _input_iteration(self):
		ch = self.mainscr.getch()
		logging.debug("input: %r (%s)" % (ch, ascii.unctrl(ch)))
		if ascii.isprint(ch):
			self.add_char(chr(ch))
		elif ch == ascii.BS or ch == 127: # 127 for me, who knows why...
			logging.debug("backspace!")
			self.remove_char()
		elif ch == ascii.NL:
			self.open_selected()
		elif ch == curses.KEY_UP:
			self.select(PREVIOUS)
		elif ch == curses.KEY_DOWN:
			self.select(NEXT)
		elif ch == ascii.ESC:
			self.set_query("")
		self.update()


	def _input_loop(self):
		try:
			while True:
				if QUITTING_TIME.isSet():
					break
				self._input_iteration()
		except (KeyboardInterrupt, EOFError):
			logging.info("exiting...")
		except Exception:
			import traceback
			logging.error(traceback.format_exc())
		finally:
			QUITTING_TIME.set()


if __name__ == '__main__':
	CursesUI().run()
	

