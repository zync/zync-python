""" Unit tests for main_thread_caller module. """
from unittest import TestCase, main

from main_thread_caller import MainThreadCaller, InterruptibleMainThreadCaller


class TestMainThreadCaller(TestCase):
  def test_should_pass_check_interrupted_to_executor_if_interruptible(self):
    # given
    results = []

    class _TestTask(InterruptibleMainThreadCaller):
      def __init__(self, executor):
        InterruptibleMainThreadCaller.__init__(self, executor)

      def run(self):
        """ Does nothing. """
        self._do_nothing()

      @InterruptibleMainThreadCaller.main_thread
      def _do_nothing(self):
        pass

    class _TestExecutor(object):
      @staticmethod
      def run_on_main_thread(_func, check_interrupted=None):
        """ Pushes task name to results. """
        results.append(check_interrupted is None)

    test_task = _TestTask(_TestExecutor())

    # when
    test_task.run()

    # then
    self.assertEqual([False], results)

  def test_should_not_pass_check_interrupted_to_executor_if_interruptible_but_interrupts_ignored(self):
    # given
    results = []

    class _TestTask(InterruptibleMainThreadCaller):
      def __init__(self, executor):
        InterruptibleMainThreadCaller.__init__(self, executor)

      def run(self):
        """ Does nothing. """
        self._do_nothing()

      @InterruptibleMainThreadCaller.main_thread_ignore_interrupts
      def _do_nothing(self):
        pass

    class _TestExecutor(object):
      @staticmethod
      def run_on_main_thread(_func, check_interrupted=None):
        """ Pushes task name to results. """
        results.append(check_interrupted is None)

    test_task = _TestTask(_TestExecutor())

    # when
    test_task.run()

    # then
    self.assertEqual([True], results)

  def test_should_not_pass_check_interrupted_to_executor_if_not_interruptible(self):
    # given
    results = []

    class _TestCaller(MainThreadCaller):
      def __init__(self, executor):
        MainThreadCaller.__init__(self, executor)

      @MainThreadCaller.main_thread
      def do_nothing(self):
        """ Does nothing. """
        pass

    class _TestExecutor(object):
      @staticmethod
      def run_on_main_thread(_func, check_interrupted=None):
        """ Pushes task to results. """
        results.append(check_interrupted is None)

    test_caller = _TestCaller(_TestExecutor())

    # when
    test_caller.do_nothing()

    # then
    self.assertEqual([True], results)

if __name__ == '__main__':
  main()
