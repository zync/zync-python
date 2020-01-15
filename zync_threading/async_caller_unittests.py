""" Integration tests for async_task module. """
from unittest import TestCase, main

from async_caller import AsyncCaller
from base_interruptible_task import BaseInterruptibleTask
from default_thread_pool import DefaultThreadPool
from main_thread_caller import MainThreadCaller
from main_thread_executor import MainThreadExecutor
from test_utils import CountDownLatch


class TestAsyncCaller(TestCase):
  def test_should_execute_success_callback(self):
    # given
    test_results = []

    def _async_func():
      return 'async result'

    def _success_handler(result):
      test_results.append(result)

    thread_pool = DefaultThreadPool()
    async_caller = AsyncCaller(thread_pool, thread_pool.create_lock())

    # when
    async_caller.start_async_call(_async_func, _success_handler)
    while thread_pool.has_tasks():
      pass

    # then
    self.assertEqual(['async result'], test_results)

  def test_should_execute_error_callback_in_the_main_thread(self):
    # given
    test_results = []

    def _async_func():
      raise RuntimeError('async error')

    def _error_handler(err):
      test_results.append(str(err))

    thread_pool = DefaultThreadPool()
    async_caller = AsyncCaller(thread_pool, thread_pool.create_lock())

    # when
    async_caller.start_async_call(_async_func, on_error=_error_handler)
    while thread_pool.has_tasks():
      pass

    # then
    self.assertEqual(['async error'], test_results)

  def test_should_interrupt_all_async_tasks_and_no_other_tasks(self):
    # given
    test_results = []
    thread_pool = DefaultThreadPool(concurrency_level=4)
    latch = CountDownLatch(thread_pool.create_wait_condition())

    class _TestTask(BaseInterruptibleTask, MainThreadCaller):
      def __init__(self, executor):
        BaseInterruptibleTask.__init__(self)
        MainThreadCaller.__init__(self, executor)

      def run(self):
        """ Submit results. """
        latch.wait()
        test_results.append('test task')
        self.run_on_main_thread(lambda: test_results.append('test task'))

    def _async_func():
      latch.wait()
      return 'async result'

    def _success_handler(result):
      test_results.append(result)

    main_thread_executor = MainThreadExecutor(thread_pool)
    async_caller = AsyncCaller(thread_pool, thread_pool.create_lock())
    thread_pool.add_task(_TestTask(main_thread_executor))

    # when
    async_caller.start_async_call(_async_func, _success_handler)
    async_caller.start_async_call(_async_func, _success_handler)
    async_caller.start_async_call(_async_func, _success_handler)
    async_caller.interrupt_all_async_calls()
    latch.decrease()
    while thread_pool.has_tasks():
      main_thread_executor.maybe_execute_action()

    # then
    self.assertEqual(['test task', 'test task'], test_results)


if __name__ == '__main__':
  main()
