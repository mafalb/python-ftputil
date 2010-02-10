# Copyright (C) 2002-2009, Stefan Schwarzer
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
import random
import time
import unittest

import _mock_ftplib
import _test_base
import ftp_error
import ftp_stat
import ftputil


#
# helper functions to generate random data
#
def random_data(pool, size=10000):
    """
    Return a sequence of characters consisting of those from
    the pool of integer numbers.
    """
    character_list = []
    for i in range(size):
        ordinal = random.choice(pool)
        character_list.append(chr(ordinal))
    result = ''.join(character_list)
    return result

def ascii_data():
    """Return an ASCII character string."""
    pool = range(32, 128)
    pool.append(ord('\n'))
    return random_data(pool)

def binary_data():
    """Return a binary character string."""
    pool = range(0, 256)
    return random_data(pool)


#
# several customized `MockSession` classes
#
class FailOnLoginSession(_mock_ftplib.MockSession):
    def __init__(self, host='', user='', password=''):
        raise ftplib.error_perm

class RecursiveListingForDotAsPathSession(_mock_ftplib.MockSession):
    dir_contents = {
      ".": """\
lrwxrwxrwx   1 staff          7 Aug 13  2003 bin -> usr/bin

dev:
total 10

etc:
total 10

pub:
total 4
-rw-r--r--   1 staff         74 Sep 25  2000 .message
----------   1 staff          0 Aug 16  2003 .notar
drwxr-xr-x  12 ftp          512 Nov 23  2008 freeware

usr:
total 4""",

      "": """\
total 10
lrwxrwxrwx   1 staff          7 Aug 13  2003 bin -> usr/bin
d--x--x--x   2 staff        512 Sep 24  2000 dev
d--x--x--x   3 staff        512 Sep 25  2000 etc
dr-xr-xr-x   3 staff        512 Oct  3  2000 pub
d--x--x--x   5 staff        512 Oct  3  2000 usr"""}

    def _transform_path(self, path):
        return path

class BinaryDownloadMockSession(_mock_ftplib.MockSession):
    mock_file_content = binary_data()

class TimeShiftMockSession(_mock_ftplib.MockSession):
    def delete(self, file_name):
        pass

#
# customized `FTPHost` class for conditional upload/download tests
#  and time shift tests
#
class FailingUploadAndDownloadFTPHost(ftputil.FTPHost):
    def upload(self, source, target, mode=''):
        assert False, "`FTPHost.upload` should not have been called"

    def download(self, source, target, mode=''):
        assert False, "`FTPHost.download` should not have been called"

class TimeShiftFTPHost(ftputil.FTPHost):
    class _Path:
        def split(self, path):
            return posixpath.split(path)
        def set_mtime(self, mtime):
            self._mtime = mtime
        def getmtime(self, file_name):
            return self._mtime
        def join(self, *args):
            return posixpath.join(*args)
        def normpath(self, path):
            return posixpath.normpath(path)
        def abspath(self, path):
            return "/home/sschwarzer/_ftputil_sync_"
        # needed for `isdir` in `FTPHost.remove`
        def isfile(self, path):
            return True

    def __init__(self, *args, **kwargs):
        ftputil.FTPHost.__init__(self, *args, **kwargs)
        self.path = self._Path()

#
# test cases
#
class TestOpenAndClose(unittest.TestCase):
    """Test opening and closing of `FTPHost` objects."""
    def test_open_and_close(self):
        """Test closing of `FTPHost`."""
        host = _test_base.ftp_host_factory()
        host.close()
        self.assertEqual(host.closed, True)
        self.assertEqual(host._children, [])


class TestLogin(unittest.TestCase):
    def test_invalid_login(self):
        """Login to invalid host must fail."""
        self.assertRaises(ftp_error.FTPOSError, _test_base.ftp_host_factory,
                          FailOnLoginSession)


class TestSetParser(unittest.TestCase):
    def test_set_parser(self):
        """Test if the selected parser is used."""
        # this test isn't very practical but should help at least a bit ...
        host = _test_base.ftp_host_factory()
        # implicitly fix at Unix format
        files = host.listdir("/home/sschwarzer")
        self.assertEqual(files, ['chemeng', 'download', 'image', 'index.html',
          'os2', 'osup', 'publications', 'python', 'scios2'])
        host.set_parser(ftp_stat.MSParser())
        files = host.listdir("/home/msformat/XPLaunch")
        self.assertEqual(files, ['WindowsXP', 'XPLaunch', 'empty',
                                 'abcd.exe', 'O2KKeys.exe'])
        self.assertEqual(host._stat._allow_parser_switching, False)


class TestCommandNotImplementedError(unittest.TestCase):
    def test_command_not_implemented_error(self):
        """
        Test if we get the anticipated exception if a command isn't
        implemented by the server.
        """
        host = _test_base.ftp_host_factory()
        self.assertRaises(ftp_error.PermanentError,
                          host.chmod, "nonexistent", 0644)
        # `CommandNotImplementedError` is a subclass of `PermanentError`
        self.assertRaises(ftp_error.CommandNotImplementedError,
                          host.chmod, "nonexistent", 0644)


class TestRecursiveListingForDotAsPath(unittest.TestCase):
    """Return a recursive directory listing when the path to list
    is a dot. This is used to test for issue #33, see
    http://ftputil.sschwarzer.net/trac/ticket/33 .
    """
    def test_recursive_listing(self):
        host = _test_base.ftp_host_factory(
                 session_factory=RecursiveListingForDotAsPathSession)
        lines = host._dir(host.curdir)
        self.assertEqual(lines[0], "total 10")
        self.failUnless(lines[1].startswith("lrwxrwxrwx   1 staff"))
        self.failUnless(lines[2].startswith("d--x--x--x   2 staff"))
        host.close()

    def test_plain_listing(self):
        host = _test_base.ftp_host_factory(
                 session_factory=RecursiveListingForDotAsPathSession)
        lines = host._dir("")
        self.assertEqual(lines[0], "total 10")
        self.failUnless(lines[1].startswith("lrwxrwxrwx   1 staff"))
        self.failUnless(lines[2].startswith("d--x--x--x   2 staff"))
        host.close()

    def test_empty_string_instead_of_dot_workaround(self):
        host = _test_base.ftp_host_factory(
                 session_factory=RecursiveListingForDotAsPathSession)
        files = host.listdir(host.curdir)
        self.assertEqual(files, ['bin', 'dev', 'etc', 'pub', 'usr'])
        host.close()


class TestUploadAndDownload(unittest.TestCase):
    """Test ASCII upload and binary download as examples."""

    def generate_ascii_file(self, data, filename):
        """Generate an ASCII data file."""
        source_file = open(filename, 'w')
        source_file.write(data)
        source_file.close()

    def test_ascii_upload(self):
        """Test ASCII mode upload."""
        local_source = '__test_source'
        data = ascii_data()
        self.generate_ascii_file(data, local_source)
        # upload
        host = _test_base.ftp_host_factory()
        host.upload(local_source, 'dummy')
        # check uploaded content
        # the data which was uploaded has its line endings converted
        #  so the conversion must also be applied to `data`
        data = data.replace('\n', '\r\n')
        remote_file_content = _mock_ftplib.content_of('dummy')
        self.assertEqual(data, remote_file_content)
        # clean up
        os.unlink(local_source)

    def test_binary_download(self):
        """Test binary mode download."""
        local_target = '__test_target'
        host = _test_base.ftp_host_factory(
               session_factory=BinaryDownloadMockSession)
        # download
        host.download('dummy', local_target, 'b')
        # read file and compare
        data = open(local_target, 'rb').read()
        remote_file_content = _mock_ftplib.content_of('dummy')
        self.assertEqual(data, remote_file_content)
        # clean up
        os.unlink(local_target)

    def test_conditional_upload(self):
        """Test conditional ASCII mode upload."""
        local_source = '__test_source'
        data = ascii_data()
        self.generate_ascii_file(data, local_source)
        # target is newer, so don't upload
        host = _test_base.ftp_host_factory(
               ftp_host_class=FailingUploadAndDownloadFTPHost)
        flag = host.upload_if_newer(local_source, '/home/newer')
        self.assertEqual(flag, False)
        # target is older, so upload
        host = _test_base.ftp_host_factory()
        flag = host.upload_if_newer(local_source, '/home/older')
        self.assertEqual(flag, True)
        # check uploaded content
        # the data which was uploaded has its line endings converted
        #  so the conversion must also be applied to 'data'
        data = data.replace('\n', '\r\n')
        remote_file_content = _mock_ftplib.content_of('older')
        self.assertEqual(data, remote_file_content)
        # target doesn't exist, so upload
        host = _test_base.ftp_host_factory()
        flag = host.upload_if_newer(local_source, '/home/notthere')
        self.assertEqual(flag, True)
        remote_file_content = _mock_ftplib.content_of('notthere')
        self.assertEqual(data, remote_file_content)
        # clean up
        os.unlink(local_source)

    def compare_and_delete_downloaded_data(self, filename):
        """Compare content of downloaded file with its source, then
        delete the local target file."""
        data = open(filename, 'rb').read()
        remote_file_content = _mock_ftplib.content_of('newer')
        self.assertEqual(data, remote_file_content)
        # clean up
        os.unlink(filename)

    def test_conditional_download_without_target(self):
        "Test conditional binary mode download when no target file exists."
        local_target = '__test_target'
        # target does not exist, so download
        host = _test_base.ftp_host_factory(
               session_factory=BinaryDownloadMockSession)
        flag = host.download_if_newer('/home/newer', local_target, 'b')
        self.assertEqual(flag, True)
        self.compare_and_delete_downloaded_data(local_target)

    def test_conditional_download_with_older_target(self):
        """Test conditional binary mode download with newer source file."""
        local_target = '__test_target'
        # make target file
        open(local_target, 'w').close()
        # source is newer, so download
        host = _test_base.ftp_host_factory(
               session_factory=BinaryDownloadMockSession)
        flag = host.download_if_newer('/home/newer', local_target, 'b')
        self.assertEqual(flag, True)
        self.compare_and_delete_downloaded_data(local_target)

    def test_conditional_download_with_newer_target(self):
        """Test conditional binary mode download with older source file."""
        local_target = '__test_target'
        # make target file
        open(local_target, 'w').close()
        # source is older, so don't download
        host = _test_base.ftp_host_factory(
               session_factory=BinaryDownloadMockSession)
        host = _test_base.ftp_host_factory(
               ftp_host_class=FailingUploadAndDownloadFTPHost,
               session_factory=BinaryDownloadMockSession)
        flag = host.download_if_newer('/home/older', local_target, 'b')
        self.assertEqual(flag, False)
        # remove target file
        os.unlink(local_target)


class TestTimeShift(unittest.TestCase):
    def test_rounded_time_shift(self):
        """Test if time shift is rounded correctly."""
        host = _test_base.ftp_host_factory(session_factory=TimeShiftMockSession)
        # use private bound method
        rounded_time_shift = host._FTPHost__rounded_time_shift
        # pairs consisting of original value and expected result
        test_data = [
          (0, 0), (0.1, 0), (-0.1, 0), (1500, 0), (-1500, 0),
          (1800, 3600), (-1800, -3600), (2000, 3600), (-2000, -3600),
          (5*3600-100, 5*3600), (-5*3600+100, -5*3600)]
        for time_shift, expected_time_shift in test_data:
            calculated_time_shift = rounded_time_shift(time_shift)
            self.assertEqual(calculated_time_shift, expected_time_shift)

    def test_assert_valid_time_shift(self):
        """Test time shift sanity checks."""
        host = _test_base.ftp_host_factory(session_factory=TimeShiftMockSession)
        # use private bound method
        assert_time_shift = host._FTPHost__assert_valid_time_shift
        # valid time shifts
        test_data = [23*3600, -23*3600, 3600+30, -3600+30]
        for time_shift in test_data:
            self.failUnless(assert_time_shift(time_shift) is None)
        # invalid time shift (exceeds one day)
        self.assertRaises(ftp_error.TimeShiftError, assert_time_shift, 25*3600)
        self.assertRaises(ftp_error.TimeShiftError, assert_time_shift, -25*3600)
        # invalid time shift (deviation from full hours unacceptable)
        self.assertRaises(ftp_error.TimeShiftError, assert_time_shift, 10*60)
        self.assertRaises(ftp_error.TimeShiftError, assert_time_shift,
                          -3600-10*60)

    def test_synchronize_times(self):
        """Test time synchronization with server."""
        host = _test_base.ftp_host_factory(ftp_host_class=TimeShiftFTPHost,
               session_factory=TimeShiftMockSession)
        # valid time shift
        host.path.set_mtime(time.time() + 3630)
        host.synchronize_times()
        self.assertEqual(host.time_shift(), 3600)
        # invalid time shift
        host.path.set_mtime(time.time() + 3600+10*60)
        self.assertRaises(ftp_error.TimeShiftError, host.synchronize_times)


if __name__ == '__main__':
    unittest.main()

