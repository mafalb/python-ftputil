# Copyright (C) 2003-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

import ftputil

import mock_ftplib


# Factory to produce `FTPHost`-like classes from a given `FTPHost`
#  class and a given `MockSession` class.
def ftp_host_factory(session_factory=mock_ftplib.MockSession,
                     ftp_host_class=ftputil.FTPHost):
    return ftp_host_class('dummy_host', 'dummy_user', 'dummy_password',
                          session_factory=session_factory)

