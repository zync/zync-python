"""
Provides classes implementing actions that can be executed in the main thread.
"""

class MainThreadActionResult(object):
  """
  Holds the result of action, which can be an exception.

  :param object result:
  """
  def __init__(self, **kwargs):
    if 'result' not in kwargs and 'exception' not in kwargs:
      raise ValueError('Either `result` or `exception` argument must be provided.')
    if 'result' in kwargs and 'exception' in kwargs:
      raise ValueError('Either `result` or `exception` argument must be provided.')
    self._result = kwargs.get('result', None)
    self._exception = kwargs.get('exception', None)
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

    :return object:
    """
    if self.is_exception:
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

  :param (ActionResult) -> None submit_result:
  :param () -> object func:
  """
  def __init__(self, submit_result, func):
    self._submit_result = submit_result
    self._func = func

  def execute(self):
    """
    Executes the action and wraps the result in MainThreadActionResult.

    :return MainThreadActionResult:
    """
    try:
      return MainThreadActionResult(result=self._func())
    except BaseException as err:
      return MainThreadActionResult(exception=err)

  def execute_and_submit(self):
    """ Executes the action and submits the action result. """
    result = self.execute()
    self._submit_result(result)
