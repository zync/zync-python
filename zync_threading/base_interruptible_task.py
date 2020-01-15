""" Contains the base class for interruptible tasks. """
from abc import ABCMeta, abstractmethod

from interruptible_task import InterruptibleTask, TaskInterruptedException


class BaseInterruptibleTask(InterruptibleTask):
  """
  Base interruptible task class.

  :param Optional[str] name: (Optional) Name of the task. Passed to thread pool error handler to help
                             find the error causes.
  """

  __metaclass__ = ABCMeta

  def __init__(self, name=None):
    self._task_name = name if name else self.__class__.__name__
    self._interrupted = False

  def raise_interrupted_exception(self):
    """
    Raises a TaskInterruptedException with task-specific message.

    :raises:
      TaskInterruptedException: Always.
    """
    msg = 'Task %s was terminated due to external event.' % self.task_name
    raise TaskInterruptedException(msg)

  def check_interrupted(self):
    """
    If task is interrupted, raises TaskInterruptedException. If it is not interrupted, does nothing.

    :raises:
      TaskInterruptedException: If task is interrupted.
    """
    if self.is_interrupted:
      self.raise_interrupted_exception()

  @property
  def task_name(self):
    """
    Gets the name of the task.
    :return str:
    """
    return self._task_name

  def interrupt(self):
    """
    Marks the task as interrupted.
    """
    self._interrupted = True

  @property
  def is_interrupted(self):
    """
    Gets the interruption status of the task.

    :return bool:
    """
    return self._interrupted

  def on_cancelled(self):
    """
    Called by the thread pool when the task is interrupted before starting.

    Default implementation does nothing, can be overridden by subclasses.
    """

  @abstractmethod
  def run(self):
    """
    To be implemented by subclasses.
    """
    raise NotImplementedError()
