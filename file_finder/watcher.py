#!/usr/bin/env python
import os
import re
import Queue as queue
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

class AddFileEvent(object):
	def __init__(self, path, name):
		self.dir = False
		self.path = path
		self.name = name

class TreeWatcher(object):
	"""
	TreeWatcher Class keeps track of all files down a tree starting at the root,
	appending events to the end of event_queue.
	Spawns an inotify watcher thread and then watches the queue indefinitely
	"""

	def __init__(self, root, event_queue, ignored_dir_regexes=()):
		self._dir_queue = queue.Queue()
		self._root = os.path.realpath(root)

		# Add a watch to the root of the dir
		self._handler = FileFinderEventHandler(event_queue=event_queue, directory_queue=self._dir_queue, root=self._root)
		notifier = Observer()
		notifier.name = "[inotify] notifier"
		notifier.daemon = True
		notifier.schedule(self._handler, self._root, recursive=True)
		notifier.start()
		self._ignored_dir_res = ignored_dir_regexes

	def run_forever(self):
		# initial walk
		self.add_dir(self._root)
		self._watch_queue()
	
	def _watch_queue(self):
		while True:
			directory, exists = self._dir_queue.get()
			if exists:
				self.add_dir(directory)
			else:
				logging.debug("got nonexistent directory: %s" % (directory,))

	def _should_skip_path(self, path):
		for pattern in self._ignored_dir_res:
			if re.search(pattern, path):
				return True
		return False

	def add_dir(self, path):
		if not self._should_skip_path(path):
			self.walk_directory(path)

	def add_file(self, path, name):
		self._handler.on_created(FileCreatedEvent(os.path.join(path,name)))

	def walk_directory(self, root):
		"""
		From a give root of a tree this method will walk through every branch
		and return a generator.
		"""
		if os.path.isdir(root):
			logging.debug("walking %s" % (root,))
			try:
				names = os.listdir(root)
				for name in names:
					try:
						if os.path.isdir(os.path.join(root, name)):
							self._dir_queue.put((os.path.join(root, name), True))
						else:
							self.add_file(root, name)
					except os.error: continue
			except os.error: pass


class Event(object):
	MOVED_TO = 'MOVED_TO'
	MOVED_FROM = 'MOVED_FROM'
	ADDED = 'ADDED'
	REMOVED = 'REMOVED'

	def __init__(self, base, event, exists, name=None):
		self.base = base
		self.name = name
		self.event = event
		self.exists = exists
	
	def __repr__(self):
		return "%s %s%s"% (
				"+" if self.exists else "-",
				self.path,
				"/" if self.is_dir else "")
	
	__str__ = __repr__
	
	def _is_dir(self): return self.name is None
	is_dir = property(_is_dir)
	
	def _get_relative_path(self):
		return os.path.join(self.base, self.name or '')
	path = property(_get_relative_path)

def handler(which, exists, path_attr='src_path'):
	def handle_event(self, event):
		path = self.relative_path(getattr(event, path_attr))
		if not self.is_dir(event):
			logging.debug("event %s occurred to path %s" % (which, path))
			base, name = os.path.split(path)
			self._event_queue.put(Event(base=base, name=name, event=which, exists=exists))
	return handle_event

class FileFinderEventHandler(FileSystemEventHandler):
	def __init__(self, event_queue, directory_queue, root):
		self._event_queue = event_queue
		self._root = root

	def is_dir(self, event):
		return event.is_directory
	
	def relative_path(self, path):
		if not os.path.isabs(path):
			return path
		if path.startswith(self._root):
			return os.path.relpath(path, self._root)
		else:
			logging.warn("non-relative path encountered: %s" % (path,))
		return path

	def on_moved(self, event):
		handler(Event.MOVED_FROM, False)
		handler(Event.MOVED_TO, True, 'dest_path')
	on_created = handler(Event.ADDED, True)
	on_deleted = handler(Event.REMOVED, False)

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	import threading
	event_queue = queue.Queue()
	def run():
		while True:
			item = event_queue.get()

	main = threading.Thread(target=run)
	main.daemon = True
	main.start()
	FileMonitor('.', event_queue, ('\\.git',))

