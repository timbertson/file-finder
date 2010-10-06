class Search(object):
	def __init__(self, text, is_repeat=False):
		self.text = text
		self.is_repeat = is_repeat
		self.results = None

	def __nonzero__(self):
		return bool(self.text)
