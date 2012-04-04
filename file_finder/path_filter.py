import re, os
import logging

DEFAULT_EXCLUDES = [
	'.*',
	'*.svn*',
	'*.pyc',
	'*.egg-info',
]

class PathFilter(object):
	def __init__(self):
		self.set_excludes(DEFAULT_EXCLUDES)
		self.include_files = []
	
	def glob_to_regexp(self, glob):
		parts = glob.split("*")
		escaped_parts = map(re.escape, parts)
		# matches if it's either surrounded by start/end of string or surrounded by slashes (os.path.sep)
		regexp = "(^|%s)%s($|%s)" % (os.path.sep, '.*'.join(escaped_parts),os.path.sep)
		logging.debug("converted %s -> %s" % (glob, regexp))
		return regexp
		return re.compile(regexp)

	def set_excludes(self, exclude_list):
		self.exclude_paths = map(self.glob_to_regexp, exclude_list)
	
	def add_exclude(self, exclude):
		logging.debug("adding user exclude: %s" % (exclude,))
		self.exclude_paths.append(self.glob_to_regexp(exclude))
	
	def set_include_files(self, include_list):
		self.include_files = map(self.glob_to_regexp, include_list)
	
	def add_include(self, include):
		self.include_files.append(self.glob_to_regexp(include))
	
	def should_include(self, path, is_file=False):
		for exclude_re in self.exclude_paths:
			if re.search(exclude_re, path):
				logging.debug("excluding %s as it matched: %s" % (path, exclude_re))
				return False
		if is_file and len(self.include_files) > 0:
			file_name = os.path.basename(path)
			for include_re in include_files:
				if re.search(include_re, file_name):
					return True
			return False
		else:
			return True
	
	def filter(self, dirnames, filenames):
		"""modify dirnames and filenames in-place to remove
		  all filtered paths"""
		for dirname in dirnames[:]:
			if not self.should_include(dirname, False):
				dirnames.remove(dirname)

		for filename in filenames[:]:
			if not self.should_include(filename, True):
				filenames.remove(filename)
		
