import optparse
import logging
import os
import subprocess

from PathFilter import PathFilter

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
		parser.add_option('-n', '--no-watch', dest='no_watch',
			action='store_true',
			help="disable inotify (folder watch) support")
		parser.add_option('-b', '--basic', dest='basic',
			action='store_true',
			help='basic mode (no curses UI)')

		(options, args) = parser.parse_args()
		self.verbose = options.verbose
		self.log_level = logging.DEBUG if options.verbose else logging.WARNING

		self.open_cmd = options.open_cmd.split()
		self.use_inotify = not options.no_watch
		self.path_filter = PathFilter()
		self.basic = options.basic
		if len(args) == 1:
			self.base_path = args[0]
		elif len(args) == 0:
			self.base_path = '.'
		else:
			parser.error("incorrect number of arguments")
		return self
	
	def main(self):
		if self.basic:
			from Repl import Repl
			Repl(self).run()
		else:
			from CursesUI import CursesUI
			CursesUI(self).run()
	
	def open(self, filepath):
		logging.info("opening file: %s" % (filepath,))
		fullpath = os.path.join(self.base_path, filepath)
		subprocess.Popen(self.open_cmd + [fullpath])

