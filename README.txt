ftputil
=======

Purpose
-------

ftputil is a high-level alternative to Python's ftplib module. With ftputil,
you can (almost) access directories and files on remote FTP servers as if they
were in your local file system. This includes using file-like objects
representing remote files.

Documentation
-------------

The documentation for ftputil can be found in the file ftputil.txt
(reStructured Text format) or ftputil.html (same contents, generated from
ftputil.txt).

Prerequisites
-------------

To use ftputil, you need Python, at least version 2.0. Python is a
programming language, available from http://www.python.org at no cost.

Installation
------------

- Unpack the archive file containing the distribution files. If you have
  ftputil version 1.2, you would type at the shell prompt

    tar xzf ftputil-1.2.tar.gz

  However, if you read this, you probably unpacked the archive already. ;-)

- Make the directory where most of the files are your current directory.
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

Author
------

Stefan Schwarzer <sschwarzer@sschwarzer.net>

Please provide feedback! It's surely appreciated. :-)

