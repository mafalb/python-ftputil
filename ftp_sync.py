# Copyright (C) 2007, Stefan Schwarzer
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
Tools for syncing combinations of local and remote directories.

*** WARNING: This is an unfinished in-development version!
"""

# Sync combinations:
# - remote -> local (download)
# - local -> remote (upload)
# - remote -> remote
# - local -> local (perhaps implicitly possible due to design, but not targeted)

import os
import shutil

from ftputil import FTPHost
import ftp_error

__all__ = ['FTPHost', 'LocalHost', 'Syncer']


# 64 KB
CHUNK_SIZE = 64*1024


class LocalHost(object):
    def open(self, path, mode):
        """
        Return a Python file object for file name `path`, opened in
        mode `mode`.
        """
        # this is the built-in `open` function, not `os.open`!
        return open(path, mode)

    def __getattr__(self, attr):
        return getattr(os, attr)


class Syncer(object):
    def __init__(self, source, target):
        """
        Init the `FTPSyncer` instance.
        
        Each of `source` and `target` is either an `FTPHost` or a
        `LocalHost` object. The source and target directories, resp.
        have to be set with the `chdir` command before passing them
        in. The semantics is so that the items under the source
        directory will show up under the target directory after the
        synchronization (unless there's an error).
        """
        self._source = source
        self._target = target

    def _mkdir(self, target_dir):
        """
        Try to create the target directory `target_dir`. If it already
        exists, don't do anything. If the directory is present but
        it's actually a file, raise a `SyncError`.
        """
        #TODO handle setting of target mtime according to source mtime
        #  (beware of rootdir anomalies; try to handle them as well)
        print "Making", target_dir
        if self._target.path.isfile(target_dir):
            raise ftp_error.SyncError("target dir '%s' is actually a file" %
                                      target_dir)
        if not self._target.path.isdir(target_dir):
            self._target.mkdir(target_dir)

    def _sync_file(self, source_file, target_file):
        #TODO handle `IOError`s
        #TODO handle conditional copy
        #TODO handle setting of target mtime according to source mtime
        #  (beware of rootdir anomalies; try to handle them as well)
        print "Syncing", source_file, "->", target_file
        source = self._source.open(source_file, "rb")
        try:
            target = self._target.open(target_file, "wb")
            try:
                shutil.copyfileobj(source, target, length=CHUNK_SIZE)
            finally:
                target.close()
        finally:
            source.close()

    def sync(self, source_dir, target_dir):
        """
        Synchronize the source and the target by updating the target
        to match the source as far as possible.

        Current limitations:
        - _don't_ delete items which are on the target path but not on the
          source path
        - files are always copied, the modification timestamps are not
          compared
        - all files are copied in binary mode, never in ASCII/text mode
        - incomplete error handling
        """
        source_dir = self._source.path.abspath(source_dir)
        target_dir = self._target.path.abspath(target_dir)
        self._mkdir(target_dir)
        for dirpath, dirnames, filenames in self._source.walk(source_dir):
            for dirname in dirnames:
                inner_source_dir = self._source.path.join(dirpath, dirname)
                inner_target_dir = inner_source_dir.replace(source_dir,
                                                            target_dir, 1)
                self._mkdir(inner_target_dir)
            for filename in filenames:
                source_file = self._source.path.join(dirpath, filename)
                target_file = source_file.replace(source_dir, target_dir, 1)
                self._sync_file(source_file, target_file)

