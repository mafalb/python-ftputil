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

import unittest
import ftputil
import getpass
import stat
import os
import time


class Base(unittest.TestCase):
    '''Base class for some test classes.'''

    def setUp(self):
        self.host = ftputil.FTPHost(host_name, user, password)
        self.rootdir = self.host.getcwd()
        self.testdir = self.host.path.join(
                       self.rootdir, '__test1')
        self.host.mkdir(self.testdir)

    def tearDown(self):
        host = self.host
        host.chdir(self.rootdir)
        host.rmdir(self.testdir)
        host.close()


class TestLogin(unittest.TestCase):
    '''Test invalid logins.'''
    
    def test_invalid_login(self):
        '''Login to invalid host must fail.'''
        # plain FTPOSError, no derived class
        self.assertRaises(ftputil.FTPOSError, ftputil.FTPHost,
          'nonexistent.ho.st.na.me', 'me', 'password')
        try:
            ftputil.FTPHost('nonexistent.ho.st.na.me')
        except ftputil.FTPOSError, obj:
            pass
        self.failUnless(obj.__class__ is ftputil.FTPOSError)


class TestRemoveAndRename(Base):
    '''Removing and renaming files.'''

    def test_remove(self):
        '''Test FTPHost.remove.'''
        host = self.host
        # try to remove a file which is not there
        self.assertRaises( ftputil.PermanentError, host.remove,
          host.path.join(self.testdir, 'notthere') )
        # remove a directory and check if it's removed
        host.mkdir( host.path.join(self.testdir, '__test2') )
        host.remove( host.path.join(self.testdir, '__test2') )
        self.failIf( host.path.exists( host.path.join(
                     self.testdir, '__test2') ) )
        # remove a file and check if it's removed
        host.upload( 'ftputil.py', host.path.join(self.testdir,
                     'ftputil2.py'), 'b' )
        host.unlink( host.path.join(self.testdir,
                                    'ftputil2.py') )
        self.failIf( host.path.exists( host.path.join(
                     self.testdir, 'ftputil2.py') ) )
        
    def test_rename(self):
        '''Test FTPHost.rename.'''
        host = self.host
        # try to rename a file which is not there
        host.chdir(self.testdir)
        self.assertRaises(ftputil.PermanentError, host.rename,
                          'notthere', 'notthere2')
        # upload a file, rename it and look if the name
        #  has changed
        host.upload('ftputil.py', 'ftputil2.py', 'b')
        host.rename('ftputil2.py', 'ftputil3.py')
        self.failIf( host.path.exists('ftputil2.py') )
        self.failUnless( host.path.exists('ftputil3.py') )
        # clean up
        host.remove('ftputil3.py')
        host.chdir(self.rootdir)


class TestDirectories(Base):
    '''Getting, making, changing, deleting directories.'''

    def test_getcwd_and_change(self):
        '''Test FTPHost.getcwd and FTPHost.chdir.'''
        host = self.host
        self.assertEqual( host.getcwd(), self.rootdir )
        host.chdir(self.testdir)
        self.assertEqual( host.getcwd(), self.testdir )

    def test_mkdir(self):
        '''Test FTPHost.mkdir.'''
        host = self.host
        # use invalid directory name (__test2 doesn't exist)
        self.assertRaises( ftputil.PermanentError, host.mkdir,
          host.path.join(self.rootdir, '__test2', '__test3') )
        # this is valid
        host.mkdir( host.path.join(self.testdir, '__test2') )
        # repeat first mkdir (now valid)
        host.mkdir( host.path.join(self.testdir, '__test2',
                                   '__test3') )
        # clean up for this test
        host.rmdir( host.path.join(self.testdir, '__test2',
                                   '__test3') )
        host.rmdir( host.path.join(self.testdir, '__test2') )

    def test_rmdir(self):
        '''Test FTPHost.rmdir.'''
        host = self.host
        # try to remove nonexistent directory
        self.assertRaises( ftputil.PermanentError, host.rmdir,
          host.path.join(self.testdir, '__test2') )
        # make two nested directories
        host.mkdir( host.path.join(self.testdir, '__test2') )
        host.mkdir( host.path.join(self.testdir, '__test2',
                                   '__test3') )
        # try to remove non-empty directory
        self.assertRaises( ftputil.PermanentError, host.rmdir,
          host.path.join(self.testdir, '__test2') )
        # remove leaf dir __test3
        host.rmdir( host.path.join(self.testdir, '__test2',
                                   '__test3') )
        # try to remove a dir we are in
        host.chdir(self.testdir)
        host.chdir('./__test2')
        self.assertRaises( ftputil.PermanentError, host.rmdir,
          host.path.join(self.testdir, '__test2') )
        # finally remove __test2
        host.chdir(self.rootdir)
        host.rmdir( host.path.join(self.testdir, '__test2') )


class TestStat(Base):
    '''Test FTPHost.lstat, FTPHost.stat, FTPHost.listdir.'''
    
    def setUp(self):
        Base.setUp(self)
        host = self.host
        host.chdir(self.testdir)
        host.mkdir('__test2')
        host.upload('ftputil.py', 'ftputil2.py', 'b')

    def tearDown(self):
        host = self.host
        host.rmdir('__test2')
        host.remove('ftputil2.py')
        Base.tearDown(self)
        
    def test_listdir(self):
        '''Test FTPHost.listdir.'''
        host = self.host
        # try to list a directory which isn't there
        self.assertRaises(ftputil.PermanentError,
                          host.listdir, 'notthere')
        # try to list a "directory" which is a file
        self.assertRaises(ftputil.PermanentError,
                          host.listdir, 'ftputil2.py')
        # do we have two files?
        self.assertEqual( len(host.listdir(host.curdir)), 2 )
        # have they the expected names?
        self.failUnless( '__test2' in
                         host.listdir(host.curdir) )
        self.failUnless( 'ftputil2.py' in
                         host.listdir(host.curdir) )

    def test_lstat(self):
        '''Test FTPHost.lstat.'''
        host = self.host
        # test status of __test2
        stat_result = host.lstat('__test2')
        self.failUnless( stat.S_ISDIR(stat_result.st_mode) )
        # check if local and remote sizes are equal
        local_size = os.path.getsize('ftputil.py')
        remote_size = host.lstat('ftputil2.py').st_size
        self.assertEqual(local_size, remote_size)
        

class TestPath(Base):
    '''Test operations in FTPHost.path.'''

    def test_isdir_isfile_islink(self):
        '''Test FTPHost._Path.isdir/isfile/islink.'''
        host = self.host
        host.chdir(self.testdir)
        # test a path which isn't there
        self.failIf( host.path.isdir('notthere') )
        self.failIf( host.path.isfile('notthere') )
        self.failIf( host.path.islink('notthere') )
        # test a directory
        self.failUnless( host.path.isdir(self.testdir) )
        self.failIf( host.path.isfile(self.testdir) )
        self.failIf( host.path.islink(self.testdir) )
        # test a file
        host.upload('ftputil.py', 'ftputil2.py', 'b')
        self.failIf( host.path.isdir('ftputil2.py') )
        self.failUnless( host.path.isfile('ftputil2.py') )
        self.failIf( host.path.islink(self.testdir) )
        # clean up
        host.remove('ftputil2.py')
        host.chdir(self.rootdir)
        
    def test_getmtime(self):
        '''Test FTPHost._Path.getmtime.'''
        host = self.host
        host.chdir(self.testdir)
        # test a directory
        local_time = time.time()
        host.mkdir('__test2')
        remote_mtime = host.path.getmtime('__test2')
        #  accept a difference of up to 30 seconds
        self.failIf(remote_mtime - local_time >= 30)
        # test a file
        local_time = time.time()
        host.upload('ftputil.py', 'ftputil2.py', 'b')
        remote_mtime = host.path.getmtime('ftputil2.py')
        #  accept a difference of up to 30 seconds
        self.failIf(remote_mtime - local_time >= 30)
        # clean up
        host.rmdir('__test2')
        host.remove('ftputil2.py')
        host.chdir(self.rootdir)

    def test_getsize(self):
        '''Test FTPHost._Path.getsize.'''
        host = self.host
        host.chdir(self.testdir)
        # test a directory
        host.mkdir('__test2')
        remote_size = host.path.getsize('__test2')
        empty_dir_size = 512
        self.assertEqual(remote_size, empty_dir_size)
        # test a file
        host.upload('ftputil.py', 'ftputil2.py', 'b')
        local_size = os.path.getsize('ftputil.py')
        remote_size = host.path.getsize('ftputil2.py')
        self.assertEqual(local_size, remote_size)
        # clean up
        host.rmdir('__test2')
        host.remove('ftputil2.py')
        host.chdir(self.rootdir)
        

class TestFileOperations(Base):
    '''Test operations with file-like objects (including
    uploads and downloads.'''

    def write_test_data(self, data, mode):
        '''Write test data to the remote host.'''
        output = self.host.file(self.remote_name, mode)
        output.write(data)
        output.close()
        
    def binary_write(self):
        '''Write binary data to the host and read it back.'''
        host = self.host
        local_data = '\000a\001b\r\n\002c\003\n\004\r\005'
        # write data in binary mode
        self.write_test_data(local_data, 'wb')
        # check the file length on the remote host
        remote_size = host.path.getsize(self.remote_name)
        self.assertEqual( remote_size, len(local_data) )
        # read the data back and compare
        input_ = host.file(self.remote_name, 'rb')
        remote_data = input_.read()
        input_.close()
        self.assertEqual(local_data, remote_data)
        
    def ascii_write(self):
        '''Write an ASCII to the host and check the written
        file.'''
        host = self.host
        local_data = ' \nline 2\nline 3'
        # write data in ASCII mode
        self.write_test_data(local_data, 'w')
        # read data back in binary mode
        input_ = host.file(self.remote_name, 'rb')
        remote_data = input_.read()
        input_.close()
        # expect the same data as above if we have a
        #  Unix FTP server
        self.assertEqual(local_data, remote_data)
        
    def ascii_writelines(self):
        '''Write data via writelines and read it back.'''
        host = self.host
        local_data = [' \n', 'line 2\n', 'line 3']
        # write data in ASCII mode
        output = host.file(self.remote_name, 'w')
        output.writelines(local_data)
        output.close()
        # read data back in ASCII mode
        input_ = host.file(self.remote_name, 'r')
        remote_data = input_.read()
        input_.close()
        # check data
        self.assertEqual( ''.join(local_data), remote_data )
        
    def test_write_to_host(self):
        '''Test _FTPFile.write*'''
        host = self.host
        host.chdir(self.testdir)
        self.remote_name = '__test.dat'
        # try to write to a directory
        self.assertRaises(ftputil.FTPIOError, host.file,
                          self.testdir, 'w')
        self.binary_write()
        self.ascii_write()
        self.ascii_writelines()
        # clean up
        host.remove(self.remote_name)
        host.chdir(self.rootdir)

    def ascii_read(self):
        '''Write some ASCII data to the host and use plain
        read operations to get it back.'''
        host = self.host
        # write some data
        local_data = 'line 1\nanother line\nyet another line'
        self.write_test_data(local_data, 'w')
        # read with read method
        input_ = host.file(self.remote_name, 'r')
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
        local_data = '\n'.join( map( str, range(20) ) )
        output = host.file(self.remote_name, 'w')
        output.writelines(local_data)
        output.close()
        input_ = host.file(self.remote_name, 'r')
        data = input_.read( len(local_data) )
        self.assertEqual(data, local_data)
        
    def ascii_readline(self):
        '''Write some ASCII data to the host and use readline
        operations to get it back.'''
        host = self.host
        # write some data
        local_data = 'line 1\nanother line\nyet another line'
        self.write_test_data(local_data, 'w')
        # read data with ascii readline
        input_ = host.file(self.remote_name, 'r')
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
        
    def binary_readline(self):
        '''Write some ASCII data to the host and use binary
        readline operations to get it back.'''
        host = self.host
        # write some data
        local_data = \
          'line 1\r\nanother line\r\nyet another line'
        self.write_test_data(local_data, 'wb')
        # read data with binary readline
        input_ = host.file(self.remote_name, 'rb')
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
        
    def ascii_readlines(self):
        '''Write some ASCII data to the host and use readline
        operations to get it back.'''
        host = self.host
        # write some data
        local_data = 'line 1\nanother line\nyet another line'
        self.write_test_data(local_data, 'w')
        input_ = host.file(self.remote_name, 'r')
        data = input_.read(3)
        self.assertEqual(data, 'lin')
        data = input_.readlines()
        self.assertEqual(data, ['e 1\n', 'another line\n',
                                'yet another line'])
        input_.close()
        
    def test_read_from_host(self):
        '''Test _FTPFile.read*'''
        host = self.host
        host.chdir(self.testdir)
        self.remote_name = '__test.dat'
        # try to read a file which isn't there
        self.assertRaises(ftputil.FTPIOError, host.file,
                          'notthere', 'r')
        self.ascii_read()
        self.ascii_readline()
        self.binary_readline()
        self.ascii_readlines()
        # clean up
        host.remove(self.remote_name)
        host.chdir(self.rootdir)

    def test_remote_copy(self):
        '''Make a copy on the remote host.'''
        host = self.host
        host.chdir(self.testdir)
        self.remote_name = '__test.dat'
        local_data = '\000a\001b\r\n\002c\003\n\004\r\005'
        # write later source data
        self.write_test_data(local_data, 'wb')
        # build paths
        source_path = self.remote_name
        host.mkdir('__test2')
        target_path = host.path.join('__test2',
                                     self.remote_name)
        # make file objects
        source = host.file(source_path, 'rb')
        target = host.file(target_path, 'wb')
        # copy
        host.copyfileobj(source, target)
        source.close()
        target.close()
        # read copy and check against original data
        input_ = host.file(target_path, 'rb')
        data = input_.read()
        input_.close()
        self.assertEqual(local_data, data)
        # clean up
        host.remove(target_path)
        host.rmdir('__test2')
        host.unlink(source_path)
        host.chdir(self.rootdir)
        
    def test_upload_download(self):
        '''Test FTPHost.upload/download.'''
        host = self.host
        local_source = 'ftputil.py'
        local_test_path = '__test.dat'
        remote_path = host.path.join(self.testdir,
                                     'ftputil2.py')
        # test ascii up/download
        host.upload(local_source, remote_path)
        host.download(remote_path, local_test_path)
        # compare local data
        input_ = file(local_source)
        original = input_.read()
        input_.close()
        input_ = file(local_test_path)
        copy = input_.read()
        input_.close()
        self.assertEqual(original, copy)
        # test binary up/download
        host.upload(local_source, remote_path, 'b')
        host.download(remote_path, local_test_path, 'b')
        # compare local data
        input_ = file(local_source, 'rb')
        original = input_.read()
        input_.close()
        input_ = file(local_test_path, 'rb')
        copy = input_.read()
        input_.close()
        self.assertEqual(original, copy)
        # clean up
        host.remove(remote_path)
        os.remove(local_test_path)


if __name__ == '__main__':
    host_name = 'ftp.ndh.net'
    user = 'sschwarzer'
    password = getpass.getpass('Password for %s@%s: ' % 
                               (user, host_name) )
    unittest.main()

