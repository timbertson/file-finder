import threading
import logging
import Queue as queue
import sqlite3
from log import log_exceptions

def adapt_str(s):
	return s.decode("iso-8859-1")
sqlite3.register_adapter(str, adapt_str)

class DB(object):
	def __init__(self, event_queue, query_queue, results_queue, path_filter):
		self.file_count = 0
		self.event_queue = event_queue
		self.query_queue = query_queue
		self.path_filter = path_filter
		self.results_queue = results_queue
		self.dblock = threading.Lock()

		self.dbqueue = queue.Queue(maxsize=1)

		query_thread = threading.Thread(target=log_exceptions(self.poll_query), name="[db] find handler")
		query_thread.daemon = True
		query_thread.start()

		file_thread = threading.Thread(target=log_exceptions(self.poll_events), name="[db] file event handler")
		file_thread.daemon = True
		file_thread.start()

		db_thread = threading.Thread(target=log_exceptions(self.poll_db), name="[db] query runner")
		db_thread.daemon = True
		db_thread.start()

	# poll_events and poll_query each look at their respective queues.
	# When they have something, they acquire the "db" lock and add their desired action
	# to the fsingle-size db queue. This causes the db thread to execute the action.
	def poll_events(self):
		while True:
			event = self.event_queue.get()
			self.dbqueue.put(lambda event=event: self.process_event(event))
	
	def poll_query(self):
		while True:
			query = self.query_queue.get()
			# empty the queue; old queries are useless
			try:
				while True:
					query = self.query_queue.get_nowait()
			except queue.Empty: pass
			self.dbqueue.put(lambda query=query: self.results_queue.put((query, self.find(query))))

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
		query_param = "%%%s%%" % (query.replace(" ", "%"),)
		res = self.execute("SELECT DISTINCT name, path FROM files " +
			"WHERE %s LIKE ? ORDER BY length(path), name LIMIT 51" % (query_type,), (query_param,))
		return list(res)

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
		self.file_count += 1
		self.execute("INSERT INTO files (name, path) VALUES (?, ?)",
			(name, path))

	def remove_file(self, path):
		self.file_count -= 1
		self.execute("DELETE FROM files where path = ?", (path, ))

	def remove_dir(self, path):
		self.file_count -= self.execute("DELETE FROM files WHERE path like ?", (path+"%", ), return_count=True)

