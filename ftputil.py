# Copyright (C) 2002, Stefan Schwarzer
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

import ftplib
import os


#####################################################################
# Simple assignments

curdir = '.'
pardir = '..'
sep = '/'
altsep = None


#####################################################################
# Exception classes

class FTPIOError(IOError):
    def __init__(self, ftp_exception):
        self.ftp_exception = ftp_exception
        IOError( self, str(ftp_exception) )

class FTPOSError(OSError):
    def __init__(self, ftp_exception):
        self.ftp_exception = ftp_exception
        OSError( self, str(ftp_exception) )


#####################################################################
# Support for file-like objects

# converters for native line ends to normalized ones in Python
_linesep = os.linesep
if _linesep == '\n':        # Posix
    _native_to_python_linesep = \
                        lambda text: text
elif _linesep == '\r\n':    # DOS and relatives
    _native_to_python_linesep = \
                        lambda text: text.replace('\r', '')
elif _linesep == '\r':      # Mac
    _native_to_python_linesep = \
                        lambda text: text.replace('\r', '\n')
else:
    def _native_to_python_linesep(text):
        raise NotImplementedError("Can't do line ending "
              "conversion for %s" % _linesep)

# converter for Python line ends in native ones
_python_to_native_linesep = \
  lambda text: text.replace('\n', _linesep)


class _FTPFile:
    '''Represents a file-like object connected to an
    FTP host. File and socket are closed appropriately if
    the close operation is requested.'''

    def __init__(self, host, conn, mode):
        '''Construct the file(-like) object.'''
        self._host = host
        self._conn = conn
        self._mode = mode
        self._binary = 'b' in mode
        #XXX needed? self._writemode = 'w' in mode
        self._fp = conn.makefile(mode)

    #
    # Read and write operations with support for
    # line separator conversion for text modes.
    #
    # Note that we must convert line endings because
    # the FTP server expects the native line separator
    # format to be sent on ASCII transfers.
    #
    def read(self, *args, **kwargs):
        '''Return read bytes, normalized if in text
        transfer mode.'''
        data = apply(self._fp.read, args, kwargs)
        if self._binary:
            return data
        return _native_to_python_linesep(data)

    def readline(self, *args, **kwargs):
        '''Return one read line, normalized if in text
        transfer mode.'''
        data = apply(self._fp.readline, args, kwargs)
        if self._binary:
            return data
        return _native_to_python_linesep(data)

    def readlines(self, *args, **kwargs):
        '''Return read lines, normalized if in text
        transfer mode.'''
        lines = apply(self._fp.readlines, args, kwargs)
        if self._binary:
            return lines
        # more memory-friendly than
        #  return [... for line in lines]
        for i in range( len(lines) ):
            lines[i] = _native_to_python_linesep(lines[i])
        return lines

    def xreadlines(self):
        '''Return an appropriate xreadlines object with
        built-in line separator conversion support.'''
        if self._binary:
            return self._fp.xreadlines()
        raise NotImplementedError(
              "xreadlines not yet supported")

    def write(self, data):
        '''Write data to file. Do linesep conversion for
        text mode.'''
        if not self._binary:
            data = _python_to_native_linesep(data)
        #self._conn.send(data)
        self._fp.write(data)

    def writelines(self, lines):
        '''Write lines to file. Do linesep conversion for
        text mode.'''
        if not self._binary:
            # more memory-friendly than [... for line in lines]
            for i in range( len(lines) ):
                lines[i] = _python_to_native_linesep(lines[i])
        self._fp.writelines(lines)

    #
    # other attributes
    #
    def __getattr__(self, attr_name):
        '''Delegate unknown attribute requests to the file.'''
        if attr_name in ( 'flush isatty fileno seek tell '
          'truncate closed name softspace'.split() ):
            return eval('self._fp.%s' % attr_name)
        else:
            raise AttributeError("'FTPFile' object has no "
                  "attribute '%s'" % attr_name)

    def close(self):
        '''Close the FTPFile. We need no 'if'; the file and the
        socket object can be closed multiply without harm.'''
        #XXX self._fp.close()
        self._conn.close()

    def __del__(self):
        # not strictly necessary; file and socket are
        #  closed on garbage collection, anyway
        self.close()


############################################################
# FTPHost class with several methods similar to those of os

class FTPHost:
    '''FTP host class'''

    def __init__(self, *args, **kwargs):
        '''Abstract initialization of FTPHost object. At this
        stage I don't know if I need a new FTP connection for
        each file transfer.'''
        self._host = apply(ftplib.FTP, args, kwargs)

    def file(self, path, mode='r'):
        '''Return a file(-like) object that is connected to an
        FTP host.'''
        if '+' in mode:
            raise FTPIOError("append modes not supported")
        if mode not in ('r', 'rb', 'w', 'wb'):
            raise FTPIOError("invalid mode")
        # select ASCII or binary mode
        transfer_type = ('A', 'I')['b' in mode]
        command = 'TYPE %s' % transfer_type
        # this logic taken from ftplib;
        #  why this strange distinction?
        if mode == 'r':
            self._host.sendcmd(command)
        else:  # rb, w, wb
            self._host.voidcmd(command)
        # make transfer command
        command_type = ('STOR', 'RETR')['r' in mode]
        command = '%s %s' % (command_type, path)
        # get connection and file object
        conn = self._host.transfercmd(command)
        self._host.voidresp()
        ftp_file = _FTPFile(self._host, conn, mode)
        return ftp_file

    def close(self):
        '''Close host connection.'''
        return self._host.close()

    #
    # miscellaneous utility methods resembling those in os
    #
    def getcwd(self):
        '''Return the current path name.'''
        return self._host.pwd()

    def chdir(self, path):
        '''Change the directory on the host.'''
        try:
            self._host.cwd(path)
        except ftplib.error_perm, obj:
            raise FTPOSError(obj)

    def listdir(self, path):
        '''Return a list with directories, files etc. in the
        directory path.'''
        pass

    def mkdir(self, path, mode=None):
        '''Make the directory path on the remote host. The
        argument mode is ignored and only supported for
        similarity with os.mkdir.'''
        self._host.mkd(path)

    def rmdir(self, path):
        '''Remove the directory on the remote host.'''
        self._host.rmd(self, path)

    def remove(self, path):
        '''Remove the given file.'''
        self._host.delete(path)

    def unlink(self, path):
        '''Remove the given file.'''
        self.remove(path)

    def rename(self, src, dst):
        '''Rename the src on the FTP host to dst.'''
        self._host.rename(src, dst)

    def stat(self. path):
        '''Return an object similar to this returned
        by os.stat.'''
        pass

    #
    # miscellaneous utility methods resembling those in os.path
    #
    class _EmptyClass:
        pass

    def _init_path(self):
        self.path = _EmptyClass()
        self.path.abspath      = self._abspath
        self.path.basename     = self._basename
        self.path.commonprefix = self._commonprefix
        self.path.dirname      = self._dirname
        self.path.exists       = self._exists
        self.path.getmtime     = self._getmtime
        self.path.getsize      = self._getsize
        self.path.isabs        = self._isabs
        self.path.isfile       = self._isfile
        self.path.isdir        = self._isdir
        self.path.join         = self._join
        self.path.normcase     = self._normcase
        self.path.normpath     = self._normpath
        self.path.split        = self._split
        self.path.splitext     = self._splitext
        self.path.walk         = self._walk

    def _abspath(self, path):
        pass

    def _basename(self, path):
        pass

    def _commonprefix(self, list):
        pass

    def _dirname(self, path):
        pass

    def _exists(self, path):
        pass

    def _getmtime(self, path):
        # implement this by parsing DIR output?
        pass

    def _getsize(self, path):
        pass

    def _isabs(self, path):
        pass

    def _isfile(self, path):
        pass

    def _isdir(self, path):
        pass

    def _join(self, *paths):
        pass

    def _normcase(self, path):
        pass

    def _normpath(self, path):
        pass

    def _split(self, path):
        pass

    def _splitext(self, path):
        pass

    def _walk(self, visit, arg):
        pass

