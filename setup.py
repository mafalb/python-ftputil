#! /usr/bin/env python

# Copyright (C) 2003, Stefan Schwarzer
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

# $Id: setup.py,v 1.1 2003/10/04 18:01:55 schwa Exp $

"""
setup.py - installation script for Python distutils
"""

from distutils import core

file_list = """
  UserTuple.py       ftp_error.py   ftp_stat.py
  _mock_ftplib.py    ftp_file.py    ftputil.py
  _test_ftputil.py   ftp_path.py    true_false.py
  setup.py           ftputil.txt    ftputil_pydoc.txt""".split()

_name = "ftputil"
_package = "ftputil"
_version = open("VERSION").read().strip()
_data_target = "%s/%s/" % (sysconfig.get_python_lib(), _package)

core.setup(
  # installation data
  name=_name,
  version=_version,
  packages=[_package],
  package_dir={_package: ""},
  data_files=[(_data_target, ["ftputil.txt", "ftputil.html"])],
  # metadata
  author="Stefan Schwarzer",
  author_email="sschwarzer@sschwarzer.net",
  url="http://www.sschwarzer.net/python/python_software.html",
  description="High-level FTP client interface",
  license="Open source (BSD-style)",
  platforms=["Pure Python (Python version >= 2.1)"],
  # has to be added yet
  #long_description="",
  download_url="http://www.sschwarzer.net/download/%s-%s.tar.gz" %
               (_name, _version))
