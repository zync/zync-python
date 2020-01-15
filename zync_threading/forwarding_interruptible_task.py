""" Contains ForwardingInterruptibleTask class. """

from interruptible_task import InterruptibleTask

class ForwardingInterruptibleTask(InterruptibleTask):
  """
  Implements proxy that delegates all methods and properties to an instance of InterruptibleTask.

  :param InterruptibleTask original_task:
  """
  def __init__(self, original_task):
    self._original_task = original_task

  def check_interrupted(self):
    """ Delegates to check_interrupted method of the original_task. """
    self._original_task.check_interrupted()

  @property
  def task_name(self):
    """
    Delegates to name method of the original_task.

    :return str:
    """
    return self._original_task.task_name

  def interrupt(self):
    """ Delegates to interrupt method of the original_task. """
    self._original_task.interrupt()

  @property
  def is_interrupted(self):
    """
    Delegates to is_interrupted property of the original_task.

    :return bool:
    """
    return self._original_task.is_interrupted

  def on_cancelled(self):
    """
    Delegates to on_cancelled method of the original_task.
    """
    self._original_task.on_cancelled()

  def run(self):
    """ Delegates to run method of the original_task. """
    self._original_task.run()
