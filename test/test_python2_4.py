# Copyright (C) 2003-2009, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

import unittest

import ftp_error


class Python24(unittest.TestCase):
    """Test for faults which occur only with Python 2.4 (possibly below)."""

    def test_exception_base_class(self):
        try:
            raise ftp_error.FTPOSError("")
        except TypeError:
            self.fail("can't use super in classic class")
        except ftp_error.FTPOSError:
            # Everything's fine
            pass


if __name__ == '__main__':
    unittest.main()
