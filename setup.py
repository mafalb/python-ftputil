#! /usr/bin/env python

# Copyright (C) 2003-2004, Stefan Schwarzer
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

# $Id: setup.py,v 1.8 2004/02/27 23:34:52 schwa Exp $

"""
setup.py - installation script for Python distutils
"""

import sys

from distutils import core
from distutils import sysconfig


_name = "ftputil"
_package = "ftputil"
_version = open("VERSION").read().strip()
_data_target = "%s/%s" % (sysconfig.get_python_lib(), _package)

# add `download_url` parameter if the version of distutils supports it
more_args = {}
if sys.version_info > (2, 2, 2):
    more_args['download_url'] = \
      "http://www.sschwarzer.net/download/%s-%s.tar.gz" % (_name, _version)

core.setup(
  # installation data
  name=_name,
  version=_version,
  packages=[_package],
  package_dir={_package: ""},
  data_files=[(_data_target, ["ftputil.txt", "ftputil.html",
                              "README.txt", "README.html"])],
  # metadata
  author="Stefan Schwarzer",
  author_email="sschwarzer@sschwarzer.net",
  url="http://www.sschwarzer.net/python/python_software.html",
  description="High-level FTP client library (virtual filesystem and more)",
  license="Open source (BSD-style)",
  platforms=["Pure Python (Python version >= 2.0)"],
  long_description="""\
ftputil is a high-level FTP client library for the Python programming
language. ftputil implements a virtual file system for accessing FTP servers,
that is, it can generate file-like objects for remote files. The library
supports many functions similar to those in the os, os.path and
shutil modules. ftputil has convenience functions for conditional uploads
and downloads, and handles FTP clients and servers in different timezones.""",
  **more_args
  )

