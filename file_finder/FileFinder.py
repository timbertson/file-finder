import os
import subprocess
import logging

from DBWrapper import DBWrapper
class FileFinder(object):
	def __init__(self, basepath):
		self.db = DBWrapper()
		self.basepath = basepath
	
	def clear(self):
		db.clear()

	def populate(self, args=['ack', '-f'], sync=False):
		def _run():
			proc = subprocess.Popen(args, stdout=subprocess.PIPE)
			for line in proc.stdout:
				line = line.rstrip('\n')
				logging.debug("got line: %s" % (line,))
				relpath, filename= os.path.split(line)
				fullpath = os.path.join(self.basepath, relpath)
				self.db.add_file(relpath, filename)
			self._poll()

		def _run_with_sigint():
			try:
				_run()
			except (KeyboardInterrupt, EOFError):
				import sys
				sys.exit(0)
			
		if sync:
			_run()
		else:
			from threading import Thread
			worker = Thread(target=_run_with_sigint)
			worker.daemon = True
			worker.start()
	
	def _poll(self):
		try:
			from FileMonitor import FileMonitor
		except ImportError:
			logging.error("Can't import FileMonitor - directory updates will be ignored")
			return
		class DummyConfig(object):
			def get_value(self, *a):
				return []
		FileMonitor.FileMonitor(self.db, self.basepath, DummyConfig())
	
	def find(self, query):
		return self.db.select_on_filename(query)
	

