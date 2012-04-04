import os
import re
import subprocess
import readline
import optparse
import threading

import logging

from file_finder import FileFinder
from highlight import Highlight
from search import Search

try:
	from termstyle import green, cyan, blue, yellow, black, auto
	import termstyle
	termstyle.auto()
except ImportError:
	logging.info("can't import termstyle - install it for pretty colours")
	termstyle = None
	green = cyan = blue = yellow = black = lambda a: a


QUITTING_TIME = threading.Event()

class Repl(object):
	def __init__(self, options):
		self.found_files = []
		self.opt = options
	
	def highlight_func(self, query_string):
		if termstyle is None:
			return lambda x: x
		highlight = Highlight(query_string)
		return lambda x: highlight.replace(x, green)
			
	def summarise(self, result_iter, query_string):
		subprocess.call(['clear'])
		self.found_files = []
		i = 0
		highlight = self.highlight_func(query_string)
		for filename, fullpath in result_iter:
			self.found_files.append(fullpath)
			relpath = os.path.split(fullpath)[0]
			explanation = ''
			if relpath:
				explanation = "(in %s)" % (relpath,)
			index = str(i+1).rjust(2)
			filename = filename.ljust(30)
			print " %s%s   %s %s" % (yellow(index), yellow(":"), highlight(filename), black(explanation))
			i += 1
		
	def open(self, index):
		index -= 1 # indexes start at 1 for readability
		if len(self.found_files) <= index:
			logging.warning("no such index: %s" % (index,))
			return
		filepath = self.found_files[index]
		self.opt.open(filepath)

	def _loop(self):
		q = raw_input(blue("\nfind/open file: "))
		if len(q) == 0:
			q = 1 # open the first found file by default
		try:
			index = int(q)
		except ValueError:
			index = None
		if index is not None:
			self.open(index)
		else:
			self.finder.find(Search(q))
			search = self.finder.results()
			self.summarise(search.results, search.text)

	def run(self):
		work_thread = threading.Thread(target=self._run, name="repl")
		work_thread.daemon = True
		work_thread.start()
		# the main thread is just going to wait till someone tells it to quit
		try:
			QUITTING_TIME.wait()
		except KeyboardInterrupt:
			# somehow the main thread fails to exit when it is the one
			# to receive KeyboardInterrupt !
			pass

	def _run(self):
		self.finder = FileFinder(self.opt.base_path, path_filter=self.opt.path_filter, quit_indicator=QUITTING_TIME)
		logging.info("getting file list...")
		self.finder.populate()
		try:
			while True:
				self._loop()
		except (KeyboardInterrupt, EOFError):
			print
			return 0
		except Exception:
			import traceback
			traceback.print_exc()
		finally:
			QUITTING_TIME.set()

