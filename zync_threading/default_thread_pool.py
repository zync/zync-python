"""
Contains implementation of thread pool using standard Python threading utilities.
"""

import traceback
from functools import partial
import multiprocessing
from multiprocessing.dummy import Pool
import threading

from thread_pool import ThreadPool
import thread_synchronization


class DefaultLock(thread_synchronization.Lock):
  """ Wraps threading.Lock to make it subclass of thread_synchronization.Lock. """
  def __init__(self):
    self._lock = threading.Lock()

  def acquire(self, blocking=True):
    """ Delegates to threading.Lock.acquire. """
    return self._lock.acquire(blocking)

  def release(self):
    """ Delegates to threading.Lock.release. """
    return self._lock.release()

  def __enter__(self):
    return self._lock.__enter__()

  def __exit__(self, exc_type, exc_val, exc_tb):
    return self._lock.__exit__(exc_type, exc_val, exc_tb)


class DefaultWaitCondition(thread_synchronization.WaitCondition):
  """ Wraps threading.Condition to make it subclass of thread_synchronization.WaitCondition. """
  def __init__(self, lock):
    self._condition = threading.Condition(lock)

  def acquire(self, blocking=True):
    """ Delegates to threading.Condition.acquire. """
    return self._condition.acquire(blocking)

  def release(self):
    """ Delegates to threading.Condition.release. """
    return self._condition.release()

  def wait(self, timeout=None):
    """ Delegates to threading.Condition.wait. """
    return self._condition.wait(timeout)

  def notify_all(self,):
    """ Delegates to threading.Condition.wait. """
    return self._condition.notify_all()

  def __enter__(self):
    return self._condition.__enter__()

  def __exit__(self, exc_type, exc_val, exc_tb):
    return self._condition.__exit__(exc_type, exc_val, exc_tb)


class DefaultThreadPool(ThreadPool, thread_synchronization.ThreadSynchronizationFactory):
  """
  Runs interruptible tasks in multiple threads.

  :param Optional[int] concurrency_level: How many threads to run in parallel. It will use CPU count
                                          if not specified.
  :param Optional[(str, BaseException, str) -> None]: Optional callback for error handling. Arguments
                                                      are: task name, exception, traceback string.
  """

  def __init__(self, concurrency_level=None, error_handler=None):
    concurrency_level = concurrency_level if concurrency_level else multiprocessing.cpu_count()
    self._pool = Pool(concurrency_level)
    self._error_handler = error_handler
    self._tasks = set()
    self._tasks_lock = DefaultLock()

  def has_tasks(self):
    """
    Returns True if there are running or pending tasks and False otherwise.

    :return bool:
    """
    return len(self._tasks) > 0

  def add_task(self, task):
    """
    Adds the task to the pool.

    If there is a free thread, task starts to run immediately, otherwise it waits for some thread
    to pick it up.

    :param interruptible_task.InterruptibleTask task:
    """
    with self._tasks_lock:
      self._tasks.add(task)
      self._pool.apply_async(partial(self._run_task, task))

  def _run_task(self, task):
    try:
      if task.is_interrupted:
        task.on_cancelled()
      else:
        task.run()
    except BaseException as err:
      if self._error_handler:
        self._error_handler(task.task_name, err, traceback.format_exc())
    finally:
      self._remove_task(task)

  def _remove_task(self, task):
    with self._tasks_lock:
      self._tasks.remove(task)

  def create_lock(self):
    """
    Creates a lock appropriate to use with threads running in this thread pool.

    :return DefaultLock:
    """
    return DefaultLock()

  def create_wait_condition(self, lock=None):
    """
    Creates a wait condition appropriate to use with threads running in this thread pool.

    :param Lock lock: A lock with which the wait condition will be associated, must be created
                      using `create_lock` method of this thread pool. If lock is not specified,
                      it will be created by the thread pool.
    :return DefaultWaitCondition:
    """
    if lock is None:
      lock = self.create_lock()
    return DefaultWaitCondition(lock)
