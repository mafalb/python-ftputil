# Copyright (C) 2003-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

from __future__ import division

import stat
import time
import unittest

import ftp_error
import ftp_stat
import ftputil

import test_base


def test_stat():
    host = test_base.ftp_host_factory()
    stat = ftp_stat._Stat(host)
    # use Unix format parser explicitly
    stat._parser = ftp_stat.UnixParser()
    return stat

def stat_tuple_to_seconds(t):
    """
    Return a float number representing the local time associated with
    the six-element tuple `t`.
    """
    assert len(t) == 6, \
           "need a six-element tuple (year, month, day, hour, min, sec)"
    return time.mktime(t + (0, 0, -1))


class TestParsers(unittest.TestCase):

    def _test_valid_lines(self, parser_class, lines, expected_stat_results):
        parser = parser_class()
        for line, expected_stat_result in zip(lines, expected_stat_results):
            # Convert to list to compare with the list `expected_stat_results`
            parse_result = parser.parse_line(line)
            stat_result = list(parse_result) + [parse_result._st_name,
                                                parse_result._st_target]
            # Convert time tuple to seconds
            expected_stat_result[8] = \
              stat_tuple_to_seconds(expected_stat_result[8])
            # Compare both lists
            self.assertEqual(stat_result, expected_stat_result)

    def _test_invalid_lines(self, parser_class, lines):
        parser = parser_class()
        for line in lines:
            self.assertRaises(ftp_error.ParserError, parser.parse_line, line)

    def _expected_year(self):
        """
        Return the expected year for the second line in the
        listing in `test_valid_unix_lines`.
        """
        # If in this year it's after Dec 19, 23:11, use the current
        #  year, else use the previous year ...
        now = time.localtime()
        # We need only month, day, hour and minute
        current_time_parts = now[1:5]
        time_parts_in_listing = (12, 19, 23, 11)
        if current_time_parts > time_parts_in_listing:
            return now[0]
        else:
            return now[0] - 1

    def test_valid_unix_lines(self):
        lines = [
          "drwxr-sr-x   2 45854    200           512 May  4  2000 "
            "chemeng link -> chemeng target",
          # The year value for this line will change with the actual time.
          "-rw-r--r--   1 45854    200          4604 Dec 19 23:11 index.html",
          "drwxr-sr-x   2 45854    200           512 May 29  2000 os2",
          "lrwxrwxrwx   2 45854    200           512 May 29  2000 osup -> "
                                                                  "../os2"
          ]
        expected_stat_results = [
          [17901, None, None, 2, '45854', '200', 512, None,
           (2000, 5, 4, 0, 0, 0), None, "chemeng link", "chemeng target"],
          [33188, None, None, 1, '45854', '200', 4604, None,
           (self._expected_year(), 12, 19, 23, 11, 0), None,
           "index.html", None],
          [17901, None, None, 2, '45854', '200', 512, None,
           (2000, 5, 29, 0, 0, 0), None, "os2", None],
          [41471, None, None, 2, '45854', '200', 512, None,
           (2000, 5, 29, 0, 0, 0), None, "osup", "../os2"]
          ]
        self._test_valid_lines(ftp_stat.UnixParser, lines,
                               expected_stat_results)

    def test_invalid_unix_lines(self):
        lines = [
          "total 14",
          "drwxr-sr-    2 45854    200           512 May  4  2000 chemeng",
          "xrwxr-sr-x   2 45854    200           512 May  4  2000 chemeng",
          "xrwxr-sr-x   2 45854    200           51x May  4  2000 chemeng",
          "drwxr-sr-x   2 45854    200           512 May 29  2000 "
            "os1 -> os2 -> os3",
          ]
        self._test_invalid_lines(ftp_stat.UnixParser, lines)

    def test_alternative_unix_format(self):
        # See http://ftputil.sschwarzer.net/trac/ticket/12 for a
        #  description for the need for an alternative format.
        lines = [
          "drwxr-sr-x   2   200           512 May  4  2000 "
            "chemeng link -> chemeng target",
          # The year value for this line will change with the actual time.
          "-rw-r--r--   1   200          4604 Dec 19 23:11 index.html",
          "drwxr-sr-x   2   200           512 May 29  2000 os2",
          "lrwxrwxrwx   2   200           512 May 29  2000 osup -> ../os2"
          ]
        expected_stat_results = [
          [17901, None, None, 2, None, '200', 512, None,
           (2000, 5, 4, 0, 0, 0), None, "chemeng link", "chemeng target"],
          [33188, None, None, 1, None, '200', 4604, None,
           (self._expected_year(), 12, 19, 23, 11, 0), None,
           "index.html", None],
          [17901, None, None, 2, None, '200', 512, None,
           (2000, 5, 29, 0, 0, 0), None, "os2", None],
          [41471, None, None, 2, None, '200', 512, None,
           (2000, 5, 29, 0, 0, 0), None, "osup", "../os2"]
          ]
        self._test_valid_lines(ftp_stat.UnixParser, lines,
                               expected_stat_results)

    def test_valid_ms_lines(self):
        lines = [
          "07-27-01  11:16AM       <DIR>          Test",
          "10-23-95  03:25PM       <DIR>          WindowsXP",
          "07-17-00  02:08PM             12266720 test.exe",
          "07-17-09  12:08AM             12266720 test.exe",
          "07-17-09  12:08PM             12266720 test.exe"
          ]
        expected_stat_results = [
          [16640, None, None, None, None, None, None, None,
           (2001, 7, 27, 11, 16, 0), None, "Test", None],
          [16640, None, None, None, None, None, None, None,
           (1995, 10, 23, 15, 25, 0), None, "WindowsXP", None],
          [33024, None, None, None, None, None, 12266720, None,
           (2000, 7, 17, 14, 8, 0), None, "test.exe", None],
          [33024, None, None, None, None, None, 12266720, None,
           (2009, 7, 17, 0, 8, 0), None, "test.exe", None],
          [33024, None, None, None, None, None, 12266720, None,
           (2009, 7, 17, 12, 8, 0), None, "test.exe", None]
          ]
        self._test_valid_lines(ftp_stat.MSParser, lines, expected_stat_results)

    def test_invalid_ms_lines(self):
        lines = [
          "07-27-01  11:16AM                      Test",
          "07-17-00  02:08             12266720 test.exe",
          "07-17-00  02:08AM           1226672x test.exe"
          ]
        self._test_invalid_lines(ftp_stat.MSParser, lines)

    #
    # The following code checks if the decision logic in the Unix
    #  line parser for determining the year works.
    #
    def datetime_string(self, time_float):
        """
        Return a datetime string generated from the value in
        `time_float`. The parameter value is a floating point value
        as returned by `time.time()`. The returned string is built as
        if it were from a Unix FTP server (format: MMM dd hh:mm")
        """
        time_tuple = time.localtime(time_float)
        return time.strftime("%b %d %H:%M", time_tuple)

    def dir_line(self, time_float):
        """
        Return a directory line as from a Unix FTP server. Most of
        the contents are fixed, but the timestamp is made from
        `time_float` (seconds since the epoch, as from `time.time()`).
        """
        line_template = "-rw-r--r--   1   45854   200   4604   %s   index.html"
        return line_template % self.datetime_string(time_float)

    def assert_equal_times(self, time1, time2):
        """
        Check if both times (seconds since the epoch) are equal. For
        the purpose of this test, two times are "equal" if they
        differ no more than one minute from each other.

        If the test fails, an exception is raised by the inherited
        `failIf` method.
        """
        abs_difference = abs(time1 - time2)
        try:
            self.failIf(abs_difference > 60.0)
        except AssertionError:
            print "Difference is", abs_difference, "seconds"
            raise

    def _test_time_shift(self, supposed_time_shift, deviation=0.0):
        """
        Check if the stat parser considers the time shift value
        correctly. `deviation` is the difference between the actual
        time shift and the supposed time shift, which is rounded
        to full hours.
        """
        host = test_base.ftp_host_factory()
        # Explicitly use Unix format parser
        host._stat._parser = ftp_stat.UnixParser()
        host.set_time_shift(supposed_time_shift)
        server_time = time.time() + supposed_time_shift + deviation
        stat_result = host._stat._parser.parse_line(self.dir_line(server_time),
                                                    host.time_shift())
        self.assert_equal_times(stat_result.st_mtime, server_time)

    def test_time_shifts(self):
        """Test correct year depending on time shift value."""
        # 1. test: Client and server share the same local time
        self._test_time_shift(0.0)
        # 2. test: Server is three hours ahead of client
        self._test_time_shift(3 * 60 * 60)
        # 3. test: Client is three hours ahead of server
        self._test_time_shift(- 3 * 60 * 60)
        # 4. test: Server is supposed to be three hours ahead, but
        #  is ahead three hours and one minute
        self._test_time_shift(3 * 60 * 60, 60)
        # 5. test: Server is supposed to be three hours ahead, but
        #  is ahead three hours minus one minute
        self._test_time_shift(3 * 60 * 60, -60)
        # 6. test: Client is supposed to be three hours ahead, but
        #  is ahead three hours and one minute
        self._test_time_shift(-3 * 60 * 60, -60)
        # 7. test: Client is supposed to be three hours ahead, but
        #  is ahead three hours minus one minute
        self._test_time_shift(-3 * 60 * 60, 60)


class TestLstatAndStat(unittest.TestCase):
    """
    Test `FTPHost.lstat` and `FTPHost.stat` (test currently only
    implemented for Unix server format).
    """
    def setUp(self):
        self.stat = test_stat()

    def test_failing_lstat(self):
        """Test whether lstat fails for a nonexistent path."""
        self.assertRaises(ftp_error.PermanentError, self.stat.lstat,
                          '/home/sschw/notthere')
        self.assertRaises(ftp_error.PermanentError, self.stat.lstat,
                          '/home/sschwarzer/notthere')

    def test_lstat_for_root(self):
        """Test `lstat` for `/` .
        Note: `(l)stat` works by going one directory up and parsing
        the output of an FTP `DIR` command. Unfortunately, it's not
        possible to do this for the root directory `/`.
        """
        self.assertRaises(ftp_error.RootDirError, self.stat.lstat, '/')
        try:
            self.stat.lstat('/')
        except ftp_error.RootDirError, exc_obj:
            self.failIf(isinstance(exc_obj, ftp_error.FTPOSError))

    def test_lstat_one_unix_file(self):
        """Test `lstat` for a file described in Unix-style format."""
        stat_result = self.stat.lstat('/home/sschwarzer/index.html')
        self.assertEqual(oct(stat_result.st_mode), '0100644')
        self.assertEqual(stat_result.st_size, 4604)
        self.assertEqual(stat_result._st_mtime_precision, 60)

    def test_lstat_one_ms_file(self):
        """Test `lstat` for a file described in DOS-style format."""
        stat_result = self.stat.lstat('/home/msformat/abcd.exe')
        self.assertEqual(stat_result._st_mtime_precision, 60)

    def test_lstat_one_unix_dir(self):
        """Test `lstat` for a directory described in Unix-style format."""
        stat_result = self.stat.lstat('/home/sschwarzer/scios2')
        self.assertEqual(oct(stat_result.st_mode), '042755')
        self.assertEqual(stat_result.st_ino, None)
        self.assertEqual(stat_result.st_dev, None)
        self.assertEqual(stat_result.st_nlink, 6)
        self.assertEqual(stat_result.st_uid, '45854')
        self.assertEqual(stat_result.st_gid, '200')
        self.assertEqual(stat_result.st_size, 512)
        self.assertEqual(stat_result.st_atime, None)
        self.failUnless(stat_result.st_mtime ==
                        stat_tuple_to_seconds((1999, 9, 20, 0, 0, 0)))
        self.assertEqual(stat_result.st_ctime, None)
        self.assertEqual(stat_result._st_mtime_precision, 24*60*60)
        self.failUnless(stat_result ==
          (17901, None, None, 6, '45854', '200', 512, None,
           stat_tuple_to_seconds((1999, 9, 20, 0, 0, 0)), None))

    def test_lstat_one_ms_dir(self):
        """Test `lstat` for a directory described in DOS-style format."""
        stat_result = self.stat.lstat('/home/msformat/WindowsXP')
        self.assertEqual(stat_result._st_mtime_precision, 60)

    def test_lstat_via_stat_module(self):
        """Test `lstat` indirectly via `stat` module."""
        stat_result = self.stat.lstat('/home/sschwarzer/')
        self.failUnless(stat.S_ISDIR(stat_result.st_mode))

    def test_stat_following_link(self):
        """Test `stat` when invoked on a link."""
        # Simple link
        stat_result = self.stat.stat('/home/link')
        self.assertEqual(stat_result.st_size, 4604)
        # Link pointing to a link
        stat_result = self.stat.stat('/home/python/link_link')
        self.assertEqual(stat_result.st_size, 4604)
        stat_result = self.stat.stat('../python/link_link')
        self.assertEqual(stat_result.st_size, 4604)
        # Recursive link structures
        self.assertRaises(ftp_error.PermanentError, self.stat.stat,
                          '../python/bad_link')
        self.assertRaises(ftp_error.PermanentError, self.stat.stat,
                          '/home/bad_link')

    #
    # Test automatic switching of Unix/MS parsers
    #
    def test_parser_switching_with_permanent_error(self):
        """Test non-switching of parser format with `PermanentError`."""
        self.assertEqual(self.stat._allow_parser_switching, True)
        # With these directory contents, we get a `ParserError` for
        #  the Unix parser, so `_allow_parser_switching` can be
        #  switched off no matter whether we got a `PermanentError`
        #  or not.
        self.assertRaises(ftp_error.PermanentError, self.stat.lstat,
                          "/home/msformat/nonexistent")
        self.assertEqual(self.stat._allow_parser_switching, False)

    def test_parser_switching_default_to_unix(self):
        """Test non-switching of parser format; stay with Unix."""
        self.assertEqual(self.stat._allow_parser_switching, True)
        self.failUnless(isinstance(self.stat._parser, ftp_stat.UnixParser))
        stat_result = self.stat.lstat("/home/sschwarzer/index.html")
        self.failUnless(isinstance(self.stat._parser, ftp_stat.UnixParser))
        self.assertEqual(self.stat._allow_parser_switching, False)

    def test_parser_switching_to_ms(self):
        """Test switching of parser from Unix to MS format."""
        self.assertEqual(self.stat._allow_parser_switching, True)
        self.failUnless(isinstance(self.stat._parser, ftp_stat.UnixParser))
        stat_result = self.stat.lstat("/home/msformat/abcd.exe")
        self.failUnless(isinstance(self.stat._parser, ftp_stat.MSParser))
        self.assertEqual(self.stat._allow_parser_switching, False)
        self.assertEqual(stat_result._st_name, "abcd.exe")
        self.assertEqual(stat_result.st_size, 12266720)

    def test_parser_switching_regarding_empty_dir(self):
        """Test switching of parser if a directory is empty."""
        self.assertEqual(self.stat._allow_parser_switching, True)
        result = self.stat.listdir("/home/msformat/XPLaunch/empty")
        self.assertEqual(result, [])
        self.assertEqual(self.stat._allow_parser_switching, True)
        self.failUnless(isinstance(self.stat._parser, ftp_stat.UnixParser))


class TestListdir(unittest.TestCase):
    """Test `FTPHost.listdir`."""
    def setUp(self):
        self.stat = test_stat()

    def test_failing_listdir(self):
        """Test failing `FTPHost.listdir`."""
        self.assertRaises(ftp_error.PermanentError,
                          self.stat.listdir, 'notthere')

    def test_succeeding_listdir(self):
        """Test succeeding `FTPHost.listdir`."""
        # Do we have all expected "files"?
        self.assertEqual(len(self.stat.listdir('.')), 9)
        # Have they the expected names?
        expected = ('chemeng download image index.html os2 '
                    'osup publications python scios2').split()
        remote_file_list = self.stat.listdir('.')
        for file in expected:
            self.failUnless(file in remote_file_list)


if __name__ == '__main__':
    unittest.main()

