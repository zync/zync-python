""" Contains PreflightCheck class. """


class PreflightCheckExecutionStatus(object):
  """ Enumerates all possible states a preflight check can have during execution. """
  PENDING = 0
  RUNNING = 1
  COMPLETED = 2
  ERRORED = 3
  CANCELLED = 4


class PreflightCheck(object):
  """ Base class for preflight checks. """
  def __init__(self, name, description):
    self._preflight_name = name
    self._preflight_description = description

  @property
  def preflight_name(self):
    """
    Gets the name of the preflight check.

    :return str:
    """
    return self._preflight_name

  @property
  def preflight_description(self):
    """
    Gets the description of preflight check.

    :return str:
    """
    return self._preflight_description
