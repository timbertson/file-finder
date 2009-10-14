import os
import subprocess
import logging

from DBWrapper import DBWrapper

class FileFinder(object):
	def __init__(self, basepath, path_filter):
		self.db = DBWrapper()
		if not basepath.endswith(os.path.sep):
			basepath = basepath + os.path.sep
		self.basepath = basepath
		self.path_filter = path_filter
	
	def clear(self):
		db.clear()

	def populate(self, sync=False, watch=True):
		def _run():
			for dirpath, dirnames, filenames in os.walk(self.basepath):
				self.path_filter.filter(dirnames, filenames)
				for filename in filenames:
					rel_dirpath = dirpath[len(self.basepath):]
					self.db.add_file(rel_dirpath, filename)
				
			if watch:
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
		monitor = FileMonitor.FileMonitor(self.db, self.basepath, DummyConfig())
		# monkey patch monitor to use our own filters
		monitor.validate = self.path_filter.should_include

	
	def find(self, query):
		return self.db.select_on_filename(query)
	

