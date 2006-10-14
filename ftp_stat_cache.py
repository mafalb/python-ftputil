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


class CacheMissError(Exception):
    pass


class StatCache(object):
    def __init__(self):
        self._cache = {}
        self._debug = False
        self.enable()

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def clear(self):
        self._cache.clear()

    def invalidate(self, path):
        try:
            del self._cache[path]
        except KeyError:
            pass

    def __getitem__(self, path):
        """
        Return the stat entry for the `path`. If there's no stored
        stat entry, raise `CacheMissError`.
        """
        try:
            lines = self._cache[path]
            self._debug_output("Requested path %s ... found" % path)
            return lines
        except KeyError:
            self._debug_output("Requested path %s ... _not_ found" % path)
            raise CacheMissError("no path %s in cache" % path)

    def __setitem__(self, path, stat_result):
        if not self._enabled:
            return
        self._cache[path] = stat_result
        self._debug_output("Set path %s" % path)
        self._debug_output("%d cache entries" % len(self))

    def __contains__(self, path):
        return (path in self._cache)

    #
    # the following methods are only intended for debugging!
    #
    def _debug_output(self, text):
        if self._debug:
            print "***", text

    def __len__(self):
        return len(self._cache)

    def __str__(self):
        lines = []
        for key in sorted(self._cache):
            lines.append("%s: %s" % (key, self[key]))
        return "\n".join(lines)

