# Copyright (C) 2002-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# Copyright (C) 2008, Roger Demetrescu <roger.demetrescu@gmail.com>
# See the file LICENSE for licensing terms.

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

import ftplib
import os
import stat
import sys
import time
import warnings

import file_transfer
import ftp_error
import ftp_file
import ftp_path
import ftp_stat
import ftputil_version


__all__ = ['FTPHost']

__version__ = ftputil_version.__version__


#####################################################################
# `FTPHost` class with several methods similar to those of `os`

class FTPHost(object):
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
        # Store arguments for later operations
        self._args = args
        self._kwargs = kwargs
        #XXX Maybe put the following in a `reset` method.
        #  The time shift setting shouldn't be reset though.
        # Make a session according to these arguments
        self._session = self._make_session()
        # Simulate os.path
        self.path = ftp_path._Path(self)
        # lstat, stat, listdir services
        self._stat = ftp_stat._Stat(self)
        self.stat_cache = self._stat._lstat_cache
        self.stat_cache.enable()
        self._cached_current_dir = \
          ftp_error._try_with_oserror(self._session.pwd)
        # Associated `FTPHost` objects for data transfer
        self._children = []
        # This is only set to something else than `None` if this instance
        #  represents an `_FTPFile`.
        self._file = None
        # Now opened
        self.closed = False
        # Set curdir, pardir etc. for the remote host. RFC 959 states
        #  that this is, strictly speaking, dependent on the server OS
        #  but it seems to work at least with Unix and Windows
        #  servers.
        self.curdir, self.pardir, self.sep = '.', '..', '/'
        # Set default time shift (used in `upload_if_newer` and
        #  `download_if_newer`).
        self.set_time_shift(0.0)

    #
    # Dealing with child sessions and file-like objects
    #  (rather low-level)
    #
    def _make_session(self):
        """
        Return a new session object according to the current state of
        this `FTPHost` instance.
        """
        # Use copies of the arguments
        args = self._args[:]
        kwargs = self._kwargs.copy()
        # If a session factory had been given on the instantiation of
        #  this `FTPHost` object, use the same factory for this
        #  `FTPHost` object's child sessions.
        factory = kwargs.pop('session_factory', ftplib.FTP)
        return ftp_error._try_with_oserror(factory, *args, **kwargs)

    def _copy(self):
        """Return a copy of this `FTPHost` object."""
        # The copy includes a new session factory return value (aka
        #  session) but doesn't copy the state of `self.getcwd()`.
        return FTPHost(*self._args, **self._kwargs)

    def _available_child(self):
        """
        Return an available (i. e. one whose `_file` object is closed
        and doesn't have a timed-out server connection) child
        (`FTPHost` object) from the pool of children or `None` if
        there aren't any.
        """
        for host in self._children:
            # Test for timeouts only after testing for a closed file:
            # - If a file isn't closed, save time; don't bother to access
            #   the remote server.
            # - If a file transfer on the child is in progress, requesting
            #   the directory is an invalid operation because of the way
            #   the FTP state machine works (see RFC 959).
            if host._file.closed:
                try:
                    host._session.pwd()
                # Timed-out sessions raise `error_temp`.
                except ftplib.error_temp:
                    continue
                else:
                    # Everything's ok; use this `FTPHost` instance.
                    return host
        # Be explicit.
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
        # Prepare for changing the directory (see whitespace workaround
        #  in method `_dir`).
        if host.path.isabs(path):
            effective_path = path
        else:
            effective_path = host.path.join(basedir, path)
        effective_dir, effective_file = host.path.split(effective_path)
        try:
            # This will fail if we can't access the directory at all.
            host.chdir(effective_dir)
        except ftp_error.PermanentError:
            # Similarly to a failed `file` in a local filesystem, we
            #  raise an `IOError`, not an `OSError`.
            raise ftp_error.FTPIOError("remote directory '%s' doesn't exist "
                  "or has insufficient access rights" % effective_dir)
        host._file._open(effective_file, mode)
        if 'w' in mode:
            # Invalidate cache entry because size and timestamps will change.
            self.stat_cache.invalidate(effective_path)
        return host._file

    open = file

    def close(self):
        """Close host connection."""
        if self.closed:
            return
        # Close associated children
        for host in self._children:
            # Children have a `_file` attribute which is an `_FTPFile` object.
            host._file.close()
            host.close()
        # Now deal with ourself
        try:
            ftp_error._try_with_oserror(self._session.close)
        finally:
            # If something went wrong before, the host/session is
            #  probably defunct and subsequent calls to `close` won't
            #  help either, so we consider the host/session closed for
            #  practical purposes.
            self.stat_cache.clear()
            self._children = []
            self.closed = True

    def __del__(self):
        # Don't complain about lazy except clause
        # pylint: disable-msg=W0702, W0704
        try:
            self.close()
        except:
            # We don't want warnings if the constructor failed.
            pass

    #
    # Setting a custom directory parser
    #
    def set_parser(self, parser):
        """
        Set the parser for extracting stat results from directory
        listings.

        The parser interface is described in the documentation, but
        here are the most important things:

        - A parser should derive from `ftp_stat.Parser`.

        - The parser has to implement two methods, `parse_line` and
          `ignores_line`. For the latter, there's a probably useful
          default in the class `ftp_stat.Parser`.

        - `parse_line` should try to parse a line of a directory
          listing and return a `ftp_stat.StatResult` instance. If
          parsing isn't possible, raise `ftp_error.ParserError` with
          a useful error message.

        - `ignores_line` should return a true value if the line isn't
          assumed to contain stat information.
        """
        # The cache contents, if any, probably aren't useful.
        self.stat_cache.clear()
        # Set the parser explicitly, don't allow "smart" switching anymore.
        self._stat._parser = parser
        self._stat._allow_parser_switching = False

    #
    # Time shift adjustment between client (i. e. us) and server
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
        # Avoid division by zero below.
        if time_shift == 0:
            return 0.0
        # Use a positive value for rounding.
        absolute_time_shift = abs(time_shift)
        signum = time_shift / absolute_time_shift
        # Round it to hours. This code should also work for later Python
        #  versions because of the explicit `int`.
        absolute_rounded_time_shift = \
          int( (absolute_time_shift + 30*minute) / hour ) * hour
        # Return with correct sign.
        return signum * absolute_rounded_time_shift

    def __assert_valid_time_shift(self, time_shift):
        """
        Perform sanity checks on the time shift value (given in
        seconds). If the value is invalid, raise a `TimeShiftError`,
        else simply return `None`.
        """
        minute = 60.0  # seconds
        hour = 60.0 * minute
        absolute_rounded_time_shift = abs(self.__rounded_time_shift(time_shift))
        # Test 1: Fail if the absolute time shift is greater than
        #  a full day (24 hours).
        if absolute_rounded_time_shift > 24 * hour:
            raise ftp_error.TimeShiftError(
                  "time shift (%.2f s) > 1 day" % time_shift)
        # Test 2: Fail if the deviation between given time shift and
        #  full hours is greater than a certain limit.
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
        work correctly. If `synchronize_times` isn't applicable
        (see below), the time shift can still be set explicitly with
        `set_time_shift`.

        This implementation of `synchronize_times` requires _all_ of
        the following:

        - The connection between server and client is established.
        - The client has write access to the directory that is
          current when `synchronize_times` is called.

        The common usage pattern of `synchronize_times` is to call it
        directly after the connection is established. (As can be
        concluded from the points above, this requires write access
        to the login directory.)

        If `synchronize_times` fails, it raises a `TimeShiftError`.
        """
        helper_file_name = "_ftputil_sync_"
        # Open a dummy file for writing in the current directory
        #  on the FTP host, then close it.
        try:
            # May raise `FTPIOError` if directory isn't writable
            file_ = self.file(helper_file_name, 'w')
            file_.close()
        except ftp_error.FTPIOError:
            raise ftp_error.TimeShiftError(
                  '''couldn't write helper file in directory "%s"''' %
                  self.getcwd())
        # If everything worked up to here it should be possible to stat
        #  and then remove the just-written file.
        try:
            server_time = self.path.getmtime(helper_file_name)
            self.unlink(helper_file_name)
        except ftp_error.FTPOSError:
            # If we got a `TimeShiftError` exception above, we should't
            #  come here: if we did not get a `TimeShiftError` above,
            #  deletion should be possible. The only reason for an exception
            #  I can think of here is a race condition by removing write
            #  permission from the directory or helper file after it has been
            #  written to.
            raise ftp_error.TimeShiftError(
                  "could write helper file but not unlink it")
        # Calculate the difference between server and client.
        time_shift = server_time - time.time()
        # Do some sanity checks.
        self.__assert_valid_time_shift(time_shift)
        # If tests passed, store the time difference as time shift value.
        self.set_time_shift(self.__rounded_time_shift(time_shift))

    #
    # Operations based on file-like objects (rather high-level),
    #  like upload and download
    #
    # This code doesn't complain if the chunk size is passed as a
    #  positional argument but emits a deprecation warning if `length`
    #  is used as a keyword argument.
    def copyfileobj(self, source, target,
                    max_chunk_size=file_transfer.MAX_COPY_CHUNK_SIZE,
                    callback=file_transfer.null_callback, **kwargs):
        "Copy data from file-like object source to file-like object target."
        if 'length' in kwargs:
            max_chunk_size = kwargs['length']
            warnings.warn(("Parameter name `length` will be removed in "
                           "ftputil 2.6, use `max_chunk_size` instead"),
                          DeprecationWarning, stacklevel=2)
        file_transfer.copyfileobj(source, target, max_chunk_size, callback)

    def __get_modes(self, mode):
        """Return modes for source and target file."""
        #XXX Should we allow mode "a" at all? We don't support appending!
        #XXX Use dictionary?
        # Invalid mode values are handled when a file object is made.
        if mode == 'b':
            return 'rb', 'wb'
        else:
            return 'r', 'w'

    def _upload_files(self, source_path, target_path, mode):
        """
        Return a `LocalFile` and `RemoteFile` as source and target,
        respectively.
        """
        source_mode, target_mode = self.__get_modes(mode)
        source_file = file_transfer.LocalFile(source_path, source_mode)
        # Passing `self` (the `FTPHost` instance) here is correct.
        target_file = file_transfer.RemoteFile(self, target_path, target_mode)
        return source_file, target_file

    def upload(self, source, target, mode='',
               callback=file_transfer.null_callback):
        """
        Upload a file from the local source (name) to the remote
        target (name). The argument `mode` is an empty string or 'a' for
        text copies, or 'b' for binary copies.
        """
        source_file, target_file = self._upload_files(source, target, mode)
        file_transfer.copy_file(source_file, target_file,
                                conditional=False, callback=callback)

    def upload_if_newer(self, source, target, mode='',
                        callback=file_transfer.null_callback):
        """
        Upload a file only if it's newer than the target on the
        remote host or if the target file does not exist. See the
        method `upload` for the meaning of the parameters.

        If an upload was necessary, return `True`, else return
        `False`.
        """
        source_file, target_file = self._upload_files(source, target, mode)
        return file_transfer.copy_file(source_file, target_file,
                                       conditional=True, callback=callback)

    def _download_files(self, source_path, target_path, mode):
        """
        Return a `RemoteFile` and `LocalFile` as source and target,
        respectively.
        """
        source_mode, target_mode = self.__get_modes(mode)
        source_file = file_transfer.RemoteFile(self, source_path, source_mode)
        target_file = file_transfer.LocalFile(target_path, target_mode)
        return source_file, target_file

    def download(self, source, target, mode='',
                 callback=file_transfer.null_callback):
        """
        Download a file from the remote source (name) to the local
        target (name). The argument mode is an empty string or 'a' for
        text copies, or 'b' for binary copies.
        """
        source_file, target_file = self._download_files(source, target, mode)
        file_transfer.copy_file(source_file, target_file,
                                conditional=False, callback=callback)

    def download_if_newer(self, source, target, mode='',
                          callback=file_transfer.null_callback):
        """
        Download a file only if it's newer than the target on the
        local host or if the target file does not exist. See the
        method `download` for the meaning of the parameters.

        If a download was necessary, return `True`, else return
        `False`.
        """
        source_file, target_file = self._download_files(source, target, mode)
        return file_transfer.copy_file(source_file, target_file,
                                       conditional=True, callback=callback)

    #
    # Helper methods to descend into a directory before executing a command
    #
    def _check_inaccessible_login_directory(self):
        """
        Raise an `InaccessibleLoginDirError` exception if we can't
        change to the login directory. This test is only reliable if
        the current directory is the login directory.
        """
        presumable_login_dir = self.getcwd()
        # Bail out with an internal error rather than modifying the
        #  current directory without hope of restoration.
        try:
            self.chdir(presumable_login_dir)
        except ftp_error.PermanentError:
            # `old_dir` is an inaccessible login directory
            raise ftp_error.InaccessibleLoginDirError(
                  "directory '%s' is not accessible" % presumable_login_dir)

    def _robust_ftp_command(self, command, path, descend_deeply=False):
        """
        Run an FTP command on a path. The return value of the method
        is the return value of the command.

        If `descend_deeply` is true (the default is false), descend
        deeply, i. e. change the directory to the end of the path.
        """
        # If we can't change to the yet-current directory, the code
        #  below won't work (see below), so in this case rather raise
        #  an exception than giving wrong results.
        self._check_inaccessible_login_directory()
        # Some FTP servers don't behave as expected if the directory
        #  portion of the path contains whitespace; some even yield
        #  strange results if the command isn't executed in the
        #  current directory. Therefore, change to the directory
        #  which contains the item to run the command on and invoke
        #  the command just there.
        # Remember old working directory.
        old_dir = self.getcwd()
        try:
            if descend_deeply:
                # Invoke the command in (not: on) the deepest directory.
                self.chdir(path)
                # Workaround for some servers that give recursive
                #  listings when called with a dot as path; see issue #33,
                #  http://ftputil.sschwarzer.net/trac/ticket/33
                return command(self, "")
            else:
                # Invoke the command in the "next to last" directory.
                head, tail = self.path.split(path)
                self.chdir(head)
                return command(self, tail)
        finally:
            # Restore the old directory.
            self.chdir(old_dir)

    #
    # Miscellaneous utility methods resembling functions in `os`
    #
    def getcwd(self):
        """Return the current path name."""
        return self._cached_current_dir

    def chdir(self, path):
        """Change the directory on the host."""
        ftp_error._try_with_oserror(self._session.cwd, path)
        # The path given as the argument is relative to the old current
        #  directory, therefore join them.
        self._cached_current_dir = \
          self.path.normpath(self.path.join(self._cached_current_dir, path))

    def mkdir(self, path, mode=None):
        """
        Make the directory path on the remote host. The argument
        `mode` is ignored and only "supported" for similarity with
        `os.mkdir`.
        """
        # Ignore unused argument `mode`
        # pylint: disable-msg=W0613
        def command(self, path):
            """Callback function."""
            return ftp_error._try_with_oserror(self._session.mkd, path)
        self._robust_ftp_command(command, path)

    def makedirs(self, path, mode=None):
        """
        Make the directory `path`, but also make not yet existing
        intermediate directories, like `os.makedirs`. The value
        of `mode` is only accepted for compatibility with
        `os.makedirs` but otherwise ignored.
        """
        # Ignore unused argument `mode`
        # pylint: disable-msg=W0613
        path = self.path.abspath(path)
        directories = path.split(self.sep)
        # Try to build the directory chain from the "uppermost" to
        #  the "lowermost" directory.
        for index in range(1, len(directories)):
            # Re-insert the separator which got lost by using `path.split`.
            next_directory = self.sep + self.path.join(*directories[:index+1])
            try:
                self.mkdir(next_directory)
            except ftp_error.PermanentError:
                # Find out the cause of the error. Re-raise the
                #  exception only if the directory didn't exist already,
                #  else something went _really_ wrong, e. g. we might
                #  have a regular file with the name of the directory.
                if not self.path.isdir(next_directory):
                    raise

    def rmdir(self, path):
        """
        Remove the _empty_ directory `path` on the remote host.

        Compatibility note:

        Previous versions of ftputil could possibly delete non-
        empty directories as well, - if the server allowed it. This
        is no longer supported.
        """
        path = self.path.abspath(path)
        if self.listdir(path):
            raise ftp_error.PermanentError("directory '%s' not empty" % path)
        #XXX How does `rmd` work with links?
        def command(self, path):
            """Callback function."""
            ftp_error._try_with_oserror(self._session.rmd, path)
        self._robust_ftp_command(command, path)
        self.stat_cache.invalidate(path)

    def remove(self, path):
        """Remove the given file or link."""
        path = self.path.abspath(path)
        # Though `isfile` includes also links to files, `islink`
        #  is needed to include links to directories.
        if self.path.isfile(path) or self.path.islink(path) or \
           not self.path.exists(path):
            # If the path doesn't exist, let the removal command trigger
            #  an exception with a more appropriate error message.
            def command(self, path):
                """Callback function."""
                ftp_error._try_with_oserror(self._session.delete, path)
            self._robust_ftp_command(command, path)
        else:
            raise ftp_error.PermanentError("remove/unlink can only delete "
                                           "files and links, not directories")
        self.stat_cache.invalidate(path)

    def unlink(self, path):
        """
        Remove the given file given by `path`.

        Raise a `PermanentError` if the path doesn't exist, raise a
        `PermanentError`, but maybe raise other exceptions depending
        on the state of the server (e. g. timeout).
        """
        self.remove(path)

    def rmtree(self, path, ignore_errors=False, onerror=None):
        """
        Remove the given remote, possibly non-empty, directory tree.
        The interface of this method is rather complex, in favor of
        compatibility with `shutil.rmtree`.

        If `ignore_errors` is set to a true value, errors are ignored.
        If `ignore_errors` is a false value _and_ `onerror` isn't set,
        all exceptions occuring during the tree iteration and
        processing are raised. These exceptions are all of type
        `PermanentError`.

        To distinguish between error situations, pass in a callable
        for `onerror`. This callable must accept three arguments:
        `func`, `path` and `exc_info`). `func` is a bound method
        object, _for example_ `your_host_object.listdir`. `path` is
        the path that was the recent argument of the respective method
        (`listdir`, `remove`, `rmdir`). `exc_info` is the exception
        info as it's got from `sys.exc_info`.

        Implementation note: The code is copied from `shutil.rmtree`
        in Python 2.4 and adapted to ftputil.
        """
        # The following code is an adapted version of Python 2.4's
        #  `shutil.rmtree` function.
        if ignore_errors:
            def new_onerror(*args):
                """Do nothing."""
                # Ignore unused arguments
                # pylint: disable-msg=W0613
                pass
        elif onerror is None:
            def new_onerror(*args):
                """Re-raise exception."""
                # Ignore unused arguments
                # pylint: disable-msg=W0613
                raise
        else:
            new_onerror = onerror
        names = []
        try:
            names = self.listdir(path)
        except ftp_error.PermanentError:
            new_onerror(self.listdir, path, sys.exc_info())
        for name in names:
            full_name = self.path.join(path, name)
            try:
                mode = self.lstat(full_name).st_mode
            except ftp_error.PermanentError:
                mode = 0
            if stat.S_ISDIR(mode):
                self.rmtree(full_name, ignore_errors, new_onerror)
            else:
                try:
                    self.remove(full_name)
                except ftp_error.PermanentError:
                    new_onerror(self.remove, full_name, sys.exc_info())
        try:
            self.rmdir(path)
        except ftp_error.FTPOSError:
            new_onerror(self.rmdir, path, sys.exc_info())

    def rename(self, source, target):
        """Rename the source on the FTP host to target."""
        # The following code is in spirit similar to the code in the
        #  method `_robust_ftp_command`, though we do _not_ do
        #  _everything_ imaginable.
        self._check_inaccessible_login_directory()
        source_head, source_tail = self.path.split(source)
        target_head, target_tail = self.path.split(target)
        paths_contain_whitespace = (" " in source_head) or (" " in target_head)
        if paths_contain_whitespace and source_head == target_head:
            # Both items are in the same directory.
            old_dir = self.getcwd()
            try:
                self.chdir(source_head)
                ftp_error._try_with_oserror(self._session.rename,
                                            source_tail, target_tail)
            finally:
                self.chdir(old_dir)
        else:
            # Use straightforward command.
            ftp_error._try_with_oserror(self._session.rename, source, target)

    #XXX One could argue to put this method into the `_Stat` class, but
    #  I refrained from that because then `_Stat` would have to know
    #  about `FTPHost`'s `_session` attribute and in turn about
    #  `_session`'s `dir` method.
    def _dir(self, path):
        """Return a directory listing as made by FTP's `DIR` command."""
        # We can't use `self.path.isdir` in this method because that
        #  would cause a call of `(l)stat` and thus a call to `_dir`,
        #  so we would end up with an infinite recursion.
        def _FTPHost_dir_command(self, path):
            """Callback function."""
            lines = []
            def callback(line):
                """Callback function."""
                lines.append(line)
            ftp_error._try_with_oserror(self._session.dir, path, callback)
            return lines
        lines = self._robust_ftp_command(_FTPHost_dir_command, path,
                                         descend_deeply=True)
        return lines

    # The `listdir`, `lstat` and `stat` methods don't use
    #  `_robust_ftp_command` because they implicitly already use
    #  `_dir` which actually uses `_robust_ftp_command`.
    def listdir(self, path):
        """
        Return a list of directories, files etc. in the directory
        named `path`.

        If the directory listing from the server can't be parsed with
        any of the available parsers raise a `ParserError`.
        """
        return self._stat.listdir(path)

    def lstat(self, path, _exception_for_missing_path=True):
        """
        Return an object similar to that returned by `os.lstat`.

        If the directory listing from the server can't be parsed with
        any of the available parsers, raise a `ParserError`. If the
        directory _can_ be parsed and the `path` is _not_ found, raise
        a `PermanentError`.

        (`_exception_for_missing_path` is an implementation aid and
        _not_ intended for use by ftputil clients.)
        """
        return self._stat.lstat(path, _exception_for_missing_path)

    def stat(self, path, _exception_for_missing_path=True):
        """
        Return info from a "stat" call on `path`.

        If the directory containing `path` can't be parsed, raise a
        `ParserError`. If the directory containing `path` can be
        parsed but the `path` can't be found, raise a
        `PermanentError`. Also raise a `PermanentError` if there's an
        endless (cyclic) chain of symbolic links "behind" the `path`.

        (`_exception_for_missing_path` is an implementation aid and
        _not_ intended for use by ftputil clients.)
        """
        return self._stat.stat(path, _exception_for_missing_path)

    def walk(self, top, topdown=True, onerror=None):
        """
        Iterate over directory tree and return a tuple (dirpath,
        dirnames, filenames) on each iteration, like the `os.walk`
        function (see http://docs.python.org/lib/os-file-dir.html ).
        """
        # The following code is copied from `os.walk` in Python 2.4
        #  and adapted to ftputil.
        try:
            names = self.listdir(top)
        except ftp_error.FTPOSError, err:
            if onerror is not None:
                onerror(err)
            return
        dirs, nondirs = [], []
        for name in names:
            if self.path.isdir(self.path.join(top, name)):
                dirs.append(name)
            else:
                nondirs.append(name)
        if topdown:
            yield top, dirs, nondirs
        for name in dirs:
            path = self.path.join(top, name)
            if not self.path.islink(path):
                for item in self.walk(path, topdown, onerror):
                    yield item
        if not topdown:
            yield top, dirs, nondirs

    def chmod(self, path, mode):
        """
        Change the mode of a remote `path` (a string) to the integer
        `mode`. This integer uses the same bits as the mode value
        returned by the `stat` and `lstat` commands.

        If something goes wrong, raise a `TemporaryError` or a
        `PermanentError`, according to the status code returned by
        the server. In particular, a non-existent path usually
        causes a `PermanentError`.
        """
        path = self.path.abspath(path)
        def command(self, path):
            """Callback function."""
            ftp_error._try_with_oserror(self._session.voidcmd,
                                        "SITE CHMOD %s %s" % (oct(mode), path))
        self._robust_ftp_command(command, path)
        self.stat_cache.invalidate(path)

    #
    # Context manager methods
    #
    def __enter__(self):
        # Return `self`, so it can be accessed as the variable
        #  component of the `with` statement.
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # We don't need the `exc_*` arguments here
        # pylint: disable-msg=W0613
        self.close()
        # Be explicit.
        return False


