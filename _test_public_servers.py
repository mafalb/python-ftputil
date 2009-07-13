# Copyright (C) 2009, Stefan Schwarzer
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

# $Id: $

import os
import subprocess
import unittest

import ftputil


def email_address():
    """
    Return the email address used to identify the client to an
    FTP server.

    If the hostname is "warpy", use my (Stefan's) email address,
    else try to use the content of the $EMAIL environment variable.
    If that doesn't exist, use a dummy address.
    """
    try:
        fobj = open("/etc/hostname")
        hostname = fobj.read().strip()
    finally:
        fobj.close()
    if hostname == "warpy":
        email = "sschwarzer@sschwarzer.net"
    else:
        dummy_address = "anonymous@example.com"
        email = os.environ.get("EMAIL", dummy_address)
        if not email:
            # environment variable exists but content is an empty string
            email = dummy_address
    return email

EMAIL = email_address()


def ftp_client_listing(server, directory):
    """
    Log into the FTP server `server` using the command line
    client, then change to the `directory` and retrieve a
    listing with "dir". Return the list of items found as the
    an `os.listdir` would return it.
    """
    # the -n option prevents an auto-login
    ftp_popen = subprocess.Popen(["ftp", "-n", server],
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True)
    commands = ["user anonymous %s" % EMAIL, "dir", "bye"]
    if directory:
        # change to this directory before calling "dir"
        commands.insert(1, "cd %s" % directory)
    input_ = "\n".join(commands)
    stdout, stderr = ftp_popen.communicate(input_)
    # collect the directory/file names from the listing's text
    names = []
    for line in stdout.strip().split("\n"):
        if line.startswith("total "):
            continue
        parts = line.split()
        if parts[-2] == "->":
            # most probably a link
            name = parts[-3]
        else:
            name = parts[-1]
        names.append(name)
    # remove entries for current and parent directory
    names = [name  for name in names  if name not in (".", "..")]
    return names


class TestPublicServers(unittest.TestCase):
    """
    Get directory listings from various public FTP servers
    with a command line client and ftputil and compare both.

    An important aspect is to test different "spellings" of
    the same directory. For example, to list the root directory
    which is usually set after login, use "" (nothing), ".",
    "/", "/.", "./.", "././", "..", "../.", "../.." etc.

    The command line client "ftp" has to be in the path.
    """

    # Implementation note:
    #
    # I (Stefan) implement the code so it works with Ubuntu's
    # client. Other clients may work or not. If you have problems
    # testing some other client, please send me a (small) patch.
    # Keep in mind that I don't plan supporting as many FTP
    # clients as servers. ;-)

    # list of pairs with server name and a directory "guaranteed
    # to exist" under the login directory which is assumed to be
    # the root directory
    servers = [# Posix format
               ("ftp.gnome.org", "pub"),
               ("ftp.debian.org", "debian"),
               ("ftp.sunfreeware.com", "pub"),
               ("ftp.chello.nl", "pub"),
               ("ftp.heanet.ie", "pub"),
               # DOS/Microsoft format
               ("ftp.microsoft.com", "deskapps")]

    # This data structure contains the initial directories "." and
    # "DIR" (which will be replaced by a valid directory name for
    # each server). The list after the initial directory contains
    # paths that will be queried after changing into the initial
    # directory. All items in these lists are actually supposed to
    # yield the same directory contents.
    paths_table = [
      (".", ["", ".", "/", "/.", "./.", "././", "..", "../.", "../..",
             "DIR/..", "/DIR/../.", "/DIR/../.."]),
      ("DIR", ["", ".", "/DIR", "/DIR/", "../DIR", "../../DIR"])
      ]

    def inner_test_server(self, server, initial_directory, paths):
        """
        Test one server for one initial directory.

        Connect to the server `server`; if the string argument
        `initial_directory` has a true value, change to this
        directory. Then iterate over all strings in the sequence
        `paths`, comparing the results of a listdir call with the
        listing from the command line client.
        """
        canonical_names = ftp_client_listing(server, initial_directory)
        host = ftputil.FTPHost(server, "anonymous", EMAIL)
        try:
            host.chdir(initial_directory)
            for path in paths:
                path = path.replace("DIR", initial_directory)
                # make sure that we don't recycle directory entries, i. e.
                #  really repeatedly retrieve the directory contents
                #  (shouldn't happen anyway with the current implementation)
                host.stat_cache.clear()
                names = host.listdir(path)
                failure_message = "For server %s, directory %s: %s != %s" % \
                                  (server, initial_directory, names,
                                   canonical_names)
                self.assertEqual(names, canonical_names)
        finally:
            host.close()

    def test_servers(self):
        """
        Test all servers in `self.servers`.

        For each server, get the listings for the login directory and
        one other directory which is known to exist. Use different
        "spellings" to retrieve each list via ftputil and compare with
        the results gotten with the command line client.
        """
        for server, actual_initial_directory in self.servers:
            for initial_directory, paths in self.paths_table:
                initial_directory = initial_directory.replace(
                                      "DIR", actual_initial_directory)
                print server, initial_directory
                self.inner_test_server(server, initial_directory, paths)


if __name__ == '__main__':
    unittest.main()

