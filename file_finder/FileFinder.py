import os
import subprocess
import logging

from DBWrapper import DBWrapper

class FileFinder(object):
	def __init__(self, basepath, path_filter, quit_indicator):
		self.quit_indicator = quit_indicator
		self.db = DBWrapper()
		if not basepath.endswith(os.path.sep):
			basepath = basepath + os.path.sep
		self.basepath = basepath
		self.path_filter = path_filter
	
	def clear(self):
		db.clear()

	def populate(self, sync=False, watch=True):
		def _run():
			if watch and self._poll():
				return

			for dirpath, dirnames, filenames in os.walk(self.basepath):
				self.path_filter.filter(dirnames, filenames)
				for filename in filenames:
					rel_dirpath = dirpath[len(self.basepath):]
					self.db.add_file(rel_dirpath, filename)


		def _run_with_sigint():
			try:
				_run()
			except Exception:
				self.quit_indicator.set()
			
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
			return False
		class DummyConfig(object):
			def get_value(self, *a):
				return []
		# monkey patch monitor to use our own filters
		def wrapped_validate(instance, _path, is_file=False):
			return self.path_filter.should_include(_path, is_file=is_file)
		FileMonitor.validate = wrapped_validate
		monitor = FileMonitor(self.db, self.basepath, DummyConfig())
		return True

	
	def find(self, query):
		return self.db.select_on_filename(query)
	

