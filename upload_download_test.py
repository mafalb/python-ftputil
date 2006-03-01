# Copyright (C) 2006, Stefan Schwarzer
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

# Test script for ticket #13 (reported by Pete Schott)

import getpass
import random
import sys

import ftputil


def login_data():
    """Get host, user, password and return them as a triple."""
    remote_host = raw_input("Host: ")
    user = raw_input("User name: ")
    password = getpass.getpass("Password: ")
    return remote_host, user, password

def test_data():
    """Return a pseudo-random string of length between 0 and 5120."""
    length = random.randint(0, 5120)
    data = [chr(random.randint(0, 255)) for i in range(length)]
    return "".join(data)
    
# open connection and read local data
login_data_ = login_data()
host = ftputil.FTPHost(*login_data_)

# download and test several times
for i in range(100):
    # save and upload random data and try to test remote integrity
    data = test_data()
    local_data_file = open("local_data", "wb")
    local_data_file.write(data)
    local_data_file.close()
    host.upload("local_data", "remote_data", "b")
    # download file and compare it with the expected data
    host.download("remote_data", "remote_data", "b")
    remote_data_file = open("remote_data", "rb")
    remote_data = remote_data_file.read()
    remote_data_file.close()
    print "Downloaded file %3d (length %4d) is" % ((i+1), len(data)),
    if data == remote_data:
        print "OK"
    else:
        print "NOT OK"

