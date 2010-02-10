# Copyright (C) 2007-2010, Stefan Schwarzer
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

import os
import shutil
import sys
import unittest

import ftp_sync


# assume the test subdirectories are or will be in the current directory
TEST_ROOT = os.getcwd()


class TestLocalToLocal(unittest.TestCase):
    def setUp(self):
        if not os.path.exists("test_empty"):
            os.mkdir("test_empty")
        if os.path.exists("test_target"):
            shutil.rmtree("test_target")
        os.mkdir("test_target")

    def test_sync_empty_dir(self):
        source = ftp_sync.LocalHost()
        target = ftp_sync.LocalHost()
        syncer = ftp_sync.Syncer(source, target)
        source_dir = os.path.join(TEST_ROOT, "test_empty")
        target_dir = os.path.join(TEST_ROOT, "test_target")
        syncer.sync(source_dir, target_dir)

    def test_source_with_and_target_without_slash(self):
        source = ftp_sync.LocalHost()
        target = ftp_sync.LocalHost()
        syncer = ftp_sync.Syncer(source, target)
        source_dir = os.path.join(TEST_ROOT, "test_source/")
        target_dir = os.path.join(TEST_ROOT, "test_target")
        syncer.sync(source_dir, target_dir)


if __name__ == '__main__':
    unittest.main()

