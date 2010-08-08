# Copyright (C) 2006-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

import sys


# ftputil version number; substituted by `make patch`
__version__ = '2.5dev'

_ftputil_version = __version__
_python_version = sys.version.split()[0]
_python_platform = sys.platform

version_info = "ftputil %s, Python %s (%s)" % \
               (_ftputil_version, _python_version, _python_platform)

