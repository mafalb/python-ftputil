#! /usr/bin/env python
# Copyright (C) 2008, Stefan Schwarzer
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

# pylint: disable-msg=W0622

"""\
This script scans a directory tree for files which contain code which
is deprecated in ftputil %s and above (and even much longer). The
script uses simple heuristics, so it may miss occurences of deprecated
usage or print some inappropriate lines of your files.

Usage: %s start_dir

where start_dir is the starting directory which will be scanned
recursively for offending code.

Currently, these deprecated features are examined:

- You should no longer use the exceptions via the ftputil module but
  via the ftp_error module. So, for example, instead of
  ftputil.PermanentError write ftp_error.PermanentError.

- Don't use the xreadlines method of FTP file objects (as returned by
  FTPHost.file = FTPHost.open). Instead use

  for line in ftp_host.open(path):
      ...
"""

import ftputil_version

import os
import re
import sys

__doc__ = __doc__ % (ftputil_version.__version__, os.path.basename(sys.argv[0]))

deprecated_features = [
  ("Possible use(s) of FTP exceptions via ftputil module",
   re.compile(r"\bftputil\s*?\.\s*?[A-Za-z]+Error\b"), {}),
  ("Possible use(s) of xreadline method of FTP file objects",
   re.compile(r"\.\s*?xreadlines\b"), {}),
]

def scan_file(file_name):
    """
    Scan a file with name `file_name` for code deprecated in
    ftputil usage and collect the offending data in the data
    structure `deprecated_features`.
    """
    fobj = open(file_name)
    try:
        for index, line in enumerate(fobj):
            # `title` isn't used here
            # pylint: disable-msg=W0612
            for title, regex, positions in deprecated_features:
                if regex.search(line):
                    positions.setdefault(file_name, [])
                    positions[file_name].append((index+1, line.rstrip()))
    finally:
        fobj.close()

def print_results():
    """
    Print statistics of deprecated code after the directory has been
    scanned.
    """
    last_title = ""
    # `regex` isn't used here
    # pylint: disable-msg=W0612
    for title, regex, positions in deprecated_features:
        if title != last_title:
            print
            print title, "..."
            print
            last_title = title
        if not positions:
            print "   no deprecated code found"
            continue
        file_names = positions.keys()
        file_names.sort()
        for file_name in file_names:
            print file_name
            for line_number, line in positions[file_name]:
                print "%5d: %s" % (line_number, line)
    print
    print "If possible, check your code also by other means."

def main(start_dir):
    """
    Scan a directory tree starting at `start_dir` and print uses
    of deprecated features, if any were found.
    """
    # `dir_names` isn't used here
    # pylint: disable-msg=W0612
    for dir_path, dir_names, file_names in os.walk(start_dir):
        for file_name in file_names:
            abs_name = os.path.abspath(os.path.join(dir_path, file_name))
            if file_name.endswith(".py"):
                scan_file(abs_name)
    print_results()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] in ("-h", "--help"):
            print __doc__
            sys.exit(0)
        start_dir = sys.argv[1]
        if not os.path.isdir(start_dir):
            print >> sys.stderr, "Directory %s not found." % start_dir
            sys.exit()
    else:
        print >> sys.stderr, "Usage: %s start_dir" % sys.argv[0]
        sys.exit()
    main(start_dir)

