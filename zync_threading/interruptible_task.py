""" Contains InterruptibleTask interface.  """
from abc import ABCMeta, abstractmethod, abstractproperty


class TaskInterruptedException(Exception):
  """
  Indicates that a task was terminated during the execution.
  """


class InterruptibleTask(object):
  """ Interface for tasks that can be interrupted. """

  __metaclass__ = ABCMeta

  @abstractmethod
  def check_interrupted(self):
    """
    If task is interrupted, raises TaskInterruptedException. If it is not interrupted, does nothing.

    :raises:
      TaskInterruptedException: If task is interrupted.
    """
    raise NotImplementedError()

  @abstractproperty
  def task_name(self):
    """
    Gets the name of the task.

    :return str:
    """
    raise NotImplementedError()

  @abstractmethod
  def interrupt(self):
    """ Marks the task as interrupted. """
    raise NotImplementedError()

  @abstractproperty
  def is_interrupted(self):
    """
    Gets the interruption status of the task.

    :return bool:
    """
    raise NotImplementedError()

  @abstractmethod
  def on_cancelled(self):
    """
    Called by the thread pool on a task that was interrupted before starting.
    """
    raise NotImplementedError()

  @abstractmethod
  def run(self):
    """
    Actual workload of the task.
    """
    raise NotImplementedError()
