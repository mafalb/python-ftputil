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

# $Id: _test_ftputil.py,v 1.31 2002/03/30 15:28:35 schwa Exp $

import unittest
import stat
import os
import time
import operator

import ftputil
import _mock_ftplib


class FTPHostWrapper(ftputil.FTPHost):
    def __init__(self, session_factory):
        ftputil.FTPHost.__init__(self, 'dummy_host', 'dummy_user',
          'dummy_password', session_factory=session_factory)


class TestLogin(unittest.TestCase):
    """Test invalid logins."""

    def test_invalid_login(self):
        """Login to invalid host must fail."""
        self.assertRaises(ftputil.FTPOSError, FTPHostWrapper,
                          _mock_ftplib.FailOnLoginSession)


class TestStat(unittest.TestCase):
    """Test FTPHost.lstat, FTPHost.stat, FTPHost.listdir.
    (test currently only implemented for Unix server format.
    """

    def test_lstat_one_file(self):
        """Test FTPHost.lstat with a file."""
        host = FTPHostWrapper(_mock_ftplib.MockSession)
        stat_result = host.lstat('/home/sschwarzer/index.html')
        self.assertEqual( oct(stat_result.st_mode), '0100644' )
        self.assertEqual(stat_result.st_size, 4604)
    
    def test_lstat_one_dir(self):
        """Test FTPHost.lstat with a directory."""
        # some directory
        host = FTPHostWrapper(_mock_ftplib.MockSession)
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
        host = FTPHostWrapper(_mock_ftplib.MockSession)
        stat_result = host.lstat('/home/sschwarzer/')
        self.failUnless( stat.S_ISDIR(stat_result.st_mode) )

    def test_listdir(self):
        """Test FTPHost.listdir."""
        # try to list a path which isn't there
        host = FTPHostWrapper(_mock_ftplib.MockSession)
        self.assertRaises(ftputil.PermanentError,
                          host.listdir, 'notthere')
        # do we have all expected "files"?
        host = FTPHostWrapper(_mock_ftplib.MockSession)
        self.assertEqual( len(host.listdir(host.curdir)), 9 )
        # have they the expected names?
        host = FTPHostWrapper(_mock_ftplib.MockSession)
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
        host = FTPHostWrapper(_mock_ftplib.MockSession)
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
        # uncomment these two when following links is implemented
        #self.failIf( host.path.isdir(testlink) )
        #self.failIf( host.path.isfile(testlink) )
        self.failUnless( host.path.islink(testlink) )


class TestFileOperations(unittest.TestCase):
    """
    Test operations with file-like objects (including
    uploads and downloads).
    """

#     def test_caching(self):
#         """Test if _FTPFile cache of FTPHost object works."""
#         host = FTPHostWrapper(host_name, user, password)
#         self.assertEqual( len(host._children), 0 )
#         path1 = host.path.join(self.testdir, '__test1.dat')
#         path2 = host.path.join(self.testdir, '__test2.dat')
#         # open one file and inspect cache
#         file1 = host.file(path1, 'w')
#         child1 = host._children[0]
#         self.assertEqual( len(host._children), 1 )
#         self.failIf(child1._file.closed)
#         # open another file
#         file2 = host.file(path2, 'w')
#         child2 = host._children[1]
#         self.assertEqual( len(host._children), 2 )
#         self.failIf(child2._file.closed)
#         # close first file
#         file1.close()
#         self.assertEqual( len(host._children), 2 )
#         self.failUnless(child1._file.closed)
#         self.failIf(child2._file.closed)
#         # re-open first child's file
#         file1 = host.file(path1, 'w')
#         child1_1 = file1._host
#         # check if it's reused
#         self.failUnless(child1 is child1_1)
#         self.failIf(child1._file.closed)
#         self.failIf(child2._file.closed)
#         # close second file
#         file2.close()
#         self.failUnless(child2._file.closed)
#         # clean up
#         host.remove(path1)
#         host.remove(path2)
#
#     def binary_write(self):
#         """Write binary data to the host and read it back."""
#         host = self.host
#         local_data = '\000a\001b\r\n\002c\003\n\004\r\005'
#         # write data in binary mode
#         self.write_test_data(local_data, 'wb')
#         # check the file length on the remote host
#         remote_size = host.path.getsize(self.remote_name)
#         self.assertEqual( remote_size, len(local_data) )
#         # read the data back and compare
#         input_ = host.file(self.remote_name, 'rb')
#         remote_data = input_.read()
#         input_.close()
#         self.assertEqual(local_data, remote_data)
# 
#     def ascii_write(self):
#         """Write an ASCII to the host and check the written file."""
#         host = self.host
#         local_data = ' \nline 2\nline 3'
#         # write data in ASCII mode
#         self.write_test_data(local_data, 'w')
#         # read data back in binary mode
#         input_ = host.file(self.remote_name, 'rb')
#         remote_data = input_.read()
#         input_.close()
#         # expect the same data as above if we have a
#         #  Unix FTP server
#         self.assertEqual(local_data, remote_data)
#
#     def ascii_writelines(self):
#         """Write data via writelines and read it back."""
#         host = self.host
#         local_data = [' \n', 'line 2\n', 'line 3']
#         # write data in ASCII mode
#         output = host.file(self.remote_name, 'w')
#         output.writelines(local_data)
#         output.close()
#         # read data back in ASCII mode
#         input_ = host.file(self.remote_name, 'r')
#         remote_data = input_.read()
#         input_.close()
#         # check data
#         self.assertEqual( ''.join(local_data), remote_data )
#
#     def test_write_to_host(self):
#         """Test _FTPFile.write*"""
#         host = self.host
#         host.chdir(self.testdir)
#         self.remote_name = '__test.dat'
#         # try to write to a directory
#         self.assertRaises(ftputil.FTPIOError, host.file,
#                           self.testdir, 'w')
#         self.binary_write()
#         self.ascii_write()
#         self.ascii_writelines()
#         # clean up
#         host.remove(self.remote_name)
#         host.chdir(self.rootdir)
#
#     def ascii_read(self):
#         """Write some ASCII data to the host and use plain
#         read operations to get it back.
#         """
#         host = self.host
#         # write some data
#         local_data = 'line 1\nanother line\nyet another line'
#         self.write_test_data(local_data, 'w')
#         # read with read method
#         input_ = host.file(self.remote_name, 'r')
#         data = input_.read(0)
#         self.assertEqual(data, '')
#         data = input_.read(3)
#         self.assertEqual(data, 'lin')
#         data = input_.read(7)
#         self.assertEqual(data, 'e 1\nano')
#         data = input_.read()
#         self.assertEqual(data, 'ther line\nyet another line')
#         data = input_.read()
#         self.assertEqual(data, '')
#         input_.close()
#         # try it again with a more "problematic" string which
#         #  makes several reads in the read() method necessary.
#         local_data = '\n'.join( map( str, range(20) ) )
#         output = host.file(self.remote_name, 'w')
#         output.writelines(local_data)
#         output.close()
#         input_ = host.file(self.remote_name, 'r')
#         data = input_.read( len(local_data) )
#         self.assertEqual(data, local_data)
#
#     def ascii_readline(self):
#         """Write some ASCII data to the host and use readline
#         operations to get it back.
#         """
#         host = self.host
#         # write some data
#         local_data = 'line 1\nanother line\nyet another line'
#         self.write_test_data(local_data, 'w')
#         # read data with ascii readline
#         input_ = host.file(self.remote_name, 'r')
#         data = input_.readline(3)
#         self.assertEqual(data, 'lin')
#         data = input_.readline(10)
#         self.assertEqual(data, 'e 1\n')
#         data = input_.readline(13)
#         self.assertEqual(data, 'another line\n')
#         data = input_.readline()
#         self.assertEqual(data, 'yet another line')
#         data = input_.readline()
#         self.assertEqual(data, '')
#         input_.close()
#
#     def binary_readline(self):
#         """Write some ASCII data to the host and use binary
#         readline operations to get it back.
#         """
#         host = self.host
#         # write some data
#         local_data = \
#           'line 1\r\nanother line\r\nyet another line'
#         self.write_test_data(local_data, 'wb')
#         # read data with binary readline
#         input_ = host.file(self.remote_name, 'rb')
#         data = input_.readline(3)
#         self.assertEqual(data, 'lin')
#         data = input_.readline(10)
#         self.assertEqual(data, 'e 1\r\n')
#         data = input_.readline(13)
#         self.assertEqual(data, 'another line\r')
#         data = input_.readline()
#         self.assertEqual(data, '\n')
#         data = input_.readline()
#         self.assertEqual(data, 'yet another line')
#         data = input_.readline()
#         self.assertEqual(data, '')
#         input_.close()
#
#     def ascii_readlines(self):
#         """Write some ASCII data to the host and use readline
#         operations to get it back.
#         """
#         host = self.host
#         # write some data
#         local_data = 'line 1\nanother line\nyet another line'
#         self.write_test_data(local_data, 'w')
#         input_ = host.file(self.remote_name, 'r')
#         data = input_.read(3)
#         self.assertEqual(data, 'lin')
#         data = input_.readlines()
#         self.assertEqual(data, ['e 1\n', 'another line\n',
#                                 'yet another line'])
#         input_.close()
#
#     def ascii_xreadlines(self):
#         """Write some ASCII data to the host and use an
#         xreadline-like object to retrieve it.
#         """
#         host = self.host
#         # write data
#         local_data = 'line 1\nanother line\nyet another line'
#         self.write_test_data(local_data, 'w')
#         # open file, skip some bytes
#         input_ = host.file(self.remote_name, 'r')
#         data = input_.read(3)
#         xrl_obj = input_.xreadlines()
#         self.failUnless(xrl_obj.__class__ is
#                         ftputil._XReadlines)
#         self.failUnless(xrl_obj._ftp_file.__class__ is
#                         ftputil._FTPFile)
#         data = xrl_obj[0]
#         self.assertEqual(data, 'e 1\n')
#         # try to skip an index
#         self.assertRaises(RuntimeError, operator.__getitem__,
#                           xrl_obj, 2)
#         # continue reading
#         data = xrl_obj[1]
#         self.assertEqual(data, 'another line\n')
#         data = xrl_obj[2]
#         self.assertEqual(data, 'yet another line')
#         # try to read beyond EOF
#         self.assertRaises(IndexError, operator.__getitem__,
#                           xrl_obj, 3)
#
#     def test_read_from_host(self):
#         """Test _FTPFile.read*"""
#         host = self.host
#         host.chdir(self.testdir)
#         self.remote_name = '__test.dat'
#         # try to read a file which isn't there
#         self.assertRaises(ftputil.FTPIOError, host.file,
#                           'notthere', 'r')
#         self.ascii_read()
#         self.ascii_readline()
#         self.binary_readline()
#         self.ascii_readlines()
#         self.ascii_xreadlines()
#         # clean up
#         host.remove(self.remote_name)
#         host.chdir(self.rootdir)
#
#     def test_remote_copy(self):
#         """Make a copy on the remote host."""
#         host = self.host
#         host.chdir(self.testdir)
#         self.remote_name = '__test.dat'
#         local_data = '\000a\001b\r\n\002c\003\n\004\r\005'
#         # write later source data
#         self.write_test_data(local_data, 'wb')
#         # build paths
#         source_path = self.remote_name
#         host.mkdir('__test2')
#         target_path = host.path.join('__test2',
#                                      self.remote_name)
#         # make file objects
#         source = host.file(source_path, 'rb')
#         target = host.file(target_path, 'wb')
#         # copy
#         host.copyfileobj(source, target)
#         source.close()
#         target.close()
#         # read copy and check against original data
#         input_ = host.file(target_path, 'rb')
#         data = input_.read()
#         input_.close()
#         self.assertEqual(local_data, data)
#         # clean up
#         host.remove(target_path)
#         host.rmdir('__test2')
#         host.unlink(source_path)
#         host.chdir(self.rootdir)
#
#     def test_upload_download(self):
#         """Test FTPHost.upload/download."""
#         host = self.host
#         local_source = 'ftputil.py'
#         local_test_path = '__test.dat'
#         remote_path = host.path.join(self.testdir,
#                                      'ftputil2.py')
#         # test ascii up/download
#         host.upload(local_source, remote_path)
#         host.download(remote_path, local_test_path)
#         # compare local data
#         input_ = file(local_source)
#         original = input_.read()
#         input_.close()
#         input_ = file(local_test_path)
#         copy = input_.read()
#         input_.close()
#         self.assertEqual(original, copy)
#         # test binary up/download
#         host.upload(local_source, remote_path, 'b')
#         host.download(remote_path, local_test_path, 'b')
#         # compare local data
#         input_ = file(local_source, 'rb')
#         original = input_.read()
#         input_.close()
#         input_ = file(local_test_path, 'rb')
#         copy = input_.read()
#         input_.close()
#         self.assertEqual(original, copy)
#         # clean up
#         host.remove(remote_path)
#         os.remove(local_test_path)


if __name__ == '__main__':
    unittest.main()

