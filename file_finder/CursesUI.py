#!/usr/bin/env python
import curses
from curses import ascii

import logging
logging.basicConfig(level=logging.DEBUG, filename='/tmp/file-finder.log')
logging.info("start..")

MAX_RESULTS = 50
END = object()
START = object()
PREVIOUS = -1
NEXT = 1

class CursesUI(object):
	def run(self):
		curses.wrapper(self._run)
	
	def _run(self, mainscr):
		self.mainscr = mainscr
		self._init_screens()
		self._init_input()
		self.update()
		self._input_loop()

	def _init_screens(self):
		curses.use_default_colors()
		self.win_height, self.win_width = self.mainscr.getmaxyx()
		self.input_win = curses.newwin(1, self.win_width, 0, 0)
		self.results_win = curses.newpad(MAX_RESULTS, self.win_width)
		self.status_win = curses.newwin(1, self.win_width, self.win_height-1, 0)
		self.screens = (self.input_win, self.results_win, self.status_win)

		self.input_win.bkgdset(' ', curses.A_REVERSE)
	
	def _init_input(self):
		self.set_query("")
		self.results = []
		self.selected = 0
		self.results_scroll = 0
	
	def update(self):
		for scr in self.screens:
			scr.clear()
		self.input_win.addnstr(0,0, self.query, self.win_width)
		self._redraw()
	
	def do_search(self):
		self.set_results([
			'result 1',
			'result 2',
			'result 3'])
	
	def open_selected(self):
		pass
	
	def select(self, amount):
		pass
	
	def set_query(self, new_query):
		self.query = new_query
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
	
	def _input_loop(self):
		while True:
			ch = self.mainscr.getch()
			logging.debug("input: %r (%s)" % (ch, ascii.unctrl(ch)))
			if ascii.isprint(ch):
				self.add_char(chr(ch))
			elif ch == ascii.BS:
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



if __name__ == '__main__':
	CursesUI().run()
	

