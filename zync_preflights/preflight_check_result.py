""" Contains PreflightCheckResult class. """


class PreflightCheckResultSeverity(object):
  """ Enumerates severity levels of PreflightCheckResults. """
  SUCCESS = 0
  INFO = 1
  WARNING = 2
  ERROR = 3


class PreflightCheckResult(object):
  """
  Describes a unit result of preflight check.

  Fix hint is optional.

  :param str name:
  :param PreflightResult.Severity severity:
  :param str description:
  :param Optional[str] fix_hint:
  """
  def __init__(self, name, severity, description, fix_hint=None):
    self._name = name
    self._severity = severity
    self._description = description
    self._fix_hint = fix_hint

  def __eq__(self, other):
    return self.severity == other.severity and \
           self.fix_hint == other.fix_hint and \
           self.name == other.name and \
           self.description == other.description

  def __repr__(self):
    return 'PreflightCheckResult{name=%s,severity=%s,description=%s,fix_hint=%s}' % (
      self.name,
      self.severity,
      self.description,
      self.fix_hint
    )

  @property
  def name(self):
    """
    Gets the name.

    :return str:
    """
    return self._name

  @property
  def description(self):
    """
    Gets the description.

    :return str:
    """
    return self._description

  @property
  def severity(self):
    """
    Gets the severity.

    :return PreflightResult.Severity:
    """
    return self._severity

  @property
  def fix_hint(self):
    """
    Gets the fix hint or None if no fix hint was provided.

    :return Optional[str]:
    """
    return self._fix_hint
