""" Contains ThreadPool interface. """
from abc import ABCMeta, abstractmethod


class ThreadPool(object):
  """ Interface for thread pools. """
  __metaclass__ = ABCMeta

  @abstractmethod
  def add_task(self, task):
    """
    Adds a task to be executed in the pool.

    :param interruptible_task.InterruptibleTask task:
    """
    raise NotImplementedError()

  @abstractmethod
  def shutdown(self, wait):
    """
    Stops accepting new tasks.

    If wait is True, it waits for running tasks to finish.

    :param bool wait:
    """
    raise NotImplementedError()
