""" Unit tests for preflight_check_suite module. """
from collections import defaultdict
from unittest import TestCase, main

from zync_threading import BaseInterruptibleTask
from zync_threading.default_thread_pool import DefaultThreadPool
from zync_threading.test_utils import CountDownLatch
from preflight_check import PreflightCheck, PreflightCheckExecutionStatus as Status
from preflight_check_result import PreflightCheckResult as Result, PreflightCheckResultSeverity as Severity
from preflight_check_suite import PreflightCheckSuite as Suite


class TestPreflightSuite(TestCase):
  def test_should_complete_check(self):
    # given
    thread_pool = DefaultThreadPool(concurrency_level=4)

    statuses = []
    def _on_status_change(_preflight_check, status):
      statuses.append(status)

    results = []
    def _on_result(result):
      results.append(result)

    class _TestCheck(PreflightCheck, BaseInterruptibleTask):
      def __init__(self):
        PreflightCheck.__init__(self, 'test-check', None)
        BaseInterruptibleTask.__init__(self, 'test-check')

      def run(self):
        """ Publishes results. """
        _on_result(Result(self.preflight_name, Severity.SUCCESS, 'result 1'))

    finished = []
    def _on_finished():
      finished.append(True)

    suite = Suite(thread_pool, thread_pool.create_lock(), _on_status_change, _on_finished, [_TestCheck()])

    # when
    suite.start()
    while len(finished) == 0:
      pass

    # then
    self.assertEqual([Status.PENDING, Status.RUNNING, Status.COMPLETED], statuses)
    self.assertEqual([Result('test-check', Severity.SUCCESS, 'result 1')], results)

  def test_should_cancel_check(self):
    # given
    thread_pool = DefaultThreadPool(concurrency_level=4)

    statuses = []
    def _on_status_change(_preflight_check, status):
      statuses.append(status)

    results = []
    def _on_result(result):
      results.append(result)

    class _TestCheck(PreflightCheck, BaseInterruptibleTask):
      def __init__(self):
        PreflightCheck.__init__(self, 'test-check', None)
        BaseInterruptibleTask.__init__(self, 'test-check')

      def run(self):
        """ Publishes results. """
        _on_result(Result(self.preflight_name, Severity.SUCCESS, 'result 1'))
        self.raise_interrupted_exception()
        _on_result(Result(self.preflight_name, Severity.INFO, 'result 2'))

    finished = []
    def _on_finished():
      finished.append(True)

    suite = Suite(thread_pool, thread_pool.create_lock(), _on_status_change, _on_finished, [_TestCheck()])

    # when
    suite.start()
    while len(finished) == 0:
      pass

    # then
    self.assertEqual([Status.PENDING, Status.RUNNING, Status.CANCELLED], statuses)
    self.assertEqual([Result('test-check', Severity.SUCCESS, 'result 1')], results)

  def test_should_error_check(self):
    # given
    thread_pool = DefaultThreadPool(concurrency_level=4)

    statuses = []
    def _on_status_change(_preflight_check, status):
      statuses.append(status)

    results = []
    def _on_result(result):
      results.append(result)

    class _TestCheck(PreflightCheck, BaseInterruptibleTask):
      def __init__(self):
        PreflightCheck.__init__(self, 'test-check', None)
        BaseInterruptibleTask.__init__(self, 'test-check')

      def run(self):
        """ Publishes results. """
        _on_result(Result(self.preflight_name, Severity.SUCCESS, 'result 1'))
        raise RuntimeError('test errored')

    finished = []
    def _on_finished():
      finished.append(True)

    suite = Suite(thread_pool, thread_pool.create_lock(), _on_status_change, _on_finished, [_TestCheck()])

    # when
    suite.start()
    while len(finished) == 0:
      pass

    # then
    self.assertEqual([Status.PENDING, Status.RUNNING, Status.ERRORED], statuses)
    self.assertEqual([Result('test-check', Severity.SUCCESS, 'result 1')], results)

  def test_should_cancel_checks(self):
    # given
    thread_pool = DefaultThreadPool(concurrency_level=4)
    count_down_latch1 = CountDownLatch(thread_pool.create_wait_condition(), 3)
    count_down_latch2 = CountDownLatch(thread_pool.create_wait_condition(), 1)

    statuses = defaultdict(list)
    def _on_status_change(preflight_check, status):
      statuses[preflight_check.preflight_name].append(status)

    results = defaultdict(list)
    def _on_result(preflight_check, result):
      results[preflight_check.preflight_name].append(result)

    class _TestCheck(PreflightCheck, BaseInterruptibleTask):
      def __init__(self, publish_result, name):
        PreflightCheck.__init__(self, name, 'test')
        BaseInterruptibleTask.__init__(self, name)

      def run(self):
        """ Publishes results. """
        count_down_latch1.decrease()
        _on_result(self, Result(self.preflight_name, Severity.SUCCESS, 'result 1'))
        count_down_latch2.wait()
        self.check_interrupted()

    test_checks = [
      _TestCheck(_on_result, 'check 1'),
      _TestCheck(_on_result, 'check 2'),
      _TestCheck(_on_result, 'check 3')
    ]

    finished = []
    def _on_finished():
      finished.append(True)

    suite = Suite(thread_pool, thread_pool.create_lock(), _on_status_change, _on_finished, test_checks)

    # when
    suite.start()
    count_down_latch1.wait()
    suite.cancel()
    count_down_latch2.decrease()
    while len(finished) == 0:
      pass

    # then
    self.assertEqual([Status.PENDING, Status.RUNNING, Status.CANCELLED], statuses['check 1'])
    self.assertEqual([Status.PENDING, Status.RUNNING, Status.CANCELLED], statuses['check 2'])
    self.assertEqual([Status.PENDING, Status.RUNNING, Status.CANCELLED], statuses['check 3'])
    self.assertEqual([Result('check 1', Severity.SUCCESS, 'result 1')], results['check 1'])
    self.assertEqual([Result('check 2', Severity.SUCCESS, 'result 1')], results['check 2'])
    self.assertEqual([Result('check 3', Severity.SUCCESS, 'result 1')], results['check 3'])


if __name__ == '__main__':
  main()
