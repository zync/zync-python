"""
Contains base class for tasks that can run part of their work on the main thread.
"""
from abc import ABCMeta
from functools import wraps, partial

from interruptible_task import InterruptibleTask


class BackgroundTask(InterruptibleTask):
  """
  Base class for background tasks that can run in arbitrary thread and do part of the work on the
  main thread.

  :param main_thread_executor.MainThreadExecutor main_thread_executor: Executor that will be used to
         execute actions that need to run on the main thread.
  :param Optional[str] name:
  :param Optional[(BaseException, str) -> None] error_handler: Accepts exception and traceback string.
         Returns True if error was handled and False otherwise.
  """

  __metaclass__ = ABCMeta

  def __init__(self, main_thread_executor, name=None, error_handler=None):
    super(BackgroundTask, self).__init__(name if name else 'Background Task %s' % id(self), error_handler)
    self._main_thread_executor = main_thread_executor

  def run_on_main_thread(self, func):
    """
    Runs func on the main thread. Returns the return value of func, or reraises any exception raised
    by func.

    :param () -> object func: Function that will be executed on main thread.
    :return object:
    :raises:
      TaskInterruptedException: if task is interrupted during the execution.
    """
    return self._main_thread_executor.run_on_main_thread(self, func)

  @staticmethod
  def main_thread(func):
    """
    Decorates a method of BackgroundTask subclass to indicate it should be run on the main thread.
    """
    @wraps(func)
    def _wrapped(self, *args, **kwargs):
      return self.run_on_main_thread(partial(func, self, *args, **kwargs))
    return _wrapped
