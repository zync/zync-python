"""
Unit tests for interruptible_task module.
"""
from unittest import TestCase, main

from base_interruptible_task import BaseInterruptibleTask
from interruptible_task import TaskInterruptedException


class _DummyTask(BaseInterruptibleTask):
  def __init__(self):
    BaseInterruptibleTask.__init__(self)

  def run(self):
    """ Does nothing. """


class TestInterruptibleTask(TestCase):
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

  def test_should_not_raise_exception_when_not_interrupted(self):
    # given
    task = _DummyTask()

    # when
    task.check_interrupted()

    # then
    # no exception

  def test_should_raise_exception_when_interrupted(self):
    # given
    task = _DummyTask()

    # when-then
    task.interrupt()
    with self.assertRaises(TaskInterruptedException) as ctx:
      task.check_interrupted()

if __name__ == '__main__':
  main()
