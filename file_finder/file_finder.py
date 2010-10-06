import os
import subprocess
import logging
from Queue import Queue
from log import log_exceptions
from multiprocessing import Queue as MPQueue
from multiprocessing import Process, Value
from watcher import TreeWatcher
from search import Search
from db import DB

EMPTY_RESULTS = Search('')
EMPTY_RESULTS.results = []

class FileFinder(object):
	def __init__(self, basepath, path_filter, quit_indicator):
		self.quit_indicator = quit_indicator
		self.event_queue = Queue(maxsize=50)
		self.search_queue = MPQueue()
		self.results_queue = MPQueue()
		if not basepath.endswith(os.path.sep):
			basepath = basepath + os.path.sep
		self.basepath = basepath
		self.path_filter = path_filter
		self._file_count = Value('i', 0)
	
	def populate(self):
		ioproc = Process(target=self._poll, args=(self,))
		ioproc.daemon = True
		ioproc.start()
	
	@log_exceptions
	def _poll(self, *a):
		db = DB(
				event_queue=self.event_queue,
				search_queue=self.search_queue,
				results_queue=self.results_queue,
				path_filter=self.path_filter,
				file_count = self._file_count)
		watcher = TreeWatcher(self.basepath, self.event_queue, self.path_filter.exclude_paths)
		watcher.run_forever()
	
	@property
	def has_pending_queries(self):
		return not self.search_queue.empty()

	def find(self, search):
		if not search:
			self.results_queue.put(EMPTY_RESULTS)
		else:
			self.search_queue.put(search)
	
	def results(self, blocking=True):
		try:
			return self.results_queue.get(block=blocking)
		except EOFError: # only happens on shutdown
			return EMPTY_RESULTS
	
	@property
	def file_count(self):
		return self._file_count.value

