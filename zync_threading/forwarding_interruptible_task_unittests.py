""" Contains unit tests for interruptible_task_proxy module. """

from unittest import TestCase, main

from interruptible_task import TaskInterruptedException
from base_interruptible_task import BaseInterruptibleTask
from forwarding_interruptible_task import ForwardingInterruptibleTask


class TestForwardingInterruptibleTask(TestCase):
  def test_should_delegate_all_methods(self):
    # given
    results = []
    class _TestTask(BaseInterruptibleTask):
      def __init__(self):
        BaseInterruptibleTask.__init__(self, 'test-task')

      def run(self):
        """ Appends to results. """
        results.append('test-result')

      def on_cancelled(self):
        """ Appends to results. """
        results.append('on-cancelled')

    proxy = ForwardingInterruptibleTask(_TestTask())

    # when
    name = proxy.task_name
    is_interrupted1 = proxy.is_interrupted
    proxy.run()
    proxy.on_cancelled()
    proxy.interrupt()
    is_interrupted2 = proxy.is_interrupted
    with self.assertRaises(TaskInterruptedException):
      proxy.check_interrupted()

    # then
    self.assertEqual('test-task', name)
    self.assertFalse(is_interrupted1)
    self.assertTrue(is_interrupted2)
    self.assertEqual(['test-result', 'on-cancelled'], results)

if __name__ == '__main__':
  main()
