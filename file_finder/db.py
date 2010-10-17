import threading
import logging
import Queue as queue
import sqlite3
from log import log_exceptions
from search import Search

def adapt_str(s):
	return s.decode("iso-8859-1")
sqlite3.register_adapter(str, adapt_str)

class DB(object):
	def __init__(self, event_queue, search_queue, results_queue, path_filter, file_count=None):
		if file_count is None:
			# it's not that important...
			class ObjectWithValue(object):
				def __init__(self, val): self.value = val
			file_count = ObjectWithValue(0)

		self._file_count = file_count
		self.event_queue = event_queue
		self.search_queue = search_queue
		self.path_filter = path_filter
		self.results_queue = results_queue
		self.dblock = threading.Lock()

		self.dbqueue = queue.Queue(maxsize=1)

		search_thread = threading.Thread(target=log_exceptions(self.poll_search), name="[db] find handler")
		search_thread.daemon = True
		search_thread.start()

		file_thread = threading.Thread(target=log_exceptions(self.poll_events), name="[db] file event handler")
		file_thread.daemon = True
		file_thread.start()

		db_thread = threading.Thread(target=log_exceptions(self.poll_db), name="[db] query runner")
		db_thread.daemon = True
		db_thread.start()

	@property
	def file_count(self):
		return self._file_count.value
	def _add_file_count(self, n):
		self._file_count.value += n

	# poll_events and poll_search each look at their respective queues.
	# When they have something, they add their desired action to the
	# single-size db queue. This causes the db thread to execute the action.
	def poll_events(self):
		while True:
			event = self.event_queue.get()
			self.dbqueue.put(lambda event=event: self.process_event(event))
	
	def poll_search(self):
		while True:
			search = self.search_queue.get()
			# empty the queue; old queries are useless
			try:
				while True:
					search = self.search_queue.get_nowait()
			except queue.Empty: pass
			self.dbqueue.put(lambda search=search: self._perform(search))

	def _perform(self, search):
		search.results = self.find(search.text)
		self.results_queue.put(search)

	def poll_db(self):
		self._create_db()
		while True:
			try:
				self.dbqueue.get()()
			except StopIteration: break
	
	def process_event(self, event):
		if not self.path_filter.should_include(event.path): return
		if event.exists:
			if event.is_dir: return
			self.add_file(event.path, event.name)
		else:
			if event.is_dir:
				self.remove_dir(event.path)
			else:
				self.remove_file(event.path)

	def execute(self, query, params=(), return_count=False):
		try:
			cursor = self.db.cursor()
			if params:
				result = cursor.execute(query, params)
				return cursor.rowcount if return_count else result
			else:
				return cursor.execute(query)
		finally:
			self.db.commit()

	def find(self, query):
		logging.debug("searching: %r" % (query))
		if '/' in query:
			query_type = 'path'
			query = query.replace('/', ' ')
		else:
			query_type = 'name'

		query_param = self._format_like_statement(query)

		sql = ("SELECT DISTINCT name, path FROM files " +
		      "WHERE %s LIKE ? escape '\\' ORDER BY length(path), name LIMIT 51" % (query_type,))
		logging.debug("%s :: %s" % (sql, query_param))
		res = self.execute(sql, (query_param,))
		return list(res)
	
	def _format_like_statement(self, query):
		# psuedo-regexp anchoring
		prefix = '' if query.startswith('^') else '%'
		suffix = '' if query.endswith('$')   else '%'

		query = query.rstrip('$').lstrip('^')
		query = query.replace('_', '\\_')
		query = query.replace('%', '\\%')
		wildcarded_query = query.replace(" ", "%")
		query_param = "%s%s%s" % (prefix, wildcarded_query, suffix)

		return query_param

	def _create_db(self):
		self.db = sqlite3.connect(":memory:")
		self.db.execute("CREATE TABLE files ( id AUTO_INCREMENT PRIMARY KEY, " +
			"path VARCHAR(255), name VARCHAR(255))")
	
	def close(self):
		def action():
			self.db.close()
			raise StopIteration()
		self.dbqueue.put(action)

	def add_file(self, path, name):
		self._add_file_count(1)
		self.execute("INSERT INTO files (name, path) VALUES (?, ?)",
			(name, path))

	def remove_file(self, path):
		self._add_file_count(-1)
		self.execute("DELETE FROM files where path = ?", (path, ))

	def remove_dir(self, path):
		files_deleted = self.execute("DELETE FROM files WHERE path like ?", (path+"%", ), return_count=True)
		self._add_file_count(-files_deleted)

