# Copyright (C) 2003-2009, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

"""
ftp_error.py - exception classes and wrappers
"""

# "Too many ancestors"
# pylint: disable-msg = R0901

import ftplib
import sys
import warnings

import ftputil_version


class FTPError(Exception):
    """General error class."""

    def __init__(self, *args):
        # `ftplib.Error` doesn't have a `__subclasses__` _method_ but a
        #  static method, so my use of `ftplib.Error.__subclasses__` in
        #  my opinion is valid
        # pylint: disable-msg = e1101
        # Contrary to what `ftplib`'s documentation says, `all_errors`
        #  does _not_ contain the subclasses, so I explicitly add them.
        if args and (args[0].__class__ in ftplib.all_errors or
                     issubclass(args[0].__class__, ftplib.Error)):
            warnings.warn(("Passing exception objects into the FTPError "
              "constructor is deprecated and will be disabled in ftputil 2.6"),
              DeprecationWarning, stacklevel=2)
        try:
            # Works only for new style-classes (Python 2.5+).
            super(FTPError, self).__init__(*args)
        except TypeError:
            # Fallback to old approach.
            Exception.__init__(self, *args)
        # Don't use `args[0]` because `args` may be empty.
        if args:
            self.strerror = self.args[0]
        else:
            self.strerror = ""
        try:
            self.errno = int(self.strerror[:3])
        except (TypeError, IndexError, ValueError):
            self.errno = None
        self.filename = None

    def __str__(self):
        return "%s\nDebugging info: %s" % \
               (self.strerror, ftputil_version.version_info)

# Internal errors are those that have more to do with the inner
#  workings of ftputil than with errors on the server side.
class InternalError(FTPError):
    """Internal error."""
    pass

class RootDirError(InternalError):
    """Raised for generic stat calls on the remote root directory."""
    pass

class InaccessibleLoginDirError(InternalError):
    """May be raised if the login directory isn't accessible."""
    pass

class TimeShiftError(InternalError):
    """Raised for invalid time shift values."""
    pass

class ParserError(InternalError):
    """Raised if a line of a remote directory can't be parsed."""
    pass

# Currently not used
class KeepAliveError(InternalError):
    """Raised if the keep-alive feature failed."""
    pass

class FTPOSError(FTPError, OSError):
    """Generic FTP error related to `OSError`."""
    pass

class TemporaryError(FTPOSError):
    """Raised for temporary FTP errors (4xx)."""
    pass

class PermanentError(FTPOSError):
    """Raised for permanent FTP errors (5xx)."""
    pass

class CommandNotImplementedError(PermanentError):
    """Raised if the server doesn't implement a certain feature (502)."""
    pass

# Currently not used
class SyncError(PermanentError):
    """Raised for problems specific to syncing directories."""
    pass


#XXX Do you know better names for `_try_with_oserror` and
#    `_try_with_ioerror`?
def _try_with_oserror(callee, *args, **kwargs):
    """
    Try the callee with the given arguments and map resulting
    exceptions from `ftplib.all_errors` to `FTPOSError` and its
    derived classes.
    """
    # Use `*exc.args` instead of `str(args)` because args might be
    #  a unicode string with non-ascii characters.
    try:
        return callee(*args, **kwargs)
    except ftplib.error_temp, exc:
        raise TemporaryError(*exc.args)
    except ftplib.error_perm, exc:
        # If `exc.args` is present, assume it's a byte or unicode string.
        if exc.args and exc.args[0].startswith("502"):
            raise CommandNotImplementedError(*exc.args)
        else:
            raise PermanentError(*exc.args)
    except ftplib.all_errors:
        exc = sys.exc_info()[1]
        raise FTPOSError(*exc.args)

class FTPIOError(FTPError, IOError):
    """Generic FTP error related to `IOError`."""
    pass


def _try_with_ioerror(callee, *args, **kwargs):
    """
    Try the callee with the given arguments and map resulting
    exceptions from `ftplib.all_errors` to `FTPIOError`.
    """
    try:
        return callee(*args, **kwargs)
    except ftplib.all_errors:
        exc = sys.exc_info()[1]
        # Use `*exc.args` instead of `str(args)` because args might be
        #  a unicode string with non-ascii characters.
        raise FTPIOError(*exc.args)

