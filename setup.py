#! /usr/bin/env python

# Copyright (C) 2003-2009, Stefan Schwarzer
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
setup.py - installation script for Python distutils
"""

import os
import sys

from distutils import core
from distutils import sysconfig
from distutils.command import install_lib as install_lib_module


_name = "ftputil"
_package = "ftputil"
_version = open("VERSION").read().strip()


# avoid byte-compiling `_test_with_statement.py` for Python < 2.5; see
#  http://mail.python.org/pipermail/distutils-sig/2002-June/002894.html
class FtputilInstallLib(install_lib_module.install_lib):
    def byte_compile(self, files):
        if sys.version_info < (2, 5):
            files = [f for f in files
                       if os.path.basename(f) != "_test_with_statement.py"]
        # `super` doesn't work with classic classes
        return install_lib_module.install_lib.byte_compile(self, files)


core.setup(
  # installation data
  name=_name,
  version=_version,
  packages=[_package],
  package_dir={_package: ""},
  data_files=[("doc", ["ftputil.txt", "ftputil.html",
                       "README.txt", "README.html"])],
  cmdclass={'install_lib': FtputilInstallLib},

  # metadata
  author="Stefan Schwarzer",
  author_email="sschwarzer@sschwarzer.net",
  url="http://ftputil.sschwarzer.net/",
  description="High-level FTP client library (virtual filesystem and more)",
  keywords="FTP, client, virtual file system",
  license="Open source (revised BSD license)",
  platforms=["Pure Python (Python version >= 2.3)"],
  long_description="""\
ftputil is a high-level FTP client library for the Python programming
language. ftputil implements a virtual file system for accessing FTP servers,
that is, it can generate file-like objects for remote files. The library
supports many functions similar to those in the os, os.path and
shutil modules. ftputil has convenience functions for conditional uploads
and downloads, and handles FTP clients and servers in different timezones.""",
  download_url=
    "http://ftputil.sschwarzer.net/trac/attachment/wiki/Download/%s-%s.tar.gz?format=raw" %
    (_name, _version),
  classifiers=[
    "Development Status :: 5 - Production/Stable",
    "Environment :: Other Environment",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Topic :: Internet :: File Transfer Protocol (FTP)",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Filesystems",
    ]
  )

