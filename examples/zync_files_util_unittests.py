#!/usr/bin/env python
# """Unittests for zync_files_util.py"""
import unittest

import zync_files_util


class TestZyncFilesUtil(unittest.TestCase):
  def test_format_file_size(self):
    test_cases = {
      1: '1.0 B',
      1024: '1.0 KB',
      1025: '1.0 KB',
      1048576: '1.0 MB',
      1548576: '1.5 MB',
      1073741824: '1.0 GB',
      1099511627776: '1.0 TB',
      2199511627776: '2.0 TB',
      1126999418470400: '1025.0 TB'
    }
    for test_case, expected in test_cases.iteritems():
      self.assertEqual(expected, zync_files_util._format_file_size(test_case))

  def test_build_gcs_prefix(self):
    test_cases = [
      ('baz', 'c:/foo/bar', 'projects/baz/c:/foo/bar'),
      ('baz', '/usr/foo/bar', 'projects/baz/usr/foo/bar')
    ]
    for project, path, expected in test_cases:
      self.assertEqual(expected,
                       zync_files_util._build_gcs_prefix(project, path))


def main():
  unittest.main()

if __name__ == '__main__':
  main()
