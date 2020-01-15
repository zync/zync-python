""" Contains implementation of MainThreadExecutor. """
import threading
from main_thread_action import MainThreadAction


class MainThreadExecutor(object):
  """
  Queues and executes MainThreadActions on the main thread.

  Main thread is the thread which creates this object.

  :param thread_synchronization.AbstractThreadSynchronizationFactory thread_synchronization_factory:
  :param () -> None on_action_submitted: Optional callback called whenever new main thread action is added.
  :param () -> None on_actions_pending: Optional callback called after executing an action in the main thread
                                        when more actions are pending.
  """
  WAIT_CONDITION_TIMEOUT_SECONDS = 1

  def __init__(self, thread_synchronization_factory, on_action_submitted=None, on_actions_pending=None):
    self._thread_synchronization_factory = thread_synchronization_factory
    self._on_action_submitted = on_action_submitted
    self._on_actions_pending = on_actions_pending
    self._action_queue = []
    self._main_thread_ident = threading.current_thread().ident
    self._action_queue_lock = thread_synchronization_factory.create_lock()

  def _in_main_thread(self):
    return self._main_thread_ident == threading.current_thread().ident

  @staticmethod
  def _do_nothing():
    # Used as noop check_interrupted to simplify code.
    pass

  def run_on_main_thread(self, func, check_interrupted=None):
    """
    Runs func in the main thread and returns the result. If func raises an exception in the main
    thread, it will be caught and reraised in the calling thread.

    This method is reentrant.

    If check_interrupted is specified, this method will call it before executing the function
    and periodically while waiting for the result. It is expected that check_interrupted raises
    TaskInterruptedException when the execution of func should be interrupted.

    :param () -> object func: Function to execute on the main thread.
    :param Optional[() -> None] check_interrupted: Callback that can interrupt execution.
    :return object:
    :raises:
      TaskInterruptedException: if task is interrupted during the execution.
    """
    if self._in_main_thread():
      return self._execute_no_wait(func, check_interrupted if check_interrupted else self._do_nothing)
    else:
      return self._execute_and_wait(func, check_interrupted if check_interrupted else self._do_nothing)

  @staticmethod
  def _execute_no_wait(func, check_interrupted):
    check_interrupted()
    action_result = MainThreadAction(func).execute()
    check_interrupted()
    return action_result.result

  def _execute_and_wait(self, func, check_interrupted):
    check_interrupted()
    action_result = self._submit_and_wait(check_interrupted, func)
    check_interrupted()
    return action_result.result

  def size(self):
    """
    Returns the size of action queue.

    :return int:
    """
    return len(self._action_queue)

  def _submit_and_wait(self, check_interrupted, func):
    """
    Waits for and returns an action result.

    :return MainThreadActionResult:
    """
    action_context = self._ActionContext(self._thread_synchronization_factory.create_wait_condition())

    def _submit_result(action_result):
      with action_context.wait_condition:
        action_context.result = action_result
        action_context.result_submitted = True
        action_context.wait_condition.notify_all()

    with action_context.wait_condition:
      with self._action_queue_lock:
        self._action_queue.append(MainThreadAction(func, _submit_result))
      self._maybe_call_hook(self._on_action_submitted)
      while not action_context.result_submitted:
        check_interrupted()
        action_context.wait_condition.wait(timeout=MainThreadExecutor.WAIT_CONDITION_TIMEOUT_SECONDS)
        check_interrupted()
      return action_context.result

  class _ActionContext(object):
    def __init__(self, wait_condition):
      self.wait_condition = wait_condition
      self.result = None
      self.result_submitted = False

  def maybe_execute_action(self):
    """ Executes next action in the queue, if any. """
    with self._action_queue_lock:
      if self._action_queue:
        action = self._action_queue.pop(0)
        action.execute_and_submit()
        if self._action_queue:
          self._maybe_call_hook(self._on_actions_pending)

  @staticmethod
  def _maybe_call_hook(hook):
    if hook:
      hook()
