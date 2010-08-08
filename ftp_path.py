# Copyright (C) 2003-2008, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

"""
ftp_path.py - simulate `os.path` for FTP servers
"""

import posixpath
import stat

import ftp_error


class _Path(object):
    """
    Support class resembling `os.path`, accessible from the `FTPHost`
    object, e. g. as `FTPHost().path.abspath(path)`.

    Hint: substitute `os` with the `FTPHost` object.
    """

    def __init__(self, host):
        self._host = host
        # Delegate these to the `posixpath` module
        pp = posixpath
        self.dirname      = pp.dirname
        self.basename     = pp.basename
        self.isabs        = pp.isabs
        self.commonprefix = pp.commonprefix
        self.join         = pp.join
        self.split        = pp.split
        self.splitdrive   = pp.splitdrive
        self.splitext     = pp.splitext
        self.normcase     = pp.normcase
        self.normpath     = pp.normpath

    def abspath(self, path):
        """Return an absolute path."""
        if not self.isabs(path):
            path = self.join(self._host.getcwd(), path)
        return self.normpath(path)

    def exists(self, path):
        """Return true if the path exists."""
        try:
            lstat_result = self._host.lstat(
                           path, _exception_for_missing_path=False)
            return lstat_result is not None
        except ftp_error.RootDirError:
            return True

    def getmtime(self, path):
        """
        Return the timestamp for the last modification for `path`
        as a float.

        This will raise `PermanentError` if the path doesn't exist,
        but maybe other exceptions depending on the state of the
        server (e. g. timeout).
        """
        return self._host.stat(path).st_mtime

    def getsize(self, path):
        """
        Return the size of the `path` item as an integer.

        This will raise `PermanentError` if the path doesn't exist,
        but maybe raise other exceptions depending on the state of the
        server (e. g. timeout).
        """
        return self._host.stat(path).st_size

    # Check whether a path is a regular file/dir/link. For the first
    #  two cases follow links (like in `os.path`).
    #
    # Implementation note: The previous implementations simply called
    # `stat` or `lstat` and returned `False` if they ended with
    # raising a `PermanentError`. That exception usually used to
    # signal a missing path. This approach has the problem, however,
    # that exceptions caused by code earlier in `lstat` are obscured
    # by the exception handling in `isfile`, `isdir` and `islink`.

    def isfile(self, path):
        """
        Return true if the `path` exists and corresponds to a regular
        file (no link).

        A non-existing path does _not_ cause a `PermanentError`.
        """
        # Workaround if we can't go up from the current directory
        if path == self._host.getcwd():
            return False
        try:
            stat_result = self._host.stat(
                          path, _exception_for_missing_path=False)
            if stat_result is None:
                return False
            else:
                return stat.S_ISREG(stat_result.st_mode)
        except ftp_error.RootDirError:
            return False

    def isdir(self, path):
        """
        Return true if the `path` exists and corresponds to a
        directory (no link).

        A non-existing path does _not_ cause a `PermanentError`.
        """
        # Workaround if we can't go up from the current directory
        if path == self._host.getcwd():
            return True
        try:
            stat_result = self._host.stat(
                          path, _exception_for_missing_path=False)
            if stat_result is None:
                return False
            else:
                return stat.S_ISDIR(stat_result.st_mode)
        except ftp_error.RootDirError:
            return True

    def islink(self, path):
        """
        Return true if the `path` exists and is a link.

        A non-existing path does _not_ cause a `PermanentError`.
        """
        try:
            lstat_result = self._host.lstat(
                           path, _exception_for_missing_path=False)
            if lstat_result is None:
                return False
            else:
                return stat.S_ISLNK(lstat_result.st_mode)
        except ftp_error.RootDirError:
            return False

    def walk(self, top, func, arg):
        """
        Directory tree walk with callback function.

        For each directory in the directory tree rooted at top
        (including top itself, but excluding '.' and '..'), call
        func(arg, dirname, fnames). dirname is the name of the
        directory, and fnames a list of the names of the files and
        subdirectories in dirname (excluding '.' and '..').  func may
        modify the fnames list in-place (e.g. via del or slice
        assignment), and walk will only recurse into the
        subdirectories whose names remain in fnames; this can be used
        to implement a filter, or to impose a specific order of
        visiting.  No semantics are defined for, or required of, arg,
        beyond that arg is always passed to func.  It can be used,
        e.g., to pass a filename pattern, or a mutable object designed
        to accumulate statistics.  Passing None for arg is common.
        """
        # This code (and the above documentation) is taken from
        #  posixpath.py, with slight modifications.
        try:
            names = self._host.listdir(top)
        except OSError:
            return
        func(arg, top, names)
        for name in names:
            name = self.join(top, name)
            try:
                stat_result = self._host.lstat(name)
            except OSError:
                continue
            if stat.S_ISDIR(stat_result[stat.ST_MODE]):
                self.walk(name, func, arg)

