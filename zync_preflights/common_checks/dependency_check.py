"""
Contains implementation of preflight check which checks if detected dependencies are readable.
"""
import os
from zync_preflights import PreflightCheck, PreflightCheckResult as Result, PreflightCheckResultSeverity as Severity
from zync_threading import BaseInterruptibleTask

# TODO: + measure performance for large number of files and NFS mounts;
#       + can an asset path contain wildcards? if yes, need to implement that
#       + investigate how to test readability and implement it
class DependencyCheck(PreflightCheck, BaseInterruptibleTask):
  """
  Checks if the files exist and are readable.

  :param collections.Iterable[str] file_paths:
  :param (preflight_check_result.PreflightCheckResult) -> None result_listener:
  """
  def __init__(self, file_paths, result_listener):
    PreflightCheck.__init__(self, 'Dependency Check', 'Checks if detected file dependencies exist.')
    BaseInterruptibleTask.__init__(self, 'Dependency Check')
    self._file_paths = file_paths
    self._publish_result = result_listener

  def run(self):
    """ Checks if files exist and are readable. """
    for file_path in self._file_paths:
      self.check_interrupted()
      if os.path.isfile(file_path):
        self._publish_result(self._success(file_path))
      else:
        self._publish_result(self._doesnt_exist(file_path))

  def _success(self, file_path):
    return Result(self.preflight_name, Severity.SUCCESS, 'File %s exists' % file_path)

  def _doesnt_exist(self, file_path):
    return Result(self.preflight_name, Severity.WARNING, "File %s doesn't exist" % file_path)
