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

# $Id: _test_ftputil.py,v 1.50 2002/03/30 22:18:20 schwa Exp $

import unittest
import stat
import os
import time
import operator
import random

import ftplib
import ftputil
import _mock_ftplib


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
        character_list.append( chr(ordinal) )
    result = ''.join(character_list)
    return result

def ascii_data():
    """Return an ASCII character string."""
    pool = range(32, 128)
    pool.append( ord('\n') )
    return random_data(pool)

def binary_data():
    """Return an binary character string."""
    pool = range(0, 256)
    return random_data(pool)

#
# several customized MockSession classes
#
class FailOnLoginSession(_mock_ftplib.MockSession):
    def __init__(self, host='', user='', password=''):
        raise ftplib.error_perm

class ReadMockSession(_mock_ftplib.MockSession):
    mock_file_content = 'line 1\r\nanother line\r\nyet another line'

class AsciiReadMockSession(_mock_ftplib.MockSession):
    mock_file_content = '\r\n'.join( map( str, range(20) ) )

class BinaryDownloadMockSession(_mock_ftplib.MockSession):
    mock_file_content = binary_data()


#
# factory to produce FTPHost-like classes from a given FTPHost
#  class and a given MockSession class
def ftp_host_factory(session_factory=_mock_ftplib.MockSession,
                     ftp_host_class=ftputil.FTPHost):
    return ftp_host_class('dummy_host', 'dummy_user', 'dummy_password',
                          session_factory=session_factory)


#
# test cases
#
class TestLogin(unittest.TestCase):
    """Test invalid logins."""

    def test_invalid_login(self):
        """Login to invalid host must fail."""
        self.assertRaises(ftputil.FTPOSError, ftp_host_factory,
                          FailOnLoginSession)


class TestStat(unittest.TestCase):
    """
    Test FTPHost.lstat and FTPHost.stat (test currently only
    implemented for Unix server format).
    """

    def test_failing_lstat(self):
        """Test whether lstat fails for a nonexistent path."""
        host = ftp_host_factory()
        self.assertRaises(ftputil.PermanentError, host.lstat,
                          '/home/sschw/notthere')
        self.assertRaises(ftputil.PermanentError, host.lstat,
                          '/home/sschwarzer/notthere')

    def test_lstat_one_file(self):
        """Test FTPHost.lstat with a file."""
        host = ftp_host_factory()
        stat_result = host.lstat('/home/sschwarzer/index.html')
        self.assertEqual( oct(stat_result.st_mode), '0100644' )
        self.assertEqual(stat_result.st_size, 4604)

    def test_lstat_one_dir(self):
        """Test FTPHost.lstat with a directory."""
        # some directory
        host = ftp_host_factory()
        stat_result = host.lstat('/home/sschwarzer/scios2')
        self.assertEqual( oct(stat_result.st_mode), '042755' )
        self.assertEqual(stat_result.st_ino, None)
        self.assertEqual(stat_result.st_dev, None)
        self.assertEqual(stat_result.st_nlink, 6)
        self.assertEqual(stat_result.st_uid, '45854')
        self.assertEqual(stat_result.st_gid, '200')
        self.assertEqual(stat_result.st_size, 512)
        self.assertEqual(stat_result.st_atime, None)
        self.assertEqual(stat_result.st_mtime, 937785600.0)
        self.assertEqual(stat_result.st_ctime, None)
        self.assertEqual(stat_result.st_name, 'scios2')

    def test_lstat_via_stat_module(self):
        """Test FTPHost.lstat indirectly via stat module."""
        host = ftp_host_factory()
        stat_result = host.lstat('/home/sschwarzer/')
        self.failUnless( stat.S_ISDIR(stat_result.st_mode) )


class TestListdir(unittest.TestCase):
    """Test FTPHost.listdir."""

    def test_failing_listdir(self):
        """Test failing FTPHost.listdir."""
        host = ftp_host_factory()
        self.assertRaises(ftputil.PermanentError,
                          host.listdir, 'notthere')

    def test_succeeding_listdir(self):
        """Test succeeding FTPHost.listdir."""
        # do we have all expected "files"?
        host = ftp_host_factory()
        self.assertEqual( len(host.listdir(host.curdir)), 9 )
        # have they the expected names?
        host = ftp_host_factory()
        expected = ('chemeng download image index.html os2 '
                    'osup publications python scios2').split()
        remote_file_list = host.listdir(host.curdir)
        for file in expected:
            self.failUnless(file in remote_file_list)


class TestPath(unittest.TestCase):
    """Test operations in FTPHost.path."""

    def test_isdir_isfile_islink(self):
        """Test FTPHost._Path.isdir/isfile/islink."""
        testdir = '/home/sschwarzer'
        host = ftp_host_factory()
        host.chdir(testdir)
        # test a path which isn't there
        self.failIf( host.path.isdir('notthere') )
        self.failIf( host.path.isfile('notthere') )
        self.failIf( host.path.islink('notthere') )
        # test a directory
        self.failUnless( host.path.isdir(testdir) )
        self.failIf( host.path.isfile(testdir) )
        self.failIf( host.path.islink(testdir) )
        # test a file
        testfile = '/home/sschwarzer/index.html'
        self.failIf( host.path.isdir(testfile) )
        self.failUnless( host.path.isfile(testfile) )
        self.failIf( host.path.islink(testfile) )
        # test a link
        testlink = '/home/sschwarzer/osup'
        #XXX uncomment these two when following links is implemented
        #self.failIf( host.path.isdir(testlink) )
        #self.failIf( host.path.isfile(testlink) )
        self.failUnless( host.path.islink(testlink) )


class TestFileOperations(unittest.TestCase):
    """Test operations with file-like objects."""

    def test_caching(self):
        """Test if _FTPFile cache of FTPHost object works."""
        host = ftp_host_factory()
        self.assertEqual( len(host._children), 0 )
        path1 = 'path1'
        path2 = 'path2'
        # open one file and inspect cache
        file1 = host.file(path1, 'w')
        child1 = host._children[0]
        self.assertEqual( len(host._children), 1 )
        self.failIf(child1._file.closed)
        # open another file
        file2 = host.file(path2, 'w')
        child2 = host._children[1]
        self.assertEqual( len(host._children), 2 )
        self.failIf(child2._file.closed)
        # close first file
        file1.close()
        self.assertEqual( len(host._children), 2 )
        self.failUnless(child1._file.closed)
        self.failIf(child2._file.closed)
        # re-open first child's file
        file1 = host.file(path1, 'w')
        child1_1 = file1._host
        # check if it's reused
        self.failUnless(child1 is child1_1)
        self.failIf(child1._file.closed)
        self.failIf(child2._file.closed)
        # close second file
        file2.close()
        self.failUnless(child2._file.closed)

    def test_write_to_directory(self):
        """Test whether attempting to write to a directory fails."""
        host = ftp_host_factory()
        self.assertRaises(ftputil.FTPIOError, host.file,
                          '/home/sschwarzer', 'w')

    def test_binary_write(self):
        """Write binary data to the host and read it back."""
        host = ftp_host_factory()
        data = '\000a\001b\r\n\002c\003\n\004\r\005'
        output = host.file('dummy', 'wb')
        output.write(data)
        output.close()
        child_data = _mock_ftplib.content_of('dummy')
        expected_data = data
        self.assertEqual(child_data, expected_data)

    def test_ascii_write(self):
        """Write an ASCII text to the host and check the written file."""
        host = ftp_host_factory()
        data = ' \nline 2\nline 3'
        output = host.file('dummy', 'w')
        output.write(data)
        output.close()
        child_data = _mock_ftplib.content_of('dummy')
        expected_data = ' \r\nline 2\r\nline 3'
        self.assertEqual(child_data, expected_data)

    def test_ascii_writelines(self):
        """Write ASCII data via writelines and check it."""
        host = ftp_host_factory()
        data = [' \n', 'line 2\n', 'line 3']
        backup_data = data[:]
        output = host.file('dummy', 'w')
        output.writelines(data)
        output.close()
        child_data = _mock_ftplib.content_of('dummy')
        expected_data = ' \r\nline 2\r\nline 3'
        self.assertEqual(child_data, expected_data)
        # ensure that the original data was not modified
        self.assertEqual(data, backup_data)

    def test_ascii_read(self):
        """Use plain ASCII read operations to get data."""
        host = ftp_host_factory(session_factory=ReadMockSession)
        input_ = host.file('dummy', 'r')
        data = input_.read(0)
        self.assertEqual(data, '')
        data = input_.read(3)
        self.assertEqual(data, 'lin')
        data = input_.read(7)
        self.assertEqual(data, 'e 1\nano')
        data = input_.read()
        self.assertEqual(data, 'ther line\nyet another line')
        data = input_.read()
        self.assertEqual(data, '')
        input_.close()
        # try it again with a more "problematic" string which
        #  makes several reads in the read() method necessary.
        host = ftp_host_factory(session_factory=AsciiReadMockSession)
        expected_data = AsciiReadMockSession.mock_file_content.\
                        replace('\r\n', '\n')
        input_ = host.file('dummy', 'r')
        data = input_.read( len(expected_data) )
        self.assertEqual(data, expected_data)

    def test_ascii_readline(self):
        """Use ASCII readline operations to get data."""
        host = ftp_host_factory(session_factory=ReadMockSession)
        input_ = host.file('dummy', 'r')
        data = input_.readline(3)
        self.assertEqual(data, 'lin')
        data = input_.readline(10)
        self.assertEqual(data, 'e 1\n')
        data = input_.readline(13)
        self.assertEqual(data, 'another line\n')
        data = input_.readline()
        self.assertEqual(data, 'yet another line')
        data = input_.readline()
        self.assertEqual(data, '')
        input_.close()

    def test_binary_readline(self):
        """Use binary readline operations to get data."""
        host = ftp_host_factory(session_factory=ReadMockSession)
        input_ = host.file('dummy', 'rb')
        data = input_.readline(3)
        self.assertEqual(data, 'lin')
        data = input_.readline(10)
        self.assertEqual(data, 'e 1\r\n')
        data = input_.readline(13)
        self.assertEqual(data, 'another line\r')
        data = input_.readline()
        self.assertEqual(data, '\n')
        data = input_.readline()
        self.assertEqual(data, 'yet another line')
        data = input_.readline()
        self.assertEqual(data, '')
        input_.close()

    def test_ascii_readlines(self):
        """Use ASCII readline operations to get data."""
        host = ftp_host_factory(session_factory=ReadMockSession)
        input_ = host.file('dummy', 'r')
        data = input_.read(3)
        self.assertEqual(data, 'lin')
        data = input_.readlines()
        self.assertEqual(data, ['e 1\n', 'another line\n',
                                'yet another line'])
        input_.close()

    def test_ascii_xreadlines(self):
        """Use an xreadline-like object to retrieve ASCII data."""
        host = ftp_host_factory(session_factory=ReadMockSession)
        # open file, skip some bytes
        input_ = host.file('dummy', 'r')
        data = input_.read(3)
        xrl_obj = input_.xreadlines()
        self.failUnless(xrl_obj.__class__ is
                        ftputil._XReadlines)
        self.failUnless(xrl_obj._ftp_file.__class__ is
                        ftputil._FTPFile)
        data = xrl_obj[0]
        self.assertEqual(data, 'e 1\n')
        # try to skip an index
        self.assertRaises(RuntimeError, operator.__getitem__,
                          xrl_obj, 2)
        # continue reading
        data = xrl_obj[1]
        self.assertEqual(data, 'another line\n')
        data = xrl_obj[2]
        self.assertEqual(data, 'yet another line')
        # try to read beyond EOF
        self.assertRaises(IndexError, operator.__getitem__,
                          xrl_obj, 3)

    def test_read_unknown_file(self):
        """Test whether reading a file which isn't there fails."""
        host = ftp_host_factory()
        self.assertRaises(ftputil.FTPIOError, host.file,
                          'notthere', 'r')


class TestUploadAndDownload(unittest.TestCase):
    """Test ascii upload and binary download as examples."""

    def test_ascii_upload(self):
        """Test ASCII mode upload."""
        local_source = '__test_source'
        # generate file
        data = ascii_data()
        source_file = open(local_source, 'w')
        source_file.write(data)
        source_file.close()
        # upload
        host = ftp_host_factory()
        host.upload(local_source, 'dummy')
        # check uploaded content
        # the data which was uploaded has its line endings converted
        #  so the conversion must also be applied to 'data'
        data = data.replace('\n', '\r\n')
        remote_file_content = _mock_ftplib.content_of('dummy')
        self.assertEqual(data, remote_file_content)
        # clean up
        os.unlink(local_source)

    def test_binary_download(self):
        """Test binary mode download."""
        local_target = '__test_target'
        host = ftp_host_factory(session_factory=BinaryDownloadMockSession)
        # download
        host.download('dummy', local_target, 'b')
        # read file and compare
        data = open(local_target, 'rb').read()
        remote_file_content = _mock_ftplib.content_of('dummy')
        self.assertEqual(data, remote_file_content)
        # clean up
        os.unlink(local_target)


if __name__ == '__main__':
    unittest.main()

