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

# $Id: _mock_ftplib.py,v 1.11 2002/03/30 18:46:59 schwa Exp $

"""
This module implements a mock version of the standard libraries
ftplib.py module. Some code is taken from there.

Not all functionality is implemented, only that which is used to
run the unit tests.
"""

import ftplib
import StringIO


class MockSession:
    """
    Mock implementation of ftplib.FTP . For information on mock
    objects see http://www.mockobjects.com/ .
    """

    # taken from ftplib.FTP
    host = ''
    sock = None
    file = None
    welcome = None
    passiveserver = 1

    # mock object settings
    voidresp_raise = None
    voidresp_result = None
    sendcmd_result = None
    voidcmd_exception = None
    voidcmd_result = None
    mock_socket_file_contents = ''
    login_raise = None
    login_result = None

    # Initialization method (called by class instantiation).
    # Initialize host to localhost, port to standard ftp port
    # Optional arguments are host (for connect()),
    # and user, passwd, acct (for login())
    def __init__(self, host='', user='', passwd='', acct=''):
        if host:
            self.connect(host)
            if user: self.login(user, passwd, acct)

    def connect(self, host = '', port = 0):
        """Connect to host.  Arguments are:
        - host: hostname to connect to (string, default previous host)
        - port: port to connect to (integer, default previous port)"""
        if host: self.host = host
        if port: self.port = port
        self.passiveserver = 1
        self.file = StringIO.StringIO()
        self.welcome = 'Welcome to the MockSession class! ;-)'
        return self.welcome

    def getwelcome(self):
        """Get the welcome message from the server.
        (this is read and squirreled away by connect())"""
        return self.welcome

    def set_pasv(self, val):
        """Use passive or active mode for data transfers.
        With a false argument, use the normal PORT mode,
        With a true argument, use the PASV command."""
        self.passiveserver = val

    def voidresp(self):
        """Expect a response beginning with '2'."""
        if self.voidresp_raise:
            raise ftplib.error_reply, resp
        return self.voidresp_result

    def sendcmd(self, cmd):
        """Send a command and return the response."""
        return self.sendcmd_result

    def voidcmd(self, cmd):
        """Send a command and expect a response beginning with '2'."""
        if self.voidcmd_exception is not None:
            raise self.voidcmd_exception
        return self.voidcmd_result

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
        conn = MockSocket(self.mock_socket_file_contents)
        size = self.ntransfercmd_size
        return conn, size

    def transfercmd(self, cmd, rest=None):
        """Like ntransfercmd() but returns only the socket."""
        return self.ntransfercmd(cmd, rest)[0]

    def login(self, user='', passwd='', acct=''):
        """Login, default anonymous."""
        if self.login_raise:
            raise ftplib.error_reply, self.login_result
        return self.login_result

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        """Retrieve data in binary mode.

        `cmd' is a RETR command.  `callback' is a callback function is
        called for each block.  No more than `blocksize' number of
        bytes will be read from the socket.  Optional `rest' is passed
        to transfercmd().

        A new port is created for you.  Return the response code.
        """
        self.voidcmd('TYPE I')
        conn = self.transfercmd(cmd, rest)
        while 1:
            data = conn.recv(blocksize)
            if not data:
                break
            callback(data)
        conn.close()
        return self.voidresp()

    def retrlines(self, cmd, callback = None):
        """Retrieve data in line mode.
        The argument is a RETR or LIST command.
        The callback function (2nd argument) is called for each line,
        with trailing CRLF stripped.  This creates a new port for you.
        print_line() is the default callback."""
        if not callback: callback = print_line
        resp = self.sendcmd('TYPE A')
        conn = self.transfercmd(cmd)
        fp = conn.makefile('rb')
        while 1:
            line = fp.readline()
            if self.debugging > 2: print '*retr*', `line`
            if not line:
                break
            if line[-2:] == CRLF:
                line = line[:-2]
            elif line[-1:] == '\n':
                line = line[:-1]
            callback(line)
        fp.close()
        conn.close()
        return self.voidresp()

    def storbinary(self, cmd, fp, blocksize=8192):
        """Store a file in binary mode."""
        self.voidcmd('TYPE I')
        conn = self.transfercmd(cmd)
        while 1:
            buf = fp.read(blocksize)
            if not buf: break
            conn.send(buf)
        conn.close()
        return self.voidresp()

    def storlines(self, cmd, fp):
        """Store a file in line mode."""
        self.voidcmd('TYPE A')
        conn = self.transfercmd(cmd)
        while 1:
            buf = fp.readline()
            if not buf: break
            if buf[-2:] != CRLF:
                if buf[-1] in CRLF: buf = buf[:-1]
                buf = buf + CRLF
            conn.send(buf)
        conn.close()
        return self.voidresp()

    def acct(self, password):
        """Send new account name."""
        cmd = 'ACCT ' + password
        return self.voidcmd(cmd)

    def nlst(self, *args):
        """Return a list of files in a given directory (default the current)."""
        cmd = 'NLST'
        for arg in args:
            cmd = cmd + (' ' + arg)
        files = []
        self.retrlines(cmd, files.append)
        return files

    def dir(self, *args):
        """List a directory in long form.
        By default list current directory to stdout.
        Optional last argument is callback function; all
        non-empty arguments before it are concatenated to the
        LIST command.  (This *should* only be used for a pathname.)"""
        cmd = 'LIST'
        func = None
        if args[-1:] and type(args[-1]) != type(''):
            args, func = args[:-1], args[-1]
        for arg in args:
            if arg:
                cmd = cmd + (' ' + arg)
        self.retrlines(cmd, func)

    def rename(self, fromname, toname):
        """Rename a file."""
        resp = self.sendcmd('RNFR ' + fromname)
        if resp[0] != '3':
            raise error_reply, resp
        return self.voidcmd('RNTO ' + toname)

    def delete(self, filename):
        """Delete a file."""
        resp = self.sendcmd('DELE ' + filename)
        if resp[:3] in ('250', '200'):
            return resp
        elif resp[:1] == '5':
            raise error_perm, resp
        else:
            raise error_reply, resp

    def cwd(self, dirname):
        """Change to a directory."""
        if dirname == '..':
            try:
                return self.voidcmd('CDUP')
            except error_perm, msg:
                if msg[:3] != '500':
                    raise error_perm, msg
        elif dirname == '':
            dirname = '.'  # does nothing, but could return error
        cmd = 'CWD ' + dirname
        return self.voidcmd(cmd)

    def size(self, filename):
        """Retrieve the size of a file."""
        # Note that the RFC doesn't say anything about 'SIZE'
        resp = self.sendcmd('SIZE ' + filename)
        if resp[:3] == '213':
            s = resp[3:].strip()
            try:
                return int(s)
            except (OverflowError, ValueError):
                return long(s)

    def mkd(self, dirname):
        """Make a directory, return its full pathname."""
        resp = self.sendcmd('MKD ' + dirname)
        return parse257(resp)

    def rmd(self, dirname):
        """Remove a directory."""
        return self.voidcmd('RMD ' + dirname)

    def pwd(self):
        """Return current working directory."""
        resp = self.sendcmd('PWD')
        return parse257(resp)

    def quit(self):
        """Quit, and close the connection."""
        resp = self.voidcmd('QUIT')
        self.close()
        return resp

    def close(self):
        """Close the connection without assuming anything about it."""
        if self.file:
            self.file.close()
            self.sock.close()
            self.file = self.sock = None


DEBUG = 0

# class MockFileObject(StringIO.StringIO):
#     """
#     Mock class for the file objects _contained in_ _FTPFile
#     objects (not for _FTPFile objects themselves!).
#     """
#     contents = ''
# 
#     def __init__(self, contents, mode='r'):
        
    
class MockSocket:
    """
    Mock class which is used to return something from
    MockSession.transfercmd.
    """
    def __init__(self, mock_file_content=''):
        if DEBUG:
            print 'File content: *%s*' % mock_file_content
        self.mock_file_content = mock_file_content

    def makefile(self, mode):
        return StringIO.StringIO(self.mock_file_content)

    def close(self):
        pass


class MockSession:
    """
    Mock class which works like ftplib.FTP for the purpose of the
    unit tests.
    """
    # used by MockSession.cwd and MockSession.pwd
    current_dir = '/home/sschwarzer'
    
    # used by MockSession.dir
    dir_contents = {
          '/home': """\
drwxr-sr-x   2 45854    200           512 May  4  2000 sschwarzer""",
          '/home/sschwarzer': """\
total 14
drwxr-sr-x   2 45854    200           512 May  4  2000 chemeng
drwxr-sr-x   2 45854    200           512 Jan  3 17:17 download
drwxr-sr-x   2 45854    200           512 Jul 30 17:14 image
-rw-r--r--   1 45854    200          4604 Jan 19 23:11 index.html
drwxr-sr-x   2 45854    200           512 May 29  2000 os2
lrwxrwxrwx   2 45854    200           512 May 29  2000 osup -> ../os2
drwxr-sr-x   2 45854    200           512 May 25  2000 publications
drwxr-sr-x   2 45854    200           512 Jan 20 16:12 python
drwxr-sr-x   6 45854    200           512 Sep 20  1999 scios2"""}

    # file content to be used (indirectly) with transfercmd
    mock_file_content = ''
    
    def __init__(self, host='', user='', password=''):
        pass

    def _remove_trailing_slash(self, path):
        if path.endswith('/'):
            path = path[:-1]
        return path
        
    def voidcmd(self, cmd):
        if DEBUG:
            print cmd
        if cmd == 'STAT':
            return 'MockSession server awaiting your commands ;-)'
        elif cmd.startswith('TYPE '):
            return
        else:
            raise ftplib.error_perm

    def voidresp(self):
        return '2xx'

    def pwd(self):
        return self.current_dir

    def cwd(self, path):
        path = self._remove_trailing_slash(path)
        self.current_dir = path

    def dir(self, path, callback=None):
        "Provide a callback function with each line of a directory listing."
        if DEBUG:
            print 'dir: %s' % path
        path = self._remove_trailing_slash(path)
        if not self.dir_contents.has_key(path):
            raise ftplib.error_perm
        dir_lines = self.dir_contents[path].split('\n')
        for line in dir_lines:
            if callback is None:
                print line
            else:
                callback(line)

    def transfercmd(self, cmd):
        """
        Return a MockSocket object whose makefile method will return
        a mock file object.
        """
        if DEBUG:
            print cmd
        # fail if attempting to read from/write to a directory
        cmd, path = cmd.split()
        path = self._remove_trailing_slash(path)
        if self.dir_contents.has_key(path):
            raise ftplib.error_perm
        # fail if path isn't available (this name is hard-coded here
        #  and has to be used for the corresponding tests)
        if cmd == 'RETR' and path == 'notthere':
            raise ftplib.error_perm
        return MockSocket(self.mock_file_content)

