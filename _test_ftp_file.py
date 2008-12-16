# Copyright (C) 2002-2008, Stefan Schwarzer
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

# $Id: $

import ftplib
import operator
import unittest

import _mock_ftplib
import _test_base
import ftp_error
import ftp_file


#
# several customized `MockSession` classes
#
class ReadMockSession(_mock_ftplib.MockSession):
    mock_file_content = 'line 1\r\nanother line\r\nyet another line'

class AsciiReadMockSession(_mock_ftplib.MockSession):
    mock_file_content = '\r\n'.join(map(str, range(20)))

class InaccessibleDirSession(_mock_ftplib.MockSession):
    _login_dir = '/inaccessible'

    def pwd(self):
        return self._login_dir

    def cwd(self, dir):
        if dir in (self._login_dir, self._login_dir + '/'):
            raise ftplib.error_perm
        else:
            _mock_ftplib.MockSession.cwd(self, dir)


class TestFileOperations(unittest.TestCase):
    """Test operations with file-like objects."""
    def test_inaccessible_dir(self):
        """Test whether opening a file at an invalid location fails."""
        host = _test_base.ftp_host_factory(
               session_factory=InaccessibleDirSession)
        self.assertRaises(ftp_error.FTPIOError, host.file,
                          '/inaccessible/new_file', 'w')

    def test_caching(self):
        """Test whether `_FTPFile` cache of `FTPHost` object works."""
        host = _test_base.ftp_host_factory()
        self.assertEqual(len(host._children), 0)
        path1 = 'path1'
        path2 = 'path2'
        # open one file and inspect cache
        file1 = host.file(path1, 'w')
        child1 = host._children[0]
        self.assertEqual(len(host._children), 1)
        self.failIf(child1._file.closed)
        # open another file
        file2 = host.file(path2, 'w')
        child2 = host._children[1]
        self.assertEqual(len(host._children), 2)
        self.failIf(child2._file.closed)
        # close first file
        file1.close()
        self.assertEqual(len(host._children), 2)
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
        host = _test_base.ftp_host_factory()
        self.assertRaises(ftp_error.FTPIOError, host.file,
                          '/home/sschwarzer', 'w')

    def test_binary_write(self):
        """Write binary data with `write`."""
        host = _test_base.ftp_host_factory()
        data = '\000a\001b\r\n\002c\003\n\004\r\005'
        output = host.file('dummy', 'wb')
        output.write(data)
        output.close()
        child_data = _mock_ftplib.content_of('dummy')
        expected_data = data
        self.assertEqual(child_data, expected_data)

    def test_ascii_write(self):
        """Write ASCII text with `write`."""
        host = _test_base.ftp_host_factory()
        data = ' \nline 2\nline 3'
        output = host.file('dummy', 'w')
        output.write(data)
        output.close()
        child_data = _mock_ftplib.content_of('dummy')
        expected_data = ' \r\nline 2\r\nline 3'
        self.assertEqual(child_data, expected_data)

    def test_ascii_writelines(self):
        """Write ASCII text with `writelines`."""
        host = _test_base.ftp_host_factory()
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
        """Read ASCII text with plain `read`."""
        host = _test_base.ftp_host_factory(session_factory=ReadMockSession)
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
        #  makes several reads in the `read` method necessary
        host = _test_base.ftp_host_factory(session_factory=AsciiReadMockSession)
        expected_data = AsciiReadMockSession.mock_file_content.\
                        replace('\r\n', '\n')
        input_ = host.file('dummy', 'r')
        data = input_.read(len(expected_data))
        self.assertEqual(data, expected_data)

    def test_binary_readline(self):
        """Read binary data with `readline`."""
        host = _test_base.ftp_host_factory(session_factory=ReadMockSession)
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

    def test_ascii_readline(self):
        """Read ASCII text with `readline`."""
        host = _test_base.ftp_host_factory(session_factory=ReadMockSession)
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

    def test_ascii_readlines(self):
        """Read ASCII text with `readlines`."""
        host = _test_base.ftp_host_factory(session_factory=ReadMockSession)
        input_ = host.file('dummy', 'r')
        data = input_.read(3)
        self.assertEqual(data, 'lin')
        data = input_.readlines()
        self.assertEqual(data, ['e 1\n', 'another line\n',
                                'yet another line'])
        input_.close()

    def test_ascii_xreadlines(self):
        """Read ASCII text with `xreadlines`."""
        host = _test_base.ftp_host_factory(session_factory=ReadMockSession)
        # open file, skip some bytes
        input_ = host.file('dummy', 'r')
        data = input_.read(3)
        xrl_obj = input_.xreadlines()
        self.failUnless(xrl_obj.__class__ is ftp_file._XReadlines)
        self.failUnless(xrl_obj._ftp_file.__class__ is ftp_file._FTPFile)
        data = xrl_obj[0]
        self.assertEqual(data, 'e 1\n')
        # try to skip an index
        self.assertRaises(RuntimeError, operator.__getitem__, xrl_obj, 2)
        # continue reading
        data = xrl_obj[1]
        self.assertEqual(data, 'another line\n')
        data = xrl_obj[2]
        self.assertEqual(data, 'yet another line')
        # try to read beyond EOF
        self.assertRaises(IndexError, operator.__getitem__, xrl_obj, 3)

    def test_binary_iterator(self):
        """Test the iterator interface of `FTPFile` objects."""
        host = _test_base.ftp_host_factory(session_factory=ReadMockSession)
        input_ = host.file('dummy')
        input_iterator = iter(input_)
        self.assertEqual(input_iterator.next(), "line 1\n")
        self.assertEqual(input_iterator.next(), "another line\n")
        self.assertEqual(input_iterator.next(), "yet another line")
        self.assertRaises(StopIteration, input_iterator.next)
        input_.close()

    def test_ascii_iterator(self):
        """Test the iterator interface of `FTPFile` objects."""
        host = _test_base.ftp_host_factory(session_factory=ReadMockSession)
        input_ = host.file('dummy', 'rb')
        input_iterator = iter(input_)
        self.assertEqual(input_iterator.next(), "line 1\r\n")
        self.assertEqual(input_iterator.next(), "another line\r\n")
        self.assertEqual(input_iterator.next(), "yet another line")
        self.assertRaises(StopIteration, input_iterator.next)
        input_.close()

    def test_read_unknown_file(self):
        """Test whether reading a file which isn't there fails."""
        host = _test_base.ftp_host_factory()
        self.assertRaises(ftp_error.FTPIOError, host.file, 'notthere', 'r')


if __name__ == '__main__':
    unittest.main()

