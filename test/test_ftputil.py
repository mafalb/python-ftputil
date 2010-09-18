# Copyright (C) 2002-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

import ftplib
import os
import posixpath
import random
import time
import unittest

import file_transfer
import ftp_error
import ftp_stat
import ftputil

import mock_ftplib
import test_base


#
# Helper functions to generate random data
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
# Several customized `MockSession` classes
#
class FailOnLoginSession(mock_ftplib.MockSession):
    def __init__(self, host='', user='', password=''):
        raise ftplib.error_perm

class FailOnKeepAliveSession(mock_ftplib.MockSession):
    def pwd(self):
        # Raise exception on second call to let the constructor work.
        if not hasattr(self, "pwd_called"):
            self.pwd_called = True
        else:
            raise ftplib.error_temp


class RecursiveListingForDotAsPathSession(mock_ftplib.MockSession):
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

class BinaryDownloadMockSession(mock_ftplib.MockSession):
    mock_file_content = binary_data()

class TimeShiftMockSession(mock_ftplib.MockSession):
    def delete(self, file_name):
        pass

#
# Customized `FTPHost` class for conditional upload/download tests
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
        # Needed for `isdir` in `FTPHost.remove`
        def isfile(self, path):
            return True

    def __init__(self, *args, **kwargs):
        ftputil.FTPHost.__init__(self, *args, **kwargs)
        self.path = self._Path()

#
# Test cases
#
class TestOpenAndClose(unittest.TestCase):
    """Test opening and closing of `FTPHost` objects."""

    def test_open_and_close(self):
        """Test closing of `FTPHost`."""
        host = test_base.ftp_host_factory()
        host.close()
        self.assertEqual(host.closed, True)
        self.assertEqual(host._children, [])


class TestLogin(unittest.TestCase):

    def test_invalid_login(self):
        """Login to invalid host must fail."""
        self.assertRaises(ftp_error.FTPOSError, test_base.ftp_host_factory,
                          FailOnLoginSession)


class TestKeepAlive(unittest.TestCase):

    def test_succeeding_keep_alive(self):
        """Assume the connection is still alive."""
        host = test_base.ftp_host_factory()
        host.keep_alive()

    def test_failing_keep_alive(self):
        """Assume the connection has timed out, so `keep_alive` fails."""
        host = test_base.ftp_host_factory(
                 session_factory=FailOnKeepAliveSession)
        self.assertRaises(ftp_error.TemporaryError, host.keep_alive)


class TestSetParser(unittest.TestCase):

    def test_set_parser(self):
        """Test if the selected parser is used."""
        # This test isn't very practical but should help at least a bit ...
        host = test_base.ftp_host_factory()
        # Implicitly fix at Unix format
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
        host = test_base.ftp_host_factory()
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
        host = test_base.ftp_host_factory(
                 session_factory=RecursiveListingForDotAsPathSession)
        lines = host._dir(host.curdir)
        self.assertEqual(lines[0], "total 10")
        self.failUnless(lines[1].startswith("lrwxrwxrwx   1 staff"))
        self.failUnless(lines[2].startswith("d--x--x--x   2 staff"))
        host.close()

    def test_plain_listing(self):
        host = test_base.ftp_host_factory(
                 session_factory=RecursiveListingForDotAsPathSession)
        lines = host._dir("")
        self.assertEqual(lines[0], "total 10")
        self.failUnless(lines[1].startswith("lrwxrwxrwx   1 staff"))
        self.failUnless(lines[2].startswith("d--x--x--x   2 staff"))
        host.close()

    def test_empty_string_instead_of_dot_workaround(self):
        host = test_base.ftp_host_factory(
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
        # Upload
        host = test_base.ftp_host_factory()
        host.upload(local_source, 'dummy')
        # Check uploaded content
        # The data which was uploaded has its line endings converted
        #  so the conversion must also be applied to `data`.
        data = data.replace('\n', '\r\n')
        remote_file_content = mock_ftplib.content_of('dummy')
        self.assertEqual(data, remote_file_content)
        # Clean up
        os.unlink(local_source)

    def test_binary_download(self):
        """Test binary mode download."""
        local_target = '__test_target'
        host = test_base.ftp_host_factory(
               session_factory=BinaryDownloadMockSession)
        # Download
        host.download('dummy', local_target, 'b')
        # Read file and compare
        data = open(local_target, 'rb').read()
        remote_file_content = mock_ftplib.content_of('dummy')
        self.assertEqual(data, remote_file_content)
        # Clean up
        os.unlink(local_target)

    def test_conditional_upload(self):
        """Test conditional ASCII mode upload."""
        local_source = '__test_source'
        data = ascii_data()
        self.generate_ascii_file(data, local_source)
        # Target is newer, so don't upload
        host = test_base.ftp_host_factory(
               ftp_host_class=FailingUploadAndDownloadFTPHost)
        flag = host.upload_if_newer(local_source, '/home/newer')
        self.assertEqual(flag, False)
        # Target is older, so upload
        host = test_base.ftp_host_factory()
        flag = host.upload_if_newer(local_source, '/home/older')
        self.assertEqual(flag, True)
        # Check uploaded content
        # The data which was uploaded has its line endings converted
        #  so the conversion must also be applied to 'data'.
        data = data.replace('\n', '\r\n')
        remote_file_content = mock_ftplib.content_of('older')
        self.assertEqual(data, remote_file_content)
        # Target doesn't exist, so upload
        host = test_base.ftp_host_factory()
        flag = host.upload_if_newer(local_source, '/home/notthere')
        self.assertEqual(flag, True)
        remote_file_content = mock_ftplib.content_of('notthere')
        self.assertEqual(data, remote_file_content)
        # Clean up
        os.unlink(local_source)

    def compare_and_delete_downloaded_data(self, filename):
        """Compare content of downloaded file with its source, then
        delete the local target file."""
        data = open(filename, 'rb').read()
        remote_file_content = mock_ftplib.content_of('newer')
        self.assertEqual(data, remote_file_content)
        # Clean up
        os.unlink(filename)

    def test_conditional_download_without_target(self):
        "Test conditional binary mode download when no target file exists."
        local_target = '__test_target'
        # Target does not exist, so download
        host = test_base.ftp_host_factory(
               session_factory=BinaryDownloadMockSession)
        flag = host.download_if_newer('/home/newer', local_target, 'b')
        self.assertEqual(flag, True)
        self.compare_and_delete_downloaded_data(local_target)

    def test_conditional_download_with_older_target(self):
        """Test conditional binary mode download with newer source file."""
        local_target = '__test_target'
        # Make target file
        open(local_target, 'w').close()
        # Source is newer, so download
        host = test_base.ftp_host_factory(
               session_factory=BinaryDownloadMockSession)
        flag = host.download_if_newer('/home/newer', local_target, 'b')
        self.assertEqual(flag, True)
        self.compare_and_delete_downloaded_data(local_target)

    def test_conditional_download_with_newer_target(self):
        """Test conditional binary mode download with older source file."""
        local_target = '__test_target'
        # Make target file
        open(local_target, 'w').close()
        # Source is older, so don't download
        host = test_base.ftp_host_factory(
               session_factory=BinaryDownloadMockSession)
        host = test_base.ftp_host_factory(
               ftp_host_class=FailingUploadAndDownloadFTPHost,
               session_factory=BinaryDownloadMockSession)
        flag = host.download_if_newer('/home/older', local_target, 'b')
        self.assertEqual(flag, False)
        # Remove target file
        os.unlink(local_target)


class TestTimeShift(unittest.TestCase):

    def test_rounded_time_shift(self):
        """Test if time shift is rounded correctly."""
        host = test_base.ftp_host_factory(session_factory=TimeShiftMockSession)
        # Use private bound method
        rounded_time_shift = host._FTPHost__rounded_time_shift
        # Pairs consisting of original value and expected result
        test_data = [
          (0, 0), (0.1, 0), (-0.1, 0), (1500, 0), (-1500, 0),
          (1800, 3600), (-1800, -3600), (2000, 3600), (-2000, -3600),
          (5*3600-100, 5*3600), (-5*3600+100, -5*3600)]
        for time_shift, expected_time_shift in test_data:
            calculated_time_shift = rounded_time_shift(time_shift)
            self.assertEqual(calculated_time_shift, expected_time_shift)

    def test_assert_valid_time_shift(self):
        """Test time shift sanity checks."""
        host = test_base.ftp_host_factory(session_factory=TimeShiftMockSession)
        # Use private bound method
        assert_time_shift = host._FTPHost__assert_valid_time_shift
        # Valid time shifts
        test_data = [23*3600, -23*3600, 3600+30, -3600+30]
        for time_shift in test_data:
            self.failUnless(assert_time_shift(time_shift) is None)
        # Invalid time shift (exceeds one day)
        self.assertRaises(ftp_error.TimeShiftError, assert_time_shift, 25*3600)
        self.assertRaises(ftp_error.TimeShiftError, assert_time_shift, -25*3600)
        # Invalid time shift (deviation from full hours unacceptable)
        self.assertRaises(ftp_error.TimeShiftError, assert_time_shift, 10*60)
        self.assertRaises(ftp_error.TimeShiftError, assert_time_shift,
                          -3600-10*60)

    def test_synchronize_times(self):
        """Test time synchronization with server."""
        host = test_base.ftp_host_factory(ftp_host_class=TimeShiftFTPHost,
               session_factory=TimeShiftMockSession)
        # Valid time shift
        host.path.set_mtime(time.time() + 3630)
        host.synchronize_times()
        self.assertEqual(host.time_shift(), 3600)
        # Invalid time shift
        host.path.set_mtime(time.time() + 3600+10*60)
        self.assertRaises(ftp_error.TimeShiftError, host.synchronize_times)


if __name__ == '__main__':
    unittest.main()
    import __main__
    # unittest.main(__main__,
    #   "TestTimestampComparison.test_source_is_newer_than_target")

