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
        # try to remove a directory
        #host.mkdir( host.path.join(self.testdir, '__test2') )
        
        # try to remove a file which is not there
        # remove a file and check if it's removed
        
    def test_rename(self):
        '''Test FTPHost.rename.'''
        pass
        

class TestDirectories(Base):
    '''Getting, making, changing, deleting directories.'''

    def test_getcwd_and_change(self):
        '''Test getcwd and chdir.'''
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
          host.path.join(self.rootdir, '__test2') )
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
    pass

class TestFiles(Base):
    pass


if __name__ == '__main__':
    host_name = 'ftp.ndh.net'
    user = 'sschwarzer'
    password = getpass.getpass('Password for %s@%s: ' % 
                               (user, host_name) )
    unittest.main()

