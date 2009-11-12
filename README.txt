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

Since version 2.4.1 the following changed:

- Some FTP servers seem to have problems using *any* directory
  argument which contains slashes. The new default for FTP commands
  now is to change into the directory before actually invoking the
  command on a relative path (report and fix suggestion by Nicola
  Murino).

- Calling the method ``FTPHost.stat_cache.resize`` with an argument 0
  caused an exception. This has been fixed; a zero cache size now
  of course doesn't cache anything but doesn't lead to a traceback
  either.

- The installation script ``setup.py`` didn't work with the ``--home``
  option because it still tried to install the documentation in a
  system directory (report by Albrecht Mühlenschulte).

  As a side effect, when using the *global* installation, the
  documentation is no longer installed in the ftputil package
  directory but in a subdirectory ``doc`` of a directory determined by
  Distutils. For example, on my system (Ubuntu 9.04) the documentation
  files are put into ``/usr/local/doc``.

Incompatibility notice
----------------------

When doing a system-wide installation, the documentation files are now
placed in another location than before (see last paragraph of the
previous section). This doesn't change anything regarding the use of
the library, though.

Both the ``xreadlines`` method and the long-deprecated direct access
of exceptions via the ``ftputil`` module (as in
``ftputil.PermanentError``) will be removed in ftputil *2.5*. Starting
with that version, exception classes will only be accessible via the
``ftp_error`` module.

The distribution contains a small tool ``find_deprecated_code.py`` to
scan a directory for the deprecated uses. Invoke the program with the
``--help`` option to see a description.

Documentation
-------------

The documentation for ftputil can be found in the file ftputil.txt
(reStructuredText format) or ftputil.html (recommended, generated
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

If you have easy_install installed, you can install the current
version of ftputil directly from the Python Package Index (PyPI)
without downloading the package explicitly.

- Just type

    easy_install ftputil

  on the command line. You'll probably need root/administrator
  privileges to do that (see above).

License
-------

ftputil is Open Source Software. It is distributed under the
new/modified/revised BSD license (see
http://www.opensource.org/licenses/bsd-license.html ).

Authors
-------

Stefan Schwarzer <sschwarzer@sschwarzer.net>

Evan Prodromou <evan@bad.dynu.ca> (lrucache module)

Please provide feedback! It's certainly appreciated. :-)

