# Copyright (C) 2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

import unittest

import file_transfer


class MockFile(object):
    """Class compatible with `LocalFile` and `RemoteFile`."""

    def __init__(self, mtime, mtime_precision):
        self._mtime = mtime
        self._mtime_precision = mtime_precision

    def mtime(self):
        return self._mtime

    def mtime_precision(self):
        return self._mtime_precision


class TestTimestampComparison(unittest.TestCase):

    def test_source_is_newer_than_target(self):
        """Test whether the source is newer than the target, i. e.
        if the file should be transferred."""
        # Define some precisions.
        second = 1.0
        minute = 60.0 * second
        hour = 60 * minute
        day = 24 * hour
        # Define input arguments; modification datetimes are in seconds.
        #  Fields are source datetime/precision, target datetime/precision,
        #  expected comparison result.
        file_data = [
          # Non-overlapping modification datetimes/precisions
          (1000.0, second, 900.0, second, True),
          (900.0, second, 1000.0, second, False),
          # Equal modification datetimes/precisions (if in doubt, transfer)
          (1000.0, second, 1000.0, second, True),
          # Just touching intervals
          (1000.0, second, 1000.0+second, minute, True),
          (1000.0+second, minute, 1000.0, second, True),
          # Other overlapping intervals
          (10000.0-0.5*hour, hour, 10000.0, day, True),
          (10000.0+0.5*hour, hour, 10000.0, day, True),
          (10000.0+0.2*hour, 0.2*hour, 10000.0, hour, True),
          (10000.0-0.2*hour, 2*hour, 10000.0, hour, True),
        ]
        for (source_mtime, source_mtime_precision,
             target_mtime, target_mtime_precision,
             expected_result) in file_data:
            # print (source_mtime, source_mtime_precision,
            #        target_mtime, target_mtime_precision,
            #        expected_result)
            source_file = MockFile(source_mtime, source_mtime_precision)
            target_file = MockFile(target_mtime, target_mtime_precision)
            result = file_transfer.source_is_newer_than_target(source_file, 
                                                               target_file)
            self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()

