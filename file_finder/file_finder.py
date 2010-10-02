import os
import subprocess
import logging
from Queue import Queue
from log import log_exceptions

from db import DB

class FileFinder(object):
	def __init__(self, basepath, path_filter, quit_indicator):
		self.quit_indicator = quit_indicator
		self.event_queue = Queue(maxsize=50)
		self.query_queue = Queue()
		self.results_queue = Queue()
		self.db = DB(
				event_queue=self.event_queue,
				query_queue=self.query_queue,
				results_queue=self.results_queue,
				path_filter=path_filter)
		if not basepath.endswith(os.path.sep):
			basepath = basepath + os.path.sep
		self.basepath = basepath
		self.path_filter = path_filter
	
	def clear(self):
		db.clear()

	def populate(self):
		def _run_with_sigint():
			try:
				self._poll()
			finally:
				logging.debug("file finder signalling quit")
				self.quit_indicator.set()
			
		from threading import Thread
		worker = Thread(target=_run_with_sigint, name="[file-finder]")
		worker.daemon = True
		worker.start()
	
	@log_exceptions
	def _poll(self):
		from watcher import TreeWatcher
		watcher = TreeWatcher(self.basepath, self.event_queue, self.path_filter.exclude_paths)
	
	@property
	def has_pending_queries(self):
		return not self.query_queue.empty()

	def find(self, query):
		self.query_queue.put(query)
	
	def results(self, blocking=True):
		return self.results_queue.get(block=blocking)
	
	@property
	def file_count(self):
		return self.db.file_count

