ftputil
=======

Purpose
-------

ftputil is a high-level FTP client library for the Python programming
language. ftputil implements a virtual file system for accessing FTP
servers, that is, it can generate file-like objects for remote files.
The library supports many functions similar to those in the os,
os.path and shutil modules. ftputil has convenience functions for
conditional uploads and downloads, and handles FTP clients and servers
in different timezones.

What's new?
-----------

From version 2.0 to 2.1, the following has changed:

- Added new methods to the FTPHost class, namely makedirs, walk,
  rmtree.

- The FTP server directory format ("Unix" vs. "Windows") is now set
  automatically (thanks to Andrew Ittner for testing it).

- Border cases like inaccessible login directories and whitespace in
  directory names, are now handled more gracefully (based on input
  from Valeriy Pogrebitskiy, Tommy Sundström and H. Y. Chu).

- The documentation was updated.

- A Russian translation of the documentation (currently slightly
  behind) was contributed by Anton Stepanov. It's also on the website
  at http://ftputil.sschwarzer.net/trac/wiki/RussianDocumentation .

- New website, http://ftputil.sschwarzer.net/ with wiki, issue tracker
  and Subversion repository (thanks to Trac!)

  Please enter not only bugs but also enhancement request into
  the issue tracker!

Possible incompatibilities:

- The exception hierarchy was changed slightly, which might break
  client code. See http://ftputil.sschwarzer.net/trac/changeset/489
  for the change details and the possibly necessary code changes.

- FTPHost.rmdir no longer removes non-empty directories. Use the new
  method FTPHost.rmtree for this.

Documentation
-------------

The documentation for ftputil can be found in the file ftputil.txt
(reStructured Text format) or ftputil.html (recommended, generated
from ftputil.txt).

Prerequisites
-------------

To use ftputil, you need Python, at least version 2.0. Python is a
programming language, available from http://www.python.org for free.

Installation
------------

- *If you have an older version of ftputil installed, delete it or move
  it somewhere else, so that it doesn't conflict with the new version!*

- Unpack the archive file containing the distribution files. If you
  had an hypothetical ftputil version 1.2, you would type at the shell
  prompt:

    tar xzf ftputil-1.2.tar.gz

  However, if you read this, you probably unpacked the archive already. ;-)

- Make the directory to where the files were unpacked your current directory.
  Consider that after unpacking, you have a directory ftputil-1.2. Make it
  the current directory with

    cd ftputil-1.2

- Type

    python setup.py install

  at the shell prompt. On Unix/Linux, you have to be root to perform the
  installation. Likewise, you have to be logged in as administrator if you
  install on Windows.

  If you want to customize the installation paths, please read
  http://www.python.org/doc/current/inst/inst.html .

License
-------

ftputil is Open Source Software. It is distributed under a BSD-style
license (see the top of ftputil.py).

Author
------

Stefan Schwarzer <sschwarzer@sschwarzer.net>

Please provide feedback! It's surely appreciated. :-)

