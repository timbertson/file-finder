import logging
import threading

class QueueHandler(logging.Handler):
	def __init__(self, queue, level=logging.NOTSET):
		logging.Handler.__init__(self, level=level)
		self.queue = queue
	
	def emit(self, record):
		self.queue.put(record.getMessage())

def log_exceptions(func):
	def _(*a, **kw):
		try:
			return func(*a, **kw)
		except Exception, e:
			logging.exception("error in thread [%s]" % (threading.current_thread().name,))
	return _

