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
import posixpath


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

    def __init__(self, host, path, mode):
        '''Construct the file(-like) object.'''
        # we need only the ftplib.FTP object
        self._ftplib_host = host._ftplib_host
        # check mode
        if '+' in mode:
            raise FTPIOError("append modes not supported")
        if mode not in ('r', 'rb', 'w', 'wb'):
            raise FTPIOError("invalid mode '%s'" % mode)
        # remember convenience variables instead of mode
        self._binary = 'b' in mode
        self._readmode = 'r' in mode
        # select ASCII or binary mode
        transfer_type = ('A', 'I')[self._binary]
        command = 'TYPE %s' % transfer_type
        self._ftplib_host.voidcmd(command)
        # make transfer command
        command_type = ('STOR', 'RETR')[self._readmode]
        command = '%s %s' % (command_type, path)
        # get connection and file object
        self._conn = self._ftplib_host.transfercmd(command)
        self._fp = self._conn.makefile(mode)
        self.closed = 0

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
        data = self._fp.read(*args, **kwargs)
        if self._binary:
            return data
        return _native_to_python_linesep(data)

    def readline(self, *args, **kwargs):
        '''Return one read line, normalized if in text
        transfer mode.'''
        data = self._fp.readline(*args, **kwargs)
        if self._binary:
            return data
        return _native_to_python_linesep(data)

    def readlines(self, *args, **kwargs):
        '''Return read lines, normalized if in text
        transfer mode.'''
        lines = self._fp.readlines(*args, **kwargs)
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
              "xreadlines in ASCII mode not yet supported")

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
        '''Close the FTPFile.'''
        if not self.closed:
            self._fp.close()
            self._conn.close()
            self._ftplib_host.voidresp()
            self.closed = 1

    def __del__(self):
        # not strictly necessary; file and socket are
        #  closed on garbage collection, anyway
        self.close()


############################################################
# FTPHost class with several methods similar to those of os

class FTPHost:
    '''FTP host class'''

    def __init__(self, *args, **kwargs):
        '''Abstract initialization of FTPHost object.'''
        self._ftplib_host = ftplib.FTP(*args, **kwargs)
        # simulate os.path
        self.path = _Path(self)
        # store arguments for later copy operations
        self._args = args
        self._kwargs = kwargs

    def _copy(self):
        '''Return a copy of this FTPHost object. This includes
        opening an additional FTP control connection and
        changing to the path which is currently set in self.'''
        copy = FTPHost(*self._args, **self._kwargs)
        current_dir = self.getcwd()
        copy.chdir(current_dir)
        return copy
        
    def file(self, path, mode='r'):
        '''Return a file(-like) object that is connected to an
        FTP host.'''
        host_copy = self._copy()
        return _FTPFile(host_copy, path, mode)

    def close(self):
        '''Close host connection.'''
        return self._ftplib_host.close()

    #
    # miscellaneous utility methods resembling those in os
    #
    def getcwd(self):
        '''Return the current path name.'''
        return self._ftplib_host.pwd()

    def chdir(self, path):
        '''Change the directory on the host.'''
        try:
            self._ftplib_host.cwd(path)
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
        self._ftplib_host.mkd(path)

    def rmdir(self, path):
        '''Remove the directory on the remote host.'''
        self._ftplib_host.rmd(self, path)

    def remove(self, path):
        '''Remove the given file.'''
        self._ftplib_host.delete(path)

    def unlink(self, path):
        '''Remove the given file.'''
        self.remove(path)

    def rename(self, src, dst):
        '''Rename the src on the FTP host to dst.'''
        self._ftplib_host.rename(src, dst)

    def _stat_candidates(self, lines, wanted_name):
        '''Return candidate lines for further analysis.
        Warning: This implementation will dismiss names
        with whitespace in them!'''
        if wanted_name.find(' ') > -1:
            raise NotImplementedError("Names to stat "
                  "'%s' must not contain whitespace" %
                  wanted_name)
        result = []
        for line in lines:
            parts = line.split()
            if parts[-2] == '->':
                # we found a link; name before "->" counts
                name = parts[-3]
            else:
                name = parts[-1]
            if name == wanted_name:
                result.append(line)
        return result
        
    def lstat(self, path):
        '''Return an object similar to that returned
        by os.stat.'''
        # get output from DIR
        lines = []
        dirname, basename = self.path.split(path)
        self._ftplib_host.dir(
          dirname, lambda line: lines.append(line) )
        # search for name to be stat'ed
        candidates = self._stat_candidates(lines, basename)
        # scan candidates
        for line in candidates:
            pass


class _Stat(tuple):
    '''Support class resembling a tuple like that which is
    returned from os.(l)stat. Deriving from the tuple type
    will only work with Python 2.2+'''
    
    _index_mapping = {'st_mode':  0, 'st_ino':   1, 
      'st_dev':   2,  'st_nlink': 3, 'st_uid':   4,
      'st_gid':   5,  'st_size':  6, 'st_atime': 7,
      'st_mtime': 8,  'st_ctime': 9}

    def __getattr__(self, attr_name):
        if attr_name in self._index_mapping:
            return self[ self._index_mapping[attr_name] ]
        else:
            raise AttributeError("'ftputil._Stat' object has "
                  "no attribute '%s'" % attr_name)


class _Path:
    '''Support class resembling os.path, accessible from the
    FTPHost() object e. g. as FTPHost().path.abspath(path).
    Hint: substitute os with the FTPHost() object.'''

    def __init__(self, host):
        self._host = host

    def abspath(self, path):
        '''Return an absolute path.'''
        if not self.isabs(path):
            path = self.join( self._host.getcwd(), path )
        return self.normpath(path)

    def basename(self, path):
        return posixpath.basename(path)

    def commonprefix(self, path_list):
        return posixpath.commonprefix(path_list)

    def dirname(self, path):
        return posixpath.dirname(path)

    def exists(self, path):
        pass

    def getmtime(self, path):
        # implement this by parsing DIR output?
        pass

    def getsize(self, path):
        pass

    def isabs(self, path):
        return posixpath.isabs(path)

    def isfile(self, path):
        pass

    def isdir(self, path):
        pass

    def join(self, *paths):
        return posixpath.join(*paths)

    def normcase(self, path):
        return path

    def normpath(self, path):
        return posixpath.normpath(path)

    def split(self, path):
        return posixpath.split(path)

    def splitdrive(self, path):
        return posixpath.splitdrive(path)

    def splitext(self, path):
        return posixpath.splitext(path)

    def walk(self, visit, arg):
        pass

