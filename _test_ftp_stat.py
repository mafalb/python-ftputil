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

# $Id: _test_ftp_stat.py,v 1.3 2003/06/09 18:16:45 schwa Exp $

import unittest

import ftp_error
import ftp_stat


class TestStatParsers(unittest.TestCase):
    def _test_valid_lines(self, parser_class, lines, expected_stat_results):
        # no `FTPHost` is needed for these tests, so set it to `None`
        parser = parser_class(None)
        for line, expected_stat_result in zip(lines, expected_stat_results):
            stat_result = parser.parse_line(line)
            self.assertEqual(stat_result, expected_stat_result)

    def _test_invalid_lines(self, parser_class, lines):
        # no `FTPHost` is needed for these tests, so set it to `None`
        parser = parser_class(None)
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
        expected_stat_results = [
          (17901, None, None, 2, '45854', '200', 512, None, 957391200.0, None),
          (33188, None, None, 1, '45854', '200', 4604, None, 1043014260.0,
           None),
          (17901, None, None, 2, '45854', '200', 512, None, 959551200.0, None),
          (41471, None, None, 2, '45854', '200', 512, None, 959551200.0, None)
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
        expected_stat_results = [
          (16640, None, None, None, None, None, None, None, 996225360.0, None),
          (16640, None, None, None, None, None, None, None, 814458300.0, None),
          (33024, None, None, None, None, None, 12266720, None, 963835680.0,
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


if __name__ == '__main__':
    unittest.main()

