""" Contains MainThreadCaller base class. """
from abc import ABCMeta
from functools import wraps, partial

from base_interruptible_task import BaseInterruptibleTask


class MainThreadCaller(object):
  """
  Base class that provides a mechanism to force part of the work to run on the main thread.

  :param main_thread_executor.MainThreadExecutor main_thread_executor:
  """
  def __init__(self, main_thread_executor):
    self._main_thread_executor = main_thread_executor

  def run_on_main_thread(self, func):
    """
    Runs func on the main thread and returns its result.

    :param () -> object func:
    :return object:
    :raises:
      TaskInterruptedException: if task is interrupted during the execution.
    """
    return self._main_thread_executor.run_on_main_thread(func)

  @staticmethod
  def main_thread(func):
    """
    Decorates a method of MainThreadCaller subclass to indicate it should be run on the main thread.
    """
    @wraps(func)
    def _wrapped(self, *args, **kwargs):
      return self.run_on_main_thread(partial(func, self, *args, **kwargs))
    return _wrapped


class InterruptibleMainThreadCaller(BaseInterruptibleTask):
  """
  Base class for interruptible task that implements a mechanism to force part of the work to run
  on the main thread.

  :param main_thread_executor.MainThreadExecutor main_thread_executor:
  """

  __metaclass__ = ABCMeta

  def __init__(self, main_thread_executor, name=None):
    BaseInterruptibleTask.__init__(self, name)
    self._main_thread_executor = main_thread_executor

  def run_on_main_thread(self, func, ignore_interrupts=False):
    """
    Runs func on the main thread and returns its result.

    :param () -> object func:
    :param bool ignore_interrupts: Ignores the interrupts if True. Default is False.
    :return object:
    """
    return self._main_thread_executor.run_on_main_thread(func, None if ignore_interrupts else self.check_interrupted)

  @staticmethod
  def main_thread(func):
    """ Decorates a method of MainThreadCaller subclass to indicate it should be run on the main thread. """
    @wraps(func)
    def _wrapped(self, *args, **kwargs):
      return self.run_on_main_thread(partial(func, self, *args, **kwargs))
    return _wrapped

  @staticmethod
  def main_thread_ignore_interrupts(func):
    """ Decorates a method of MainThreadCaller subclass to indicate it should be run on the main thread. """
    @wraps(func)
    def _wrapped(self, *args, **kwargs):
      return self.run_on_main_thread(partial(func, self, *args, **kwargs), ignore_interrupts=True)
    return _wrapped
