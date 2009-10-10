import os
import re
import subprocess
import readline

import logging

from FileFinder import FileFinder

try:
	from termstyle import green, cyan, blue, yellow, black, auto
	import termstyle
	termstyle.auto()
except ImportError:
	logging.info("can't import termstyle - install it for pretty colours")
	termstyle = None
	green = cyan = blue = yellow = black = lambda a: a

class Repl(object):
	def __init__(self):
		self.basepath = os.getcwd()
		self.found_files = []
		self.finder = FileFinder(self.basepath)
	
	def highlight_func(self, query_string):
		if termstyle is None:
			return lambda x: x
		bits = query_string.split(' ')
		bits = [bit.lower() for bit in bits]
		searches = [re.compile("(%s)" % (re.escape(bit),), re.I) for bit in bits]
		def do_highlight(s):
			for search in searches:
				s = search.sub(cyan('\\1'), s)
			return s
		return do_highlight
			
	def summarise(self, result_iter, query_string):
		subprocess.call(['clear'])
		self.found_files = []
		i = 0
		bits = query_string.split()
		highlight = self.highlight_func(query_string)
		for filename, fullpath in result_iter:
			self.found_files.append(fullpath)
			relpath = os.path.split(fullpath)[0][len(self.basepath)+1:]
			explanation = ''
			if relpath:
				explanation = "(in ./%s)" % (relpath,)
			index = str(i+1).rjust(2)
			filename = filename.ljust(30)
			print " %s%s   %s %s" % (green(index), black(":"), highlight(filename), black(explanation))
			i += 1
		
	def open(self, index, cmd=["gvim", "--remote"]):
		index -= 1 # indexes start at 1 for readability
		if len(self.found_files) <= index:
			logging.warning("no such index: %s" % (index,))
			return
		filepath = self.found_files[index]
		logging.info("opening file: %s" % (filepath,))
		subprocess.Popen(cmd + [filepath])

	def _loop(self):
		q = raw_input(yellow("\nfind/open file: "))
		if len(q) == 0:
			q = 1 # open the first found file by default
		try:
			index = int(q)
		except ValueError:
			index = None
		if index is not None:
			self.open(index)
		else:
			results = self.finder.find(q)
			self.summarise(results, q)

	def run(self):
		logging.info("getting file list...")
		self.finder.populate()
		try:
			while True:
				self._loop()
		except (KeyboardInterrupt, EOFError):
			return 0
