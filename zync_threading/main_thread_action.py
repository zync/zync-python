"""
Provides classes implementing actions that can be executed in the main thread.
"""
import sys

class MainThreadActionResult(object):
  """
  Holds the result of action or exception that was raised during the execution of the action.

  Arguments result and exception are mutually exclusive.

  :param Optional[object] result:
  :param Optional[BaseException] exception:
  :param Optional[object] traceback:
  """
  def __init__(self, **kwargs):
    if 'result' not in kwargs and 'exception' not in kwargs:
      raise ValueError('Either `result` or `exception` argument must be provided.')
    if 'result' in kwargs and 'exception' in kwargs:
      raise ValueError('Either `result` or `exception` argument must be provided.')
    self._result = kwargs.get('result', None)
    self._exception = kwargs.get('exception', None)
    self._traceback = kwargs.get('traceback', None)
    if self._exception is not None and not isinstance(self._exception, BaseException):
      raise ValueError('Argument `exception` must be an exception.')

  @property
  def is_exception(self):
    """
    Checks if the result is an exception.

    :return bool:
    """
    return self.exception is not None

  @property
  def result(self):
    """
    Gets the result or raises it if it is an exception.

    If traceback was provided, it will be appended to the traceback of reraised exception.

    :return object:
    """
    if self.is_exception:
      if self._traceback:
        raise self.exception, None, self._traceback
      else:
        raise self.exception
    return self._result

  @property
  def exception(self):
    """
    Gets the exception or None.

    :return BaseException:
    """
    return self._exception


class MainThreadAction(object):
  """
  Function-like object executed in the main thread.

  :param () -> object func:
  :param Optional[(ActionResult) -> None] submit_result: (Optional) Called by execute_and_submit,
                                                         action result is passed to this callback.
  """
  def __init__(self, func, submit_result=None):
    self._func = func
    self._submit_result = submit_result

  def execute(self):
    """
    Executes the action and wraps the result in MainThreadActionResult.

    :return MainThreadActionResult:
    """
    try:
      return MainThreadActionResult(result=self._func())
    except BaseException as err:
      return MainThreadActionResult(exception=err, traceback=sys.exc_info()[2])

  def execute_and_submit(self):
    """ Executes the action and submits the action result. """
    result = self.execute()
    if not self._submit_result:
      raise RuntimeError('submit_result callback not specified')
    self._submit_result(result)
