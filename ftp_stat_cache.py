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

"""
ftp_stat_cache.py - cache for (l)stat data
"""

import lrucache


class CacheMissError(Exception):
    pass


class StatCache(object):
    _CACHE_SIZE = 5000

    def __init__(self):
        # number of cache entries
        self._cache = lrucache.LRUCache(self._CACHE_SIZE)
        self._debug = False
        self.enable()

    def enable(self):
        """Enable storage of stat results."""
        self._enabled = True

    def disable(self):
        """
        Disable the cache. Further storage attempts with `__setitem__`
        won't have any visible effect.

        Disabling the cache only effects new storage attempts. Values
        stored before calling `disable` can still be retrieved.
        """
        self._enabled = False

    def clear(self):
        """Clear (invalidate) all cache entries."""
        # implicitly clear the cache by setting the size to zero
        self._cache.size = 0
        self._cache.size = self._CACHE_SIZE

    def invalidate(self, path):
        """
        Invalidate the cache entry for `path` if present. After
        that, the stat result data for `path` can no longer be
        retrieved, as if it had never been stored.

        If no stat result for `path` is in the cache, do _not_
        raise an exception.
        """
        try:
            del self._cache[path]
        except lrucache.CacheKeyError:
            pass

    def __getitem__(self, path):
        """
        Return the stat entry for the `path`. If there's no stored
        stat entry, raise `CacheMissError`.
        """
        try:
            stat_result = self._cache[path]
            self._debug_output("Requested path %s ... found" % path)
            return stat_result
        except lrucache.CacheKeyError:
            self._debug_output("Requested path %s ... _not_ found" % path)
            raise CacheMissError("no path %s in cache" % path)

    def __setitem__(self, path, stat_result):
        """
        Put the stat data for `path` into the cache, unless it's
        disabled.
        """
        if not self._enabled:
            return
        self._cache[path] = stat_result
        self._debug_output("Set path %s" % path)
        self._debug_output("%d cache entries" % len(self))

    def __contains__(self, path):
        """
        Support for the `in` operator. Return a true value, if data
        for `path` is in the cache, else return a false value.
        """
        return (path in self._cache)

    #
    # the following methods are only intended for debugging!
    #
    def _debug_output(self, text):
        if self._debug:
            print "***", text

    def __len__(self):
        """Return the number of entries in the cache."""
        return len(self._cache)

    def __str__(self):
        """Return a string representation of the cache contents."""
        lines = []
        for key in sorted(self._cache):
            lines.append("%s: %s" % (key, self[key]))
        return "\n".join(lines)

