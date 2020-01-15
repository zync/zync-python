""" Contains utility classes for testing. """

class CountDownLatch(object):
  """
  Implements count down latch.

  :param thread_synchronization.WaitCondition wait_condition:
  :param int count:
  """
  def __init__(self, wait_condition, count=1):
    self._count = count
    self._wait_condition = wait_condition

  def decrease(self):
    """ Decreases the counter. """
    self._wait_condition.acquire()
    self._count -= 1
    if self._count <= 0:
      self._wait_condition.notify_all()
    self._wait_condition.release()

  def wait(self):
    """ Waits until the counter is not positive. """
    self._wait_condition.acquire()
    while self._count > 0:
      self._wait_condition.wait()
    self._wait_condition.release()
