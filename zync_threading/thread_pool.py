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
