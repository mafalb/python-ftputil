# Copyright (C) 2003, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# - Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# - Neither the name of the above author nor the names of the
#   contributors to the software may be used to endorse or promote
#   products derived from this software without specific prior written
#   permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# $Id: ftputil.py,v 1.123 2003/06/09 17:23:51 schwa Exp $

"""
ftputil - higher level support for FTP sessions

FTPHost objects
    This class resembles the `os` module's interface to ordinary file
    systems. In addition, it provides a method `file` which will
    return file-objects corresponding to remote files.

    # example session
    host = ftputil.FTPHost('ftp.domain.com', 'me', 'secret')
    print host.getcwd()  # e. g. '/home/me'
    source = host.file('sourcefile', 'r')
    host.mkdir('newdir')
    host.chdir('newdir')
    target = host.file('targetfile', 'w')
    host.copyfileobj(source, target)
    source.close()
    target.close()
    host.remove('targetfile')
    host.chdir(host.pardir)
    host.rmdir('newdir')
    host.close()

    There are also shortcuts for uploads and downloads:

    host.upload(local_file, remote_file)
    host.download(remote_file, local_file)

    Both accept an additional mode parameter. If it is 'b', the
    transfer mode will be for binary files.

    For even more functionality refer to the documentation in
    `ftputil.txt`.

FTPFile objects
    `FTPFile` objects are constructed via the `file` method of
    `FTPHost` objects. `FTPFile` objects support the usual file
    operations for non-seekable files (`read`, `readline`,
    `readlines`, `xreadlines`, `write`, `writelines`, `close`).

Note: ftputil currently is not threadsafe. More specifically, you can
      use different `FTPHost` objects in different threads but not
      using a single `FTPHost` object in different threads.
"""

# TODO
# - move "stat stuff" into an own module `ftp_stat.py`
# - fix defects regarding timeshift/stat calculations
# - package ftputil for distutils
#
# Ideas for future development:
# - handle connection timeouts
# - what about thread safety? (also have a look at `ftplib`)
# - caching of `FTPHost.stat` results? policy?
# - map FTP error numbers to os error numbers (ENOENT etc.)?

# for Python 2.1
from __future__ import nested_scopes

import ftp_error
import ftp_file
import ftp_path
import ftp_stat
import ftplib
import os
import stat
import sys
import time

# make exceptions available in this module for backwards compatibilty
from ftp_error import *
# `True`, `False`
from true_false import *


__all__ = ['FTPError', 'FTPOSError', 'TemporaryError',
           'PermanentError', 'ParserError', 'FTPIOError',
           'RootDirError', 'FTPHost']
__version__ = '1.2 beta'


#####################################################################
# `FTPHost` class with several methods similar to those of `os`

class FTPHost:
    """FTP host class."""

    # Implementation notes:
    #
    # Upon every request of a file (`_FTPFile` object) a new FTP
    # session is created ("cloned"), leading to a child session of
    # the `FTPHost` object from which the file is requested.
    #
    # This is needed because opening an `_FTPFile` will make the
    # local session object wait for the completion of the transfer.
    # In fact, code like this would block indefinitely, if the `RETR`
    # request would be made on the `_session` of the object host:
    #
    #   host = FTPHost(ftp_server, user, password)
    #   f = host.file('index.html')
    #   host.getcwd()   # would block!
    #
    # On the other hand, the initially constructed host object will
    # store references to already established `_FTPFile` objects and
    # reuse an associated connection if its associated `_FTPFile`
    # has been closed.

    def __init__(self, *args, **kwargs):
        """Abstract initialization of `FTPHost` object."""
        # store arguments for later operations
        self._args = args
        self._kwargs = kwargs
        # make a session according to these arguments
        self._session = self._make_session()
        # simulate os.path
        self.path = ftp_path._Path(self)
        # associated `FTPHost` objects for data transfer
        self._children = []
        self.closed = False
        # set curdir, pardir etc. for the remote host; RFC 959 states
        #  that this is, strictly spoken, dependent on the server OS
        #  but it seems to work at least with Unix and Windows
        #  servers
        self.curdir, self.pardir, self.sep = '.', '..', '/'
        # set default time shift (used in `upload_if_newer` and
        #  `download_if_newer`)
        self.set_time_shift(0.0)
        # check if we have a Microsoft ROBIN server
        try:
            response = ftp_error._try_with_oserror(
                       self._session.voidcmd, 'STAT')
        except ftp_error.PermanentError:
            response = ''
        #XXX If these servers can be configured to change their
        #  directory output format, we will need a more sophisticated
        #  test.
        if response.find('ROBIN Microsoft') != -1 or \
           response.find('Bliss_Server Microsoft') != -1:
            self._parser = ftp_stat._MSStatParser()
        else:
            self._parser = ftp_stat._UnixStatParser()

    #
    # dealing with child sessions and file-like objects (rather
    #  low-level)
    #
    def _make_session(self):
        """
        Return a new session object according to the current state of
        this `FTPHost` instance.
        """
        # use copies of the arguments
        args = self._args[:]
        kwargs = self._kwargs.copy()
        # if a session factory had been given on the instantiation of
        #  this `FTPHost` object, use the same factory for this
        #  `FTPHost` object's child sessions
        if kwargs.has_key('session_factory'):
            factory = kwargs['session_factory']
            del kwargs['session_factory']
        else:
            factory = ftplib.FTP
        return ftp_error._try_with_oserror(factory, *args, **kwargs)

    def _copy(self):
        """Return a copy of this FTPHost object."""
        # The copy includes a new session factory return value (aka
        #  session) but doesn't copy the state of `self.getcwd()`.
        return FTPHost(*self._args, **self._kwargs)

    def _available_child(self):
        """
        Return an available (i. e. one whose `_file` object is closed)
        child (`FTPHost` object) from the pool of children or `None`
        if there aren't any.
        """
        for host in self._children:
            if host._file.closed:
                return host
        # be explicit
        return None

    def file(self, path, mode='r'):
        """
        Return an open file(-like) object which is associated with
        this `FTPHost` object.

        This method tries to reuse a child but will generate a new one
        if none is available.
        """
        host = self._available_child()
        if host is None:
            host = self._copy()
            self._children.append(host)
            host._file = ftp_file._FTPFile(host)
        basedir = self.getcwd()
        host.chdir(basedir)
        host._file._open(path, mode)
        return host._file

    def open(self, path, mode='r'):
        return self.file(path, mode)

    def close(self):
        """Close host connection."""
        if not self.closed:
            # close associated children
            for host in self._children:
                # only children have `_file` attributes
                host._file.close()
                host.close()
            # now deal with our-self
            ftp_error._try_with_oserror(self._session.close)
            self._children = []
            self.closed = True

    def __del__(self):
        try:
            self.close()
        except:
            # we don't want warnings if the constructor did fail
            pass

    #
    # time shift adjustment between client (i. e. us) and server
    #
    def set_time_shift(self, time_shift):
        """
        Set the time shift value (i. e. the time difference between
        client and server) for this `FTPHost` object. By (my)
        definition, the time shift value is positive if the local
        time of the server is greater than the local time of the
        client (for the same physical time). The time shift is
        measured in seconds.
        """
        self._time_shift = time_shift

    def time_shift(self):
        """
        Return the time shift between FTP server and client. See the
        docstring of `set_time_shift` for more on this value.
        """
        return self._time_shift

    def __rounded_time_shift(self, time_shift):
        """
        Return the given time shift in seconds, but rounded to
        full hours. The argument is also assumed to be given in
        seconds.
        """
        minute = 60.0
        hour = 60.0 * minute
        # avoid division by zero below
        if time_shift == 0:
            return 0.0
        # use a positive value for rounding
        absolute_time_shift = abs(time_shift)
        signum = time_shift / absolute_time_shift
        # round it to hours; this code should also work for later Python
        #  versions because of the explicit `int`
        absolute_rounded_time_shift = \
          int( (absolute_time_shift + 30*minute) / hour) * hour
        # return with correct sign
        return signum * absolute_rounded_time_shift

    def __assert_valid_time_shift(self, time_shift):
        """
        Perform sanity checks on the time shift value (given in
        seconds). If the value fails, raise a `TimeShiftError`,
        else simply return `None`.
        """
        minute = 60.0
        hour = 60.0 * minute
        absolute_rounded_time_shift = \
          abs( self.__rounded_time_shift(time_shift) )
        # test 1: fail if the absolute time shift is greater than
        #  a full day (24 hours)
        if absolute_rounded_time_shift > 24 * hour:
            raise ftp_error.TimeShiftError(
                  "time shift (%.2f s) > 1 day" % time_shift)
        # test 2: fail if the deviation between given time shift and
        #  full hours is greater than a certain limit (e. g. five minutes)
        maximum_deviation = 5 * minute
        if abs( time_shift - self.__rounded_time_shift(time_shift) ) > \
           maximum_deviation:
            raise ftp_error.TimeShiftError(
                  "time shift (%.2f s) deviates more than %d s from full hours"
                  % (time_shift, maximum_deviation) )

    def synchronize_time(self):
        """
        Synchronize the local times of FTP client and server. This
        is necessary to let `upload_if_newer` and `download_if_newer`
        work correctly.

        This implementation of `synchronize_time` requires _all_ of
        the following:

        - The connection between server and client is established.
        - The client has write access to the directory that is
          current when `synchronize_time` is called.
        - That directory is _not_ the root directory of the FTP
          server.

        The usual usage pattern of `synchronize_time` is to call it
        directly after the connection is established. (As can be
        concluded from the points above, this requires write access
        to the login directory.)

        If `synchronize_time` fails, it raises a `TimeShiftError`.
        """
        #FIXME `synchronize_time`, `upload_if_newer`,
        #  `download_if_newer` and the `*stat` methods will fail
        #  if the timezones for client and server "cross the
        #  dateline" (see mail from Andrew Ittner, 2003-03-17)
        helper_file_name = "_ftputil_sync_"
        # open a dummy file for writing in the current directory
        #  on the FTP host, then close it
        try:
            file_ = self.file(helper_file_name, 'w')
            file_.close()
            # get the modification time of the new file
            try:
                remote_time = self.path.getmtime(helper_file_name)
            except ftp_error.RootDirError:
                raise ftp_error.TimeShiftError(
                      "can't use root directory for temp file")
        finally:
            # remove the just written file
            self.unlink(helper_file_name)
        # calculate the difference between server and client
        time_shift = remote_time - time.time()
        # do some sanity checks
        self.__assert_valid_time_shift(time_shift)
        # if tests passed, store the time difference as time shift value
        self.set_time_shift( self.__rounded_time_shift(time_shift) )

    #
    # operations based on file-like objects (rather high-level)
    #
    def copyfileobj(self, source, target, length=64*1024):
        "Copy data from file-like object source to file-like object target."
        # inspired by `shutil.copyfileobj` (I don't use the `shutil`
        #  code directly because it might change)
        while True:
            buffer = source.read(length)
            if not buffer:
                break
            target.write(buffer)

    def __get_modes(self, mode):
        """Return modes for source and target file."""
        if mode == 'b':
            return 'rb', 'wb'
        else:
            return 'r', 'w'

    def __copy_file(self, source, target, mode, source_open, target_open):
        """
        Copy a file from source to target. Which of both is a local
        or a remote file is determined by the arguments.
        """
        source_mode, target_mode = self.__get_modes(mode)
        source = source_open(source, source_mode)
        target = target_open(target, target_mode)
        self.copyfileobj(source, target)
        source.close()
        target.close()

    def upload(self, source, target, mode=''):
        """
        Upload a file from the local source (name) to the remote
        target (name). The argument mode is an empty string or 'a' for
        text copies, or 'b' for binary copies.
        """
        self.__copy_file(source, target, mode, open, self.file)

    def download(self, source, target, mode=''):
        """
        Download a file from the remote source (name) to the local
        target (name). The argument mode is an empty string or 'a' for
        text copies, or 'b' for binary copies.
        """
        self.__copy_file(source, target, mode, self.file, open)

    #XXX the use of the `copy_method` seems less-than-ideal
    #  factoring; can we handle it in another way?

    def __copy_file_if_newer(self, source, target, mode,
      source_mtime, target_mtime, target_exists, copy_method):
        """
        Copy a source file only if it's newer than the target. The
        direction of the copy operation is determined by the
        arguments. See methods `upload_if_newer` and
        `download_if_newer` for examples.

        If the copy was necessary, return `True`, else return `False`.
        """
        source_timestamp = source_mtime(source)
        if target_exists(target):
            target_timestamp = target_mtime(target)
        else:
            # every timestamp is newer than this one
            target_timestamp = 0.0
        if source_timestamp > target_timestamp:
            copy_method(source, target, mode)
            return True
        else:
            return False

    def __shifted_local_mtime(self, file_name):
        """
        Return last modification of a local file, corrected with
        respect to the time shift between client and server.
        """
        local_mtime = os.path.getmtime(file_name)
        return local_mtime + self.time_shift()

    def upload_if_newer(self, source, target, mode=''):
        """
        Upload a file only if it's newer than the target on the
        remote host or if the target file does not exist.

        If an upload was necessary, return `True`, else return
        `False`.
        """
        return self.__copy_file_if_newer(source, target, mode,
          self.__shifted_local_mtime, self.path.getmtime,
          self.path.exists, self.upload)

    def download_if_newer(self, source, target, mode=''):
        """
        Download a file only if it's newer than the target on the
        local host or if the target file does not exist.

        If a download was necessary, return `True`, else return
        `False`.
        """
        return self.__copy_file_if_newer(source, target, mode,
          self.path.getmtime, self.__shifted_local_mtime,
          os.path.exists, self.download)

    #
    # miscellaneous utility methods resembling those in `os`
    #
    def getcwd(self):
        """Return the current path name."""
        return ftp_error._try_with_oserror(self._session.pwd)

    def chdir(self, path):
        """Change the directory on the host."""
        ftp_error._try_with_oserror(self._session.cwd, path)

    def mkdir(self, path, mode=None):
        """
        Make the directory path on the remote host. The argument mode
        is ignored and only "supported" for similarity with os.mkdir.
        """
        ftp_error._try_with_oserror(self._session.mkd, path)

    def rmdir(self, path):
        """Remove the directory on the remote host."""
        ftp_error._try_with_oserror(self._session.rmd, path)

    def remove(self, path):
        """Remove the given file."""
        ftp_error._try_with_oserror(self._session.delete, path)

    def unlink(self, path):
        """Remove the given file."""
        self.remove(path)

    def rename(self, source, target):
        """Rename the source on the FTP host to target."""
        ftp_error._try_with_oserror(self._session.rename, source, target)

    def _dir(self, path):
        """Return a directory listing as made by FTP's `DIR` command."""
        # we can't use `self.path.isdir` in this method because that
        #  would cause a call of `(l)stat` and thus a call to `_dir`,
        #  so we would end up with an infinite recursion
        lines = []
        # use `name=name` for Python versions which don't support
        #  "nested scopes"
        callback = lambda line, lines=lines: lines.append(line)
        ftp_error._try_with_oserror(self._session.dir, path, callback=callback)
        return lines

    def _parse_line(self, line, fail=True):
        """Return `_Stat` instance corresponding to the given text line."""
        try:
            return self._parser.parse_line(line)
        except ftp_error.ParserError:
            if fail:
                raise
            else:
                return None

    def listdir(self, path):
        """
        Return a list with directories, files etc. in the directory
        named path.
        """
        path = self.path.abspath(path)
        if not self.path.isdir(path):
            raise ftp_error.PermanentError("550 %s: no such directory" % path)
        lines = self._dir(path)
        names = []
        for line in lines:
            stat_result = self._parse_line(line, fail=False)
            if stat_result is not None:
                names.append(stat_result._st_name)
        return names

    def _stat_candidates(self, lines, wanted_name):
        """Return candidate lines for further analysis."""
        return [ line  for line in lines
                 if line.find(wanted_name) != -1 ]

    def lstat(self, path):
        """Return an object similar to that returned by `os.lstat`."""
        # get output from FTP's `DIR` command
        lines = []
        path = self.path.abspath(path)
        # Note: (l)stat works by going one directory up and parsing
        #  the output of an FTP `DIR` command. Unfortunately, it is
        #  not possible to to this for the root directory `/`.
        if path == '/':
            raise ftp_error.RootDirError(
                  "can't invoke stat for remote root directory")
        dirname, basename = self.path.split(path)
        lines = self._dir(dirname)
        # search for name to be stat'ed without parsing the whole
        #  directory listing
        candidates = self._stat_candidates(lines, basename)
        # parse candidates
        for line in candidates:
            stat_result = self._parse_line(line, fail=False)
            if (stat_result is not None) and \
              (stat_result._st_name == basename):
                return stat_result
        raise ftp_error.PermanentError(
              "550 %s: no such file or directory" % path)

    def stat(self, path):
        """Return info from a `stat` call."""
        # most code in this method is used to detect recursive
        #  link structures
        visited_paths = {}
        while True:
            # stat the link if it is one, else the file/directory
            stat_result = self.lstat(path)
            # if the file is not a link, the `stat` result is the
            #  same as the `lstat` result
            if not stat.S_ISLNK(stat_result.st_mode):
                return stat_result
            # if we stat'ed a link, calculate a normalized path for
            #  the file the link points to
            dirname, basename = self.path.split(path)
            path = self.path.join(dirname, stat_result._st_target)
            path = self.path.normpath(path)
            # check for cyclic structure
            if visited_paths.has_key(path):
                # we had this path already
                raise ftp_error.PermanentError(
                      "recursive link structure detected")
            # remember the path we have encountered
            visited_paths[path] = True

