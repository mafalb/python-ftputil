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

"""
ftp_stat.py - stat result, parsers, and FTP stat'ing for `ftputil`
"""

# $Id: ftp_stat.py,v 1.22 2003/10/25 21:33:56 schwa Exp $

import stat
import sys
import time

import ftp_error


# Set up the base class for the stat results, depending on the
#  capabilities of the used Python version. In older Python versions,
#  classes can't inherit from builtin types.
try:
    class __InheritanceTest(tuple):
        pass
    _StatResultBase = tuple
except TypeError:
    # "base is not a class object"
    import UserTuple
    _StatResultBase = UserTuple.UserTuple


class _StatResult(_StatResultBase):
    """
    Support class resembling a tuple like that returned from
    `os.(l)stat`.
    """
    _index_mapping = {
      'st_mode':  0, 'st_ino':   1, 'st_dev':    2, 'st_nlink':    3,
      'st_uid':   4, 'st_gid':   5, 'st_size':   6, 'st_atime':    7,
      'st_mtime': 8, 'st_ctime': 9, '_st_name': 10, '_st_target': 11}

    def __getattr__(self, attr_name):
        if self._index_mapping.has_key(attr_name):
            return self[ self._index_mapping[attr_name] ]
        else:
            raise AttributeError("'_Stat' object has no attribute '%s'" %
                                 attr_name)


class _Stat:
    """Methods for stat'ing directories, links and regular files."""
    def __init__(self, host):
        self._host = host
        self._path = host.path

    def parse_line(self, line):
        """
        Return a `_Stat` object as derived from the string `line`.
        The parser code to use depends on the directory format the
        FTP server delivers (also see examples at end of file).
        """
        raise NotImplementedError("must be defined by subclass")

    def parse_lines(self, lines):
        """
        Return a list of `_Stat` objects with one `_Stat` object per
        line in the list `lines`. The order of the returned list
        corresponds to the order in the `lines` argument.
        """
        stat_results = [ self.parse_line(line) for line in lines ]
        return stat_results

    def _host_dir(self, path):
        """
        Return a list of lines, as fetched by FTP's `DIR` command,
        when applied to `path`.
        """
        return self._host._dir(path)

    def listdir(self, path):
        """
        Return a list with directories, files etc. in the directory
        named `path`.
        """
        # we _can't_ put this check into `FTPHost._dir`, see its docstring
        path = self._path.abspath(path)
        if not self._path.isdir(path):
            raise ftp_error.PermanentError("550 %s: no such directory" % path)
        lines = self._host_dir(path)
        names = []
        for line in lines:
            try:
                stat_result = self.parse_line(line)
                st_name = stat_result._st_name
                if st_name not in (self._host.curdir, self._host.pardir):
                    names.append(st_name)
            except ftp_error.ParserError:
                pass
        return names

    def _stat_candidates(self, lines, wanted_name):
        """Return candidate lines for further analysis."""
        # return only lines that contain the name of the file to stat
        #  (however, the string may be _anywhere_ on the line but not
        #  necessarily the file's basename; e. g. the string could
        #  occur as the name of the file's group)
        return [ line  for line in lines
                 if line.find(wanted_name) != -1 ]

    def lstat(self, path):
        """Return an object similar to that returned by `os.lstat`."""
        # get output from FTP's `DIR` command
        lines = []
        path = self._path.abspath(path)
        # Note: (l)stat works by going one directory up and parsing
        #  the output of an FTP `DIR` command. Unfortunately, it is
        #  not possible to do this for the root directory `/`.
        if path == '/':
            raise ftp_error.RootDirError(
                  "can't invoke stat for remote root directory")
        dirname, basename = self._path.split(path)
        lines = self._host_dir(dirname)
        # search for name to be stat'ed without parsing the whole
        #  directory listing
        candidates = self._stat_candidates(lines, basename)
        # parse candidates; return the first stat result where the
        #  calculated name matches the previously determined
        #  basename
        for line in candidates:
            try:
                stat_result = self.parse_line(line)
            except ftp_error.ParserError:
                pass
            else:
                if stat_result._st_name == basename:
                    return stat_result
        # if the basename wasn't found in any line, raise an
        #  exception
        raise ftp_error.PermanentError(
              "550 %s: no such file or directory" % path)

    def stat(self, path):
        """Return info from a `stat` call."""
        # most code in this method is used to detect recursive
        #  link structures
        visited_paths = {}
        while True:
            # stat the link if it is one, else the file/directory
            stat_result = self.lstat(path)
            # if the file is not a link, the `stat` result is the
            #  same as the `lstat` result
            if not stat.S_ISLNK(stat_result.st_mode):
                return stat_result
            # if we stat'ed a link, calculate a normalized path for
            #  the file the link points to
            dirname, basename = self._path.split(path)
            path = self._path.join(dirname, stat_result._st_target)
            path = self._path.normpath(path)
            # check for cyclic structure
            if visited_paths.has_key(path):
                # we had this path already
                raise ftp_error.PermanentError(
                      "recursive link structure detected")
            # remember the path we have encountered
            visited_paths[path] = True


class _UnixStat(_Stat):
    """`_Stat` class for Unix-specific directory format."""
    # map month abbreviations to month numbers
    _month_numbers = {
      'jan':  1, 'feb':  2, 'mar':  3, 'apr':  4,
      'may':  5, 'jun':  6, 'jul':  7, 'aug':  8,
      'sep':  9, 'oct': 10, 'nov': 11, 'dec': 12}

    def parse_line(self, line):
        """
        Return `_Stat` instance corresponding to the given text line.
        If the line can't be parsed, raise a `ParserError`.
        """
        try:
            metadata, nlink, user, group, size, month, day, \
              year_or_time, name = line.split(None, 8)
        except ValueError:
            # "unpack list of wrong size"
            raise ftp_error.ParserError("line '%s' can't be parsed" % line )
        # st_mode
        st_mode = 0
        if len(metadata) != 10:
            raise ftp_error.ParserError("invalid metadata '%s'" % metadata)
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
            raise ftp_error.ParserError(
                  "unknown file type character '%s'" % file_type)
        # st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime
        st_ino = None
        st_dev = None
        st_nlink = int(nlink)
        st_uid = user
        st_gid = group
        st_size = int(size)
        st_atime = None
        # st_mtime
        try:
            month = self._month_numbers[ month.lower() ]
        except KeyError:
            raise ftp_error.ParserError("invalid month name '%s'" % month)
        day = int(day)
        if year_or_time.find(':') == -1:
            # `year_or_time` is really a year
            year, hour, minute = int(year_or_time), 0, 0
            st_mtime = time.mktime( (year, month, day, hour,
                       minute, 0, 0, 0, -1) )
        else:
            # `year_or_time` is a time hh:mm
            hour, minute = year_or_time.split(':')
            year, hour, minute = None, int(hour), int(minute)
            # try the current year
            year = time.localtime()[0]
            st_mtime = time.mktime( (year, month, day, hour,
                       minute, 0, 0, 0, -1) )
            # rhs of comparison: transform client time to server time
            #  (as on the lhs), so both can be compared with respect
            #  to the set time shift (see the definition of the time
            #  shift in `FTPHost.set_time_shift`'s docstring); the
            #  last addend allows for small deviations between the
            #  supposed (rounded) and the actual time shift
            # #XXX the downside of this "correction" is that there is
            #  a one-minute time interval excatly one year ago that
            #  may cause that datetime to be recognized as the current
            #  datetime, but after all the datetime from the server
            #  can only be exact up a minute
            if st_mtime > time.time() + self._host.time_shift() + 60.0:
                # if it's in the future, use previous year
                st_mtime = time.mktime( (year-1, month, day,
                           hour, minute, 0, 0, 0, -1) )
        # st_ctime
        st_ctime = None
        # st_name
        if name.find(' -> ') != -1:
            st_name, st_target = name.split(' -> ')
        else:
            st_name, st_target = name, None
        stat_result = _StatResult(
                      (st_mode, st_ino, st_dev, st_nlink, st_uid,
                       st_gid, st_size, st_atime, st_mtime, st_ctime) )
        stat_result._st_name = st_name
        stat_result._st_target = st_target
        return stat_result


class _MSStat(_Stat):
    """`_Stat` class for MS-specific directory format."""
    def parse_line(self, line):
        """
        Return `_Stat` instance corresponding to the given text line
        from a MS ROBIN FTP server. If the line can't be parsed,
        raise a `ParserError`.
        """
        try:
            date, time_, dir_or_size, name = line.split(None, 3)
        except ValueError:
            # "unpack list of wrong size"
            raise ftp_error.ParserError("line '%s' can't be parsed" % line )
        # st_mode
        st_mode = 0400   # default to read access only;
                         #  in fact, we can't tell
        if dir_or_size == "<DIR>":
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
        if dir_or_size != "<DIR>":
            try:
                st_size = int(dir_or_size)
            except ValueError:
                raise ftp_error.ParserError("invalid size %s" % dir_or_size)
        else:
            st_size = None
        # st_atime
        st_atime = None
        # st_mtime
        try:
            month, day, year = map( int, date.split('-') )
            if year >= 70:
                year = 1900 + year
            else:
                year = 2000 + year
            hour, minute, am_pm = time_[0:2], time_[3:5], time_[5]
            hour, minute = int(hour), int(minute)
        except (ValueError, IndexError):
            raise ftp_error.ParserError("invalid time string '%s'" % time_)
        if am_pm == 'P':
            hour = hour + 12
        st_mtime = time.mktime( (year, month, day, hour,
                                 minute, 0, 0, 0, -1) )
        # st_ctime
        st_ctime = None
        stat_result = _StatResult(
                      (st_mode, st_ino, st_dev, st_nlink, st_uid,
                       st_gid, st_size, st_atime, st_mtime, st_ctime) )
        # _st_name and _st_target
        stat_result._st_name = name
        stat_result._st_target = None
        return stat_result


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

