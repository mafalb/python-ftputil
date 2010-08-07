#! /usr/bin/env python
# Copyright (C) 2003-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

"""
setup.py - installation script for Python distutils
"""

import os
import sys

from distutils import core


_name = "ftputil"
_package = "ftputil"
_version = open("VERSION").read().strip()


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
  data_files=[("share/doc/ftputil", ["ftputil.txt", "ftputil.html",
                                     "README.txt", "README.html"])],
  # metadata
  author="Stefan Schwarzer",
  author_email="sschwarzer@sschwarzer.net",
  url="http://ftputil.sschwarzer.net/",
  description="High-level FTP client library (virtual filesystem and more)",
  keywords="FTP, client, library, virtual file system",
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

