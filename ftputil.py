# Copyright (C) 2002-2004, Stefan Schwarzer <sschwarzer@sschwarzer.net>
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

# $Id$

"""
ftputil - high-level FTP client library

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
    `FTPFile` objects are constructed via the `file` method (`open`
    is an alias) of `FTPHost` objects. `FTPFile` objects support the
    usual file operations for non-seekable files (`read`, `readline`,
    `readlines`, `xreadlines`, `write`, `writelines`, `close`).

Note: ftputil currently is not threadsafe. More specifically, you can
      use different `FTPHost` objects in different threads but not
      using a single `FTPHost` object in different threads.
"""

# for Python 2.1
from __future__ import nested_scopes

import ftplib
import os
import sys
import time

import ftp_error
import ftp_file
import ftp_path
import ftp_stat

# make exceptions available in this module for backwards compatibilty
from ftp_error import *
# `True`, `False`
from true_false import *


# it's recommended to use the error classes via the `ftp_error` module;
#  they're only here for backward compatibility
__all__ = ['FTPError', 'FTPOSError', 'TemporaryError',
           'PermanentError', 'ParserError', 'FTPIOError',
           'RootDirError', 'FTPHost']
__version__ = '2.0.4'


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
        # check whether we have an FTP server which emits Microsoft-
        #  style directory listings
        if self.__emits_ms_format():
            self.set_directory_format("ms")
        else:
            self.set_directory_format("unix")

    #
    # setting the directory format for the remote server
    #
    def __emits_ms_format(self):
        """
        Return a true value if the FTP server seems to emit Microsoft
        directory listing format; else return a false value.
        """
        #XXX if these servers can be configured to change their
        #  directory output format, we will need a more sophisticated
        #  test
        try:
            stat_response = ftp_error._try_with_oserror(
                            self._session.voidcmd, 'STAT')
        except ftp_error.PermanentError:
            # some FTP servers have the `STAT` command disabled
            stat_response = ''
        # check for indicators in `STAT` response
        ms_indicators = ("ROBIN Microsoft", "Bliss_Server Microsoft",
                         "Microsoft Windows NT FTP Server status")
        for indicator in ms_indicators:
            if stat_response.find(indicator) != -1:
                return True
        return False

    def set_directory_format(self, server_platform):
        """
        Tell this `FTPHost` object the directory format of the remote
        server. Ideally, this should never be necessary, but you can
        use it as a resort if the automatic server detection does not
        work as it should.

        `server_platform` is one of the following strings:

        "unix": Use this if the directory listing from the server
        looks like

        drwxr-sr-x   2 45854    200           512 Jul 30 17:14 image
        -rw-r--r--   1 45854    200          4604 Jan 19 23:11 index.html

        "ms": Use this if the directory listing from the server looks
        like

        12-07-01  02:05PM       <DIR>          XPLaunch
        07-17-00  02:08PM             12266720 digidash.exe

        If the argument is none of the above strings, a `ValueError`
        is raised.
        """
        parsers = {"unix"   : ftp_stat._UnixStat,
                   "ms"     : ftp_stat._MSStat}
        if parsers.has_key(server_platform):
            self._stat = parsers[server_platform](self)
        else:
            raise ValueError("invalid server platform '%s'" % server_platform)

    #
    # dealing with child sessions and file-like objects
    #  (rather low-level)
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
        """Return a copy of this `FTPHost` object."""
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
        # prepare for changing the directory (see whitespace workaround
        #  in method `_dir`)
        if host.path.isabs(path):
            effective_path = path
        else:
            effective_path = host.path.join(basedir, path)
        effective_dir, effective_file = host.path.split(effective_path)
        try:
            # this will fail if we can't access the directory at all
            host.chdir(effective_dir)
        except ftp_error.PermanentError:
            # similarly to a failed `file` in a local filesystem, we
            #  raise an `IOError`, not an `OSError`
            raise ftp_error.FTPIOError("directory '%s' is not accessible" %
                                       effective_dir)
        host._file._open(effective_file, mode)
        return host._file

    def open(self, path, mode='r'):
        # alias for `file` method
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
        client (for the same physical time), i. e.

            time_shift =def= t_server - t_client
        <=> t_server = t_client + time_shift
        <=> t_client = t_server - time_shift

        The time shift is measured in seconds.
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
          int( (absolute_time_shift + 30*minute) / hour ) * hour
        # return with correct sign
        return signum * absolute_rounded_time_shift

    def __assert_valid_time_shift(self, time_shift):
        """
        Perform sanity checks on the time shift value (given in
        seconds). If the value is invalid, raise a `TimeShiftError`,
        else simply return `None`.
        """
        minute = 60.0
        hour = 60.0 * minute
        absolute_rounded_time_shift = abs(self.__rounded_time_shift(time_shift))
        # test 1: fail if the absolute time shift is greater than
        #  a full day (24 hours)
        if absolute_rounded_time_shift > 24 * hour:
            raise ftp_error.TimeShiftError(
                  "time shift (%.2f s) > 1 day" % time_shift)
        # test 2: fail if the deviation between given time shift and
        #  full hours is greater than a certain limit (e. g. five minutes)
        maximum_deviation = 5 * minute
        if abs(time_shift - self.__rounded_time_shift(time_shift)) > \
           maximum_deviation:
            raise ftp_error.TimeShiftError(
                  "time shift (%.2f s) deviates more than %d s from full hours"
                  % (time_shift, maximum_deviation))

    def synchronize_times(self):
        """
        Synchronize the local times of FTP client and server. This
        is necessary to let `upload_if_newer` and `download_if_newer`
        work correctly.

        This implementation of `synchronize_times` requires _all_ of
        the following:

        - The connection between server and client is established.
        - The client has write access to the directory that is
          current when `synchronize_times` is called.
        - That directory is _not_ the root directory (i. e. `/`) of
          the FTP server.

        The usual usage pattern of `synchronize_times` is to call it
        directly after the connection is established. (As can be
        concluded from the points above, this requires write access
        to the login directory.)

        If `synchronize_times` fails, it raises a `TimeShiftError`.
        """
        helper_file_name = "_ftputil_sync_"
        # open a dummy file for writing in the current directory
        #  on the FTP host, then close it
        try:
            file_ = self.file(helper_file_name, 'w')
            file_.close()
            # get the modification time of the new file
            try:
                server_time = self.path.getmtime(helper_file_name)
            except ftp_error.RootDirError:
                raise ftp_error.TimeShiftError(
                      "can't use root directory for temp file")
        finally:
            # remove the just written file
            self.unlink(helper_file_name)
        # calculate the difference between server and client
        time_shift = server_time - time.time()
        # do some sanity checks
        self.__assert_valid_time_shift(time_shift)
        # if tests passed, store the time difference as time shift value
        self.set_time_shift(self.__rounded_time_shift(time_shift))

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
        or a remote file, repectively, is determined by the arguments.
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
        # transform to server time
        return local_mtime + self.time_shift()

    def upload_if_newer(self, source, target, mode=''):
        """
        Upload a file only if it's newer than the target on the
        remote host or if the target file does not exist. See the
        method `upload` for the meaning of the parameters.

        If an upload was necessary, return `True`, else return
        `False`.
        """
        return self.__copy_file_if_newer(source, target, mode,
          self.__shifted_local_mtime, self.path.getmtime,
          self.path.exists, self.upload)

    def download_if_newer(self, source, target, mode=''):
        """
        Download a file only if it's newer than the target on the
        local host or if the target file does not exist. See the
        method `download` for the meaning of the parameters.

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
        Make the directory path on the remote host. The argument
        `mode` is ignored and only "supported" for similarity with
        `os.mkdir`.
        """
        ftp_error._try_with_oserror(self._session.mkd, path)

    def rmdir(self, path, _remove_only_empty=True):
        """
        Remove the _empty_ directory `path` on the remote host.

        Compatibility note:
        
        Previous versions of ftputil simply delegated the `rmdir`
        call to the FTP server's `RMD` command, thus often allowing
        to delete non-empty directories. By default, that's no
        longer possible and should be avoided.

        If you really need the old behaviour, pass in an argument
        `_remove_only_empty=False` and `rmdir` will delegate to the
        FTP server, as before. Note, however, that deleting non-empty
        directories may be disallowed in future versions of ftputil.
        """
        #XXX Though in a local file system it's forbidden to remove
        # non-empty directories with `rmdir`, some (most?) FTP servers
        # allow to delete non-empty directories via their `RMD`
        # command. See the compatibilty note in the docstring.
        if _remove_only_empty and self.listdir(path):
            path = self.path.abspath(path)
            raise ftp_error.PermanentError("directory '%s' not empty" % path)
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

    #XXX one could argue to put this method into the `_Stat` class, but
    #  I refrained from that because then `_Stat` would have to know
    #  about `FTPHost`'s `_session` attribute and in turn about
    #  `_session`'s `dir` method
    def _dir(self, path):
        """Return a directory listing as made by FTP's `DIR` command."""
        # we can't use `self.path.isdir` in this method because that
        #  would cause a call of `(l)stat` and thus a call to `_dir`,
        #  so we would end up with an infinite recursion
        lines = []
        # use `lines=lines` for Python versions which don't support
        #  "nested scopes"
        callback = lambda line, lines=lines: lines.append(line)
        # see below for this decision logic
        if path.find(" ") == -1:
            # use straight-forward approach, without changing directories
            ftp_error._try_with_oserror(self._session.dir, path, callback)
        else:
            # remember old working directory
            old_dir = self.getcwd()
            # bail out with an internal error rather than modifying the
            #  current directory without hope of restoration
            try:
                self.chdir(old_dir)
            except ftp_error.PermanentError:
                # `old_dir` is an inaccessible login directory
                raise ftp_error.InaccessibleLoginDirError(
                      "directory '%s' is not accessible" % old_dir)
            # because of a bug in `ftplib` (or even in FTP servers?)
            #  the straight-forward code
            #    ftp_error._try_with_oserror(self._session.dir, path, callback)
            #  fails if some of the path components but the last contain
            #  whitespace; therefore, I change the current directory
            #  before listing in the "last" directory
            try:
                # invoke the listing in the "previous-to-last" directory
                head, tail = self.path.split(path)
                self.chdir(head)
                ftp_error._try_with_oserror(self._session.dir, tail, callback)
            finally:
                # restore the old directory
                self.chdir(old_dir)
        return lines

    def listdir(self, path):
        return self._stat.listdir(path)

    def lstat(self, path, _exception_for_missing_path=True):
        return self._stat.lstat(path, _exception_for_missing_path)

    def stat(self, path, _exception_for_missing_path=True):
        return self._stat.stat(path, _exception_for_missing_path)

