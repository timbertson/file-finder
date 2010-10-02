#!/usr/bin/env python
import os
import re
import Queue as queue
import logging

from pyinotify import WatchManager, ThreadedNotifier, ProcessEvent

try:
	# Supports < pyinotify 0.8.6
	from pyinotify import EventsCodes
	EVENT_MASK = EventsCodes.IN_DELETE | EventsCodes.IN_CREATE | EventsCodes.IN_MOVED_TO | EventsCodes.IN_MOVED_FROM # watched events
except AttributeError:
	# Support for pyinotify 0.8.6
	from pyinotify import IN_DELETE, IN_CREATE, IN_MOVED_FROM, IN_MOVED_TO
	EVENT_MASK = IN_DELETE | IN_CREATE | IN_MOVED_TO | IN_MOVED_FROM

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
		self._watch_manager = WatchManager()
		self._processor = FileProcessEvent(event_queue=event_queue, directory_queue=self._dir_queue, root=self._root)
		self._notifier = ThreadedNotifier(self._watch_manager, self._processor)
		self._notifier.name = "[inotify] notifier"
		self._notifier.daemon = True
		self._notifier.start()
		self._ignored_dir_res = ignored_dir_regexes

		# initial walk
		self.add_dir(self._root)
		self._watch_queue()
	
	def _watch_queue(self):
		while True:
			directory, exists = self._dir_queue.get()
			if exists:
				self.add_dir(directory)
			else:
				self.remove_dir(directory)

	def add_dir(self, path, on_complete=None):
		for pattern in self._ignored_dir_res:
			if re.search(pattern, path):
				logging.debug("skipping: %s (matched %r)" % (path,pattern))
				return
		self._watch_manager.add_watch(path, EVENT_MASK)
		self.walk_directory(path)

	def add_file(self, path, name):
		self._processor.process_IN_CREATE(AddFileEvent(path, name))

	def remove_dir(self, path):
		self._watch_manager.rm_watch(path)

	def walk_directory(self, root):
		"""
		From a give root of a tree this method will walk through every branch
		and return a generator.
		"""
		logging.debug("walking %s" % (root,))
		if os.path.isdir(root):
			names = os.listdir(root)
			for name in names:
				try:
					if os.path.isdir(os.path.join(root, name)):
						self._dir_queue.put((os.path.join(root, name), True))
					else:
						self.add_file(root, name)
				except os.error:
					continue


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

def handler(which, exists):
	def handle_event(self, event):
		event_path = self.relative_path(event.path)
		path = os.path.join(event_path, event.name)
		logging.debug("event %s occurred to path %s" % (which, path))
		if self.is_dir(event):
			self._dir_queue.put((path, exists))
		else:
			self._event_queue.put(Event(base=event_path, name=event.name, event=which, exists=exists))
	return handle_event

class FileProcessEvent(ProcessEvent):
	def __init__(self, event_queue, directory_queue, root):
		self._event_queue = event_queue
		self._dir_queue = directory_queue
		self._root = root
	
	def is_dir(self, event):
		if hasattr(event, "dir"):
			return event.dir
		else:
			return event.is_dir
	
	def relative_path(self, path):
		if path.startswith(self._root):
			return path[len(self._root)+1:]
		else:
			logging.warn("non-relative path encountered: %s" % (path,))
		return path

	process_IN_CREATE = handler(Event.ADDED, True)
	process_IN_DELETE = handler(Event.REMOVED, False)
	process_IN_MOVED_FROM = handler(Event.MOVED_FROM, False)
	process_IN_MOVED_TO = handler(Event.MOVED_TO, True)



if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	import threading
	event_queue = queue.Queue()
	def run():
		while True:
			item = event_queue.get()
			print repr(item)

	main = threading.Thread(target=run)
	main.daemon = True
	main.start()
	FileMonitor('.', event_queue, ('\\.git',))

