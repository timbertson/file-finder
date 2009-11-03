import logging

class QueueHandler(logging.Handler):
	def __init__(self, queue, level=logging.NOTSET):
		logging.Handler.__init__(self, level=level)
		self.queue = queue
	
	def emit(self, record):
		self.queue.put(record.getMessage())

