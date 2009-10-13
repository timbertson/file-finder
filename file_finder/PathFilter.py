import re

DEFAULT_EXCLUDES = [
	'.*',
	'*.svn*',
	'*.pyc',
]

class PathFilter(object):
	def __init__(self):
		self.exclude_paths = []
		self.include_files = []
	
	def glob_to_regexp(self, glob):
		parts = glob.split("*")
		escaped_parts = map(re.escape, parts)
		print '.*'.join(escaped_parts)
		return re.compile(".*".join(escaped_parts))

	def set_excludes(self, exclude_list):
		self.exclude_paths = map(self.glob_to_regexp, exclude_list)
	
	def add_exclude(self, exclude):
		self.exclude_paths.append(self.glob_to_regexp(exclude))
	
	def set_include_files(self, include_list):
		self.include_files = map(self.glob_to_regexp, include_list)
	
	def add_include(self, include):
		self.include_files.append(self.glob_to_regexp(include))
	
	def include(self, path, is_file=False):
		for exclude_re in self.exclude_paths:
			if exclude_re.match(path):
				return False
		if is_file and len(self.include_files) > 0:
			file_name = os.path.basename(path)
			for include_re in include_files:
				if include_re.match(file_name):
					return True
			return False
		else:
			return True
	
	def filter(self, dirnames, filenames):
		"""modify dirnames and filenames in-place to remove
		  all filtered paths"""
		pass
		
