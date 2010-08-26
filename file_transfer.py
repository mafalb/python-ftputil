# Copyright (C) 2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

"""
file_transfer.py - upload, download and generic file copy
"""

import os


__all__ = []


# Maximum size of buffer in `FTPHost.copyfileobj` in bytes.
MAX_COPY_BUFFER_SIZE = 64 * 1024


class LocalFile(object):
    """
    Represent a file on the local side which is to be transferred or
    is already transferred.
    """

    def __init__(self, name, mode):
        self.name = os.path.abspath(name)
        self.mode = mode

    def exists(self):
        """
        Return `True` if the path representing this file exists.
        Otherwise return `False`.
        """
        return os.path.exists(self.name)

    def mtime(self):
        """Return the timestamp for the last modification in seconds."""
        return os.path.getmtime(self.name)

    def mtime_precision(self):
        """Return the precision of the last modification time in seconds."""
        # Assume modification timestamps for local filesystems are
        #  at least precise up to a second.
        return 1.0

    def fobj(self):
        """Return a file object for the name/path in the constructor."""
        return open(self.name, self.mode)


class RemoteFile(object):
    """
    Represent a file on the remote side which is to be transferred or
    is already transferred.
    """

    def __init__(self, ftp_host, name, mode):
        self._host = ftp_host
        self._path = ftp_host.path
        self.name = self._path.abspath(name)
        self.mode = mode

    def exists(self):
        """
        Return `True` if the path representing this file exists.
        Otherwise return `False`.
        """
        return self._path.exists(self.name)

    def mtime(self):
        """Return the timestamp for the last modification in seconds."""
        # Convert to client time zone (see definition of time
        #  shift in docstring of `FTPHost.set_time_shift`).
        return self._path.getmtime(self.name) - self._host.time_shift()

    def mtime_precision(self):
        """Return the precision of the last modification time in seconds."""
        # I think using `stat` instead of `lstat` makes more sense here.
        return self._host.stat(self.name)._st_mtime_precision

    def fobj(self):
        """Return a file object for the name/path in the constructor."""
        return self._host.file(self.name, self.mode)


def source_is_newer_than_target(source_file, target_file):
    """
    Return `True` if the source is newer than the target, else `False`.
    
    Both arguments are `LocalFile` or `RemoteFile` objects.

    For the purpose of this test the source is newer than the
    target, if the target modification datetime plus its precision
    is before the source precision. In other words: If in doubt,
    the file should be transferred.
    """
    return source_file.mtime() + source_file.mtime_precision() >= \
           target_file.mtime()


def null_callback(*args, **kwargs):
    """Default callback, does nothing."""
    pass


# This code doesn't complain if the buffer size is passed as a
#  positional argument but emits a deprecation warning if `length`
#  is used as a keyword argument.
def copyfileobj(source_fobj, target_fobj, buffer_size=MAX_COPY_BUFFER_SIZE,
                callback=null_callback):
    """Copy data from file-like object source to file-like object target."""
    # Inspired by `shutil.copyfileobj` (I don't use the `shutil`
    #  code directly because it might change)
    # Call callback function before transfer actually starts.
    transferred_buffers = 0
    actual_buffer_size = 0
    transferred_bytes = 0
    callback(transferred_buffers, actual_buffer_size, transferred_bytes)
    while True:
        buffer_ = source_fobj.read(buffer_size)
        if not buffer_:
            break
        target_fobj.write(buffer_)
        # Update callback data and call the function.
        transferred_buffers += 1
        actual_buffer_size = len(buffer_)
        transferred_bytes += actual_buffer_size
        callback(transferred_buffers, actual_buffer_size,
                 transferred_bytes)


def copy_file(source_file, target_file, conditional, callback):
    """
    Copy a file from `source_file` to `target_file`.

    These are `LocalFile` or `RemoteFile` objects. Which of them
    is a local or a remote file, respectively, is determined by
    the arguments. If `conditional` is true, the file is only
    copied if the target doesn't exist or is older than the
    source. If `conditional` is false, the file is copied
    unconditionally. Return `True` if the file was copied, else
    `False`.
    """
    if conditional:
        # Evaluate condition: The target file either doesn't exist or is
        #  older than the source file. If in doubt (due to imprecise
        #  timestamps), perform the transfer.
        transfer_condition = not target_file.exists() or \
          source_is_newer_than_target(source_file, target_file)
        if not transfer_condition:
            # We didn't transfer.
            return False
    source_fobj = source_file.fobj()
    try:
        target_fobj = target_file.fobj()
        try:
            copyfileobj(source_fobj, target_fobj, callback=callback)
        finally:
            target_fobj.close()
    finally:
        source_fobj.close()
    # Transfer accomplished
    return True

