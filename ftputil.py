# Copyright (C) 2002, Stefan Schwarzer <s.schwarzer@ndh.net>
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

# $Id: ftputil.py,v 1.71 2002/03/29 16:19:49 schwa Exp $

"""
ftputil - higher level support for FTP sessions

FTPHost objects
    This class resembles the os module's interface to
    ordinary file systems. In addition, it provides a
    method file which will return file-objects correspond-
    ing to remote files.

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

    Both accept an additional mode parameter. If it's 'b'
    the transfer mode will be for binary files.

FTPFile objects
    FTPFile objects are constructed via the file method of
    FTPHost objects. FTPFile objects support the usual file
    operations for non-seekable files (read, readline,
    readlines, xreadlines, write, writelines, close).

Note: ftputil currently is not threadsafe. More specifically,
      you can use different FTPHost objects in different
      threads but not using a single FTPHost object in
      different threads.
"""

# Ideas for future development:
# - provide sensible "fallback" when imported with Python versions
#   before 2.2 (or make all Python 2.1-compatible)
# - handle connection timeouts
# - follow links in FTPHost.path.stat implementation!
# - write documentation
# - conditional upload/download (only when the source file
#   is newer than the target file, depends on FTPHost.stat)
# - caching of FTPHost.stat results??
# - map FTP error numbers to os error numbers (ENOENT etc.)?

# for Python 2.1
from __future__ import nested_scopes

import ftplib
import stat
import time
import sys
import posixpath
import UserList

__all__ = ['FTPError', 'FTPOSError', 'TemporaryError',
           'PermanentError', 'ParserError', 'FTPIOError',
           'FTPHost']
__version__ = '1.0.7rc1'


#####################################################################
# Exception classes and wrappers

class FTPError:
    """General error class"""

    def __init__(self, ftp_exception):
        self.args = (ftp_exception,)
        self.strerror = str(ftp_exception)
        try:
            self.errno = int(self.strerror[:3])
        except (TypeError, IndexError, ValueError):
            self.errno = None
        self.filename = None

    def __str__(self):
        return self.strerror

class FTPOSError(FTPError, OSError): pass
class TemporaryError(FTPOSError): pass
class PermanentError(FTPOSError): pass
class ParserError(FTPOSError): pass

#XXX Do you know better names for _try_with_oserror and
#    _try_with_ioerror?
def _try_with_oserror(callee, *args, **kwargs):
    """
    Try the callee with the given arguments and map resulting
    exceptions from ftplib.all_errors to FTPOSError and its
    derived classes.
    """
    try:
        return callee(*args, **kwargs)
    except ftplib.error_temp, obj:
        raise TemporaryError(obj)
    except ftplib.error_perm, obj:
        raise PermanentError(obj)
    except ftplib.all_errors:
        ftp_error = sys.exc_info()[1]
        raise FTPOSError(ftp_error)

class FTPIOError(FTPError, IOError): pass

def _try_with_ioerror(callee, *args, **kwargs):
    """
    Try the callee with the given arguments and map resulting
    exceptions from ftplib.all_errors to FTPIOError.
    """
    try:
        return callee(*args, **kwargs)
    except ftplib.all_errors:
        ftp_error = sys.exc_info()[1]
        raise FTPIOError(ftp_error)


#####################################################################
# Support for file-like objects

# converter for \r\n line ends to normalized ones in Python.
#  RFC 959 states that the server will send \r\n on text mode
#  transfers, so this conversion should be safe. I still use
#  text mode transfers (mode 'r', not 'rb') in socket.makefile
#  (below) because the server may do charset conversions on
#  text transfers.
_crlf_to_python_linesep = lambda text: text.replace('\r', '')

# converter for Python line ends into \r\n
_python_to_crlf_linesep = lambda text: text.replace('\n', '\r\n')


# helper class for xreadline protocol for ASCII transfers
class _XReadlines:
    """Represents xreadline objects for ASCII transfers."""

    def __init__(self, ftp_file):
        self._ftp_file = ftp_file
        self._next_index = 0

    def __getitem__(self, index):
        """Return next line with specified index."""
        if index != self._next_index:
            raise RuntimeError( "_XReadline access index "
                  "out of order (expected %s but got %s)" %
                  (self._next_index, index) )
        line = self._ftp_file.readline()
        if not line:
            raise IndexError("_XReadline object out of data")
        self._next_index = self._next_index + 1
        return line


class _FTPFile:
    """
    Represents a file-like object connected to an FTP host.
    File and socket are closed appropriately if the close
    operation is requested.
    """

    def __init__(self, host):
        """Construct the file(-like) object."""
        self._host = host
        self._session = host._session
        self.closed = 1   # yet closed

    def _open(self, path, mode):
        """Open the remote file with given pathname and mode."""
        # check mode
        if 'a' in mode:
            raise FTPIOError("append mode not supported")
        if mode not in ('r', 'rb', 'w', 'wb'):
            raise FTPIOError("invalid mode '%s'" % mode)
        # remember convenience variables instead of mode
        self._binmode = 'b' in mode
        self._readmode = 'r' in mode
        # select ASCII or binary mode
        transfer_type = ('A', 'I')[self._binmode]
        command = 'TYPE %s' % transfer_type
        _try_with_ioerror(self._session.voidcmd, command)
        # make transfer command
        command_type = ('STOR', 'RETR')[self._readmode]
        command = '%s %s' % (command_type, path)
        # ensure we can process the raw line separators;
        #  force to binary regardless of transfer type
        if not 'b' in mode:
            mode = mode + 'b'
        # get connection and file object
        self._conn = _try_with_ioerror(
                     self._session.transfercmd, command)
        self._fo = self._conn.makefile(mode)
        # this comes last so that close does not try to
        #  close _FTPFile objects without _conn and _fo
        #  attributes
        self.closed = 0

    #
    # Read and write operations with support for
    # line separator conversion for text modes.
    #
    # Note that we must convert line endings because
    # the FTP server expects \r\n to be sent on text
    # transfers.
    #
    def read(self, *args):
        """Return read bytes, normalized if in text transfer mode."""
        data = self._fo.read(*args)
        if self._binmode:
            return data
        data = _crlf_to_python_linesep(data)
        if args == ():
            return data
        # If the read data contains \r characters the number
        #  of read characters will be too small! Thus we
        #  (would) have to continue to read until we have
        #  fetched the requested number of bytes (or run out
        #  of source data).
        # The algorithm below avoids repetitive string
        #  concatanations in the style of
        #      data = data + more_data
        #  and so should also work relatively well if there
        #  are many short lines in the file.
        wanted_size = args[0]
        chunks = [data]
        current_size = len(data)
        while current_size < wanted_size:
            # print 'not enough bytes (now %s, wanting %s)' % \
            #       (current_size, wanted_size)
            more_data = self._fo.read(wanted_size-current_size)
            if not more_data:
                break
            more_data = _crlf_to_python_linesep(more_data)
            # print '-> new (normalized) data:', \
            #       repr(more_data)
            chunks.append(more_data)
            current_size += len(more_data)
        return ''.join(chunks)

    def readline(self, *args):
        """Return one read line, normalized if in text transfer mode."""
        data = self._fo.readline(*args)
        if self._binmode:
            return data
        # eventually complete begun newline
        if data and data[-1] == '\r':
            data = data + self.read(1)
        return _crlf_to_python_linesep(data)

    def readlines(self, *args):
        """Return read lines, normalized if in text transfer mode."""
        lines = self._fo.readlines(*args)
        if self._binmode:
            return lines
        # more memory-friendly than
        #  return [... for line in lines]
        for i in range( len(lines) ):
            lines[i] = _crlf_to_python_linesep(lines[i])
        return lines

    def xreadlines(self):
        """
        Return an appropriate xreadlines object with
        built-in line separator conversion support.
        """
        if self._binmode:
            return self._fo.xreadlines()
        return _XReadlines(self)

    def write(self, data):
        """Write data to file. Do linesep conversion for text mode."""
        if not self._binmode:
            data = _python_to_crlf_linesep(data)
        self._fo.write(data)

    def writelines(self, lines):
        """Write lines to file. Do linesep conversion for text mode."""
        if self._binmode:
            self._fo.writelines(lines)
            return
        for line in lines:
            self._fo.write( _python_to_crlf_linesep(line) )

    #
    # other attributes
    #
    def __getattr__(self, attr_name):
        """Delegate unknown attribute requests to the file."""
        if attr_name in ( 'flush isatty fileno seek tell '
                          'truncate name softspace'.split() ):
            return getattr(self._fo, attr_name)
        raise AttributeError("'FTPFile' object has no "
              "attribute '%s'" % attr_name)

    def close(self):
        """Close the FTPFile."""
        if not self.closed:
            self._fo.close()
            _try_with_ioerror(self._conn.close)
            _try_with_ioerror(self._session.voidresp)
            self.closed = 1

    def __del__(self):
        self.close()


############################################################
# FTPHost class with several methods similar to those of os

class FTPHost:
    """FTP host class"""

    # Implementation notes:
    #
    # Upon every request of a file (_FTPFile object) a
    # new ftplib.FTP session is created ("cloned"), leading
    # to a child session of the FTPHost object from which the
    # file is requested.
    #
    # This is needed because opening an _FTPFile will make
    # the local session object wait for the completion of the
    # transfer. In fact, code like this would block
    # indefinitely, if the RETR request would be made on the
    # _session of the object host:
    #
    # host = FTPHost(ftp_server, user, password)
    # f = host.file('index.html')
    # host.getcwd()   # would block!
    #
    # On the other hand, the initially constructed host object
    # will store references to already established _FTPFile
    # objects and reuse an associated connection if its
    # associated _FTPFile has been closed.

    def __init__(self, *args, **kwargs):
        """Abstract initialization of FTPHost object."""
        self._session = _try_with_oserror(ftplib.FTP,
                        *args, **kwargs)
        # simulate os.path
        self.path = _Path(self)
        # store arguments for later copy operations
        self._args = args
        self._kwargs = kwargs
        # associated FTPHost objects for data transfer
        self._children = []
        self.closed = 0
        # set curdir, pardir etc. for the remote host;
        #  RFC 959 states that this is, strictly spoken,
        #  dependent on the server OS but it seems to work
        #  at least with Unix and Windows servers
        self.curdir, self.pardir, self.sep = '.', '..', '/'
        # check if we have a Microsoft ROBIN server
        try:
            response = _try_with_oserror(
                       self._session.voidcmd, 'STAT')
        except PermanentError:
            response = ''
        if response.find('ROBIN Microsoft') != -1:
            self._parser = self._parse_robin_line
        else:
            self._parser = self._parse_unix_line

    def _copy(self):
        """Return a copy of this FTPHost object."""
        # The copy includes a new ftplib.FTP instance
        #  (aka session) but doesn't copy the state of
        #  self.getcwd().
        return FTPHost(*self._args, **self._kwargs)

    def _available_child(self):
        """
        Return an available (i. e. one whose _file object is closed)
        child (FTPHost object) from the pool of children or None if
        there aren't any.
        """
        for host in self._children:
            if host._file.closed:
                return host
        return None

    def file(self, path, mode='r'):
        """
        Return an open file(-like) object which is associated with
        this FTPHost object.

        This method tries to reuse a child but will generate a new one
        if none is available.
        """
        host = self._available_child()
        if host is None:
            host = self._copy()
            self._children.append(host)
            host._file = _FTPFile(host)
        basedir = self.getcwd()
        host.chdir(basedir)
        host._file._open(path, mode)
        return host._file

    def close(self):
        """Close host connection."""
        if not self.closed:
            # close associated children
            for host in self._children:
                # only children have _file attributes
                host._file.close()
                host.close()
            # now deal with our-self
            _try_with_oserror(self._session.close)
            self._children = []
            self.closed = 1

    def __del__(self):
        try:
            self.close()
        except:
            # don't want warnings if constructor had failed
            pass

    #
    # miscellaneous utility methods resembling those in os
    #
    def getcwd(self):
        """Return the current path name."""
        return _try_with_oserror(self._session.pwd)

    def chdir(self, path):
        """Change the directory on the host."""
        _try_with_oserror(self._session.cwd, path)

    def mkdir(self, path, mode=None):
        """
        Make the directory path on the remote host. The argument mode
        is ignored and only "supported" for similarity with os.mkdir.
        """
        _try_with_oserror(self._session.mkd, path)

    def rmdir(self, path):
        """Remove the directory on the remote host."""
        _try_with_oserror(self._session.rmd, path)

    def remove(self, path):
        """Remove the given file."""
        _try_with_oserror(self._session.delete, path)

    def unlink(self, path):
        """Remove the given file."""
        self.remove(path)

    def rename(self, src, dst):
        """Rename the src on the FTP host to dst."""
        _try_with_oserror(self._session.rename, src, dst)

    def listdir(self, path):
        """
        Return a list with directories, files etc. in the directory
        named path.
        """
        path = self.path.abspath(path)
        if not self.path.isdir(path):
            raise PermanentError(
                  "550 %s: no such directory" % path)
        names = []
        def callback(line):
            stat_result = self._parse_line(line, fail=0)
            if stat_result is not None:
                names.append(stat_result.st_name)
        _try_with_oserror(self._session.dir, path, callback)
        return names

    def _stat_candidates(self, lines, wanted_name):
        """Return candidate lines for further analysis."""
        return [line  for line in lines
                if line.find(wanted_name) != -1]

    _month_numbers = {
      'jan':  1, 'feb':  2, 'mar':  3, 'apr':  4,
      'may':  5, 'jun':  6, 'jul':  7, 'aug':  8,
      'sep':  9, 'oct': 10, 'nov': 11, 'dec': 12}

    def _parse_unix_line(self, line):
        """
        Return _Stat instance corresponding to the given text line.
        Exceptions are caught in _parse_line.
        """
        metadata, nlink, user, group, size, month, day, \
          year_or_time, name = line.split(None, 8)
        # st_mode
        st_mode = 0
        for bit in metadata[1:10]:
            bit = (bit != '-')
            st_mode = (st_mode << 1) + bit
        if metadata[3] == 's':
            st_mode = st_mode | stat.S_ISUID
        if metadata[6] == 's':
            st_mode = st_mode | stat.S_ISGID
        char_to_mode = {'d': stat.S_IFDIR, 'l': stat.S_IFLNK,
                        'c': stat.S_IFCHR, '-': stat.S_IFREG}
        file_type = metadata[0]
        if char_to_mode.has_key(file_type):
            st_mode = st_mode | char_to_mode[file_type]
        else:
            raise ParserError("unknown file type "
                  "character '%s'" % file_type)
        # st_ino, st_dev, st_nlink, st_uid, st_gid,
        # st_size, st_atime
        st_ino = None
        st_dev = None
        st_nlink = int(nlink)
        st_uid = user
        st_gid = group
        st_size = int(size)
        st_atime = None
        # st_mtime
        month = self._month_numbers[ month.lower() ]
        day = int(day)
        if year_or_time.find(':') == -1:
            # year_or_time is really a year
            year, hour, minute = int(year_or_time), 0, 0
            st_mtime = time.mktime( (year, month, day, hour,
                       minute, 0, 0, 0, 0) )
        else:
            # year_or_time is a time hh:mm
            hour, minute = year_or_time.split(':')
            year, hour, minute = None, int(hour), int(minute)
            # try the current year
            year = time.localtime()[0]
            st_mtime = time.mktime( (year, month, day, hour,
                       minute, 0, 0, 0, 0) )
            if st_mtime > time.time():
                # if it's in the future use previous year
                st_mtime = time.mktime( (year-1, month, day,
                           hour, minute, 0, 0, 0, 0) )
        # st_ctime
        st_ctime = None
        # st_name
        if name.find(' -> ') != -1:
            st_name = name.split(' -> ')[0]
        else:
            st_name = name
        return _Stat( (st_mode, st_ino, st_dev, st_nlink,
                       st_uid, st_gid, st_size, st_atime,
                       st_mtime, st_ctime, st_name) )

    def _parse_robin_line(self, line):
        """
        Return _Stat instance corresponding to the given text line
        from a MS ROBIN FTP server. Exceptions are caught in
        _parse_line.
        """
        date, time_, dir_or_size, name = line.split(None, 3)
        # st_mode
        st_mode = 0400   # default to read access only;
                         #  in fact, we can't tell
        if dir_or_size == '<DIR>':
            st_mode = st_mode | stat.S_IFDIR
        else:
            st_mode = st_mode | stat.S_IFREG
        # st_ino, st_dev, st_nlink, st_uid, st_gid
        st_ino = None
        st_dev = None
        st_nlink = None
        st_uid = None
        st_gid = None
        # st_size
        if dir_or_size != '<DIR>':
            st_size = int(dir_or_size)
        else:
            st_size = None
        # st_atime
        st_atime = None
        # st_mtime
        month, day, year = map( int, date.split('-') )
        if year >= 70:
            year = 1900 + year
        else:
            year = 2000 + year
        hour, minute, am_pm = time_[0:2], time_[3:5], time_[5]
        hour, minute = int(hour), int(minute)
        if am_pm == 'P':
            hour = 12 + hour
        st_mtime = time.mktime( (year, month, day, hour,
                   minute, 0, 0, 0, 0) )
        # st_ctime
        st_ctime = None
        # st_name
        st_name = name
        return _Stat( (st_mode, st_ino, st_dev, st_nlink,
                       st_uid, st_gid, st_size, st_atime,
                       st_mtime, st_ctime, st_name) )

    def _parse_line(self, line, fail=1):
        """Return _Stat instance corresponding to the given text line."""
        try:
            return self._parser(line)
        except (ValueError, IndexError):
            if fail:
                raise ParserError(
                      "can't parse line '%s'" % line)
            else:
                return None

    def lstat(self, path):
        """Return an object similar to that returned by os.stat."""
        # get output from DIR
        lines = []
        dirname, basename = self.path.split(path)
        dirname = self.path.abspath(dirname)
        _try_with_oserror( self._session.dir, dirname,
                           lambda line: lines.append(line) )
        # search for name to be stat'ed without full parsing
        candidates = self._stat_candidates(lines, basename)
        # parse candidates
        for line in candidates:
            stat_result = self._parse_line(line, fail=0)
            if (stat_result is not None) and \
              (stat_result.st_name == basename):
                return stat_result
        raise PermanentError(
              "550 %s: no such file or directory" % path)

    def stat(self, path):
        """Return info from a stat call."""
        stat_result = self.lstat(path)
        if stat.S_ISLNK(stat_result.st_mode):
            raise NotImplementedError("following links "
                  "is not yet implemented")
        else:
            return stat_result

    def copyfileobj(self, source, target, length=64*1024):
        "Copy data from file-like object source to file-like object target."
        # inspired by shutil.copyfileobj (I don't use the
        #  shutil code directly because it might change)
        while 1:
            buf = source.read(length)
            if not buf:
                break
            target.write(buf)

    #TODO Test this
    def copyfile(self, src, dst):
        """Copy data from src to dst (adapted from shutil.copyfile)."""
        fsrc = None
        fdst = None
        try:
            fsrc = self.file(src, 'rb')
            fdst = self.file(dst, 'wb')
            self.copyfileobj(fsrc, fdst)
        finally:
            if fdst:
                fdst.close()
            if fsrc:
                fsrc.close()

    def __get_modes(self, mode):
        """Return modes for source and target file."""
        if mode == 'b':
            return 'rb', 'wb'
        else:
            return 'r', 'w'

    def upload(self, source, target, mode=''):
        """
        Upload a file from the local source (name) to the remote
        target (name). The argument mode is an empty string or 'a' for
        text copies, or 'b' for binary copies.
        """
        source_mode, target_mode = self.__get_modes(mode)
        source = open(source, source_mode)
        target = self.file(target, target_mode)
        self.copyfileobj(source, target)
        source.close()
        target.close()

    def download(self, source, target, mode=''):
        """
        Download a file from the remote source (name) to the local
        target (name). The argument mode is an empty string or 'a' for
        text copies, or 'b' for binary copies.
        """
        source_mode, target_mode = self.__get_modes(mode)
        source = self.file(source, source_mode)
        target = open(target, target_mode)
        self.copyfileobj(source, target)
        source.close()
        target.close()


#####################################################################
# Helper classes _Stat and _Path to imitate behaviour of stat objects
#  and os.path module contents.

class _Stat(UserList.UserList):
    """
    Support class resembling a tuple like that which is returned
    from os.(l)stat. Deriving from the tuple type will only work
    in Python 2.2+
    """

    _index_mapping = {'st_mode':  0, 'st_ino':   1,
      'st_dev':   2,  'st_nlink': 3, 'st_uid':   4,
      'st_gid':   5,  'st_size':  6, 'st_atime': 7,
      'st_mtime': 8,  'st_ctime': 9, 'st_name': 10}

    def __getattr__(self, attr_name):
        if self._index_mapping.has_key(attr_name):
            return self[ self._index_mapping[attr_name] ]
        else:
            raise AttributeError("'_Stat' object has "
                  "no attribute '%s'" % attr_name)


class _Path:
    """
    Support class resembling os.path, accessible from the
    FTPHost() object e. g. as FTPHost().path.abspath(path).
    Hint: substitute os with the FTPHost() object.
    """

    def __init__(self, host):
        self._host = host
        # delegate these to posixpath
        pp = posixpath
        self.dirname      = pp.dirname
        self.basename     = pp.basename
        self.isabs        = pp.isabs
        self.commonprefix = pp.commonprefix
        self.join         = pp.join
        self.split        = pp.split
        self.splitdrive   = pp.splitdrive
        self.splitext     = pp.splitext
        self.normcase     = pp.normcase
        self.normpath     = pp.normpath

    def abspath(self, path):
        """Return an absolute path."""
        if not self.isabs(path):
            path = self.join( self._host.getcwd(), path )
        return self.normpath(path)

    def exists(self, path):
        try:
            self._host.lstat(path)
            return 1
        except FTPOSError:
            return 0

    def getmtime(self, path):
        return self._host.stat(path).st_mtime

    def getsize(self, path):
        return self._host.stat(path).st_size

    # check whether a path is a regular file/dir/link;
    #  for the first two cases follow links (like in os.path)
    def isfile(self, path):
        try:
            stat_result = self._host.stat(path)
        except FTPOSError:
            return 0
        return stat.S_ISREG(stat_result.st_mode)

    def isdir(self, path):
        try:
            stat_result = self._host.stat(path)
        except FTPOSError:
            return 0
        return stat.S_ISDIR(stat_result.st_mode)

    def islink(self, path):
        try:
            stat_result = self._host.lstat(path)
        except FTPOSError:
            return 0
        return stat.S_ISLNK(stat_result.st_mode)

    def walk(self, top, func, arg):
        """
        Directory tree walk with callback function.

        For each directory in the directory tree rooted at top
        (including top itself, but excluding '.' and '..'), call
        func(arg, dirname, fnames). dirname is the name of the
        directory, and fnames a list of the names of the files and
        subdirectories in dirname (excluding '.' and '..').  func may
        modify the fnames list in-place (e.g. via del or slice
        assignment), and walk will only recurse into the
        subdirectories whose names remain in fnames; this can be used
        to implement a filter, or to impose a specific order of
        visiting.  No semantics are defined for, or required of, arg,
        beyond that arg is always passed to func.  It can be used,
        e.g., to pass a filename pattern, or a mutable object designed
        to accumulate statistics.  Passing None for arg is common.
        """
        # This code (and the above documentation) is taken from
        #  posixpath.py, with slight modifications
        try:
            names = self._host.listdir(top)
        except OSError:
            return
        func(arg, top, names)
        for name in names:
            name = self.join(top, name)
            try:
                st = self._host.lstat(name)
            except OSError:
                continue
            if stat.S_ISDIR(st[stat.ST_MODE]):
                self.walk(name, func, arg)

# Unix format
# total 14
# drwxr-sr-x   2 45854    200           512 May  4  2000 chemeng
# drwxr-sr-x   2 45854    200           512 Jan  3 17:17 download
# drwxr-sr-x   2 45854    200           512 Jul 30 17:14 image
# -rw-r--r--   1 45854    200          4604 Jan 19 23:11 index.html
# drwxr-sr-x   2 45854    200           512 May 29  2000 os2
# lrwxrwxrwx   2 45854    200           512 May 29  2000 osup -> ../os2
# drwxr-sr-x   2 45854    200           512 May 25  2000 publications
# drwxr-sr-x   2 45854    200           512 Jan 20 16:12 python
# drwxr-sr-x   6 45854    200           512 Sep 20  1999 scios2

# Microsoft ROBIN FTP server
# 07-04-01  12:57PM       <DIR>          SharePoint_Launch
# 11-12-01  04:38PM       <DIR>          Solution Sales
# 06-27-01  01:53PM       <DIR>          SPPS
# 01-08-02  01:32PM       <DIR>          technet
# 07-27-01  11:16AM       <DIR>          Test
# 10-23-01  06:49PM       <DIR>          Wernerd
# 10-23-01  03:25PM       <DIR>          WindowsXP
# 12-07-01  02:05PM       <DIR>          XPLaunch
# 07-17-00  02:08PM             12266720 digidash.exe
# 07-17-00  02:08PM                89264 O2KKeys.exe

