# coding: utf-8
# Copyright (C) 2002-2009, Stefan Schwarzer
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

import ftplib
import unittest

import ftp_error


class TestFTPErrorArguments(unittest.TestCase):
    def test_bytestring_argument(self):
        # a umlaut as latin-1 character
        os_error = ftp_error.FTPOSError("\xe4")

    def test_unicode_argument(self):
        # a umlaut as unicode character
        io_error = ftp_error.FTPIOError(u"\xe4")


class TestTryWithFTPError(unittest.TestCase):
    def callee(self):
        raise ftplib.error_perm()

    def test_try_with_oserror(self):
        "Ensure the `ftplib` exception isn't used as `FTPOSError` argument."
        try:
            ftp_error._try_with_oserror(self.callee)
        except ftp_error.FTPOSError, exc:
            pass
        self.failIf(exc.args and isinstance(exc.args[0], ftplib.error_perm))

    def test_try_with_ioerror(self):
        "Ensure the `ftplib` exception isn't used as `FTPIOError` argument."
        try:
            ftp_error._try_with_ioerror(self.callee)
        except ftp_error.FTPIOError, exc:
            pass
        self.failIf(exc.args and isinstance(exc.args[0], ftplib.error_perm))


if __name__ == '__main__':
    unittest.main()

