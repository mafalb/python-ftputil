# Copyright (C) 2006, Stefan Schwarzer
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

import unittest

import ftp_stat_cache


class TestStatCache(unittest.TestCase):
    def setUp(self):
        self.cache = ftp_stat_cache.StatCache()

    def test_get_set(self):
        self.assertRaises(ftp_stat_cache.CacheMissError,
                          self.cache.__getitem__, "path")
        self.cache["path"] = "test"
        self.assertEqual(self.cache["path"], "test")

    def test_invalidate(self):
        # don't raise a `CacheMissError` for missing paths
        self.cache.invalidate("test")
        self.cache["path"] = "test"
        self.cache.invalidate("path")
        self.assertEqual(len(self.cache), 0)

    def test_clear(self):
        self.cache["path1"] = "test1"
        self.cache["path2"] = "test2"
        self.cache.clear()
        self.assertEqual(len(self.cache), 0)

    def test_contains(self):
        self.cache["path1"] = "test1"
        self.assertEqual("path1" in self.cache, True)
        self.assertEqual("path2" in self.cache, False)

    def test_len(self):
        self.assertEqual(len(self.cache), 0)
        self.cache["path1"] = "test1"
        self.cache["path2"] = "test2"
        self.assertEqual(len(self.cache), 2)

    def test_disabled(self):
        self.cache["path1"] = "test1"
        self.cache.disable()
        self.cache["path2"] = "test2"
        self.assertEqual(self.cache["path1"], "test1")
        self.assertRaises(ftp_stat_cache.CacheMissError,
                          self.cache.__getitem__, "path2")
        self.assertEqual(len(self.cache), 1)
        # don't raise a `CacheMissError` for missing paths
        self.cache.invalidate("path2")


if __name__ == '__main__':
    unittest.main()

