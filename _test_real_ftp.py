# Copyright (C) 2003-2007, Stefan Schwarzer
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

def utc_local_time_shift():
    """
    Return the expected time shift in seconds assuming the server
    uses UTC in its listings and the client uses local time.

    This is needed because Pure-FTPd meanwhile seems to insist that
    the displayed time for files is in UTC.
    """
    utc_tuple = time.gmtime()
    localtime_tuple = time.localtime()
    # to calculate the correct times shift, we need to ignore the
    #  DST component in the localtime tuple, i. e. set it to 0
    localtime_tuple = localtime_tuple[:-1] + (0,)
    time_shift_in_seconds = time.mktime(utc_tuple) - \
                            time.mktime(localtime_tuple)
    # to be safe, round the above value to units of 3600 s (1 h)
    return round(time_shift_in_seconds / 3600.0) * 3600

# difference between local times of server and client; if 0.0, server
#  and client use the same timezone
EXPECTED_TIME_SHIFT = utc_local_time_shift()


class RealFTPTest(unittest.TestCase):
    def setUp(self):
        self.host = ftputil.FTPHost(server, user, password)

    def tearDown(self):
        self.host.close()

    def make_file(self, path):
        file_ = self.host.file(path, 'wb')
        file_.close()

    def test_open_for_reading(self):
        # test for issue #17, http://ftputil.sschwarzer.net/trac/ticket/17
        file1 = self.host.file("debian-keyring.tar.gz", 'rb')
        file1.close()
        # make sure that there are no problems if the connection is reused
        file2 = self.host.file("debian-keyring.tar.gz", 'rb')
        file2.close()
        self.failUnless(file1._session is file2._session)

    def test_time_shift(self):
        self.host.synchronize_times()
        self.assertEqual(self.host.time_shift(), EXPECTED_TIME_SHIFT)

    def test_names_with_spaces(self):
        # test if directories and files with spaces in their names
        #  can be used
        host = self.host
        self.failUnless(host.path.isdir("dir with spaces"))
        self.assertEqual(host.listdir("dir with spaces"),
                         ['second dir', 'some file', 'some_file'])
        self.failUnless(host.path.isdir("dir with spaces/second dir"))
        self.failUnless(host.path.isfile("dir with spaces/some_file"))
        self.failUnless(host.path.isfile("dir with spaces/some file"))
        host.close()

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
        # no `_dir1_` yet
        self.failIf('_dir1_' in host.listdir(host.curdir))
        # vanilla case, all should go well
        host.makedirs('_dir1_/dir2/dir3/dir4')
        # check host
        self.failUnless(host.path.isdir('_dir1_'))
        self.failUnless(host.path.isdir('_dir1_/dir2'))
        self.failUnless(host.path.isdir('_dir1_/dir2/dir3'))
        self.failUnless(host.path.isdir('_dir1_/dir2/dir3/dir4'))
        # clean up
        host.rmdir('_dir1_/dir2/dir3/dir4')
        host.rmdir('_dir1_/dir2/dir3')
        host.rmdir('_dir1_/dir2')
        host.rmdir('_dir1_')

    def test_makedirs_from_non_root_directory(self):
        # this is a testcase for issue #22, see
        #  http://ftputil.sschwarzer.net/trac/ticket/22
        host = self.host
        # no `_dir1_` and `_dir2_` yet
        self.failIf('_dir1_' in host.listdir(host.curdir))
        self.failIf('_dir2_' in host.listdir(host.curdir))
        # part 1: try to make directories starting from `_dir1_`
        # make and change to non-root directory
        host.mkdir('_dir1_')
        host.chdir('_dir1_')
        host.makedirs('_dir2_/_dir3_')
        # test for expected directory hierarchy
        self.failUnless(host.path.isdir('/_dir1_'))
        self.failUnless(host.path.isdir('/_dir1_/_dir2_'))
        self.failUnless(host.path.isdir('/_dir1_/_dir2_/_dir3_'))
        self.failIf(host.path.isdir('/_dir1_/_dir1_'))
        # remove all but the directory were in
        host.rmdir('/_dir1_/_dir2_/_dir3_')
        host.rmdir('/_dir1_/_dir2_')
        # part 2: try to make directories starting from root
        host.makedirs('/_dir2_/_dir3_')
        # test for expected directory hierarchy
        self.failUnless(host.path.isdir('/_dir2_'))
        self.failUnless(host.path.isdir('/_dir2_/_dir3_'))
        self.failIf(host.path.isdir('/_dir1_/_dir2_'))
        # clean up
        host.rmdir('/_dir2_/_dir3_')
        host.rmdir('/_dir2_')
        host.chdir(host.pardir)
        host.rmdir('/_dir1_')

    def test_makedirs_from_non_root_directory_fake_windows_os(self):
        saved_sep = os.sep
        os.sep = '\\'
        try:
            self.test_makedirs_from_non_root_directory()
        finally:
            os.sep = saved_sep

    def test_makedirs_of_existing_directory(self):
        host = self.host
        # the (chrooted) login directory
        host.makedirs('/')

    def test_makedirs_with_file_in_the_way(self):
        host = self.host
        host.mkdir('_dir1_')
        self.make_file('_dir1_/file1')
        # try it
        self.assertRaises(ftp_error.PermanentError, host.makedirs,
                          '_dir1_/file1')
        self.assertRaises(ftp_error.PermanentError, host.makedirs,
                          '_dir1_/file1/dir2')
        # clean up
        host.unlink('_dir1_/file1')
        host.rmdir('_dir1_')

    def test_makedirs_with_existing_directory(self):
        host = self.host
        host.mkdir('_dir1_')
        host.makedirs('_dir1_/dir2')
        # check
        self.failUnless(host.path.isdir('_dir1_'))
        self.failUnless(host.path.isdir('_dir1_/dir2'))
        # clean up
        host.rmdir('_dir1_/dir2')
        host.rmdir('_dir1_')

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
        host.makedirs('_dir1_/dir2')
        self.make_file('_dir1_/file1')
        self.make_file('_dir1_/file2')
        self.make_file('_dir1_/dir2/file3')
        self.make_file('_dir1_/dir2/file4')
        # try to remove a _file_ with `rmtree`
        self.assertRaises(ftp_error.PermanentError, host.rmtree, '_dir1_/file2')
        # remove dir2
        host.rmtree('_dir1_/dir2')
        self.failIf(host.path.exists('_dir1_/dir2'))
        self.failUnless(host.path.exists('_dir1_/file2'))
        # remake dir2 and remove _dir1_
        host.mkdir('_dir1_/dir2')
        self.make_file('_dir1_/dir2/file3')
        self.make_file('_dir1_/dir2/file4')
        host.rmtree('_dir1_')
        self.failIf(host.path.exists('_dir1_'))

    def test_rmtree_with_error_handler(self):
        host = self.host
        host.mkdir('_dir1_')
        self.make_file('_dir1_/file1')
        # prepare error "handler"
        log = []
        def error_handler(*args):
            log.append(args)
        # try to remove a file as root "directory"
        host.rmtree('_dir1_/file1', ignore_errors=True, onerror=error_handler)
        self.assertEqual(log, [])
        host.rmtree('_dir1_/file1', ignore_errors=False, onerror=error_handler)
        self.assertEqual(log[0][0], host.listdir)
        self.assertEqual(log[0][1], '_dir1_/file1')
        self.assertEqual(log[1][0], host.rmdir)
        self.assertEqual(log[1][1], '_dir1_/file1')
        host.rmtree('_dir1_')
        # try to remove a non-existent directory
        del log[:]
        host.rmtree('_dir1_', ignore_errors=False, onerror=error_handler)
        self.assertEqual(log[0][0], host.listdir)
        self.assertEqual(log[0][1], '_dir1_')
        self.assertEqual(log[1][0], host.rmdir)
        self.assertEqual(log[1][1], '_dir1_')

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
        host.synchronize_times()
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

    def test_concurrent_access(self):
        self.make_file("_testfile_")
        host1 = ftputil.FTPHost(server, user, password)
        host2 = ftputil.FTPHost(server, user, password)
        stat_result1 = host1.stat("_testfile_")
        stat_result2 = host2.stat("_testfile_")
        self.assertEqual(stat_result1, stat_result2)
        host2.remove("_testfile_")
        # can still get the result via `host1`
        stat_result1 = host1.stat("_testfile_")
        self.assertEqual(stat_result1, stat_result2)
        # stat'ing on `host2` gives an exception
        self.assertRaises(ftp_error.PermanentError, host2.stat, "_testfile_")
        # stat'ing on `host1` after invalidation
        absolute_path = host1.path.join(host1.getcwd(), "_testfile_")
        host1.stat_cache.invalidate(absolute_path)
        self.assertRaises(ftp_error.PermanentError, host1.stat, "_testfile_")
        # clean up
        host1.close()
        host2.close()

    def test_rename(self):
        host = self.host
        self.make_file("_testfile1_")
        host.rename("_testfile1_", "_testfile2_")
        self.failIf(host.path.exists("_testfile1_"))
        self.failUnless(host.path.exists("_testfile2_"))
        host.remove("_testfile2_")
        host.close()

    def test_rename_with_spaces_in_directory(self):
        host = self.host
        dir_name = "_dir with spaces_"
        host.mkdir(dir_name)
        self.make_file(dir_name + "/testfile1")
        host.rename(dir_name + "/testfile1", dir_name + "/testfile2")
        self.failIf(host.path.exists(dir_name + "/testfile1"))
        self.failUnless(host.path.exists(dir_name + "/testfile2"))
        host.remove(dir_name + "/testfile2")
        host.rmdir(dir_name)
        host.close()


if __name__ == '__main__':
    print """\
Test for real FTP access.

This test writes some files and directories on the local client and the
remote server. Thus, you may want to skip this test by pressing [Ctrl-C].
If the test should run, enter the login data for the remote server. You
need write access in the login directory. This test can last a few minutes
because it has to wait to test the timezone calculation.
"""
    try:
        raw_input("[Return] to continue, or [Ctrl-C] to skip test. ")
    except KeyboardInterrupt:
        print "\nTest aborted."
        sys.exit()
    # get login data only once, not for each test
    server, user, password = get_login_data()
    unittest.main()

