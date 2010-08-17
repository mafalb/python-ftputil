# Copyright (C) 2003-2007, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

import ftplib
import unittest

import _mock_ftplib
import _test_base
import ftp_error
import ftputil


class FailingFTPHost(ftputil.FTPHost):
    def _dir(self, path):
        raise ftp_error.FTPOSError("simulate a failure, e. g. timeout")


# Mock session, used for testing an inaccessible login directory
class SessionWithInaccessibleLoginDirectory(_mock_ftplib.MockSession):
    def cwd(self, dir):
        # Assume that `dir` is the inaccessible login directory.
        raise ftplib.error_perm("can't change into this directory")


class TestPath(unittest.TestCase):
    """Test operations in `FTPHost.path`."""
    def test_regular_isdir_isfile_islink(self):
        """Test regular `FTPHost._Path.isdir/isfile/islink`."""
        testdir = '/home/sschwarzer'
        host = _test_base.ftp_host_factory()
        host.chdir(testdir)
        # Test a path which isn't there
        self.failIf(host.path.isdir('notthere'))
        self.failIf(host.path.isfile('notthere'))
        self.failIf(host.path.islink('notthere'))
        # Test a directory
        self.failUnless(host.path.isdir(testdir))
        self.failIf(host.path.isfile(testdir))
        self.failIf(host.path.islink(testdir))
        # Test a file
        testfile = '/home/sschwarzer/index.html'
        self.failIf(host.path.isdir(testfile))
        self.failUnless(host.path.isfile(testfile))
        self.failIf(host.path.islink(testfile))
        # Test a link
        testlink = '/home/sschwarzer/osup'
        self.failIf(host.path.isdir(testlink))
        self.failIf(host.path.isfile(testlink))
        self.failUnless(host.path.islink(testlink))

    def test_workaround_for_spaces(self):
        """Test whether the workaround for space-containing paths is used."""
        testdir = '/home/sschwarzer'
        host = _test_base.ftp_host_factory()
        host.chdir(testdir)
        # Test a file name containing spaces
        testfile = '/home/dir with spaces/file with spaces'
        self.failIf(host.path.isdir(testfile))
        self.failUnless(host.path.isfile(testfile))
        self.failIf(host.path.islink(testfile))

    def test_inaccessible_home_directory_and_whitespace_workaround(self):
        "Test combination of inaccessible home directory + whitespace in path."
        host = _test_base.ftp_host_factory(
               session_factory=SessionWithInaccessibleLoginDirectory)
        self.assertRaises(ftp_error.InaccessibleLoginDirError,
                          host._dir, '/home dir')

    def test_abnormal_isdir_isfile_islink(self):
        """Test abnormal `FTPHost._Path.isdir/isfile/islink`."""
        testdir = '/home/sschwarzer'
        host = _test_base.ftp_host_factory(ftp_host_class=FailingFTPHost)
        host.chdir(testdir)
        # Test a path which isn't there
        self.assertRaises(ftp_error.FTPOSError, host.path.isdir, "index.html")
        self.assertRaises(ftp_error.FTPOSError, host.path.isfile, "index.html")
        self.assertRaises(ftp_error.FTPOSError, host.path.islink, "index.html")

    def test_exists(self):
        """Test if "abnormal" FTP errors come through `path.exists`."""
        # Regular use of `exists`
        testdir = '/home/sschwarzer'
        host = _test_base.ftp_host_factory()
        host.chdir(testdir)
        self.assertEqual(host.path.exists("index.html"), True)
        self.assertEqual(host.path.exists("notthere"), False)
        # "Abnormal" failure
        host = _test_base.ftp_host_factory(ftp_host_class=FailingFTPHost)
        self.assertRaises(ftp_error.FTPOSError, host.path.exists, "index.html")


if __name__ == '__main__':
    unittest.main()

