#! /usr/bin/env python
# Copyright (C) 2003-2009, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

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


if "install" in sys.argv[1:] and \
  not (os.path.isfile("ftputil.html") and os.path.isfile("README.html")):
    print "One or more of the HTML documentation files are missing."
    print "Please generate them with `make docs`."
    sys.exit(1)

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
  platforms=["Pure Python (Python version >= 2.4)"],
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

