# Copyright (C) 2001, Stefan Schwarzer
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

# $Id: _mock_ftplib.py,v 1.2 2002/03/29 18:34:38 schwa Exp $

"""
This module implements a mock version of the standard libraries
ftplib.py module. Some code is taken from there.

Not all functionality is implemented, only that which is used to
run the unit tests.
"""

class FTP:
    """
    Mock implementation of ftplib.FTP . For information on mock
    objects see http://www.mockobjects.com/ .
    """
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def voidresp(self):
        """Expect a response beginning with '2'."""
    
    def sendcmd(self, cmd):
        """Send a command and return the response."""
    
    def voidcmd(self, cmd):
        """Send a command and expect a response beginning with '2'."""

    def ntransfercmd(self, cmd, rest=None):
        """Initiate a transfer over the data connection.

        If the transfer is active, send a port command and the
        transfer command, and accept the connection.  If the server is
        passive, send a pasv command, connect to it, and start the
        transfer command.  Either way, return the socket for the
        connection and the expected size of the transfer.  The
        expected size may be None if it could not be determined.

        Optional `rest' argument can be a string that is sent as the
        argument to a RESTART command.  This is essentially a server
        marker used to tell the server to skip over any data up to the
        given marker.
        """

    def transfercmd(self, cmd, rest=None):
        """Like ntransfercmd() but returns only the socket."""
        return self.ntransfercmd(cmd, rest)[0]

    def dir(self, *args):
        """List a directory in long form.
        By default list current directory to stdout.
        Optional last argument is callback function; all
        non-empty arguments before it are concatenated to the
        LIST command.  (This *should* only be used for a pathname.)"""

    def rename(self, fromname, toname):
        """Rename a file."""

    def delete(self, filename):
        """Delete a file."""

    def cwd(self, dirname):
        """Change to a directory."""

    def mkd(self, dirname):
        """Make a directory, return its full pathname."""

    def rmd(self, dirname):
        """Remove a directory."""

    def pwd(self):
        """Return current working directory."""

    def quit(self):
        """Quit, and close the connection."""

    def close(self):
        """Close the connection without assuming anything about it."""

