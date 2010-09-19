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

Since version 2.4.2 the following changed:

- As announced `over a year ago`_, the ``xreadlines`` method for
  FTP file objects has been removed, and exceptions can no longer be
  accessed via the ``ftputil`` namespace. Only use ``ftp_error`` to access
  the exceptions.

  The distribution contains a small tool ``find_deprecated_code.py`` to
  scan a directory tree for the deprecated uses. Invoke the program
  with the ``--help`` option to see a description.

- Upload and download methods now accept a ``callback`` argument to do
  things during a transfer. Modification time comparisons in
  ``upload_if_newer`` and ``download_if_newer`` now consider the timestamp
  precision of the remote file which may lead to some unneccesary
  transfers. These can be avoided by waiting at least a minute between
  calls of ``upload_if_newer`` (or ``download_if_newer``) for the same
  file. See the documentation for `details`_.

- The ``FTPHost`` class got a ``keep_alive`` method. It should be used
  carefully though, not routinely. Please read the `description`_ in
  the documentation.

- Several bugs were fixed (`#44`_, `#46`_, `#47`_, `#51`_).

- The source code was restructured. The tests are now in a ``test``
  subdirectory and are no longer part of the release archive. You can
  still get them via the source repository. Licensing matters have
  been moved to a common ``LICENSE`` file.

Documentation
-------------

The documentation for ftputil can be found in the file ftputil.txt
(reStructuredText format) or ftputil.html (recommended, generated
from ftputil.txt).

Prerequisites
-------------

To use ftputil, you need Python, at least version 2.4. Python is a
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

.. _`over a year ago`: http://codespeak.net/pipermail/ftputil/2009q1/000256.html
.. _`details`: http://ftputil.sschwarzer.net/trac/wiki/Documentation#uploading-and-downloading-files
.. _`description`: http://ftputil.sschwarzer.net/trac/wiki/Documentation#keep-alive
.. _`#44`: http://ftputil.sschwarzer.net/trac/ticket/44
.. _`#46`: http://ftputil.sschwarzer.net/trac/ticket/46
.. _`#47`: http://ftputil.sschwarzer.net/trac/ticket/47
.. _`#51`: http://ftputil.sschwarzer.net/trac/ticket/51
