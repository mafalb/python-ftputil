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


class FTPIOError(IOError):
    def __init__(self, msg, ftp_exception=None):
        self.ftp_exception = ftp_exception
        IOError(self, msg)


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
        if mode == 'r':
            # the FTP server ensures the correct mode via
            #  the previous TYPE command
            mode = 'rb'
        self._fp = conn.makefile(mode)
        
    def _normalize_linefeeds(text):
        r'''Return data with occurences of \r removed.'''
        return data.replace('\r', '')

    def read(self, *args, **kwargs):
        '''Return read bytes, normalized if in ASCII
        transfer mode.'''
        text = apply(self._fp.read, args, kwargs)
        if self._binary:
            return text
        else:
            return self._normalize_linefeeds(text)

    def readlines(self, *args, **kwargs):
        '''Return read lines, normalized if in ASCII
        transfer mode.'''
        lines = apply(self._fp.readlines, args, kwargs)
        return [self._normalize_linefeeds(line)
                for line in lines]
        
    def __getattr__(self, attr_name):
        '''Delegate unknown attribute requests to the file.'''
        if attr_name in ( 'flush isatty fileno read readline '
          'readlines xreadlines seek tell truncate write '
          'writelines closed name softspace'.split() ):
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
        if mode not in ( 'r rb br w wb bw'.split() ):
            raise FTPIOError("invalid mode")
        # select ASCII or binary mode
        transfer_type = ('A', 'I')['b' in mode]
        command = 'TYPE %s' % transfer_type
        # logic taken from ftplib;
        #  why this strange distinction?
        if mode == 'r':
            self._host.sendcmd(command)
        else:
            self._host.voidcmd(command)
        # make transfer command
        command_type = ('STOR', 'RETR')['r' in mode]
        command = '%s %s' % (command_type, path)
        # get connection and file object
        conn = self._host.transfercmd(command)
        self._host.voidresp()
        ftp_file = _FTPFile(conn, mode)
        return ftp_file

