"""
File Monitor Contains
- FileMonitor Class
-- Keeps track of files with in a give tree

- WalkDirectoryThread
-- Thread to walk through the tree and store the file paths to a DBWrapper
"""
import os
import stat
import re
import urllib
from Logger import log
from pyinotify import WatchManager, Notifier, ThreadedNotifier, EventsCodes, ProcessEvent
from threading import Thread
from threadpool import ThreadPool

try:
    # Supports < pyinotify 0.8.6
    EVENT_MASK = EventsCodes.IN_DELETE | EventsCodes.IN_CREATE | EventsCodes.IN_MOVED_TO | EventsCodes.IN_MOVED_FROM # watched events
except AttributeError:
    # Support for pyinotify 0.8.6
    from pyinotify import IN_DELETE, IN_CREATE, IN_MOVED_FROM, IN_MOVED_TO
    EVENT_MASK = IN_DELETE | IN_CREATE | IN_MOVED_TO | IN_MOVED_FROM
    
    
THREAD_POOL_WORKS = 20


class FileMonitor(object):
    """
    FileMonitor Class keeps track of all files down a tree starting at the root
    """

    def __init__(self, db_wrapper, root, config, on_complete=None):
        self._file_count = 0
        self._db_wrapper = db_wrapper
        self._root = os.path.realpath(root)
        self._config = config
        self._ignore_regexs = []
        self._set_ignore_list()
        
        self._thread_pool = ThreadPool(THREAD_POOL_WORKS)

        # Add a watch to the root of the dir
        self._watch_manager = WatchManager()
        self._notifier = ThreadedNotifier(self._watch_manager,
            FileProcessEvent(self))
        self._notifier.start()

        # initial walk
        self.add_dir(self._root, on_complete = on_complete)

    def _set_ignore_list(self):
        log.info("[FileMonitor] Set Regexs for Ignore List")

        self._ignore_regexs = []
        # Complie Ignore list in to a list of regexs
        for ignore in self._config.get_value("IGNORE_FILE_FILETYPES"):
            ignore = ignore.strip()
            ignore = ignore.replace(".", "\.")
            ignore = ignore.replace("*", ".*")
            ignore = "^"+ignore+"$"
            log.debug("[FileMonitor] Ignore Regex = %s" % ignore)
            self._ignore_regexs.append(re.compile(ignore))

    def add_dir(self, path, on_complete=None):
        """
        Starts a WalkDirectoryThread to add the directory
        """
        if self.validate(path, is_file=False):
            self._watch_manager.add_watch(path, EVENT_MASK)
            if on_complete:
                _on_complete = lambda *a: on_complete()
            else:
                _on_complete = None
            self._thread_pool.queueTask(self.walk_directory, path, _on_complete)

    def _make_relative_path(self, path):
        if path.startswith(self._root):
            return path[len(self._root)+1:]
        return path

    def add_file(self, path, name):
        if self.validate(name, is_file=True):
            path = self._make_relative_path(path)
            self._db_wrapper.add_file(path, name)
            self._file_count = self._file_count + 1

    def validate(self, name, is_file=False):
         # Check to make sure the file not in the ignore list
        for ignore_re in self._ignore_regexs:
            if ignore_re.match(name):
                log.debug("[WalkDirectoryThread] ##### Ignored %s #####", name)
                return False
        log.debug("[WalkDirectoryThread] # Passed %s", name)
        return True

    def remove_file(self, path, name):
        path = self._make_relative_path(path)
        self._db_wrapper.remove_file(path, name)

    def remove_dir(self, path):
        self._db_wrapper.remove_dir(path)

    def _validate_file_query_input(self, name):
        if name.find("%") > -1:
            return False
        return True

    def set_root_path(self, root):
        self._root = root

    def change_root(self, root):
        if self._root != root:
            self._root = root
            self._db_wrapper.clear_database()
            self.add_dir(self._root)

    def refresh_database(self):
        self._db_wrapper.clear_database()
        self._set_ignore_list()
        self.add_dir(self._root)

    def search_for_files(self, name):
        res_filewrappers = []
        if self._validate_file_query_input(name):
            path_name = self._root + "%" + name
            for row in self._db_wrapper.select_on_filename(path_name):
                res_filewrappers.append(FileWrapper(name, self._root,
                    row[0], row[1]))
        return res_filewrappers

    def walk_directory(self, root):
        """
        From a give root of a tree this method will walk through ever branch
        and return a generator.
        """
        if os.path.isdir(root):
            names = os.listdir(root)
            for name in names:
                try:
                    file_stat = os.lstat(os.path.join(root, name))
                except os.error:
                    continue

                if stat.S_ISDIR(file_stat.st_mode):
                    if self.validate(name, is_file=False):
                      self.add_dir(os.path.join(root, name))
                else:
                    self.add_file(root, name)


class FileProcessEvent(ProcessEvent):

    def __init__(self, file_monitor):
        self._file_monitor = file_monitor
    
    def is_dir(self, event):
        if hasattr(event, "dir"):
            return event.dir
        else:
            return event.is_dir

    def process_IN_CREATE(self, event):
        path = os.path.join(event.path, event.name)
        
        if self.is_dir(event):
            log.info("[FileProcessEvent] CREATED DIRECTORY: " + path)
            self._file_monitor.add_dir(path)
        else:
            log.info("[FileProcessEvent] CREATED FILE: " + path)
            self._file_monitor.add_file(event.path, event.name)

    def process_IN_DELETE(self, event):
        path = os.path.join(event.path, event.name)
        if self.is_dir(event):
            log.info("[FileProcessEvent] DELETED DIRECTORY: " + path)
            self._file_monitor.remove_dir(path)
        else:
            log.info("[FileProcessEvent] DELETED FILE: " + path)
            self._file_monitor.remove_file(event.path, event.name)

    def process_IN_MOVED_FROM(self, event):
        path = os.path.join(event.path, event.name)
        log.info("[FileProcessEvent] MOVED_FROM: " + path)
        self.process_IN_DELETE(event)

    def process_IN_MOVED_TO(self, event):
        path = os.path.join(event.path, event.name)
        log.info("[FileProcessEvent] MOVED_TO: " + path)
        self.process_IN_CREATE(event)


class FileWrapper(object):

    def __init__(self, query_input, root, name, path):
        self._path = path
        self._name = name
        self._query_input = query_input
        self._root = root

    def _get_path(self):
        return self._path
    path = property(_get_path)

    def _get_uri(self):
        uri = "file://" + urllib.quote(self._path)
        return uri
    uri = property(_get_uri)

    def _get_display_path(self):
        return self.highlight_pattern(self.path)
    display_path = property(_get_display_path)

    def highlight_pattern(self, path):
        path = path.replace(self._root + "/", "") # Relative path
        log.debug("[FileWrapper] path = " + path)
        query_list = self._query_input.lower().split(" ")

        last_postion = 0
        for word in query_list:
            location = path.lower().find(word, last_postion)
            log.debug("[FileWrapper] Found Postion = " + str(location))
            if location > -1:
                last_postion = (location + len(word) + 3)
                a_path = list(path)
                a_path.insert(location, "<b>")
                a_path.insert(location + len(word) + 1, "</b>")
                path = "".join(a_path)

        log.debug("[FileWrapper] Markup Path = " + path)
        return path

if __name__ == '__main__':
    from DBWrapper import DBWrapper
    from Config import Config
    db = DBWrapper()
    file_mon = FileMonitor(db, ".", Config())

