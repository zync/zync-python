""" Unit tests for main_thread_action module. """

from unittest import TestCase, main
from main_thread_action import MainThreadActionResult, MainThreadAction

class TestActionResult(TestCase):
  def test_should_return_true_if_exception(self):
    # given
    action_result = MainThreadActionResult(exception=RuntimeError())

    # then
    self.assertTrue(action_result.is_exception)

  def test_should_return_false_if_not_exception(self):
    # given
    action_result = MainThreadActionResult(result=list())

    # then
    self.assertFalse(action_result.is_exception)

  def test_should_reraise_exception(self):
    # given
    action_result = MainThreadActionResult(exception=Exception('action error'))

    # then
    with self.assertRaises(Exception) as ctx:
      _result = action_result.result
    self.assertEqual('action error', str(ctx.exception))

  def test_should_return_result_if_not_exception(self):
    # given
    action_result = MainThreadActionResult(result='success')

    # when
    result = action_result.result

    # then
    self.assertEqual('success', result)

  def test_should_raise_exception_if_arguments_not_provided(self):
    # when
    with self.assertRaises(ValueError) as ctx:
      MainThreadActionResult()

    # then
    self.assertEqual('Either `result` or `exception` argument must be provided.', str(ctx.exception))

  def test_should_raise_exception_if_both_arguments_provided(self):
    # when
    with self.assertRaises(ValueError) as ctx:
      MainThreadActionResult(result=list(), exception=RuntimeError())

    # then
    self.assertEqual('Either `result` or `exception` argument must be provided.', str(ctx.exception))

  def test_should_raise_exception_if_exception_argument_is_not_exception(self):
    # when
    with self.assertRaises(ValueError) as ctx:
      MainThreadActionResult(exception=list())

    # then
    self.assertEqual('Argument `exception` must be an exception.', str(ctx.exception))

class TestAction(TestCase):
  def test_should_return_action_result_with_call_result(self):
    # given
    action = MainThreadAction(lambda: 13)

    # when
    action_result = action.execute()

    # then
    self.assertEqual(13, action_result.result)

  def test_should_return_action_result_with_exception(self):
    # given
    def _raise_syntax_error():
      raise SyntaxError('call error')
    action = MainThreadAction(_raise_syntax_error)

    # when
    action_result = action.execute()

    # then
    with self.assertRaises(SyntaxError) as ctx:
      _result = action_result.result
    self.assertEqual('call error', str(ctx.exception))

  def test_should_submit_result(self):
    # given
    submitted_results = []

    def _submit_result(result):
      submitted_results.append(result)

    action = MainThreadAction(lambda: 23, _submit_result)

    # when
    action.execute_and_submit()

    # then
    self.assertEqual([23], [action_result.result for action_result in submitted_results])


if __name__ == '__main__':
  main()
