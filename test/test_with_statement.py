# Copyright (C) 2008, Roger Demetrescu <roger.demetrescu@gmail.com>
# Copyright (C) 2008, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

from __future__ import with_statement

import unittest

import ftp_error

import test_base
from test_ftputil import FailOnLoginSession
from test_ftp_file import InaccessibleDirSession, ReadMockSession


# Exception raised by client code, i. e. code using ftputil
class ClientCodeException(Exception):
    pass


#
# Test cases
#
class TestHostContextManager(unittest.TestCase):

    def test_normal_operation(self):
        with test_base.ftp_host_factory() as host:
            self.assertEqual(host.closed, False)
        self.assertEqual(host.closed, True)

    def test_ftputil_exception(self):
        try:
            with test_base.ftp_host_factory(FailOnLoginSession) as host:
                pass
        except ftp_error.FTPOSError:
            # We arrived here, that's fine. Because the `FTPHost` object
            #  wasn't successfully constructed the assignment to `host`
            #  shouldn't have happened.
            self.failIf('host' in locals())
        else:
            raise self.failureException("ftp_error.FTPOSError not raised")

    def test_client_code_exception(self):
        try:
            with test_base.ftp_host_factory() as host:
                self.assertEqual(host.closed, False)
                raise ClientCodeException()
        except ClientCodeException:
            self.assertEqual(host.closed, True)
        else:
            raise self.failureException("ClientCodeException not raised")


class TestFileContextManager(unittest.TestCase):

    def test_normal_operation(self):
        with test_base.ftp_host_factory(session_factory=ReadMockSession) \
             as host:
            with host.file('dummy', 'r') as f:
                self.assertEqual(f.closed, False)
                data = f.readline()
                self.assertEqual(data, 'line 1\n')
                self.assertEqual(f.closed, False)
            self.assertEqual(f.closed, True)

    def test_ftputil_exception(self):
        with test_base.ftp_host_factory(
               session_factory=InaccessibleDirSession) as host:
            try:
                # This should fail since the directory isn't accessible
                #  by definition.
                with host.file('/inaccessible/new_file', 'w') as f:
                    pass
            except ftp_error.FTPIOError:
                # The file construction didn't succeed, so `f` should
                #  be absent from the namespace.
                self.failIf('f' in locals())
            else:
                raise self.failureException("ftp_error.FTPIOError not raised")

    def test_client_code_exception(self):
        with test_base.ftp_host_factory(session_factory=ReadMockSession) \
             as host:
            try:
                with host.file('dummy', 'r') as f:
                    self.assertEqual(f.closed, False)
                    raise ClientCodeException()
            except ClientCodeException:
                self.assertEqual(f.closed, True)
            else:
                raise self.failureException("ClientCodeException not raised")


if __name__ == '__main__':
    unittest.main()

