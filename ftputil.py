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
import cStringIO

class FTPIOError(IOError):
    pass

class _FTPFile:
    '''Represents a file-like object connected to an
    FTP host.'''

    def __init__(self, host, path):
        '''Construct the file(-like) object.'''
        self._host = host
        self._path = path
        self.closed = 0
        
    def read(self, bytes=None):
        '''Return 'bytes' bytes from the file object, or up
        to EOF if the argument is not provided.'''
        pass

    def readline(self):
        '''Return a single line from the file object.'''
        pass

    def readlines(self):
        '''Return a list of lines until EOF.'''
        pass

    def write(self, data):
        '''Write a data string to the file.'''
        pass

    def writelines(self, data):
        '''Write a list of strings to the file object.'''
        pass

    def close(self):
        if not self.closed:
            # what will we do?
            pass

    
class FTPHost:
    '''FTP host class'''

    def __init__(self, hostname, user='anonymous', password=''):
        '''Abstract initialization of FTPHost object. At this
        stage I don't know if I need a new FTP connection for
        each file transfer.'''
        self._hostname = host
        self._user = user
        self._password = password
        self._host = ftplib.FTP(hostnamme, user, password)
    
    def file(self, path, mode='r'):
        '''Return a file-like object that is connected to
        FTP host.'''
        # we don't support append modes
        assert '+' not in mode
        if 'r' in mode:
            # read modes
            if 'b' in mode:
                # open for binary reading
            else:
                # open for ASCII reading
        elif 'w' in mode:
            # write modes
            if 'b' in mode:
                # open for binary writing
            else:
                # open for ASCII writing

