# Copyright (C) 2003-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# Copyright (C) 2008, Roger Demetrescu <roger.demetrescu@gmail.com>
# See the file LICENSE for licensing terms.

"""
ftp_file.py - support for file-like objects on FTP servers
"""

import ftp_error


# converter for `\r\n` line ends to normalized ones in Python. RFC 959
#  states that the server will send `\r\n` on text mode transfers, so
#  this conversion should be safe. I still use text mode transfers
#  (mode 'r', not 'rb') in `socket.makefile` (below) because the
#  server may do charset conversions on text transfers.
#
# Note that the "obvious" implementation of replacing "\r\n" with
#  "\n" would fail, if "\r" (without "\n") occured at the end of the
#  string `text`
def _crlf_to_python_linesep(text):
    """
    Return `text` with ASCII line endings (CR/LF) converted to
    Python's internal representation (LF).
    """
    return text.replace('\r', '')

# converter for Python line ends into `\r\n`
def _python_to_crlf_linesep(text):
    """
    Return `text` with Python's internal line ending representation
    (LF) converted to ASCII line endings (CR/LF).
    """
    return text.replace('\n', '\r\n')


class _FTPFile(object):
    """
    Represents a file-like object connected to an FTP host. File and
    socket are closed appropriately if the `close` operation is
    requested.
    """

    def __init__(self, host):
        """Construct the file(-like) object."""
        self._host = host
        self._session = host._session
        # the file is closed yet
        self.closed = True
        # overwritten later in `_open`
        self._bin_mode = None
        self._conn = None
        self._read_mode = None
        self._fo = None

    def _open(self, path, mode):
        """Open the remote file with given path name and mode."""
        # check mode
        if 'a' in mode:
            raise ftp_error.FTPIOError("append mode not supported")
        if mode not in ('r', 'rb', 'w', 'wb'):
            raise ftp_error.FTPIOError("invalid mode '%s'" % mode)
        # remember convenience variables instead of mode
        self._bin_mode = 'b' in mode
        self._read_mode = 'r' in mode
        # select ASCII or binary mode
        transfer_type = ('A', 'I')[self._bin_mode]
        command = 'TYPE %s' % transfer_type
        ftp_error._try_with_ioerror(self._session.voidcmd, command)
        # make transfer command
        command_type = ('STOR', 'RETR')[self._read_mode]
        command = '%s %s' % (command_type, path)
        # ensure we can process the raw line separators;
        #  force to binary regardless of transfer type
        if not 'b' in mode:
            mode = mode + 'b'
        # get connection and file object
        self._conn = ftp_error._try_with_ioerror(
                     self._session.transfercmd, command)
        self._fo = self._conn.makefile(mode)
        # this comes last so that `close` does not try to
        #  close `_FTPFile` objects without `_conn` and `_fo`
        #  attributes
        self.closed = False

    #
    # Read and write operations with support for line separator
    # conversion for text modes.
    #
    # Note that we must convert line endings because the FTP server
    # expects `\r\n` to be sent on text transfers.
    #
    def read(self, *args):
        """Return read bytes, normalized if in text transfer mode."""
        data = self._fo.read(*args)
        if self._bin_mode:
            return data
        data = _crlf_to_python_linesep(data)
        if args == ():
            return data
        # If the read data contains `\r` characters the number of read
        #  characters will be too small! Thus we (would) have to
        #  continue to read until we have fetched the requested number
        #  of bytes (or run out of source data).
        #
        # The algorithm below avoids repetitive string concatanations
        #  in the style of
        #      data = data + more_data
        #  and so should also work relatively well if there are many
        #  short lines in the file.
        wanted_size = args[0]
        chunks = [data]
        current_size = len(data)
        while current_size < wanted_size:
            # print 'not enough bytes (now %s, wanting %s)' % \
            #       (current_size, wanted_size)
            more_data = self._fo.read(wanted_size - current_size)
            if not more_data:
                break
            more_data = _crlf_to_python_linesep(more_data)
            # print '-> new (normalized) data:', repr(more_data)
            chunks.append(more_data)
            current_size += len(more_data)
        return ''.join(chunks)

    def readline(self, *args):
        """Return one read line, normalized if in text transfer mode."""
        data = self._fo.readline(*args)
        if self._bin_mode:
            return data
        # if necessary, complete begun newline
        if data.endswith('\r'):
            data = data + self.read(1)
        return _crlf_to_python_linesep(data)

    def readlines(self, *args):
        """Return read lines, normalized if in text transfer mode."""
        lines = self._fo.readlines(*args)
        if self._bin_mode:
            return lines
        # more memory-friendly than `return [... for line in lines]`
        for index, line in enumerate(lines):
            lines[index] = _crlf_to_python_linesep(line)
        return lines

    def __iter__(self):
        """Return a file iterator."""
        return self

    def next(self):
        """
        Return the next line or raise `StopIteration`, if there are
        no more.
        """
        # apply implicit line ending conversion
        line = self.readline()
        if line:
            return line
        else:
            raise StopIteration

    def write(self, data):
        """Write data to file. Do linesep conversion for text mode."""
        if not self._bin_mode:
            data = _python_to_crlf_linesep(data)
        self._fo.write(data)

    def writelines(self, lines):
        """Write lines to file. Do linesep conversion for text mode."""
        if self._bin_mode:
            self._fo.writelines(lines)
            return
        # we can't modify the list of lines in-place, as in the
        #  `readlines` method; that would modify the original list,
        #  given as argument `lines`
        for line in lines:
            self._fo.write(_python_to_crlf_linesep(line))

    #
    # context manager methods
    #
    def __enter__(self):
        # return `self`, so it can be accessed as the variable
        #  component of the `with` statement.
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # we don't need the `exc_*` arguments here
        # pylint: disable-msg=W0613
        self.close()
        # be explicit
        return False

    #
    # other attributes
    #
    def __getattr__(self, attr_name):
        """
        Handle requests for attributes unknown to `_FTPFile` objects:
        delegate the requests to the contained file object.
        """
        if attr_name in ('flush isatty fileno seek tell '
                         'truncate name softspace'.split()):
            return getattr(self._fo, attr_name)
        raise AttributeError(
              "'FTPFile' object has no attribute '%s'" % attr_name)

    def close(self):
        """Close the `FTPFile`."""
        if self.closed:
            return
        try:
            self._fo.close()
            ftp_error._try_with_ioerror(self._conn.close)
            try:
                ftp_error._try_with_ioerror(self._session.voidresp)
            except ftp_error.FTPIOError, exception:
                # ignore some errors, see ticket #17 at
                #  http://ftputil.sschwarzer.net/trac/ticket/17
                error_code = str(exception).split()[0]
                if error_code not in ("426", "450", "451"):
                    raise
        finally:
            # if something went wrong before, the file is probably
            #  defunct and subsequent calls to `close` won't help
            #  either, so we consider the file closed for practical
            #  purposes
            self.closed = True

