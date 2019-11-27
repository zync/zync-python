""" Contains interfaces for thread synchronization primitives and factory to create them. """
from abc import ABCMeta, abstractmethod


class Lock(object):
  """
  Lock interface.

  Different implementations of ThreadPool might use different locks, this class abstracts
  the expected lock interface.
  """
  __metaclass__ = ABCMeta

  @abstractmethod
  def acquire(self, blocking):
    """
    Acquire a lock, blocking or non-blocking.

    When invoked with blocking = True, it blocks until the lock can be locked and returns True.
    When invoked with blocking = False, it returns False instead of blocking.

    :param bool blocking:
    :return bool:
    """
    raise NotImplementedError()

  @abstractmethod
  def release(self):
    """
    Release lock.

    :raises:
      ThreadError: if invoked on an unlocked lock.
    """
    raise NotImplementedError()

  @abstractmethod
  def __enter__(self):
    """ Enter a context """
    raise NotImplementedError()

  @abstractmethod
  def __exit__(self, exc_type, exc_val, exc_tb):
    """ Exit the context """
    raise NotImplementedError()


class WaitCondition(object):
  """
  Wait condition interface.

  Different implementations of ThreadPool might use different wait conditions, this class abstracts
  the expected wait condition interface.
  """

  __metaclass__ = ABCMeta

  @abstractmethod
  def acquire(self, blocking):
    """
    Acquires the lock associated with this wait condition, blocking or non-blocking.

    When invoked with blocking = True, it blocks until the lock can be locked and returns True.
    When invoked with blocking = False, it returns False instead of blocking.

    :param bool blocking:
    :return bool:
    """
    raise NotImplementedError()

  @abstractmethod
  def release(self):
    """
    Releases the lock associated with this wait condition.

    :raises:
      ThreadError: if invoked on a wait condition with the associated lock unlocked.
    """
    raise NotImplementedError()

  @abstractmethod
  def wait(self, timeout):
    """
    Wait until notified or a timeout.

    :param Optional[float] timeout: Timeout in seconds or None for blocking call.
    :raises:
      RuntimeError: if the associated lock is not acquired first.
    """
    raise NotImplementedError()

  @abstractmethod
  def notify_all(self):
    """
    Wake up threads waiting for this condition.

    :raises:
      RuntimeError: if the associated lock is not acquired first.
    """
    raise NotImplementedError()

  @abstractmethod
  def __enter__(self):
    """ Enter a context """
    raise NotImplementedError()

  @abstractmethod
  def __exit__(self, exc_type, exc_val, exc_tb):
    """ Exit the context """
    raise NotImplementedError()


class ThreadSynchronizationFactory(object):
  """ Factory interface for creating synchronization primitives. """
  __metaclass__ = ABCMeta

  @abstractmethod
  def create_lock(self):
    """
    Creates a lock.

    :return Lock:
    """
    raise NotImplementedError()

  @abstractmethod
  def create_wait_condition(self, lock):
    """
    Creates a wait condition.

    :param Lock lock: The lock that will be used by wait condition. If None, new lock will be
                      created using create_lock method.
    :return WaitCondition:
    """
    raise NotImplementedError()
