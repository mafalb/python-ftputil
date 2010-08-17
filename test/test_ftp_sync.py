# Copyright (C) 2007-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

import os
import shutil
import sys
import unittest

import ftp_sync


# Assume the test subdirectories are or will be in the current directory
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

