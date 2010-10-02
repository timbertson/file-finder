# create whatever globals are needed for watcher to
# at least populate the initial tree

EVENT_MASK = None
class WatchManager(object):
	def add_watch(*a, **k): pass
class ThreadedNotifier(object):
	def __init__(self, *a, **kw):
		self.name = "fake"
		self.daemon = True
	def start(self): pass
ProcessEvent = object
