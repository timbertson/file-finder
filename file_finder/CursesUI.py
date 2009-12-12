#!/usr/bin/env python
import curses
import os
import sys
import subprocess
from curses import ascii
from time import sleep
import threading
from Queue import Queue, Empty

from FileFinder import FileFinder
from PathFilter import PathFilter
from Highlight import Highlight
from QueueHandler import QueueHandler

import logging

MAX_RESULTS = 50
END = object()
START = object()
PREVIOUS = -1
NEXT = 1

A_FILENAME = None
A_PATH = None
A_INPUT = None
A_HIGHLIGHT = None
A_ERR = None
A_PROMPT = None

QUITTING_TIME = threading.Event()

class CursesUI(object):
	def __init__(self, options):
		self.opt = options
		self.status = ""
		self.ui_lock = threading.Lock()
		self.query_queue = Queue()
		self.results_queue = Queue()
		self.status_queue = Queue()

	def run(self):
		logging.basicConfig(level=self.opt.log_level, filename='/tmp/file-finder.log')
		rootLogger = logging.getLogger()
		rootLogger.addHandler(QueueHandler(self.status_queue, level=logging.INFO))
		logging.info("scanning directory ...")
		def _doit():
			self.finder = FileFinder(self.opt.base_path, path_filter=self.opt.path_filter, quit_indicator=QUITTING_TIME)
			def log_scan_complete():
				logging.warn("file scan complete")
			self.finder.populate(watch=self.opt.use_inotify, on_complete = log_scan_complete)
			curses.wrapper(self._run)

		work_thread = threading.Thread(target=_doit, name="Curses master")
		work_thread.start()
		# the main thread is just going to wait till someone tells it to quit
		try:
			QUITTING_TIME.wait()
		except KeyboardInterrupt:
			# somehow the main thread fails to exit when it is the one
			# to receive KeyboardInterrupt !
			QUITTING_TIME.set()
	
	def search_loop(self):
		while True:
			query = self.query_queue.get()
			try:
				query = self.query_queue.get(timeout=0.1)
			except Empty: pass
			logging.debug("searching: %r" % (query))
			if query:
				results = self.finder.find(query)
			else:
				results = []
			self.results_queue.put((query, results))
	
	def display_loop(self):
		while True:
			query, results = self.results_queue.get()
			self.ui_lock.acquire()
			self.set_results(results, query)
			self.update()
			self.ui_lock.release()
	
	def status_loop(self):
		def _stat(msg):
			self.ui_lock.acquire()
			self.status = msg
			self.update()
			self.ui_lock.release()
		while True:
			status_msg = self.status_queue.get()
			_stat(status_msg)
			sleep(0.5)

	def _run(self, mainscr):
		self.mainscr = mainscr
		self._init_colors()
		self._init_screens()
		self._init_input()
		self.update()

		display_thread = threading.Thread(target=self.display_loop, name="Curses display")
		search_thread = threading.Thread(target=self.search_loop, name="Curses search")
		status_thread = threading.Thread(target=self.status_loop, name="Curses status")
		display_thread.daemon = True
		search_thread.daemon = True
		status_thread.daemon = True

		display_thread.start()
		search_thread.start()
		status_thread.start()

		self._input_loop()
	
	def _init_colors(self):
		global A_INPUT, A_FILENAME, A_PATH, A_HIGHLIGHT, A_ERR, A_PROMPT
		curses.use_default_colors()
		curses.curs_set(1) # line (input) cursor
		A_INPUT = curses.A_REVERSE

		n_filename = 1
		n_path = 2
		n_hi = 3
		n_err = 4
		n_prompt = 5
		bg_index = -1
		curses.init_pair(n_filename, curses.COLOR_WHITE, bg_index)
		curses.init_pair(n_path, curses.COLOR_BLACK, bg_index)
		curses.init_pair(n_hi, curses.COLOR_GREEN, bg_index)
		curses.init_pair(n_err, curses.COLOR_WHITE, curses.COLOR_RED)
		curses.init_pair(n_prompt, curses.COLOR_BLUE, bg_index)

		A_FILENAME = curses.color_pair(n_filename)
		A_PATH = curses.color_pair(n_path)
		A_HIGHLIGHT = curses.color_pair(n_hi) | curses.A_BOLD
		A_ERR = curses.color_pair(n_err) | curses.A_BOLD
		A_PROMPT = curses.color_pair(n_prompt)

	def _init_screens(self):
		self.win_height, self.win_width = self.mainscr.getmaxyx()
		self.input_win = curses.newwin(1, self.win_width, 0, 0)
		self.results_win = curses.newpad(MAX_RESULTS, self.win_width)
		self.status_win = curses.newwin(1, self.win_width, self.win_height-1, 0)

		#IMPORTANT: input_win *must* be the last, so that it gets redrawed
		#           last (and therefore gets the cursor)
		self.screens = (self.results_win, self.status_win, self.input_win)
	
	def resize(self):
		self._init_screens()

	def _init_input(self):
		self.results = []
		self.input_position = 0
		self.selected = 0
		self.results_scroll = 0
		self.set_query("")
	
	def update(self):
		if (self.win_height, self.win_width) != self.mainscr.getmaxyx():
			logging.debug("resizing...")
			self.resize()
		self.draw_input()
		self.draw_results()
		self.draw_status()
		self._redraw()
	
	def draw_input(self):
		self.input_win.clear()
		find_text = "Find: "

		self.input_win.addnstr(0,0, find_text, self.win_width, A_PROMPT)
		self.input_win.addnstr(0, len(find_text), self.query, self.win_width, A_INPUT)
		self.input_win.bkgdset(' ', curses.A_REVERSE)

		self.input_win.move(0,self.input_position + len(find_text))
		
	def draw_results(self):
		#TODO: scroll results buffer
		linepos = 0
		indent_width = 6
		filename_len = min(int(self.win_width / 1.5), 50)
		path_len = self.win_width - filename_len - 1 - indent_width

		self.results_win.clear()
		for file, path in self.results:
			attr_mod = curses.A_REVERSE if linepos == self.selected else curses.A_NORMAL
			drawn_chars = 0
			remaining_chars = filename_len
			for highlighted, segment in self.highlight(file):
				attrs = A_FILENAME | A_HIGHLIGHT if highlighted else A_FILENAME
				self.results_win.insnstr(linepos, indent_width + drawn_chars, segment, remaining_chars, attrs | attr_mod)
				drawn_chars += len(segment)
				remaining_chars -= len(segment)
				if remaining_chars <= 0:
					break
			
			# now draw the path
			relpath = os.path.split(path)[0]
			explanation = ''
			if relpath:
				explanation = "(in %s)" % (relpath,)
			self.results_win.insnstr(linepos, indent_width + filename_len + 1, explanation, path_len, A_PATH)
			linepos += 1
			if linepos >= MAX_RESULTS:
				break
		if linepos == 0 and len(self.query) > 0 and self.query_queue.empty():
			self.results_win.insnstr(linepos, indent_width, 'No Matches...', self.win_width - indent_width, A_ERR)
	
	def draw_status(self):
		self.status_win.clear()
		self.status_win.insnstr(0, 0, self.status, self.win_width, A_PATH)
	
	def open_selected(self):
		index = self.selected
		if len(self.results) <= index:
			logging.warning("no such index: %s" % (index,))
			return
		filepath = self.results[index][-1]
		self.opt.open(filepath)
	
	def select(self, amount):
		self.ui_lock.acquire()
		if amount == NEXT or amount == PREVIOUS:
			self.selected += amount
		elif amount == START:
			self.selected = 0
		elif amount == END:
			self.selected = len(self.results)-1
		self.selected = min(self.selected, len(self.results)-1)
		self.selected = max(self.selected, 0)
		self.ui_lock.release()
	
	def set_query(self, new_query):
		self.query_queue.put(new_query)
		self.ui_lock.acquire()
		self.query = new_query
		if self.input_position > len(self.query):
			self.input_position = len(self.query)
		self.ui_lock.release()
	
	def set_results(self, results, query):
		self.highlight = Highlight(query)
		self.results = list(results)
		self.selected = 0

	def add_char(self, ch):
		new_query = self.modify_query_as_list(lambda q: q.insert(self.input_position, ch))
		self.input_position += 1
		self.set_query(new_query)
		logging.debug("query = %s" % (self.query, ))
	
	def modify_query_as_list(self, proc):
		query_list = list(self.query)
		proc(query_list)
		return ''.join(query_list)
	
	def remove_char(self, forwards=False):
		letter_index = self.input_position if forwards else self.input_position - 1
		if letter_index >= len(self.query) or letter_index < 0:
			return
		new_query = self.modify_query_as_list(lambda q: q.pop(letter_index))
		if forwards:
			self.input_position = max(self.input_position, len(self.query))
		elif self.input_position > 0:
			self.input_position -= 1
		self.set_query(new_query)
	
	def move_cursor(self, backwards=False):
		offset = -1 if backwards else 1
		self.input_position += offset
		self.input_position = max(0, min(self.input_position, len(self.query)))
	
	def move_cursor_to(self, index):
		self.input_position = index

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
		if QUITTING_TIME.isSet(): return False
		logging.debug("input: %r (%s)" % (ch, ascii.unctrl(ch)))
		if ascii.isprint(ch):
			self.add_char(chr(ch))
		elif ch in (ascii.BS, ascii.DEL, curses.KEY_BACKSPACE):
			self.remove_char()
		elif ch == ascii.NL:
			self.open_selected()
		elif ch == curses.KEY_UP:
			self.select(PREVIOUS)
		elif ch == curses.KEY_DOWN:
			self.select(NEXT)
		elif ch == curses.KEY_LEFT:
			self.move_cursor(backwards=True)
		elif ch == curses.KEY_RIGHT:
			self.move_cursor()
		elif ch == curses.KEY_HOME:
			self.move_cursor_to(0)
		elif ch == curses.KEY_END:
			self.move_cursor_to(len(self.query))
		elif ch == ascii.ESC:
			self.set_query("")
		elif ch == ascii.EOT: # ctrl-D
			return False
		self.ui_lock.acquire()
		self.update()
		self.ui_lock.release()
		return True


	def _input_loop(self):
		try:
			logging.debug("input loop begins")
			while self._input_iteration(): pass
		except (KeyboardInterrupt, EOFError):
			logging.info("exiting...")
		except Exception:
			import traceback
			logging.error(traceback.format_exc())
		finally:
			QUITTING_TIME.set()

