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

class FTPIOError(IOError):
    def __init__(self, msg, ftp_exception=None):
        self.ftp_exception = ftp_exception
        IOError(self, msg)

# converters for native line ends to normalized ones in Python
_linesep = os.linesep
if _linesep == '\n':
    _native_to_python_linesep = \
                        lambda text: text
elif _linesep == '\r\n':
    _native_to_python_linesep = \
                        lambda text: text.replace('\r', '')
elif _linesep == '\r':
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

    def __init__(self, conn, mode):
        '''Construct the file(-like) object.'''
        self._conn = conn
        # this should be returned if someone asks
        self.mode = mode
        self._binary = 'b' in mode
        self._fp = conn.makefile(mode)
        
    #
    # Read and write operations with support for
    # line separator conversion for text modes.
    #
    # Note that we must convert line endings because
    # the FTP server expects the native line separator
    # format sent on ASCII transfers.
    #
    def read(self, *args, **kwargs):
        '''Return read bytes, normalized if in text
        transfer mode.'''
        data = apply(self._fp.read, args, kwargs)
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
        self._fp.write(data)

    def writelines(self, lines):
        '''Write lines to file. Do linesep conversion for
        text mode.'''
        if not self._binary:
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
        self._fp.close()
        self._conn.close()

    def __del__(self):
        # not strictly necessary; file and socket are
        #  closed on garbage collection, anyway
        self.close()


class FTPHost:
    '''FTP host class'''

    def __init__(self, hostname, user='anonymous', password=''):
        '''Abstract initialization of FTPHost object. At this
        stage I don't know if I need a new FTP connection for
        each file transfer.'''
        self._hostname = hostname
        self._user = user
        self._password = password
        self._host = ftplib.FTP(hostname, user, password)
    
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
        ftp_file = _FTPFile(conn, mode)
        return ftp_file

