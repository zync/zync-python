""" Unit tests for detected_files_preflight_check module. """
import fcntl
import os
import shutil
import tempfile
from unittest import TestCase, main

from dependency_check import DependencyCheck
from zync_preflights import PreflightCheckResult as Result, PreflightCheckResultSeverity as Severity


class TestDetectedFilesPreflightCheck(TestCase):
  def __init__(self, *args, **kwargs):
    super(TestDetectedFilesPreflightCheck, self).__init__(*args, **kwargs)
    self._test_dir = None
    self.maxDiff = None

  def setUp(self):
    self._test_dir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self._test_dir)

  def _make_empty_files(self, file_names):
    file_paths = []
    for file_name in file_names:
      full_file_name = os.path.join(self._test_dir, file_name)
      open(full_file_name, 'a').close()
      file_paths.append(full_file_name)
    return file_paths

  def test_should_publish_correct_results(self):
    # given
    file_paths = self._make_empty_files(['A'])
    results = []
    check = DependencyCheck(file_paths + [os.path.join(self._test_dir, 'B')], lambda result: results.append(result))

    check.run()

    # then
    expected = [
      Result('Dependency Check', Severity.SUCCESS, 'File %s/A exists' % self._test_dir),
      Result('Dependency Check', Severity.WARNING, "File %s/B doesn't exist" % self._test_dir),
    ]
    self.assertEqual(expected, results)

if __name__ == '__main__':
  main()
