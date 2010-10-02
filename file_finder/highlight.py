import re
import logging

class Highlight(object):
	def __init__(self, query):
		bits = query.replace('/',' ').split()
		bits = sorted(bits, key=len, reverse=True)
		bits = [bit.lower() for bit in bits]
		searches = ["(%s)" % (re.escape(bit),) for bit in bits]
		self.highlight_re = re.compile("(%s)" % ('|'.join(searches),), re.I)

	def __call__(self, string):
		last_end = 0
		for match in self.highlight_re.finditer(string):
			start, end = match.start(), match.end()
			if start > last_end:
				yield (False, string[last_end:start])
			last_end = end
			yield (True, string[start:end])
		if last_end < len(string):
			yield (False, string[last_end:])

	def replace(self, string, replacement_func):
		return self.highlight_re.sub(replacement_func('\\1'), string)

