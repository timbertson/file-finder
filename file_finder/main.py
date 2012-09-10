import optparse
import logging
import os
import subprocess
import tempfile

from path_filter import PathFilter

ignore_path = os.path.expanduser(os.environ.get("FILE_FINDER_IGNORE", "~/.config/file-finder/ignore"))

class Options(object):
	def configure(self):
		usage = "finder [base_path]"
		parser = optparse.OptionParser(usage)
		parser.add_option('-o', '--open-cmd',
			dest='open_cmd',
			default="gvim --remote-tab",
			help="command to open files with (%default)")
		parser.add_option('-v', '--verbose', dest='verbose',
			action='store_true',
			help='more information than you require')
		#parser.add_option('-n', '--no-watch', dest='no_watch',
		#	action='store_true',
		#	help="disable inotify (folder watch) support")
		parser.add_option('-b', '--basic', dest='basic',
			action='store_true',
			help='basic mode (no curses UI)')
		parser.add_option('-x', '--exclude', action='append',
			default=[], help='add an exclude')

		(options, args) = parser.parse_args()
		self.verbose = options.verbose
		self.log_level = logging.DEBUG if options.verbose else logging.INFO
		if options.basic:
			# logging to terminal is fine
			logging.basicConfig(level=self.log_level)
		else:
			# terminal logging would break curses layout:
			logging.basicConfig(level=self.log_level, filename=os.path.join(tempfile.gettempdir(), 'file-finder.log'), filemode='w')
			if not options.verbose:
				# carelessly discard stdout and stderr
				import sys
				sys.stdout = sys.stderr = open(os.devnull, 'w')

		self.open_cmd = options.open_cmd.split()
		#self.use_inotify = not options.no_watch
		self.path_filter = PathFilter()
		map(self.path_filter.add_exclude, options.exclude)
		self.load_user_excludes()
		self.basic = options.basic
		if len(args) == 1:
			self.base_path = args[0]
		elif len(args) == 0:
			self.base_path = '.'
		else:
			parser.error("incorrect number of arguments")
		return self
	
	def load_user_excludes(self):
		try:
			with open(ignore_path) as ignore_file:
				strip = lambda x: x.strip()
				valid = lambda x: x and not x.startswith('#')
				ignore_lines = filter(valid, map(strip, ignore_file.readlines()))
			map(self.path_filter.add_exclude, ignore_lines)
		except IOError: pass

	def main(self):
		if self.basic:
			from repl import Repl
			Repl(self).run()
		else:
			from curses_ui import CursesUI
			CursesUI(self).run()
			logging.debug("curses UI is finished")
			import threading
			for t in threading.enumerate():
				logging.debug("thread: %r is daemon? %r" % (t.name, t.daemon))
	
	def open(self, filepath):
		logging.debug("opening file: %s" % (filepath,))
		fullpath = self.full_path(filepath)
		logging.debug("full command: %r" % (self.open_cmd + [fullpath],))
		subprocess.Popen(self.open_cmd + [fullpath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	
	def full_path(self, relpath):
		return os.path.abspath(os.path.join(self.base_path, relpath))

