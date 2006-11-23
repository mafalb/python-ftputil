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

From version 2.1 to 2.2, the following has changed:

- Results of stat calls (also indirect calls, i. e. listdir,
  isdir/isfile/islink, exists, getmtime etc.) are now cached and
  reused. This results in remarkable speedups for many use cases.

- The current directory is also locally cached, resulting in further
  speedups.

- File-like objects generated via ``FTPHost.file`` now support the
  iterator protocol (for line in some_file: ...).

- It's now possible to write and plug in custom parsers for directory
  formats which ftputil doesn't support natively.

- The documentation has been updated accordingly.

Possible incompatibilities:

- This release requires at least Python 2.3. (Previous releases
  worked with Python versions from 2.1 up.)

- The "old" method ``FTPHost.set_directory_format`` has been removed,
  since the directory format (Unix or MS) is set automatically. (The
  new method ``set_parser`` is a different animal since it takes
  a parser object to parse "foreign" formats, not a string.)

Documentation
-------------

The documentation for ftputil can be found in the file ftputil.txt
(reStructured Text format) or ftputil.html (recommended, generated
from ftputil.txt).

Prerequisites
-------------

To use ftputil, you need Python, at least version 2.3. Python is a
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
  http://docs.python.org/inst/inst.html .

License
-------

ftputil is Open Source Software. It is distributed under the
new/modified/revised BSD license (see
http://www.opensource.org/licenses/bsd-license.html ).

Authors
-------

Stefan Schwarzer <sschwarzer@sschwarzer.net>
Evan Prodromou <evan@bad.dynu.ca> (contributed lrucache module)

Please provide feedback! It's surely appreciated. :-)

