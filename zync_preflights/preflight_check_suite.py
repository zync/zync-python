""" Contains PreflightExecutor class. """
import traceback

from preflight_check import PreflightCheckExecutionStatus as Status
from zync_threading import ForwardingInterruptibleTask, TaskInterruptedException


class _PreflightWrapper(ForwardingInterruptibleTask):
  def __init__(self, preflight_check, execution_status_listener, finalize_callback):
    super(_PreflightWrapper, self).__init__(preflight_check)
    self._preflight_check = preflight_check
    self._execution_status_listener = execution_status_listener
    self._finalize_callback = finalize_callback
    self._execution_status = Status.PENDING

  def _change_execution_status(self, new_status):
    if new_status != self._execution_status:
      self._execution_status_listener(self._preflight_check, new_status)
      self._execution_status = new_status

  def run(self):
    """ Calls the original run method and marks the preflight check as finished. """
    self._change_execution_status(Status.RUNNING)
    try:
      super(_PreflightWrapper, self).run()
      self._change_execution_status(Status.COMPLETED)
    except TaskInterruptedException:
      self._change_execution_status(Status.CANCELLED)
    except BaseException:
      self._change_execution_status(Status.ERRORED)
      raise
    finally:
      self._finalize_callback(self._preflight_check)

  def on_cancelled(self):
    """ Marks the preflight check as finished. """
    super(_PreflightWrapper, self).on_cancelled()
    self._change_execution_status(Status.CANCELLED)
    self._finalize_callback(self._preflight_check)


class PreflightCheckSuite(object):
  """
  Allows to run and cancel a collection of PreflightChecks and publishes notifications about
  their state.

  :param zync_threading.abstract_thread_pool.AbstractThreadPool thread_pool:
  :param zync_threading.thread_synchronization.Lock lock:
  :param (preflight_check.PreflightCheck,
  preflight_check_execution_status.PreflightCheckExecutionStatus) -> None execution_status_listener:
  :param () -> None on_checks_finished:
  :param [preflight_check.PreflightCheck] preflight_checks:
  """
  def __init__(self, thread_pool, lock, execution_status_listener, on_checks_finished, preflight_checks):
    self._thread_pool = thread_pool
    self._preflight_checks_lock = lock
    self._preflight_checks = set(preflight_checks)
    self._execution_status_listener = execution_status_listener
    self._on_checks_finished = on_checks_finished

  def start(self):
    """ Starts to run preflight checks as tasks in the thread pool. """
    with self._preflight_checks_lock:
      for preflight_check in self._preflight_checks:
        self._execution_status_listener(preflight_check, Status.PENDING)
        self._thread_pool.add_task(_PreflightWrapper(preflight_check, self._execution_status_listener, self._finalize_check))

  def _finalize_check(self, preflight_check):
    with self._preflight_checks_lock:
      self._preflight_checks.remove(preflight_check)
      if len(self._preflight_checks) == 0:
        if self._on_checks_finished:
          self._on_checks_finished()

  def cancel(self):
    """ Cancels all unfinished or pending preflight checks by interrupting them. """
    with self._preflight_checks_lock:
      for preflight_check in self._preflight_checks:
        preflight_check.interrupt()
