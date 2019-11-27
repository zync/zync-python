"""
Unit tests for default_thread_pool module.
"""

from unittest import TestCase
from default_thread_pool import DefaultThreadPool
from interruptible_task import InterruptibleTask
from test_utils import CountDownLatch
import thread_synchronization

class TestDefaultThreadPool(TestCase):
  def test_should_run_4_parallel_tasks(self):
    # given
    class _TestTask(InterruptibleTask):
      def __init__(self, counter, order, num_threads, iterations, results):
        super(_TestTask, self).__init__()
        self._counter = counter
        self._order = order
        self._num_threads = num_threads
        self._iterations = iterations
        self._results = results

      def run(self):
        """ Wait for the correct number and increment it"""
        for iteration in xrange(self._iterations):
          while self._counter['value'] % self._num_threads != self._order:
            pass
          if iteration + 1 == self._iterations:
            self._results.append((self._order, iteration))
          self._counter['value'] += 1

    thread_pool = DefaultThreadPool(concurrency_level=4)
    test_counter = {'value': 0}
    test_results = []

    # when
    for task_order in xrange(4):
      task = _TestTask(test_counter, 3 - task_order, 4, 100, test_results)
      thread_pool.add_task(task)
    while len(test_results) < 4:
      pass

    # then
    self.assertEqual([(0, 99), (1, 99), (2, 99), (3, 99)], test_results)

  def test_should_not_start_interrupted_task(self):
    # given
    class _TestTask(InterruptibleTask):
      def __init__(self, results):
        super(_TestTask, self).__init__()
        self._results = results

      def run(self):
        """ Append a number to results """
        self._results.append(13)

    test_results = []
    task = _TestTask(test_results)
    task.interrupt()
    thread_pool = DefaultThreadPool()

    # when
    thread_pool.add_task(task)
    while thread_pool.has_tasks():
      pass

    # then
    self.assertEqual([], test_results)

  def test_should_create_lock_and_wait_condition(self):
    # given
    errors = []
    def _error_handler(exception, traceback):
      errors.append((str(exception), traceback))

    class _TestTask(InterruptibleTask):
      def __init__(self, wait_first, results, wait_condition, latch):
        super(_TestTask, self).__init__(error_handler=_error_handler)
        self._wait_first = wait_first
        self._results = results
        self._wait_condition = wait_condition
        self._latch = latch

      def run(self):
        """ Waits for a condition or notifies other thread """
        if self._wait_first:
          self._wait()
        else:
          self._notify()

      def _wait(self):
        with self._wait_condition:
          self._results.append((self._wait_first, 'wait'))
          self._latch.decrease()
          self._wait_condition.wait()
          self._results.append((self._wait_first, 'wakeup'))

      def _notify(self):
        self._latch.wait()
        with self._wait_condition:
          self._wait_condition.notify_all()
          self._results.append((self._wait_first, 'notify'))

    test_thread_pool = DefaultThreadPool(concurrency_level=2)
    test_latch = CountDownLatch(test_thread_pool.create_wait_condition())
    test_results = []
    test_lock = test_thread_pool.create_lock()
    test_wait_condition = test_thread_pool.create_wait_condition(test_lock)

    # when
    test_thread_pool.add_task(_TestTask(True, test_results, test_wait_condition, test_latch))
    test_thread_pool.add_task(_TestTask(False, test_results, test_wait_condition, test_latch))
    while len(test_results) < 3 and len(errors) == 0:
      pass

    # then
    self.assertEqual([], errors)
    self.assertEqual([(True, 'wait'), (False, 'notify'), (True, 'wakeup')], test_results)


  def test_should_call_task_error_handler_and_not_pool_error_handler(self):
    # given
    task_result = dict()
    pool_result = dict()

    def _task_error_handler(exception, traceback):
      task_result['exception'] = str(exception)
      task_result['traceback'] = traceback

    def _pool_error_handler(_name, exception, traceback):
      pool_result['exception'] = exception
      pool_result['traceback'] = traceback

    class _TestTask(InterruptibleTask):
      def __init__(self):
        super(_TestTask, self).__init__(error_handler=_task_error_handler)

      def run(self):
        """ Raises an exception """
        raise RuntimeError('test error')

    thread_pool = DefaultThreadPool(error_handler=_pool_error_handler)

    # when
    thread_pool.add_task(_TestTask())
    while thread_pool.has_tasks():
      pass

    # then
    self.assertEqual(dict(), pool_result)
    self.assertEqual('test error', task_result['exception'])
    self.assertTrue(len(task_result['traceback']) > 0)

  def test_should_call_pool_error_handler_and_task_error_handler(self):
    # given
    task_results = []
    pool_results = []

    def _task_error_handler(exception, _traceback):
      task_results.append(str(exception))

    def _pool_error_handler(task_name, exception, _traceback):
      pool_results.append((task_name, str(exception)))

    class _TestTask(InterruptibleTask):
      def __init__(self, name, error_handler=None):
        super(_TestTask, self).__init__(name=name, error_handler=error_handler)

      def run(self):
        """ Raises an exception """
        raise RuntimeError(self.name + ' test error')

    thread_pool = DefaultThreadPool(error_handler=_pool_error_handler)

    # when
    thread_pool.add_task(_TestTask('task1', _task_error_handler))
    thread_pool.add_task(_TestTask('task2'))
    while thread_pool.has_tasks():
      pass

    # then
    self.assertEqual(['task1 test error'], task_results)
    self.assertTrue(('task2', 'task2 test error') in pool_results)

  def test_should_handle_exception_in_task_error_handler(self):
    # given
    pool_results = {}

    def _task_error_handler(_exception, _traceback):
      raise RuntimeError('faulty handler')

    def _pool_error_handler(task_name, exception, traceback):
      pool_results[str(exception)] = (task_name, traceback)

    class _TestTask(InterruptibleTask):
      def __init__(self):
        super(_TestTask, self).__init__(name='test task', error_handler=_task_error_handler)

      def run(self):
        """ Raise an exception """
        raise RuntimeError('task error')

    thread_pool = DefaultThreadPool(error_handler=_pool_error_handler)

    # when
    thread_pool.add_task(_TestTask())
    while thread_pool.has_tasks():
      pass

    # then
    self.assertEqual('test task', pool_results['faulty handler'][0])
    self.assertTrue(len(pool_results['faulty handler'][1]) > 0)


class TestSynchronizationPrimitives(TestCase):
  def test_default_lock_should_be_subclass_of_zync_threading_lock(self):
    self.assertTrue(isinstance(DefaultThreadPool().create_lock(), thread_synchronization.Lock))

  def test_default_condition_should_be_subclass_of_zync_threading_wait_condition(self):
    self.assertTrue(isinstance(DefaultThreadPool().create_wait_condition(), thread_synchronization.WaitCondition))
