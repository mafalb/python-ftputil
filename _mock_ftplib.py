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

# $Id: _mock_ftplib.py,v 1.3 2002/03/29 18:50:33 schwa Exp $

"""
This module implements a mock version of the standard libraries
ftplib.py module. Some code is taken from there.

Not all functionality is implemented, only that which is used to
run the unit tests.
"""

import ftplib

class FTP(ftplib.FTP):
    """
    Mock implementation of ftplib.FTP . For information on mock
    objects see http://www.mockobjects.com/ .
    """
    debugging = 0
    host = ''
    port = ftplib.FTP_PORT
    sock = None
    file = None
    welcome = None
    passiveserver = 1

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
        self.passiveserver = 0
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg
        self.af = af
        self.file = self.sock.makefile('rb')
        self.welcome = self.getresp()
        return self.welcome

    def getwelcome(self):
        """Get the welcome message from the server.
        (this is read and squirreled away by connect())"""
        if self.debugging:
            print '*welcome*', self.sanitize(self.welcome)
        return self.welcome

    def set_debuglevel(self, level):
        """Set the debugging level.
        The required argument level means:
        0: no debugging output (default)
        1: print commands and responses but not body text etc.
        2: also print raw lines read and sent before stripping CR/LF"""
        self.debugging = level
    debug = set_debuglevel

    def set_pasv(self, val):
        """Use passive or active mode for data transfers.
        With a false argument, use the normal PORT mode,
        With a true argument, use the PASV command."""
        self.passiveserver = val

    # Internal: "sanitize" a string for printing
    def sanitize(self, s):
        if s[:5] == 'pass ' or s[:5] == 'PASS ':
            i = len(s)
            while i > 5 and s[i-1] in '\r\n':
                i = i-1
            s = s[:5] + '*'*(i-5) + s[i:]
        return `s`

    # Internal: send one line to the server, appending CRLF
    def putline(self, line):
        line = line + CRLF
        if self.debugging > 1: print '*put*', self.sanitize(line)
        self.sock.send(line)

    # Internal: send one command to the server (through putline())
    def putcmd(self, line):
        if self.debugging: print '*cmd*', self.sanitize(line)
        self.putline(line)

    # Internal: return one line from the server, stripping CRLF.
    # Raise EOFError if the connection is closed
    def getline(self):
        line = self.file.readline()
        if self.debugging > 1:
            print '*get*', self.sanitize(line)
        if not line: raise EOFError
        if line[-2:] == CRLF: line = line[:-2]
        elif line[-1:] in CRLF: line = line[:-1]
        return line

    # Internal: get a response from the server, which may possibly
    # consist of multiple lines.  Return a single string with no
    # trailing CRLF.  If the response consists of multiple lines,
    # these are separated by '\n' characters in the string
    def getmultiline(self):
        line = self.getline()
        if line[3:4] == '-':
            code = line[:3]
            while 1:
                nextline = self.getline()
                line = line + ('\n' + nextline)
                if nextline[:3] == code and \
                        nextline[3:4] != '-':
                    break
        return line

    # Internal: get a response from the server.
    # Raise various errors if the response indicates an error
    def getresp(self):
        resp = self.getmultiline()
        if self.debugging: print '*resp*', self.sanitize(resp)
        self.lastresp = resp[:3]
        c = resp[:1]
        if c == '4':
            raise error_temp, resp
        if c == '5':
            raise error_perm, resp
        if c not in '123':
            raise error_proto, resp
        return resp

    def voidresp(self):
        """Expect a response beginning with '2'."""
        resp = self.getresp()
        if resp[0] != '2':
            raise error_reply, resp
        return resp

    def abort(self):
        """Abort a file transfer.  Uses out-of-band data.
        This does not follow the procedure from the RFC to send Telnet
        IP and Synch; that doesn't seem to work with the servers I've
        tried.  Instead, just send the ABOR command as OOB data."""
        line = 'ABOR' + CRLF
        if self.debugging > 1: print '*put urgent*', self.sanitize(line)
        self.sock.send(line, MSG_OOB)
        resp = self.getmultiline()
        if resp[:3] not in ('426', '226'):
            raise error_proto, resp

    def sendcmd(self, cmd):
        """Send a command and return the response."""
        self.putcmd(cmd)
        return self.getresp()

    def voidcmd(self, cmd):
        """Send a command and expect a response beginning with '2'."""
        self.putcmd(cmd)
        return self.voidresp()

    def sendport(self, host, port):
        """Send a PORT command with the current host and the given
        port number.
        """
        hbytes = host.split('.')
        pbytes = [`port/256`, `port%256`]
        bytes = hbytes + pbytes
        cmd = 'PORT ' + ','.join(bytes)
        return self.voidcmd(cmd)

    def sendeprt(self, host, port):
        """Send a EPRT command with the current host and the given port number."""
        af = 0
        if self.af == socket.AF_INET:
            af = 1
        if self.af == socket.AF_INET6:
            af = 2
        if af == 0:
            raise error_proto, 'unsupported address family'
        fields = ['', `af`, host, `port`, '']
        cmd = 'EPRT ' + string.joinfields(fields, '|')
        return self.voidcmd(cmd)

    def makeport(self):
        """Create a new socket and send a PORT command for it."""
        msg = "getaddrinfo returns an empty list"
        sock = None
        for res in socket.getaddrinfo(None, 0, self.af, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                sock = socket.socket(af, socktype, proto)
                sock.bind(sa)
            except socket.error, msg:
                if sock:
                    sock.close()
                sock = None
                continue
            break
        if not sock:
            raise socket.error, msg
        sock.listen(1)
        port = sock.getsockname()[1] # Get proper port
        host = self.sock.getsockname()[0] # Get proper host
        if self.af == socket.AF_INET:
            resp = self.sendport(host, port)
        else:
            resp = self.sendeprt(host, port)
        return sock

    def makepasv(self):
        if self.af == socket.AF_INET:
            host, port = parse227(self.sendcmd('PASV'))
        else:
            host, port = parse229(self.sendcmd('EPSV'), self.sock.getpeername())
        return host, port

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
        size = None
        if self.passiveserver:
            host, port = self.makepasv()
            af, socktype, proto, canon, sa = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]
            conn = socket.socket(af, socktype, proto)
            conn.connect(sa)
            if rest is not None:
                self.sendcmd("REST %s" % rest)
            resp = self.sendcmd(cmd)
            if resp[0] != '1':
                raise error_reply, resp
        else:
            sock = self.makeport()
            if rest is not None:
                self.sendcmd("REST %s" % rest)
            resp = self.sendcmd(cmd)
            if resp[0] != '1':
                raise error_reply, resp
            conn, sockaddr = sock.accept()
        if resp[:3] == '150':
            # this is conditional in case we received a 125
            size = parse150(resp)
        return conn, size

    def transfercmd(self, cmd, rest=None):
        """Like ntransfercmd() but returns only the socket."""
        return self.ntransfercmd(cmd, rest)[0]

    def login(self, user = '', passwd = '', acct = ''):
        """Login, default anonymous."""
        if not user: user = 'anonymous'
        if not passwd: passwd = ''
        if not acct: acct = ''
        if user == 'anonymous' and passwd in ('', '-'):
            # get fully qualified domain name of local host
            thishost = socket.getfqdn()
            try:
                if os.environ.has_key('LOGNAME'):
                    realuser = os.environ['LOGNAME']
                elif os.environ.has_key('USER'):
                    realuser = os.environ['USER']
                else:
                    realuser = 'anonymous'
            except AttributeError:
                # Not all systems have os.environ....
                realuser = 'anonymous'
            passwd = passwd + realuser + '@' + thishost
        resp = self.sendcmd('USER ' + user)
        if resp[0] == '3': resp = self.sendcmd('PASS ' + passwd)
        if resp[0] == '3': resp = self.sendcmd('ACCT ' + acct)
        if resp[0] != '2':
            raise error_reply, resp
        return resp

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
