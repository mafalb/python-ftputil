# Copyright (C) 2003-2006, Stefan Schwarzer
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

# $Id$

# Execute a test on a real FTP server (other tests use a mock server)

import getpass
import os
import time
import unittest
import sys

import ftputil
from ftputil import ftp_error
from ftputil import ftp_stat

# difference between local times of server and client; if 0.0, server
#  and client are in the same timezone
EXPECTED_TIME_SHIFT = 0.0

def get_login_data():
    """
    Return a three-element tuple consisting of server name, user id
    and password. The data - used to be - requested interactively.
    """
    #server = raw_input("Server: ")
    #user = raw_input("User: ")
    #password = getpass.getpass()
    #return server, user, password
    return "localhost", 'ftptest', 'd605581757de5eb56d568a4419f4126e'


class RealFTPTest(unittest.TestCase):
    def setUp(self):
        self.host = ftputil.FTPHost(server, user, password)

    def tearDown(self):
        self.host.close()

    def make_file(self, path):
        file = self.host.file(path, 'wb')
        file.close()

    def test_time_shift(self):
        self.host.synchronize_times()
        self.assertEqual(self.host.time_shift(), EXPECTED_TIME_SHIFT)

    def test_mkdir_rmdir(self):
        host = self.host
        dir_name = "_testdir_"
        file_name = host.path.join(dir_name, "_nonempty_")
        # make dir and check if it's there
        host.mkdir(dir_name)
        files = host.listdir(host.curdir)
        self.failIf(dir_name not in files)
        # try to remove non-empty directory
        non_empty = host.file(file_name, "w")
        non_empty.close()
        self.assertRaises(ftp_error.PermanentError, host.rmdir, dir_name)
        # remove file
        host.unlink(file_name)
        # `remove` on a directory should fail
        try:
            try:
                host.remove(dir_name)
            except ftp_error.PermanentError, exc:
                self.failUnless(str(exc).startswith(
                                         "remove/unlink can only delete files"))
            else:
                self.failIf(True, "we shouldn't have come here")
        finally:
            # delete empty directory
            host.rmdir(dir_name)
        files = host.listdir(host.curdir)
        self.failIf(dir_name in files)

    def test_makedirs_without_existing_dirs(self):
        host = self.host
        # no `dir1` yet
        self.failIf('dir1' in host.listdir(host.curdir))
        # vanilla case, all should go well
        host.makedirs('dir1/dir2/dir3/dir4')
        # check host
        self.failUnless(host.path.isdir('dir1'))
        self.failUnless(host.path.isdir('dir1/dir2'))
        self.failUnless(host.path.isdir('dir1/dir2/dir3'))
        self.failUnless(host.path.isdir('dir1/dir2/dir3/dir4'))
        # clean up
        host.rmdir('dir1/dir2/dir3/dir4')
        host.rmdir('dir1/dir2/dir3')
        host.rmdir('dir1/dir2')
        host.rmdir('dir1')

    def test_makedirs_of_existing_directory(self):
        host = self.host
        # the (chrooted) login directory
        host.makedirs('/')

    def test_makedirs_with_file_in_the_way(self):
        host = self.host
        host.mkdir('dir1')
        self.make_file('dir1/file1')
        # try it
        self.assertRaises(ftp_error.PermanentError, host.makedirs, 'dir1/file1')
        self.assertRaises(ftp_error.PermanentError, host.makedirs,
                          'dir1/file1/dir2')
        # clean up
        host.unlink('dir1/file1')
        host.rmdir('dir1')

    def test_makedirs_with_existing_directory(self):
        host = self.host
        host.mkdir('dir1')
        host.makedirs('dir1/dir2')
        # check
        self.failUnless(host.path.isdir('dir1'))
        self.failUnless(host.path.isdir('dir1/dir2'))
        # clean up
        host.rmdir('dir1/dir2')
        host.rmdir('dir1')

    def test_makedirs_in_non_writable_directory(self):
        host = self.host
        # preparation: `rootdir1` exists but is only writable by root
        self.assertRaises(ftp_error.PermanentError, host.makedirs,
                          'rootdir1/dir2')

    def test_makedirs_with_writable_directory_at_end(self):
        host = self.host
        # preparation: `rootdir2` exists but is only writable by root;
        #  `dir2` is writable by regular ftp user
        # these both should work
        host.makedirs('rootdir2/dir2')
        host.makedirs('rootdir2/dir2/dir3')
        # clean up
        host.rmdir('rootdir2/dir2/dir3')

    def test_rmtree_without_error_handler(self):
        host = self.host
        # build a tree
        host.makedirs('dir1/dir2')
        self.make_file('dir1/file1')
        self.make_file('dir1/file2')
        self.make_file('dir1/dir2/file3')
        self.make_file('dir1/dir2/file4')
        # try to remove a _file_ with `rmtree`
        self.assertRaises(ftp_error.PermanentError, host.rmtree, 'dir1/file2')
        # remove dir2
        host.rmtree('dir1/dir2')
        self.failIf(host.path.exists('dir1/dir2'))
        self.failUnless(host.path.exists('dir1/file2'))
        # remake dir2 and remove dir1
        host.mkdir('dir1/dir2')
        self.make_file('dir1/dir2/file3')
        self.make_file('dir1/dir2/file4')
        host.rmtree('dir1')
        self.failIf(host.path.exists('dir1'))

    def test_rmtree_with_error_handler(self):
        host = self.host
        host.mkdir('dir1')
        self.make_file('dir1/file1')
        # prepare error "handler"
        log = []
        def error_handler(*args):
            log.append(args)
        # try to remove a file as root "directory"
        host.rmtree('dir1/file1', ignore_errors=True, onerror=error_handler)
        self.assertEqual(log, [])
        host.rmtree('dir1/file1', ignore_errors=False, onerror=error_handler)
        self.assertEqual(log[0][0], host.listdir)
        self.assertEqual(log[0][1], 'dir1/file1')
        self.assertEqual(log[1][0], host.rmdir)
        self.assertEqual(log[1][1], 'dir1/file1')
        host.rmtree('dir1')
        # try to remove a non-existent directory
        del log[:]
        host.rmtree('dir1', ignore_errors=False, onerror=error_handler)
        self.assertEqual(log[0][0], host.listdir)
        self.assertEqual(log[0][1], 'dir1')
        self.assertEqual(log[1][0], host.rmdir)
        self.assertEqual(log[1][1], 'dir1')

    def test_stat(self):
        host = self.host
        dir_name = "_testdir_"
        file_name = host.path.join(dir_name, "_nonempty_")
        # make a directory and a file in it
        host.mkdir(dir_name)
        fobj = host.file(file_name, "wb")
        fobj.write("abc\x12\x34def\t")
        fobj.close()
        # do some stats
        # - dir
        self.assertEqual(host.listdir(dir_name), ["_nonempty_"])
        self.assertEqual(bool(host.path.isdir(dir_name)), True)
        self.assertEqual(bool(host.path.isfile(dir_name)), False)
        self.assertEqual(bool(host.path.islink(dir_name)), False)
        # - file
        self.assertEqual(bool(host.path.isdir(file_name)), False)
        self.assertEqual(bool(host.path.isfile(file_name)), True)
        self.assertEqual(bool(host.path.islink(file_name)), False)
        self.assertEqual(host.path.getsize(file_name), 9)
        # - file's modification time; allow up to two minutes difference
        host.synchronize_times()
        server_mtime = host.path.getmtime(file_name)
        client_mtime = time.mktime(time.localtime())
        calculated_time_shift = server_mtime - client_mtime
        self.failIf(abs(calculated_time_shift-host.time_shift()) > 120)
        # clean up
        host.unlink(file_name)
        host.rmdir(dir_name)

    def make_local_file(self):
        fobj = file("_localfile_", "wb")
        fobj.write("abc\x12\x34def\t")
        fobj.close()

    def test_upload(self):
        host = self.host
        # make local file and upload it
        self.make_local_file()
        # wait; else small time differences between client and server
        #  actually could trigger the update
        time.sleep(60)
        host.upload("_localfile_", "_remotefile_", "b")
        # retry; shouldn't be uploaded
        uploaded = host.upload_if_newer("_localfile_", "_remotefile_", "b")
        self.assertEqual(uploaded, False)
        # rewrite the local file
        self.make_local_file()
        time.sleep(60)
        # retry; should be uploaded
        uploaded = host.upload_if_newer("_localfile_", "_remotefile_", "b")
        self.assertEqual(uploaded, True)
        # clean up
        os.unlink("_localfile_")
        host.unlink("_remotefile_")

    def test_walk_topdown(self):
        # preparation: build tree in directory `walk_test`
        host = self.host
        expected = [
          ('walk_test', ['dir1', 'dir2', 'dir3'], ['file4']),
          ('walk_test/dir1', ['dir11', 'dir12'], []),
          ('walk_test/dir1/dir11', [], []),
          ('walk_test/dir1/dir12', ['dir123'], ['file121', 'file122']),
          ('walk_test/dir1/dir12/dir123', [], ['file1234']),
          ('walk_test/dir2', [], []),
          ('walk_test/dir3', ['dir33'], ['file31', 'file32']),
          ('walk_test/dir3/dir33', [], []),
          ]
        # collect data, using `walk`
        actual = []
        for items in host.walk('walk_test'):
            actual.append(items)
        # compare with expected results
        self.assertEqual(len(actual), len(expected))
        for index in range(len(actual)):
            self.assertEqual(actual[index], expected[index])

    def test_walk_depth_first(self):
        # preparation: build tree in directory `walk_test`
        host = self.host
        expected = [
          ('walk_test/dir1/dir11', [], []),
          ('walk_test/dir1/dir12/dir123', [], ['file1234']),
          ('walk_test/dir1/dir12', ['dir123'], ['file121', 'file122']),
          ('walk_test/dir1', ['dir11', 'dir12'], []),
          ('walk_test/dir2', [], []),
          ('walk_test/dir3/dir33', [], []),
          ('walk_test/dir3', ['dir33'], ['file31', 'file32']),
          ('walk_test', ['dir1', 'dir2', 'dir3'], ['file4'])
          ]
        # collect data, using `walk`
        actual = []
        for items in host.walk('walk_test', topdown=False):
            actual.append(items)
        # compare with expected results
        self.assertEqual(len(actual), len(expected))
        for index in range(len(actual)):
            self.assertEqual(actual[index], expected[index])

    def test_keep_connection(self):
        # adjust server timeout (in seconds) here
        server_timeout = 3 * 60.0
        # host
        host = self.host
        host.keep_alive()
        # prepare file to read (below)
        written_file = host.file("_test_file_", "w")
        written_file.write("Test")
        written_file.close()
        # open files
        read_file = host.file("_test_file_", "r")
        written_file = host.file("_test_file2_", "w")
        written_file.write("x")
        stale_read_file = host.file("_test_file_")
        stale_written_file = host.file("_test_file3_", "w")
        stale_read_file.close()
        stale_written_file.write("abc")
        stale_written_file.close()
        try:
            # wait for would-be connection timeout (plus a bit more, to be sure)
            interval_length = 30.0
            intervals = int(server_timeout / interval_length) + 2
            for i in range(intervals):
                print "Keeping host alive (%d of %d) " % (i+1, intervals)
                host.keep_alive(ignore_errors=True)
                self.assertRaises(ftp_error.KeepAliveError, host.keep_alive)
                # open written files can't be "kept alive",
                #  so cause some activity
                written_file.write("x")
                written_file.flush()
                time.sleep(interval_length)
            # do some tests; order of statements is important
            # - access the open files (must be left open so that the stale
            #   files get reused)
            self.assertEqual(read_file.read(2), "Te")
            # - try to reuse the stale files
            written_file2 = host.file("_test_file3_", "w")
            read_file2 = host.file("_test_file_")
            written_file2.write("blah")
            self.assertEqual(read_file2.read(2), "Te")
            written_file2.close()
            read_file2.close()
            read_file.close()
            written_file.close()
        finally:
            # clean up
            host.remove("_test_file_")
            host.remove("_test_file2_")
            host.remove("_test_file3_")


if __name__ == '__main__':
    print """\
Test for real FTP access.

This test writes some files and directories on the local client and the
remote server. Thus, you may want to skip this test by pressing [Ctrl-C].
If the test should run, enter the login data for the remote server. You
need write access in the login directory. This test can last a few minutes.
"""
    try:
        raw_input("[Return] to continue, or [Ctrl-C] to skip test. ")
    except KeyboardInterrupt:
        print "\nTest aborted."
        sys.exit()
    # get login data only once, not for each test
    server, user, password = get_login_data()
    unittest.main()

