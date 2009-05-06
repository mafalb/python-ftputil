# Copyright (C) 2003-2009, Stefan Schwarzer <sschwarzer@sschwarzer.net>
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

"""
ftp_error.py - exception classes and wrappers
"""

# $Id$

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
        # contrary to what `ftplib`'s documentation says, `all_errors`
        #  does _not_ contain the subclasses, so I explicitly add them
        if args and (args[0].__class__ in ftplib.all_errors or
                     issubclass(args[0].__class__, ftplib.Error)):
            warnings.warn(("Passing exception objects into the FTPError "
              "constructor is deprecated and will be disabled in ftputil 2.6"),
              DeprecationWarning, stacklevel=2)
        try:
            # works only for new style-classes (Python 2.5+)
            super(FTPError, self).__init__(*args)
        except TypeError:
            # fallback to old approach
            Exception.__init__(self, *args)
        # don't use `args[0]` because `args` may be empty
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

# internal errors are those that have more to do with the inner
#  workings of ftputil than with errors on the server side
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

# currently not used
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

# currently not used
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
    # use `*exc.args` instead of `str(args)` because args might be
    #  a unicode string with non-ascii characters
    try:
        return callee(*args, **kwargs)
    except ftplib.error_temp, exc:
        raise TemporaryError(*exc.args)
    except ftplib.error_perm, exc:
        # if `exc.args` is present, assume it's a byte or unicode string
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
        # use `*exc.args` instead of `str(args)` because args might be
        #  a unicode string with non-ascii characters
        raise FTPIOError(*exc.args)

