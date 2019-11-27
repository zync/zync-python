"""
Contains the base class for interruptible tasks.
"""
import traceback
from abc import ABCMeta, abstractmethod


class TaskInterruptedException(Exception):
  """
  Indicates that a task was terminated during the execution.
  """


class InterruptibleTask(object):
  """
  Base interruptible task class.

  :param str | None name: (Optional) Name of the task. Passed to thread pool error handler to help
                          find the error causes.
  :param (BaseException, str) -> None | None error_handler: (Optional) Called when exception is raised
                                                            in the run method. The exception and
                                                            traceback are passed to this callback.
  """

  __metaclass__ = ABCMeta

  def __init__(self, name=None, error_handler=None):
    self._name = name if name else 'Task %s' % id(self)
    self._error_handler = error_handler
    self._interrupted = False

  def raise_interrupted_exception(self):
    """
    Raises a TaskInterruptedException with task-specific message.

    :raises:
      TaskInterruptedException: Always.
    """
    msg = 'Task %s was terminated due to external event.' % self.name
    raise TaskInterruptedException(msg)

  @property
  def name(self):
    """
    Gets the name of the task.
    :return str:
    """
    return self._name

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

  def run_task(self):
    """
    Runs the task and handles errors.
    """
    try:
      if not self.is_interrupted:
        self.run()
    except BaseException as err:
      if self._error_handler:
        self._error_handler(err, traceback.format_exc())
      else:
        raise

  @abstractmethod
  def run(self):
    """
    To be implemented by subclasses.
    """
    raise NotImplementedError()
