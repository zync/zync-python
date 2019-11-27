""" Contains implementation of asynchronous calls. """
from functools import wraps, partial

from background_task import BackgroundTask
from interruptible_task import TaskInterruptedException


class AsyncCaller(object):
  """
  Base class for classes that want to run asynchronous calls.

  :param thread_pool.ThreadPool thread_pool:
  :param thread_synchronization.Lock lock:
  :param main_thread_executor.MainThreadExecutor main_thread_executor:
  """
  def __init__(self, thread_pool, lock, main_thread_executor):
    super(AsyncCaller, self).__init__()
    self._thread_pool = thread_pool
    self._main_thread_executor = main_thread_executor
    self._async_tasks = set()
    self._async_tasks_lock = lock

  def start_async_call(self, func, on_success=None, on_error=None, name=None):
    """
    Schedules asynchronous call to func in the background.

    Optional on_success and on_error callbacks are executed in the main thread.

    :param () -> object func: Function to be executed asynchronously.
    :param Optional[(object) -> None] on_success: (Optional) Called when func returns without raising
                                                  exceptions. The return value is passed to this callback.
    :param Optional[(BaseException) -> None] on_error: (Optional) Called when func raises an exception.
                                                       The exception is passed to this callback.
    :param Optional[str] name: (Optional) Sets the name of the task that will execute this call. Name
                               is passed to thread pool error handlers to help identify error causes.
    :return interruptible_task.InterruptibleTask:
    """
    outer = self
    class _AsyncTask(BackgroundTask):
      def __init__(self):
        super(_AsyncTask, self).__init__(outer._main_thread_executor, name=name)

      def run(self):
        """ Executes func and calls back either on_success or on_error. """
        try:
          result = func()
          if on_success:
            self.run_on_main_thread(partial(on_success, result))
        except TaskInterruptedException:
          pass
        except BaseException as err:
          if on_error:
            self.run_on_main_thread(partial(on_error, err))
          else:
            raise
        finally:
          with outer._async_tasks_lock:
            outer._async_tasks.remove(self)

    async_task = _AsyncTask()
    with self._async_tasks_lock:
      self._async_tasks.add(async_task)
    self._thread_pool.add_task(async_task)
    return async_task

  def interrupt_all_async_calls(self):
    """ Marks all running and pending asynchronous calls as interrupted. """
    with self._async_tasks_lock:
      for task in self._async_tasks:
        task.interrupt()

  @staticmethod
  def async_call(on_success=None, on_error=None, name=None):
    """
    Convenience decorator for AsyncCaller subclasses that marks methods as asynchronous.

    Arguments of the decorator should be methods, they will be bound to `self` of the wrapped method.
    Static methods are not supported.

    Optional on_success and on_error callbacks are executed in the main thread.

    :param Optional[(object) -> None] on_success: (Optional) Called when func returns without raising
                                                  exceptions. The return value is passed to this callback.
    :param Optional[(BaseException) -> None] on_error: (Optional) Called when func raises an exception.
                                                       The exception is passed to this callback.
    :param Optional[str] name: (Optional) Sets the name of the task that will execute this call. Name
                               is passed to thread pool error handlers to help identify error causes.
    :return function:
    """
    def _wrap(func):
      @wraps(func)
      def _wrapper(self, *args, **kwargs):
        method = partial(func, self, *args, **kwargs)
        success_handler = partial(on_success, self) if on_success else None
        error_handler = partial(on_error, self) if on_error else None
        self.start_async_call(method, success_handler, error_handler, name)
      return _wrapper
    return _wrap
