""" Unit tests for main_thread_executor module. """
from unittest import TestCase, main
from threading import current_thread
from collections import defaultdict

from default_thread_pool import DefaultThreadPool
from main_thread_caller import InterruptibleMainThreadCaller
from main_thread_executor import MainThreadExecutor
from test_utils import CountDownLatch


class TestMainThreadExecutor(TestCase):
  def test_should_not_block_when_called_from_the_main_thread(self):
    # given
    results = []
    executor = MainThreadExecutor(DefaultThreadPool())

    def _test_func1(x):
      results.append(x)

    def _test_func2():
      results.append(1)
      _test_func1(2)

    # when
    executor.run_on_main_thread(_test_func2)

    # then
    self.assertEqual([1, 2], results)

  def test_should_run_parallel_tasks_and_part_of_work_in_main_thread(self):
    # given
    main_thread = current_thread().ident

    class _TestTask(InterruptibleMainThreadCaller):
      def __init__(self, executor, results, latch):
        InterruptibleMainThreadCaller.__init__(self, executor)
        self._results = results
        self._latch = latch

      def run(self):
        """ Does work in a background thread and main thread """
        self._latch.decrease()
        self._latch.wait()
        self._results.append((1, main_thread == current_thread().ident))
        self.run_on_main_thread(lambda: self._results.append((2, main_thread == current_thread().ident)))
        self._results.append((3, main_thread == current_thread().ident))
        self._append_4()

      @InterruptibleMainThreadCaller.main_thread
      def _append_4(self):
        self._results.append((4, main_thread == current_thread().ident))
        # this call tests if executor is reentrant
        self._append_5()

      @InterruptibleMainThreadCaller.main_thread
      def _append_5(self):
        self._results.append((5, main_thread == current_thread().ident))

    test_results = defaultdict(list)

    thread_pool = DefaultThreadPool(concurrency_level=4)
    main_thread_executor = MainThreadExecutor(thread_pool)
    test_latch = CountDownLatch(thread_pool.create_wait_condition(), 4)

    for i in xrange(4):
      thread_pool.add_task(_TestTask(main_thread_executor, test_results['task' + str(i)], test_latch))

    # when
    while thread_pool.has_tasks():
      main_thread_executor.maybe_execute_action()

    # then
    expected_task_result = [(1, False), (2, True), (3, False), (4, True), (5, True)]
    expected = defaultdict(list, {
      'task0':expected_task_result,
      'task1':expected_task_result,
      'task2':expected_task_result,
      'task3':expected_task_result
    })
    self.assertEqual(expected, test_results)

  def test_should_execute_callbacks(self):
    # given
    thread_pool = DefaultThreadPool(concurrency_level=2)

    latch1 = CountDownLatch(thread_pool.create_wait_condition(), 2)
    latch2 = CountDownLatch(thread_pool.create_wait_condition(), 2)

    class _TestTask(InterruptibleMainThreadCaller):
      def __init__(self, executor):
        InterruptibleMainThreadCaller.__init__(self, executor)

      def run(self):
        """ Does work in the main thread """
        latch1.decrease()
        latch1.wait()
        self.run_on_main_thread(lambda: None)
        latch2.decrease()
        latch2.wait()
        self.run_on_main_thread(lambda: None)

    callback_results = []

    def _on_action_submitted():
      callback_results.append('submit')

    def _on_actions_pending():
      callback_results.append('pending')


    main_thread_executor = MainThreadExecutor(thread_pool, _on_action_submitted, _on_actions_pending)
    thread_pool.add_task(_TestTask(main_thread_executor))
    thread_pool.add_task(_TestTask(main_thread_executor))

    # when
    while main_thread_executor.size() < 2:
      pass
    main_thread_executor.maybe_execute_action()
    main_thread_executor.maybe_execute_action()
    while main_thread_executor.size() < 2:
      pass
    main_thread_executor.maybe_execute_action()
    main_thread_executor.maybe_execute_action()

    # then
    self.assertEqual(['submit','submit','pending','submit','submit', 'pending'], callback_results)

if __name__ == '__main__':
  main()
