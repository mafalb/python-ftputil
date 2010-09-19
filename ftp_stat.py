# Copyright (C) 2002-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

"""
ftp_stat.py - stat result, parsers, and FTP stat'ing for `ftputil`
"""

import re
import stat
import time

import ftp_error
import ftp_stat_cache


# These can be used to write custom parsers.
__all__ = ['StatResult', 'Parser', 'UnixParser', 'MSParser']


class StatResult(tuple):
    """
    Support class resembling a tuple like that returned from
    `os.(l)stat`.
    """

    _index_mapping = {
      'st_mode':  0, 'st_ino':   1, 'st_dev':    2, 'st_nlink':    3,
      'st_uid':   4, 'st_gid':   5, 'st_size':   6, 'st_atime':    7,
      'st_mtime': 8, 'st_ctime': 9, '_st_name': 10, '_st_target': 11}

    def __init__(self, sequence):
        # Don't call `__init__` via `super`. Construction from a
        #  sequence is implicitly handled by `tuple.__new__`, not
        #  `tuple.__init__`. As a by-product, this avoids a
        #  `DeprecationWarning` in Python 2.6+ .
        # These may be overwritten in a `Parser.parse_line` method.
        self._st_name = ""
        self._st_target = None
        self._st_mtime_precision = None

    def __getattr__(self, attr_name):
        if attr_name in self._index_mapping:
            return self[self._index_mapping[attr_name]]
        else:
            raise AttributeError("'StatResult' object has no attribute '%s'" %
                                 attr_name)

#
# FTP directory parsers
#
class Parser(object):
    """
    Represent a parser for directory lines. Parsers for specific
    directory formats inherit from this class.
    """

    # Map month abbreviations to month numbers
    _month_numbers = {
      'jan':  1, 'feb':  2, 'mar':  3, 'apr':  4,
      'may':  5, 'jun':  6, 'jul':  7, 'aug':  8,
      'sep':  9, 'oct': 10, 'nov': 11, 'dec': 12}

    _total_regex = re.compile(r"^total\s+\d+")

    def ignores_line(self, line):
        """
        Return a true value if the line should be ignored, i. e. is
        assumed to _not_ contain actual directory/file/link data.
        A typical example are summary lines like "total 23" which
        are emitted by some FTP servers.

        If the line should be used to extract stat data from it,
        return a false value.
        """
        # Either a `_SRE_Match` instance or `None`
        match = self._total_regex.search(line)
        return bool(match)

    def parse_line(self, line, time_shift=0.0):
        """
        Return a `StatResult` object as derived from the string
        `line`. The parser code to use depends on the directory format
        the FTP server delivers (also see examples at end of file).

        If the given text line can't be parsed, raise a `ParserError`.

        For the definition of `time_shift` see the docstring of
        `FTPHost.set_time_shift` in `ftputil.py`. Not all parsers
        use the `time_shift` parameter.
        """
        raise NotImplementedError("must be defined by subclass")

    #
    # Helper methods for parts of a directory listing line
    #
    def parse_unix_mode(self, mode_string):
        """
        Return an integer from the `mode_string`, compatible with
        the `st_mode` value in stat results. Such a mode string
        may look like "drwxr-xr-x".

        If the mode string can't be parsed, raise an
        `ftp_error.ParserError`.
        """
        if len(mode_string) != 10:
            raise ftp_error.ParserError("invalid mode string '%s'" %
                                        mode_string)
        st_mode = 0
        #TODO Add support for "S" and sticky bit ("t", "T")
        for bit in mode_string[1:10]:
            bit = (bit != '-')
            st_mode = (st_mode << 1) + bit
        if mode_string[3] == 's':
            st_mode = st_mode | stat.S_ISUID
        if mode_string[6] == 's':
            st_mode = st_mode | stat.S_ISGID
        file_type_to_mode = {'b': stat.S_IFBLK, 'c': stat.S_IFCHR,
                             'd': stat.S_IFDIR, 'l': stat.S_IFLNK,
                             'p': stat.S_IFIFO, 's': stat.S_IFSOCK,
                             '-': stat.S_IFREG,
                             # Ignore types which `ls` can't make sense of
                             #  (assuming the FTP server returns listings
                             #  like `ls` does).
                             '?': 0,
                            }
        file_type = mode_string[0]
        if file_type in file_type_to_mode:
            st_mode = st_mode | file_type_to_mode[file_type]
        else:
            raise ftp_error.ParserError(
                  "unknown file type character '%s'" % file_type)
        return st_mode

    def parse_unix_time(self, month_abbreviation, day, year_or_time,
                        time_shift, with_precision=False):
        """
        Return a floating point number, like from `time.mktime`, by
        parsing the string arguments `month_abbreviation`, `day` and
        `year_or_time`. The parameter `time_shift` is the difference
        "time on server" - "time on client" and is available as the
        `time_shift` parameter in the `parse_line` interface.

        If `with_precision` is true (default: false), return a
        two-element tuple consisting of the floating point number as
        described in the previous paragraph and the precision of the
        time in seconds. This takes into account that, for example, a
        time string like "May 26  2005" has only a precision of one
        day. This information is important for the `upload_if_newer`
        and `download_if_newer` methods in the `FTPHost` class.

        Times in Unix-style directory listings typically have one of
        these formats:

        - "Nov 23 02:33" (month name, day of month, time)

        - "May 26  2005" (month name, day of month, year)

        If this method can not make sense of the given arguments, it
        raises an `ftp_error.ParserError`.
        """
        try:
            month = self._month_numbers[month_abbreviation.lower()]
        except KeyError:
            raise ftp_error.ParserError("invalid month name '%s'" % month)
        day = int(day)
        if ":" not in year_or_time:
            # `year_or_time` is really a year
            year, hour, minute = int(year_or_time), 0, 0
            st_mtime = time.mktime( (year, month, day,
                                     hour, minute, 0, 0, 0, -1) )
            # Precise up to a day
            st_mtime_precision = 24 * 60 * 60
        else:
            # `year_or_time` is a time hh:mm
            hour, minute = year_or_time.split(':')
            year, hour, minute = None, int(hour), int(minute)
            # Try the current year
            year = time.localtime()[0]
            st_mtime = time.mktime( (year, month, day,
                                     hour, minute, 0, 0, 0, -1) )
            # Precise up to a minute
            st_mtime_precision = 60
            # Rhs of comparison: Transform client time to server time
            #  (as on the lhs), so both can be compared with respect
            #  to the set time shift (see the definition of the time
            #  shift in `FTPHost.set_time_shift`'s docstring). The
            #  last addend allows for small deviations between the
            #  supposed (rounded) and the actual time shift.
            # #XXX The downside of this "correction" is that there is
            #  a one-minute time interval exactly one year ago that
            #  may cause that datetime to be recognized as the current
            #  datetime, but after all the datetime from the server
            #  can only be exact up to a minute.
            if st_mtime > time.time() + time_shift + 60.0:
                # If it's in the future, use previous year
                st_mtime = time.mktime( (year-1, month, day,
                                         hour, minute, 0, 0, 0, -1) )
        if with_precision:
            return (st_mtime, st_mtime_precision)
        else:
            return st_mtime

    def parse_ms_time(self, date, time_, time_shift):
        """
        Return a floating point number, like from `time.mktime`, by
        parsing the string arguments `date` and `time_`. The parameter
        `time_shift` is the difference

            "time on server" - "time on client"

        and can be set as the `time_shift` parameter in the
        `parse_line` interface.

        Times in MS-style directory listings typically have the
        format "10-23-01 03:25PM" (month-day_of_month-two_digit_year,
        hour:minute, am/pm).

        If this method can not make sense of the given arguments, it
        raises an `ftp_error.ParserError`.
        """
        # Don't complain about unused `time_shift` argument
        # pylint: disable=W0613
        # For the time being, I don't add a `with_precision`
        #  parameter as in the Unix parser because the precision for
        #  the DOS format is always a minute and can be set in
        #  `MSParser.parse_line`. Should you find yourself needing
        #  support for `with_precision` for a derived class, please
        #  send a mail (see ftputil.txt/html).
        try:
            month, day, year = [int(part) for part in date.split('-')]
            if year >= 70:
                year = 1900 + year
            else:
                year = 2000 + year
            hour, minute, am_pm = time_[0:2], time_[3:5], time_[5]
            hour, minute = int(hour), int(minute)
        except (ValueError, IndexError):
            raise ftp_error.ParserError("invalid time string '%s'" % time_)
        if hour == 12 and am_pm == 'A':
            hour = 0
        if hour != 12 and am_pm == 'P':
            hour = hour + 12
        st_mtime = time.mktime( (year, month, day,
                                 hour, minute, 0, 0, 0, -1) )
        return st_mtime


class UnixParser(Parser):
    """`Parser` class for Unix-specific directory format."""

    def _split_line(self, line):
        """
        Split a line in metadata, nlink, user, group, size, month,
        day, year_or_time and name and return the result as an
        nine-element list of these values. If the name is a link,
        it will be encoded as a string "link_name -> link_target".
        """
        # This method encapsulates the recognition of an unusual
        #  Unix format variant (see ticket
        #  http://ftputil.sschwarzer.net/trac/ticket/12 ).
        line_parts = line.split()
        FIELD_COUNT_WITHOUT_USERID = 8
        FIELD_COUNT_WITH_USERID = FIELD_COUNT_WITHOUT_USERID + 1
        if len(line_parts) < FIELD_COUNT_WITHOUT_USERID:
            # No known Unix-style format
            raise ftp_error.ParserError("line '%s' can't be parsed" % line)
        # If we have a valid format (either with or without user id field),
        #  the field with index 5 is either the month abbreviation or a day.
        try:
            int(line_parts[5])
        except ValueError:
            # Month abbreviation, "invalid literal for int"
            line_parts = line.split(None, FIELD_COUNT_WITH_USERID-1)
        else:
            # Day
            line_parts = line.split(None, FIELD_COUNT_WITHOUT_USERID-1)
            USER_FIELD_INDEX = 2
            line_parts.insert(USER_FIELD_INDEX, None)
        return line_parts

    def parse_line(self, line, time_shift=0.0):
        """
        Return a `StatResult` instance corresponding to the given
        text line. The `time_shift` value is needed to determine
        to which year a datetime without an explicit year belongs.

        If the line can't be parsed, raise a `ParserError`.
        """
        mode_string, nlink, user, group, size, month, day, \
          year_or_time, name = self._split_line(line)
        # st_mode
        st_mode = self.parse_unix_mode(mode_string)
        # st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime
        st_ino = None
        st_dev = None
        st_nlink = int(nlink)
        st_uid = user
        st_gid = group
        st_size = int(size)
        st_atime = None
        # st_mtime
        st_mtime, st_mtime_precision = \
          self.parse_unix_time(month, day, year_or_time, time_shift,
                               with_precision=True)
        # st_ctime
        st_ctime = None
        # st_name
        if name.count(" -> ") > 1:
            # If we have more than one arrow we can't tell where the link
            #  name ends and the target name starts.
            raise ftp_error.ParserError(
                  'name "%s" contains more than one "->"' % name)
        elif name.count(" -> ") == 1:
            st_name, st_target = name.split(' -> ')
        else:
            st_name, st_target = name, None
        stat_result = StatResult(
                      (st_mode, st_ino, st_dev, st_nlink, st_uid,
                       st_gid, st_size, st_atime, st_mtime, st_ctime) )
        stat_result._st_mtime_precision = st_mtime_precision
        stat_result._st_name = st_name
        stat_result._st_target = st_target
        return stat_result


class MSParser(Parser):
    """`Parser` class for MS-specific directory format."""

    def parse_line(self, line, time_shift=0.0):
        """
        Return a `StatResult` instance corresponding to the given
        text line from a FTP server which emits "Microsoft format"
        (see end of file).

        If the line can't be parsed, raise a `ParserError`.

        The parameter `time_shift` isn't used in this method but is
        listed for compatibilty with the base class.
        """
        try:
            date, time_, dir_or_size, name = line.split(None, 3)
        except ValueError:
            # "unpack list of wrong size"
            raise ftp_error.ParserError("line '%s' can't be parsed" % line )
        # st_mode
        #  Default to read access only; in fact, we can't tell.
        st_mode = 0400
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
        st_mtime = self.parse_ms_time(date, time_, time_shift)
        # st_ctime
        st_ctime = None
        stat_result = StatResult(
                      (st_mode, st_ino, st_dev, st_nlink, st_uid,
                       st_gid, st_size, st_atime, st_mtime, st_ctime) )
        # _st_name and _st_target
        stat_result._st_name = name
        stat_result._st_target = None
        # mtime precision in seconds
        stat_result._st_mtime_precision = 60
        return stat_result

#
# Stat'ing operations for files on an FTP server
#
class _Stat(object):
    """Methods for stat'ing directories, links and regular files."""

    def __init__(self, host):
        self._host = host
        self._path = host.path
        # Use the Unix directory parser by default
        self._parser = UnixParser()
        # Allow one chance to switch to another parser if the default
        #  doesn't work.
        self._allow_parser_switching = True
        # Cache only lstat results. `stat` works locally on `lstat` results.
        self._lstat_cache = ftp_stat_cache.StatCache()

    def _host_dir(self, path):
        """
        Return a list of lines, as fetched by FTP's `DIR` command,
        when applied to `path`.
        """
        return self._host._dir(path)

    def _real_listdir(self, path):
        """
        Return a list of directories, files etc. in the directory
        named `path`.

        If the directory listing from the server can't be parsed
        raise a `ParserError`.
        """
        # We _can't_ put this check into `FTPHost._dir`; see its docstring.
        path = self._path.abspath(path)
        # `listdir` should only be allowed for directories and links to them.
        if not self._path.isdir(path):
            raise ftp_error.PermanentError(
                  "550 %s: no such directory or wrong directory parser used" %
                  path)
        # Set up for `for` loop
        lines = self._host_dir(path)
        # Exit the method now if there aren't any files
        if lines == ['']:
            return []
        names = []
        for line in lines:
            if self._parser.ignores_line(line):
                continue
            # For `listdir`, we are interested in just the names,
            #  but we use the `time_shift` parameter to have the
            #  correct timestamp values in the cache.
            stat_result = self._parser.parse_line(line,
                                                  self._host.time_shift())
            loop_path = self._path.join(path, stat_result._st_name)
            self._lstat_cache[loop_path] = stat_result
            st_name = stat_result._st_name
            if st_name not in (self._host.curdir, self._host.pardir):
                names.append(st_name)
        return names

    def _real_lstat(self, path, _exception_for_missing_path=True):
        """
        Return an object similar to that returned by `os.lstat`.

        If the directory listing from the server can't be parsed,
        raise a `ParserError`. If the directory can be parsed and the
        `path` is not found, raise a `PermanentError`. That means that
        if the directory containing `path` can't be parsed we get a
        `ParserError`, independent on the presence of `path` on the
        server.

        (`_exception_for_missing_path` is an implementation aid and
        _not_ intended for use by ftputil clients.)
        """
        path = self._path.abspath(path)
        # If the path is in the cache, return the lstat result.
        if path in self._lstat_cache:
            return self._lstat_cache[path]
        # Note: (l)stat works by going one directory up and parsing
        #  the output of an FTP `DIR` command. Unfortunately, it is
        #  not possible to do this for the root directory `/`.
        if path == '/':
            raise ftp_error.RootDirError(
                  "can't stat remote root directory")
        dirname, basename = self._path.split(path)

        # If even the directory doesn't exist and we don't want the
        #  exception, treat it the same as if the path wasn't found in
        #  the directory's contents (compare below). The use of `isdir`
        #  here causes a recursion but that should be ok because that
        #  will at the latest stop when we've got to the root directory.
#         if not self._path.isdir(dirname) and not _exception_for_missing_path:
#             return None
        # Loop through all lines of the directory listing. We
        #  probably won't need all lines for the particular path but
        #  we want to collect as many stat results in the cache as
        #  possible.
        lstat_result_for_path = None
        lines = self._host_dir(dirname)
        for line in lines:
            if self._parser.ignores_line(line):
                continue
            stat_result = self._parser.parse_line(line,
                          self._host.time_shift())
            loop_path = self._path.join(dirname, stat_result._st_name)
            self._lstat_cache[loop_path] = stat_result
            # Needed to work without cache or with disabled cache
            if stat_result._st_name == basename:
                lstat_result_for_path = stat_result
        if lstat_result_for_path is not None:
            return lstat_result_for_path
        # Path was not found during the loop
        if _exception_for_missing_path:
            #TODO Use FTP DIR command on the file to implicitly use
            #  the usual status code of the server for missing files
            #  (450 vs. 550).
            raise ftp_error.PermanentError(
                  "550 %s: no such file or directory" % path)
        else:
            # Be explicit. Returning `None` is a signal for
            #  `_Path.exists/isfile/isdir/islink` that the path was
            #  not found. If we would raise an exception, there would
            #  be no distinction between a missing path or a more
            #  severe error in the code above.
            return None

    def _real_stat(self, path, _exception_for_missing_path=True):
        """
        Return info from a "stat" call on `path`.

        If the directory containing `path` can't be parsed, raise
        a `ParserError`. If the listing can be parsed but the
        `path` can't be found, raise a `PermanentError`. Also raise
        a `PermanentError` if there's an endless (cyclic) chain of
        symbolic links "behind" the `path`.

        (`_exception_for_missing_path` is an implementation aid and
        _not_ intended for use by ftputil clients.)
        """
        # Save for error message
        original_path = path
        # Most code in this method is used to detect recursive
        #  link structures.
        #TODO Now, as we require Python 2.4, we can use sets.
        visited_paths = {}
        while True:
            # Stat the link if it is one, else the file/directory.
            lstat_result = self._real_lstat(path, _exception_for_missing_path)
            if lstat_result is None:
                return None
            # If the file is not a link, the `stat` result is the
            #  same as the `lstat` result.
            if not stat.S_ISLNK(lstat_result.st_mode):
                return lstat_result
            # If we stat'ed a link, calculate a normalized path for
            #  the file the link points to.
            # We don't use `basename`
            # pylint: disable=W0612
            dirname, basename = self._path.split(path)
            path = self._path.join(dirname, lstat_result._st_target)
            path = self._path.abspath(self._path.normpath(path))
            # Check for cyclic structure
            if path in visited_paths:
                # We had seen this path already
                raise ftp_error.PermanentError(
                      "recursive link structure detected for remote path '%s'" %
                      original_path)
            # Remember the path we have encountered
            visited_paths[path] = True

    def __call_with_parser_retry(self, method, *args, **kwargs):
        """
        Call `method` with the `args` and `kwargs` once. If that
        results in a `ParserError` and only one parser has been
        used yet, try the other parser. If that still fails,
        propagate the `ParserError`.
        """
        # Do _not_ set `_allow_parser_switching` in a `finally` clause!
        #  This would cause a `PermanentError` due to a not-found
        #  file in an empty directory to finally establish the
        #  parser - which is wrong.
        try:
            result = method(*args, **kwargs)
            # If a `listdir` call didn't find anything, we can't
            #  say anything about the usefulness of the parser.
            if (method is not self._real_listdir) and result:
                self._allow_parser_switching = False
            return result
        except ftp_error.ParserError:
            if self._allow_parser_switching:
                self._allow_parser_switching = False
                self._parser = MSParser()
                return method(*args, **kwargs)
            else:
                raise

    def listdir(self, path):
        """
        Return a list of items in `path`.

        Raise a `PermanentError` if the path doesn't exist, but
        maybe raise other exceptions depending on the state of
        the server (e. g. timeout).
        """
        return self.__call_with_parser_retry(self._real_listdir, path)

    def lstat(self, path, _exception_for_missing_path=True):
        """
        Return a `StatResult` without following links.

        Raise a `PermanentError` if the path doesn't exist, but
        maybe raise other exceptions depending on the state of
        the server (e. g. timeout).
        """
        return self.__call_with_parser_retry(self._real_lstat, path,
                                             _exception_for_missing_path)

    def stat(self, path, _exception_for_missing_path=True):
        """
        Return a `StatResult` with following links.

        Raise a `PermanentError` if the path doesn't exist, but
        maybe raise other exceptions depending on the state of
        the server (e. g. timeout).
        """
        return self.__call_with_parser_retry(self._real_stat, path,
                                             _exception_for_missing_path)

