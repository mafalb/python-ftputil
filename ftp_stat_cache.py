# Copyright (C) 2006-2009, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

"""
ftp_stat_cache.py - cache for (l)stat data
"""

import time

import lrucache


#TODO Move this to `ftp_error.py`!
class CacheMissError(Exception):
    """Raised if a path isn't found in the cache."""
    pass


class StatCache(object):
    """
    Implement an LRU (least-recently-used) cache.

    `StatCache` objects have an attribute `max_age`. After this
    duration after _setting_ it a cache entry will expire. For
    example, if you code

    my_cache = StatCache()
    my_cache.max_age = 10
    my_cache["/home"] = ...

    the value my_cache["/home"] can be retrieved for 10 seconds. After
    that, the entry will be treated as if it had never been in the
    cache and should be fetched again from the remote host.

    Note that the `__len__` method does no age tests and thus may
    include some or many already expired entries.
    """
    # Default number of cache entries
    _DEFAULT_CACHE_SIZE = 1000

    def __init__(self):
        # Can be reset with method `resize`
        self._cache = lrucache.LRUCache(self._DEFAULT_CACHE_SIZE)
        # Never expire
        self.max_age = None
        self.enable()

    def enable(self):
        """Enable storage of stat results."""
        # `enable` is called by `__init__`, so it's not set outside `__init__`
        # pylint: disable-msg=W0201
        self._enabled = True

    def disable(self):
        """
        Disable the cache. Further storage attempts with `__setitem__`
        won't have any visible effect.

        Disabling the cache only effects new storage attempts. Values
        stored before calling `disable` can still be retrieved unless
        disturbed by a `resize` command or normal cache expiration.
        """
        self._enabled = False

    def resize(self, new_size):
        """
        Set number of cache entries to the integer `new_size`.
        If the new size is greater than the current cache size,
        relatively long-unused elements will be removed.
        """
        self._cache.size = new_size

    def _age(self, path):
        """
        Return the age of a cache entry for `path` in seconds. If
        the path isn't in the cache, raise a `CacheMissError`.
        """
        try:
            return time.time() - self._cache.mtime(path)
        except lrucache.CacheKeyError:
            raise CacheMissError("no entry for path %s in cache" % path)

    def clear(self):
        """Clear (invalidate) all cache entries."""
        old_size = self._cache.size
        try:
            # Implicitly clear the cache by setting the size to zero
            self.resize(0)
        finally:
            self.resize(old_size)

    def invalidate(self, path):
        """
        Invalidate the cache entry for the absolute `path` if present.
        After that, the stat result data for `path` can no longer be
        retrieved, as if it had never been stored.

        If no stat result for `path` is in the cache, do _not_
        raise an exception.
        """
        #XXX To be 100 % sure, this should be `host.sep`, but I don't
        #  want to introduce a reference to the `FTPHost` object for
        #  only that purpose.
        assert path.startswith("/"), "%s must be an absolute path" % path
        try:
            del self._cache[path]
        # Don't complain about lazy except clause
        # pylint: disable-msg=W0704
        except lrucache.CacheKeyError:
            # Ignore errors
            pass

    def __getitem__(self, path):
        """
        Return the stat entry for the `path`. If there's no stored
        stat entry or the cache is disabled, raise `CacheMissError`.
        """
        if not self._enabled:
            raise CacheMissError("cache is disabled")
        # Possibly raise a `CacheMissError` in `_age`
        if (self.max_age is not None) and (self._age(path) > self.max_age):
            self.invalidate(path)
            raise CacheMissError("entry for path %s has expired" % path)
        else:
            #XXX I don't know if this may raise a `CacheMissError` in
            #  case of race conditions. I prefer robust code.
            try:
                return self._cache[path]
            except lrucache.CacheKeyError:
                raise CacheMissError("entry for path %s not found" % path)

    def __setitem__(self, path, stat_result):
        """
        Put the stat data for `path` into the cache, unless it's
        disabled.
        """
        if not self._enabled:
            return
        self._cache[path] = stat_result

    def __contains__(self, path):
        """
        Support for the `in` operator. Return a true value, if data
        for `path` is in the cache, else return a false value.
        """
        try:
            # Implicitly do an age test which may raise `CacheMissError`.
            #  Deliberately ignore the return value `stat_result`.
            # pylint: disable-msg=W0612
            stat_result = self[path]
            return True
        except CacheMissError:
            return False

    #
    # The following methods are only intended for debugging!
    #
    def __len__(self):
        """
        Return the number of entries in the cache. Note that this
        may include some (or many) expired entries.
        """
        return len(self._cache)

    def __str__(self):
        """Return a string representation of the cache contents."""
        lines = []
        for key in sorted(self._cache):
            lines.append("%s: %s" % (key, self[key]))
        return "\n".join(lines)

