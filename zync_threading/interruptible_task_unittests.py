"""
Unit tests for interruptible_task module.
"""
from unittest import TestCase
from interruptible_task import InterruptibleTask


class _DummyTask(InterruptibleTask):
  def run(self):
    """ Does nothing. """


class TestInterruptibleTask(TestCase):
  def test_default_name_should_be_unique(self):
    # given
    task1 = _DummyTask()
    task2 = _DummyTask()

    # then
    self.assertNotEqual(task1.name, task2.name)

  def test_should_start_not_interrupted(self):
    # given
    task = _DummyTask()

    # then
    self.assertFalse(task.is_interrupted)

  def test_should_be_marked_interrupted(self):
    # given
    task = _DummyTask()

    # when
    task.interrupt()

    # then
    self.assertTrue(task.is_interrupted)

  def test_should_handle_exceptions(self):
    # given
    test_results = []

    def _handle_error(exception, traceback_str):
      test_results.append((str(exception), traceback_str))

    class _TestTask(InterruptibleTask):
      def __init__(self):
        super(_TestTask, self).__init__(error_handler=_handle_error)

      def run(self):
        """ Raises an exception """
        raise RuntimeError('task error')

    task = _TestTask()

    # when
    task.run_task()

    # then
    self.assertEqual('task error', test_results[0][0])
    self.assertTrue(len(test_results[0][1]) > 0)
    self.assertTrue(len(test_results) == 1)
