from functools import partial
import hashlib
import os
import platform
import re
import sys
import traceback
from urllib import urlencode

from zync_threading import BaseInterruptibleTask
from zync_threading.default_thread_pool import DefaultThreadPool
from zync import HTTPBackend

TRACKING_ID = 'UA-74927307-3'

thread_pool = DefaultThreadPool(concurrency_level=1)


def _post_event(site_code, category, action, label, app, app_version,
                plugin_version):
  platform_string = platform.platform(terse=True)
  user_agent = '%s/%s (%s) %s' % (app, app_version, platform_string,
                                  plugin_version)
  headers = {
      'user-agent': user_agent,
      'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
  }
  if site_code:
    uid = hashlib.sha256(site_code + '=0w835ohs;e5ut').hexdigest()
  else:
    uid = 'unknown'
  params = {
      'v': 1,
      't': 'event',
      'tid': TRACKING_ID,
      'ec': category,
      'ea': action,
      'cid': uid,
      'cd1': app,
      'cd2': app_version,
      'cd3': plugin_version,
      'fl': plugin_version,
  }
  if label:
    params['el'] = label

  body = urlencode(params)
  url = 'https://www.google-analytics.com/collect'
  http = HTTPBackend.get_http(timeout=30)
  resp, content = http.request(url, 'POST', headers=headers, body=body)
  if resp.status == 200:
    return content
  else:
    sys.stderr.write('post_event failed with [%d] %s\n' %
                     (resp.status, content))


class PostEventTask(BaseInterruptibleTask):
  """
  Task that sends events to GA.

  :param str site_code:
  :param str category: event category
  :param str action: event action
  :param str label: event label
  :param str app: host app like 'maya'
  :param str app_version: host app version
  :param str plugin_version:
  """

  def __init__(self, site_code, category, action, label, app, app_version, plugin_version):
    super(PostEventTask, self).__init__()
    self._site_code = site_code
    self._category = category
    self._action = action
    self._label = label
    self._app = app
    self._app_version = app_version
    self._plugin_version = plugin_version

  def run(self):
    """ Sends event to GA. """
    try:
      _post_event(self._site_code, self._category, self._action, self._label, self._app, self._app_version, self._plugin_version)
    except:
      traceback.print_exc()


def post_event_async(site_code, action, label, app, app_version, plugin_version):
  """
  Sends event to GA asynchronously.

  :param str site_code:
  :param str action: event action
  :param Optional[str] label: event label
  :param str app: host app like 'maya'
  :param str app_version: host app version
  :param str plugin_version:
  """
  thread_pool.add_task(PostEventTask(site_code, 'plugin', action, label, app, app_version, plugin_version))


def post_plugin_error_event(site_code,
                            app,
                            app_version,
                            plugin_version,
                            error):
  """
  Posts an event with error.
  Args:
    :param str site_code:
    :param str app:
    :param str app_version:
    :param str plugin_version:
    :param Exception|str error: Favorably result of traceback.format_exc()
    or just an error message.
  """
  post_event_async(site_code, 'error', format_error(error), app, app_version,
                   plugin_version)


def post_login_event(site_code, app, app_version, plugin_version):
  """
  Posts an event for a successful login.
  Args:
    :param str site_code:
    :param str app:
    :param str app_version:
    :param str plugin_version:
  """
  post_event_async(site_code, 'login', None, app, app_version, plugin_version)


def post_job_submission_start_event(site_code, app, host_app_version,
                                    plugin_version):
  """
  Posts an event for a beginning of a job submission.
  Args:
    :param str site_code:
    :param str app:
    :param str host_app_version:
    :param str plugin_version:
  """
  post_event_async(site_code, 'submitting_job', None, app, host_app_version,
                   plugin_version)


def _mask_file_name(filename):
  if not filename:
    return filename
  name, extension = os.path.splitext(filename)
  if extension in ['.py', '.pyp']:
    return filename
  return name[0] + extension


def _is_windows_drive(dir_name):
  return len(dir_name) == 2 and dir_name[1] == ':'


def _shorten_dir_name(dir_name):
  if not dir_name:
    return dir_name
  if _is_windows_drive(dir_name):
    return dir_name
  return dir_name[0]


def _shorten_path(path):
  parts = path.replace('\\', '/').split('/')
  # Do not consider strings with less than two slashes as paths
  # unless they start with windows drive.
  if len(parts) <= 1:
    return path
  if len(parts) == 2 and not _is_windows_drive(parts[0]):
    return path

  shortened = [_shorten_dir_name(p) for p in parts[:-1]]
  return '/'.join(shortened) + '/' + _mask_file_name(parts[-1])


def format_error(error, limit=500):
  error = unicode(error)
  truncate_left = 'Traceback (most recent call last):' in error
  error = error.replace('Traceback (most recent call last):', '').strip()

  def replace_path(match, group_idx=0, surround_with=''):
    return surround_with + _shorten_path(match.group(group_idx)) + surround_with

  def replace_backtrace_entry(match):
    return match.group(1) + ':' + match.group(2)

  # linux paths
  error = re.sub('/?[^/\s"]+/[^/\s"]+(/[^/\s"]+)*', replace_path, error)
  # windows paths
  error = re.sub('([a-zA-Z]:\\\\)?[^\\\\\s"]+\\\\[^\\\\\s"]+(\\\\[^\\\\\s"]+)*',
                 replace_path, error)

  # Shorten paths containing spaces when they are in quotes
  error = re.sub('"([^"]+)"',
                 partial(replace_path, group_idx=1, surround_with='"'), error)

  error = re.sub('File "([^"]+)", line (\d+)', replace_backtrace_entry, error)

  # mask emails
  error = re.sub(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}\b",
                 '<email>', error)
  error = error.strip()

  if truncate_left:
    return error[-limit:]
  return error[0:limit]


def main():
  """ Entry point. """
  import time
  timestamp = time.time()

  for i in range(1, 3):
    site_code = 'test-%s-%s-' % (timestamp, i)
    post_login_event(site_code, 'maya', '2018', '1.0.0')
    post_job_submission_start_event(site_code, 'maya', '2018', '1.0.0')
    post_plugin_error_event(site_code, 'maya', '2018', '1.0.0',
                            'something_failed')
    try:
      raise Exception('Error message')
    except Exception:
      post_plugin_error_event(site_code, 'maya', '2018', '1.0.0',
                              traceback.format_exc())
  thread_pool.shutdown()

if __name__ == '__main__':
  main()
