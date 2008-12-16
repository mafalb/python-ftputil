# Copyright (C) 2008, Roger Demetrescu, Stefan Schwarzer
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

# $Id: _test_with_statement.py 689 2007-04-16 01:07:10Z schwa $

from __future__ import with_statement

import unittest

import _test_base
import ftp_error

from _test_ftputil import FailOnLoginSession
from _test_ftp_file import InaccessibleDirSession, ReadMockSession


# exception raised by client code, i. e. code using ftputil
class ClientCodeException(Exception):
    pass


#
# test cases
#
class TestHostContextManager(unittest.TestCase):
    def test_normal_operation(self):
        with _test_base.ftp_host_factory() as host:
            self.assertEqual(host.closed, False)
        self.assertEqual(host.closed, True)

    def test_ftputil_exception(self):
        try:
            with _test_base.ftp_host_factory(FailOnLoginSession) as host:
                pass
        except ftp_error.FTPOSError:
            # we arrived here, that's fine
            # because the `FTPHost` object wasn't successfully constructed
            #  the assignment to `host` shouldn't have happened
            self.failIf('host' in locals())
        else:
            raise self.failureException("ftp_error.FTPOSError not raised")

    def test_client_code_exception(self):
        try:
            with _test_base.ftp_host_factory() as host:
                self.assertEqual(host.closed, False)
                raise ClientCodeException()
        except ClientCodeException:
            self.assertEqual(host.closed, True)
        else:
            raise self.failureException("ClientCodeException not raised")


class TestFileContextManager(unittest.TestCase):
    def test_normal_operation(self):
        with _test_base.ftp_host_factory(session_factory=ReadMockSession) \
             as host:
            with host.file('dummy', 'r') as f:
                self.assertEqual(f.closed, False)
                data = f.readline()
                self.assertEqual(data, 'line 1\n')
                self.assertEqual(f.closed, False)
            self.assertEqual(f.closed, True)

    def test_ftputil_exception(self):
        with _test_base.ftp_host_factory(
               session_factory=InaccessibleDirSession) as host:
            try:
                # this should fail since the directory isn't accessible
                #  by definition
                with host.file('/inaccessible/new_file', 'w') as f:
                    pass
            except ftp_error.FTPIOError:
                # the file construction didn't succeed, so `f` should
                #  be absent from the namespace
                self.failIf('f' in locals())
            else:
                raise self.failureException("ftp_error.FTPIOError not raised")

    def test_client_code_exception(self):
        with _test_base.ftp_host_factory(session_factory=ReadMockSession) \
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

