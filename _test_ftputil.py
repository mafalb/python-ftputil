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


class Base(unittest.TestCase):
    '''Base class for some test classes.'''

    def setUp(self):
        host_name = 'ftp.ndh.net'
        user = 'sschwarzer'
        self.host = ftputil.FTPHost(host_name, user, password)
        self.testdir = '__test1'
        self.host.mkdir(self.testdir)
        self.rootdir = self.host.getcwd()

    def tearDown(self):
        host = self.host
        host.chdir(self.rootdir)
        host.rmdir(self.testdir)
        host.close()


class TestLoginAndClose(unittest.TestCase):
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


class TestDirectories(Base):
    '''Getting, making, changing, deleting directories.'''

    def test_get_change(self):
        '''Change directory and get the value.'''
        host = self.host
        self.assertEqual( host.getcwd(), self.rootdir )
        host.chdir(self.testdir)
        self.assertEqual( host.getcwd(),
          host.path.join(self.rootdir, self.testdir) )

    def test_mkdir(self):
        '''Dirs must be constructed on the host.'''
        host = self.host
        # use invalid directory name (__test2 doesn't exist)
        self.assertRaises( host.mkdir, host.path.join(
          self.rootdir, '__test2', '__test3') )
        # this is valid
        host.mkdir( host.path.join(self.rootdir, self.testdir,
                    '__test2') )
        # repeat first mkdir (now valid)
        host.mkdir( host.path.join(self.rootdir, '__test2',
                    '__test3') )
        # clean up for this test
        host.rmdir( host.path.join(self.rootdir, '__test2',
                    '__test3') )
        host.rmdir( host.path.join(self.rootdir, '__test2') )


class TestStat(Base):
    pass

class TestPath(Base):
    pass

class TestFiles(unittest.TestCase):
    pass


if __name__ == '__main__':
    password = getpass.getpass(
               'Password for sschwarzer@ftp.ndh.net: ')
    unittest.main()

