# Copyright (C) 2003, Stefan Schwarzer
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

# $Id: _test_ftp_stat.py,v 1.11 2003/12/30 20:45:00 schwa Exp $

import stat
import time
import unittest

import _test_base
import ftp_error
import ftp_stat
import ftputil


def test_stat():
    host = _test_base.ftp_host_factory()
    stat = ftp_stat._UnixStat(host)
    return stat

def time_offset():
    """
    Return the difference between local time and GMT as a number
    of seconds, rounded to full hours.
    """
    local_time, gm_time = time.localtime(), time.gmtime()
    offset = time.mktime(local_time) - time.mktime(gm_time)
    # round to full hours
    hour = 60 * 60
    return (offset + hour//2) // hour * hour
        

class TestStatParsers(unittest.TestCase):
    def _test_valid_lines(self, parser_class, lines, expected_stat_results):
        parser = parser_class(_test_base.ftp_host_factory())
        for line, expected_stat_result in zip(lines, expected_stat_results):
            stat_result = parser.parse_line(line)
            self.assertEqual(stat_result, expected_stat_result)

    def _test_invalid_lines(self, parser_class, lines):
        parser = parser_class(_test_base.ftp_host_factory())
        for line in lines:
            self.assertRaises(ftp_error.ParserError, parser.parse_line, line)

    def test_valid_unix_lines(self):
        lines = [
          "drwxr-sr-x   2 45854    200           512 May  4  2000 chemeng",
          # the results for this line will change with the actual time
          "-rw-r--r--   1 45854    200          4604 Jan 19 23:11 index.html",
          "drwxr-sr-x   2 45854    200           512 May 29  2000 os2",
          "lrwxrwxrwx   2 45854    200           512 May 29  2000 osup -> "
                                                                  "../os2"
          ]
        o = time_offset()
        expected_stat_results = [
          (17901, None, None, 2, '45854', '200', 512, None, 957387600+o, None),
          (33188, None, None, 1, '45854', '200', 4604, None, 1043010660+o,
           None),
          (17901, None, None, 2, '45854', '200', 512, None, 959547600+o, None),
          (41471, None, None, 2, '45854', '200', 512, None, 959547600+o, None)
          ]
        self._test_valid_lines(ftp_stat._UnixStat, lines, expected_stat_results)

    def test_invalid_unix_lines(self):
        lines = [
          "total 14",
          "drwxr-sr-    2 45854    200           512 May  4  2000 chemeng",
          "xrwxr-sr-x   2 45854    200           512 May  4  2000 chemeng",
          "xrwxr-sr-x   2 45854    200           51x May  4  2000 chemeng",
          "drwxr-sr-x     45854    200           512 May  4  2000 chemeng"
          ]
        self._test_invalid_lines(ftp_stat._UnixStat, lines)

    def test_valid_ms_lines(self):
        lines = [
          "07-27-01  11:16AM       <DIR>          Test",
          "10-23-95  03:25PM       <DIR>          WindowsXP",
          "07-17-00  02:08PM             12266720 test.exe"
          ]
        o = time_offset()
        expected_stat_results = [
          (16640, None, None, None, None, None, None, None, 996221760+o, None),
          (16640, None, None, None, None, None, None, None, 814454700+o, None),
          (33024, None, None, None, None, None, 12266720, None, 963832080+o,
           None)
          ]
        self._test_valid_lines(ftp_stat._MSStat, lines, expected_stat_results)

    def test_invalid_ms_lines(self):
        lines = [
          "07-27-01  11:16AM                      Test",
          "07-17-00  02:08             12266720 test.exe",
          "07-17-00  02:08AM           1226672x test.exe"
          ]
        self._test_invalid_lines(ftp_stat._MSStat, lines)

    #
    # the following code checks if the decision logic in the Unix
    #  line parser for determining the year works
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
        parser = ftp_stat._UnixStat(_test_base.ftp_host_factory())
        parser._host.set_time_shift(supposed_time_shift)
        server_time = time.time() + supposed_time_shift + deviation
        stat_result = parser.parse_line(self.dir_line(server_time))
        self.assert_equal_times(stat_result.st_mtime, server_time)

    def test_time_shifts(self):
        """Test correct year depending on time shift value."""
        # 1. test: client and server share the same local time
        self._test_time_shift(0.0)
        # 2. test: server is three hours ahead of client
        self._test_time_shift(3 * 60 * 60)
        # 3. test: client is three hours ahead of server
        self._test_time_shift(- 3 * 60 * 60)
        # 4. test: server is supposed to be three hours ahead, but
        #  is ahead three hours and one minute
        self._test_time_shift(3 * 60 * 60, 60)
        # 5. test: server is supposed to be three hours ahead, but
        #  is ahead three hours minus one minute
        self._test_time_shift(3 * 60 * 60, -60)
        # 6. test: client is supposed to be three hours ahead, but
        #  is ahead three hours and one minute
        self._test_time_shift(-3 * 60 * 60, -60)
        # 7. test: client is supposed to be three hours ahead, but
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
        self.assertRaises(ftputil.PermanentError, self.stat.lstat,
                          '/home/sschw/notthere')
        self.assertRaises(ftputil.PermanentError, self.stat.lstat,
                          '/home/sschwarzer/notthere')

    def test_lstat_for_root(self):
        """Test `lstat` for `/` .
        Note: `(l)stat` works by going one directory up and parsing
        the output of an FTP `DIR` command. Unfortunately, it is not
        possible to to this for the root directory `/`.
        """
        self.assertRaises(ftputil.RootDirError, self.stat.lstat, '/')
        try:
            self.stat.lstat('/')
        except ftputil.RootDirError, exc_obj:
            self.failIf(isinstance(exc_obj, ftputil.FTPOSError))

    def test_lstat_one_file(self):
        """Test `lstat` for a file."""
        stat_result = self.stat.lstat('/home/sschwarzer/index.html')
        self.assertEqual(oct(stat_result.st_mode), '0100644')
        self.assertEqual(stat_result.st_size, 4604)

    def test_lstat_one_dir(self):
        """Test `lstat` for a directory."""
        stat_result = self.stat.lstat('/home/sschwarzer/scios2')
        self.assertEqual(oct(stat_result.st_mode), '042755')
        self.assertEqual(stat_result.st_ino, None)
        self.assertEqual(stat_result.st_dev, None)
        self.assertEqual(stat_result.st_nlink, 6)
        self.assertEqual(stat_result.st_uid, '45854')
        self.assertEqual(stat_result.st_gid, '200')
        self.assertEqual(stat_result.st_size, 512)
        self.assertEqual(stat_result.st_atime, None)
        o = time_offset()
        self.failUnless(stat_result.st_mtime == 937774800+o)
        self.assertEqual(stat_result.st_ctime, None)
        self.failUnless(stat_result == (17901, None, None, 6, '45854', '200',
                                        512, None, 937774800+o, None))

    def test_lstat_via_stat_module(self):
        """Test `lstat` indirectly via `stat` module."""
        stat_result = self.stat.lstat('/home/sschwarzer/')
        self.failUnless(stat.S_ISDIR(stat_result.st_mode))

    def test_stat_following_link(self):
        """Test `stat` when invoked on a link."""
        # simple link
        stat_result = self.stat.stat('/home/link')
        self.assertEqual(stat_result.st_size, 4604)
        # link pointing to a link
        stat_result = self.stat.stat('/home/python/link_link')
        self.assertEqual(stat_result.st_size, 4604)
        stat_result = self.stat.stat('../python/link_link')
        self.assertEqual(stat_result.st_size, 4604)
        # recursive link structures
        self.assertRaises(ftputil.PermanentError, self.stat.stat,
                          '../python/bad_link')
        self.assertRaises(ftputil.PermanentError, self.stat.stat,
                          '/home/bad_link')


class TestListdir(unittest.TestCase):
    """Test `FTPHost.listdir`."""
    def setUp(self):
        self.stat = test_stat()

    def test_failing_listdir(self):
        """Test failing `FTPHost.listdir`."""
        self.assertRaises(ftputil.PermanentError, self.stat.listdir, 'notthere')

    def test_succeeding_listdir(self):
        """Test succeeding `FTPHost.listdir`."""
        # do we have all expected "files"?
        self.assertEqual(len(self.stat.listdir('.')), 9)
        # have they the expected names?
        expected = ('chemeng download image index.html os2 '
                    'osup publications python scios2').split()
        remote_file_list = self.stat.listdir('.')
        for file in expected:
            self.failUnless(file in remote_file_list)


if __name__ == '__main__':
    unittest.main()

