"""
Zync Python API

A Python wrapper around the Zync HTTP API.
"""


__version__ = '1.2.6'


import argparse
import errno
import hashlib
import json
import os
import platform
import random
import select
import SocketServer
import sys
import time
from urllib import urlencode
from distutils.version import StrictVersion

import zync_lib.httplib2 as httplib2
import zync_lib.oauth2client as oauth2client


# This is a workaround for a problem that appears on CentOS.
# The stacktrace the user gets when trying to login with Google to a plugin is this:
# Traceback (most recent call last):
#   File "/usr/local/Nuke9.0v7/plugins/nuke/callbacks.py", line 127, in knobChanged
#     _doCallbacks(knobChangeds)
#   File "/usr/local/Nuke9.0v7/plugins/nuke/callbacks.py", line 46, in _doCallbacks
#     f[0](*f[1],**f[2])
#   File "/usr/local/Nuke9.0v7/plugins/nukescripts/panels.py", line 23, in PythonPanelKnobChanged
#     widget.knobChangedCallback(nuke.thisKnob())
#   File "/usr/local/Nuke9.0v7/plugins/nukescripts/panels.py", line 71, in knobChangedCallback
#     self.knobChanged(knob)
#   File "/home/shortcut/zync/zync-nuke/zync_nuke.py", line 644, in knobChanged
#     self.userLabel.setValue('  %s' % ZYNC.login_with_google())
#   File "/home/shortcut/zync/zync-python/zync.py", line 210, in login_with_google
#     credentials = oauth2client.tools.run_flow(flow, storage, flags)
#   File "/home/shortcut/zync/zync-python/zync_lib/oauth2client/util.py", line 129, in positional_wrapper
#     return wrapped(*args, **kwargs)
#   File "/home/shortcut/zync/zync-python/zync_lib/oauth2client/tools.py", line 199, in run_flow
#     httpd.handle_request()
#   File "/usr/local/Nuke9.0v7/lib/python2.7/SocketServer.py", line 265, in handle_request
#     fd_sets = select.select([self], [], [], timeout)
# select.error: (4, 'Interrupted system call')
# The cause of that is that both Maya and Nuke have an old version of SocketServer.py that does
# not correctly retry "select" call interrupted by EINTR. So we inject an implementation
# of handle_request() to ClientRedirectServer which does retries.
def _eintr_retry(redirect_server):
  """Call handle_request() from base class, retrying if interrupted by EINTR.

  Args:
    redirect_server: oauth2client.tools.ClientRedirectServer
  """
  while True:
    try:
      # We cannot call super() here, because ClientRedirectServer inherits
      # from an old-style class.
      # The full inheritance hierarchy is:
      # BaseServer <- TCPServer <- HTTPServer <- ClientRedirectServer
      # but the handle_request() method is defined in BaseServer and not
      # redefined in subclasses.
      return SocketServer.BaseServer.handle_request(redirect_server)
    except (OSError, select.error) as e:
      if e.args[0] != errno.EINTR:
        raise

oauth2client.tools.ClientRedirectServer.handle_request = _eintr_retry


class ZyncAuthenticationError(Exception):
    pass


class ZyncError(Exception):
    pass


class ZyncConnectionError(Exception):
    pass


class ZyncPreflightError(Exception):
    pass


current_dir = os.path.dirname(os.path.abspath(__file__))
if os.environ.get('ZYNC_URL'):
  ZYNC_URL = os.environ.get('ZYNC_URL')
else:
  # FIXME: maintained for backwards compatibility
  config_path = os.path.join(current_dir, 'config.py')
  if not os.path.exists(config_path):
    raise ZyncError('Could not locate config.py, please create.')
  from config import *

required_config = ['ZYNC_URL']

for key in required_config:
  if not key in globals():
    raise ZyncError('config.py must define a value for %s.' % (key,))


def __get_config_dir():
  """Return the directory in which Zync configuration should be stored.
  Varies depending on current system Operating System conventioned.

  Returns:
    str, absolute path to the Zync config directory
  """
  config_dir = os.path.expanduser('~')
  if platform.system().lower() in ('win32', 'windows'):
    config_dir = os.path.join(config_dir, 'AppData', 'Roaming', 'Zync')
  elif platform.system().lower() == 'darwin':
    config_dir = os.path.join(config_dir, 'Library', 'Application Support', 'Zync')
  else:
    config_dir = os.path.join(config_dir, '.zync')
  if not os.path.exists(config_dir):
    os.makedirs(config_dir)
  return config_dir


CLIENT_SECRET = os.path.join(current_dir, 'client_secret.json')
OAUTH2_STORAGE = os.path.join(__get_config_dir(), 'oauth2.dat')
OAUTH2_SCOPES = ['https://www.googleapis.com/auth/userinfo.profile',
                 'https://www.googleapis.com/auth/userinfo.email']


class HTTPBackend(object):
  """
  Methods for talking to services over HTTP.
  """
  def __init__(self, timeout=60.0,
               disable_ssl_certificate_validation=False,
               url=None, access_token=None, email=None):
    """
    Args:
      timeout: float, timeout limit for HTTP connection in seconds
      disable_ssl_certificate_validation: bool, if True, will disable SSL
        certificate validation (for Zync integration tests).
      url: str, URL to the site, defaults to ZYNC_URL in config.py.
      access_token: str, OAuth access token to use for this connection. if not
        provided Zync will perform the proper OAuth flow.
      email: str, email address to use to authentication this connection. used
        in combination with access_token.
    """
    if not url:
      url = ZYNC_URL
    self.url = url
    self.timeout = timeout
    self.disable_ssl_certificate_validation = disable_ssl_certificate_validation
    self.access_token = None
    self.email = None
    self.externally_provided_access_token = access_token
    self.externally_provided_email = email
    self.login_with_google(self.externally_provided_access_token,
                           self.externally_provided_email)

  def __get_http(self):
    return httplib2.Http(
        timeout=self.timeout,
        disable_ssl_certificate_validation=self.disable_ssl_certificate_validation)

  def up(self):
    """
    Checks for the site to be available.
    """
    http = self.__get_http()
    try:
      response, _ = http.request(self.url, 'GET')
    except httplib2.ServerNotFoundError:
      return False
    except AttributeError:
      return False
    else:
      status = str(response['status'])
      return status.startswith('2') or status.startswith('3')

  def set_cookie(self, headers=None):
    """
    Adds the auth cookie to the given headers, raises
    ZyncAuthenticationError if cookie doesn't exist.
    """
    if not headers:
      headers = {}
    if self.cookie:
      headers['Cookie'] = self.cookie
      return headers
    else:
      raise ZyncAuthenticationError('Zync authentication failed.')

  def __auth(self, access_token, email):
    """
    Authenticate with Zync.
    """
    http = self.__get_http()
    url = '%s/api/validate' % self.url
    args = {
      'access_token': access_token,
      'email': email,
    }
    data = urlencode(args)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response, content = http.request(url, 'POST', data, headers=headers)
    if response['status'] == '200':
      return response['set-cookie']
    else:
      raise ZyncAuthenticationError(content)

  def __google_api(self, api_path, params=None):
    """Make a call to a Google API.

    Args:
      api_path: str, the API path to call, i.e. the tail of the
        URL with no hostname
      params: dict, key-value pairs of any parameters to be passed with
        the GET request as part of the URL

    Returns:
      str, the response body

    Raises:
      ZyncError, if the response contains anything other than a
        200 status code.
    """
    http = httplib2.Http()
    headers = {'Authorization': 'OAuth %s' % self.access_token}
    url = 'https://www.googleapis.com/%s' % api_path
    if params:
      url += '?%s' % urlencode(params)
    resp, content = http.request(url, 'GET', headers=headers)
    if resp.status == 200:
      return content
    else:
      raise ZyncError(content)

  def login_with_google(self, access_token=None, email=None, attempts=5,
                        max_delay=15):
    """Wraps _login_with_google() in additional retrial loop.

    If request fails, retry after waiting random time between 1 and
    `max_delay` seconds.
    """
    for attempt in range(attempts):
      try:
        if attempt > 0:
          time.sleep(1 + random.random() * (max_delay - 1))
        return self._login_with_google(access_token, email)
      except ZyncAuthenticationError:
        exc_info = sys.exc_info()
    # no attempt successful, re-raise last exception
    raise exc_info[0], exc_info[1], exc_info[2]

  def _login_with_google(self, access_token=None, email=None):
    """Performs the Google OAuth flow, which will open the user's browser
    for authorization if necessary, then retrieves the user's account info
    and authorizes with Zync.

    Args:
      access_token: str, access token to use for authentication flow. only
        necessary if you must perform OAuth manually for some reason; in
        most cases this should be left blank so Zync performs the OAuth
        flow
      email: str, email address to use to authenticate with. used in
        combination with access_token. usually blank.

    Returns:
      str, the user's email address

    Raises:
      ZyncAuthenticationError if user info is invalid or the login fails
      ZyncConnectionError if the Zync site is down
    """
    if not self.up():
      raise ZyncConnectionError('ZYNC is down at URL: %s' % self.url)
    # if auth details were provided, no need to do anything else, just save
    # them out. this will make the appropriate call to pass auth details to
    # Zync to check that they are valid for that Zync account.
    if access_token and email:
      self._save_oauth_credentials(
          access_token, email)
      return email
    # otherwise, run the standard OAuth flow
    else:
      storage = oauth2client.file.Storage(OAUTH2_STORAGE)
      credentials = storage.get()
      if credentials is None or credentials.invalid:
        flow = oauth2client.client.flow_from_clientsecrets(CLIENT_SECRET,
                                                           scope=' '.join(OAUTH2_SCOPES))
        parser = argparse.ArgumentParser(parents=[oauth2client.tools.argparser])
        flags = parser.parse_args([])
        # if --noauth_local_webserver was given on the original commandline
        # pass it through, this will cause OAuth to display a link with which
        # to perform auth, rather than try to open a browser.
        if '--noauth_local_webserver' in sys.argv:
          flags.noauth_local_webserver = True
        credentials = oauth2client.tools.run_flow(flow, storage, flags)
      credentials.refresh(httplib2.Http())
      self.access_token = credentials.access_token
      userinfo = json.loads(self.__google_api('plus/v1/people/me'))
      primary_email = None
      for email in userinfo['emails']:
        if email['type'] == 'account':
          primary_email = email['value']
          break
      if not primary_email:
        self.access_token = None
        raise ZyncAuthenticationError('Could not locate user email address. ' +
          'Emails found: %s' % str(userinfo['emails']))
      self._save_oauth_credentials(
          credentials.access_token, primary_email)
      return primary_email

  def _save_oauth_credentials(self, access_token, email):
    """Saves credentials for oauth authentication.

    Used by Zync integration tests.

    Args:
      access_token: str, the OAuth access token.
      email: str, email address of the user authenticating with oauth
    """
    self.access_token = access_token
    self.email = email
    self.cookie = self.__auth(self.access_token, self.email)

  def logout(self):
    """Reduce current session back to script-level login."""
    self._clear_oauth_credentials()
    self.cookie = None

  def _clear_oauth_credentials(self):
    """Clear OAuth credentials."""
    self.access_token = None
    self.email = None
    # Remove the saved session from disk, ignore errors if it does not exist
    try:
      os.remove(OAUTH2_STORAGE)
    except OSError as e:
      if e.errno != errno.ENOENT:
        raise

  def has_user_login(self):
    """Check if current session has run the login-with-google flow.

    Returns:
      bool, True if logged in, False otherwise.
    """
    return (self.access_token is not None)

  def request(self, url, operation, data=None, headers=None, attempts=5):
    """Wraps _request() in additional authentication and retrial logic.

    If request fails with ZyncAuthenticationError, try to log in
    and retry up to `attempts` times.
    """
    for attempt in range(attempts):
      if self.cookie is None:
        self.login_with_google(self.externally_provided_access_token,
                               self.externally_provided_email)
      try:
        return self._request(url, operation, data, headers)
      except ZyncAuthenticationError:
        exc_info = sys.exc_info()
        # forget credentials
        self.access_token = None
        self.email = None
        self.cookie = None
    # no attempt successful, re-raise last exception
    raise exc_info[0], exc_info[1], exc_info[2]

  def _request(self, url, operation, data=None, headers=None):
    """Former request(); performs requests to Zync site."""
    http = self.__get_http()
    if not data:
      data = {}
    if not headers:
      headers = {}
    headers = self.set_cookie(headers=headers)
    headers['X-Zync-Header'] = '1'
    if operation == 'GET':
      if data:
        url += '?%s' % (urlencode(data),)
      resp, content = http.request(url, operation, headers=headers)
    else:
      if 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
      resp, content = http.request(url, operation, urlencode(data), headers=headers)
    if resp['status'] == '200':
      try:
        return json.loads(content)
      except ValueError:
        return content
    # Unfortunately, for historical reasons the login error and some fatal errors
    # all return 400 HTTP code. We have to resort to filtering by the message here.
    elif resp['status'] == '403' or (resp['status'] == '400' and
                                     ('invalid_token' in content or 'Please login' in content)):
      raise ZyncAuthenticationError(content)
    else:
      raise ZyncError('%s: %s: %s' % (url.split('?')[0], resp['status'], content))


class Zync(HTTPBackend):
  """
  The entry point to the Zync service. Initialize this with your script name
  and token to use most API methods.
  """

  def __init__(self, timeout=60.0, application=None,
               disable_ssl_certificate_validation=False, url=None,
               access_token=None, email=None):
    """
    Create a Zync object, for interacting with the Zync service.

    Args:
      timeout: float, timeout limit for HTTP connection in seconds
      application: str, name of the application in use, if any
      disable_ssl_certificate_validation: bool, if True, will disable SSL
        certificate validation (for Zync integration tests).
      url: str, URL to the site, defaults to ZYNC_URL in config.py.
      access_token: str, OAuth access token to use for this connection. if not
        provided Zync will perform the proper OAuth flow.
      email: str, email address to use to authentication this connection. used
        in combination with access_token.
    """
    #
    #   Call the HTTPBackend.__init__() method.
    #
    super(Zync, self).__init__(
        timeout=timeout,
        disable_ssl_certificate_validation=disable_ssl_certificate_validation,
        url=url, access_token=access_token, email=email)
    self.application = application
    #
    #   Initialize class variables by pulling various info from ZYNC.
    #
    self.CONFIG = self.get_config()
    self.INSTANCE_TYPES = self.get_instance_types()
    self.FEATURES = self.get_enabled_features()
    self.JOB_SUBTYPES = self.get_job_subtypes()
    self.MAYA_RENDERERS = self.get_maya_renderers()
    self.PRICING = self.get_pricing()

  def get_config(self, var=None):
    """
    Get your site's configuration settings. Use the "var" argument to
    get a specific value, or leave it out to get all values.
    """
    url = '%s/api/config' % self.url
    if var != None:
      url += '/%s' % var
    result = self.request(url, 'GET')
    if var == None:
      return result
    elif var in result:
      return result[var]
    else:
      return None

  def is_experiment_enabled(self, experiment):
    """Checks if experiment is enabled for the side using Zync web API.
    Args:
      experiment: str, name of the experiment

    Returns:
      True if experiment is enabled, False otherwise
    """
    url = '%s/api/experiment/%s' % (self.url, experiment)
    result = self.request(url, 'GET')

    return result

  def compare_instance_types(self, type_a, type_b):
    obj_a = self.INSTANCE_TYPES[type_a]
    obj_b = self.INSTANCE_TYPES[type_b]
    if 'order' in obj_a and 'order' in obj_b:
      return obj_a['order'] - obj_b['order']
    elif 'order' in obj_a and 'order' not in obj_b:
      return 1
    elif 'order' not in obj_a and 'order' in obj_b:
      return -1
    else:
      return 0

  def get_instance_types(self, renderer=None):
    """
    Get a list of instance types available to your site.
    """
    if self.application and renderer:
      data = {'plugin_type': '%s_%s' % (self.application, renderer)}
    elif self.application:
      data = {'plugin_type': self.application}
    else:
      data = {}
    return self.request('%s/api/instance_types' % self.url, 'GET', data=data)

  def get_enabled_features(self):
    """
    Get a list of enabled features available to your site.
    """
    url = '%s/api/features' % (self.url,)
    return self.request(url, 'GET')

  def get_job_subtypes(self):
    """
    Get a list of job subtypes available to your site. This will
    typically only be "render" - in the future ZYNC will likely support
    other subtypes like Texture Baking, etc.
    """
    url = '%s/api/job_subtypes' % (self.url,)
    return self.request(url, 'GET')

  def get_maya_renderers(self):
    """
    Get a list of Maya renderers available to your site.
    """
    url = '%s/api/maya_renderers' % (self.url,)
    return self.request(url, 'GET')

  def get_project_list(self):
    """
    Get a list of existing ZYNC projects on your site.
    """
    url = '%s/api/projects' % (self.url,)
    return self.request(url, 'GET')

  def get_project_name(self, file_path):
    """
    Takes the name of a file - either a Maya or Nuke script - and returns
    the default Zync project name for it.
    """
    url = '%s/api/project_name' % (self.url,)
    data = {'file': file_path}
    return self.request(url, 'GET', data)

  def get_jobs(self, max=100):
    """
    Returns a list of existing ZYNC jobs.
    """
    url = '%s/api/jobs' % (self.url,)
    data = {}
    if max != None:
      data['max'] = max
    return self.request(url, 'GET', data)

  def get_job_details(self, job_id):
    """
    Get a list of a specific job's details.
    """
    url = '%s/api/jobs/%d' % (self.url, job_id)
    return self.request(url, 'GET')

  def submit_job(self, job_type, *args, **kwargs):
    """
    Submit a new job to Zync.
    """
    #
    #   Select a Job subclass based on the job_type argument.
    #
    job_type = job_type.lower()
    if job_type == 'nuke':
      JobSelect = NukeJob
    elif job_type == 'maya':
      JobSelect = MayaJob
    elif job_type == 'arnold':
      JobSelect = ArnoldJob
    elif job_type == 'vray':
      JobSelect = VrayJob
    elif job_type == 'ae':
      JobSelect = AEJob
    elif job_type == 'houdini':
      JobSelect = HoudiniJob
    elif job_type == 'c4d':
      JobSelect = C4dJob
    else:
      raise ZyncError('Unrecognized job_type "%s".' % (job_type,))
    #
    #   Initialize the Job subclass.
    #
    new_job = JobSelect(self)
    #
    #   Run job.preflight(). If preflight does not succeed, an error will be
    #   thrown, so no need to check output here.
    #
    new_job.preflight()
    #
    #   Submit the job and return the output of that method.
    #
    new_job.submit(*args, **kwargs)
    return new_job

  def generate_file_path(self, file_path):
    """
    Returns a hash-embedded scene path for separation from user scenes.
    """
    scene_dir, scene_name = os.path.split(file_path)
    zync_dir = os.path.join(scene_dir, '__zync')

    if not os.path.exists(zync_dir):
      os.makedirs(zync_dir)

    local_time = time.localtime()

    times = [local_time.tm_mon, local_time.tm_mday, local_time.tm_year,
             local_time.tm_hour, local_time.tm_min, local_time.tm_sec]
    timecode = ''.join(['%02d' % x for x in times])

    old_filename, ext = os.path.splitext(scene_name)

    to_hash = '_'.join([old_filename, timecode])
    hash = hashlib.md5(to_hash).hexdigest()[-6:]

    # filename will be something like: shotName_comp_v094_37aa20.nk
    new_filename = '_'.join([old_filename, hash]) + ext

    return os.path.join(zync_dir, new_filename)

  def get_pricing(self):
    url = ('http://zync.cloudpricingcalculator.appspot.com' +
      '/static/data/pricelist.json')
    return self.request(url, 'GET')

  def get_eulas(self):
    return self.request('%s/api/eulas' % self.url, 'GET', {})


class Job(object):
  """
  Zync Job main class.
  """
  def __init__(self, zync):
    """
    The base Zync Job object, not useful on its own, but should be
    the parent for application-specific Job implementations.
    """
    self.zync = zync
    self.id = None
    self.job_type = None

  def _check_id(self):
    if self.id == None:
      raise ZyncError('This Job hasn\'t been initialized with an ID, ' +
        'yet, so this method is unavailable.')

  def details(self):
    """
    Returns a dictionary of the job details.
    """
    self._check_id()
    url = '%s/api/jobs/%d' % (self.zync.url, self.id)
    return self.zync.request(url, 'GET')

  def set_status(self, status):
    """
    Sets the job status for the given job. This is the method by which most
    job controls are initiated.
    """
    self._check_id()
    url = '%s/api/jobs/%d' % (self.zync.url, int(self.id))
    data = {'status': status}
    return self.zync.request(url, 'POST', data)

  def cancel(self):
    """
    Cancels the given job.
    """
    return self.set_status('canceled')

  def resume(self):
    """
    Resumes the given job.
    """
    return self.set_status('resume')

  def pause(self):
    """
    Pauses the given job.
    """
    return self.set_status('paused')

  def unpause(self):
    """
    Unpauses the given job.
    """
    return self.set_status('unpaused')

  def restart(self):
    """
    Requeues the given job.
    """
    return self.set_status('queued')

  def get_preflight_checks(self):
    """
    Gets a list of preflight checks for the current job type.
    """
    if self.job_type == None:
      raise ZyncError('job_type parameter not set. This is probably because ' +
        'your subclass of Job doesn\'t define it.')
    url = '%s/api/preflight/%s' % (self.zync.url, self.job_type)
    return self.zync.request(url, 'GET')

  def preflight(self):
    """
    Run the Job's preflight, which performs checks for common mistakes before
    submitting the job to ZYNC.
    """
    #
    #   Get the list of preflight checks.
    #
    preflight_list = self.get_preflight_checks()
    #
    #   Set up the environment needed to run the API commands passed to us. If
    #   Exceptions occur when loading the app APIs, return, as we're probably
    #   running in an external script and don't have access to the API.
    #
    #   TODO: can we move these into the Job subclasses? kind of annoying to have
    #         app-specific code here, but AFAIK the imports have to happen in this
    #         function in order to persist.
    #
    if len(preflight_list) > 0:
      if self.job_type == 'maya':
        try:
          import maya.cmds as cmds
        except:
          return
      elif self.job_type == 'nuke':
        try:
          import nuke
        except:
          return
    #
    #   Run the preflight checks.
    #
    for preflight_obj in preflight_list:
      matches = []
      try:
        #
        #   eval() the API code passed to us, which must return either a string or a list.
        #
        api_result = eval( preflight_obj['api_call'] )
        #
        #   If its not a list or a tuple, turn it into a list.
        #
        if (not type(api_result) is list) and (not type(api_result) is tuple):
          api_result = [ api_result ]
        #
        #   Look through the API result to see if the result meets the conditions laid
        #   out by the check.
        #
        for result_item in api_result:
          if preflight_obj['operation_type'] == 'equal' and result_item in preflight_obj['condition']:
            matches.append( str(result_item) )
          elif preflight_obj['operation_type'] == 'not_equal' and result_item not in preflight_obj['condition']:
            matches.append( str(result_item) )
      except Exception as e:
        continue
      #
      #   If there were any conditions matched, raise a ZyncPreflightError.
      #
      if len(matches) > 0:
        raise ZyncPreflightError(preflight_obj['error'].replace('%match%', ', '.join(matches)))

  def submit(self, params):
    """
    Submit a new job to ZYNC.

    Returns:
      str, ID of the submitted job.
    """
    #
    #   The submit_params dict will store most job options. Build
    #   some defaults in; most of these will be overridden by the
    #   submission script.
    #
    data = {}
    data['upload_only'] = 0
    data['start_new_slots'] = 1
    data['chunk_size'] = 1
    data['distributed'] = 0
    data['num_instances'] = 1
    data['skip_check'] = 0
    data['notify_complete'] = 0
    data['job_subtype'] = 'render'
    #
    #   Update data with any passed in params.
    #
    data.update(params)
    #
    #   Special case for the "scene_info" parameter, which is JSON, so
    #   we'll encode it into a string.
    #
    if 'scene_info' in data:
      data['scene_info'] = json.dumps(data['scene_info'])
    # Another special case for parameters which may hold the job's output
    # directory, which we must resolve to an absolute path.
    output_params = (
      'output_dir',
      'out_path',
    )
    for output_param in output_params:
      if output_param in data:
        data[output_param] = os.path.abspath(data[output_param])
    url = '%s/api/jobs' % (self.zync.url,)
    self.id = self.zync.request(url, 'POST', data)
    return self.id


class NukeJob(Job):
  """
  Encapsulates Nuke-specific Job functions.
  """
  def __init__(self, *args, **kwargs):
    #
    #   Just run Job.__init__(), and set the job_type.
    #
    super(NukeJob, self).__init__(*args, **kwargs)
    self.job_type = 'nuke'

  def submit(self, script_path, write_name, params=None):
    """
    Submits a Nuke job to ZYNC.

    Nuke-specific submit parameters. * == required.

    * write_node: The write node to render. Can be 'All' to render
        all nodes.

    * frange: The frame range to render.

    * chunk_size: The number of frames to render per task.

    step: The frame step, i.e. a step of 1 will render very frame,
        a step of 2 will render every other frame. Setting step > 1
        will cause chunk_size to be set to 1. Defaults to 1.

    """
    #
    #   Build default params, and update them with what's been passed
    #   in.
    #
    data = {}
    data['job_type'] = 'nuke'
    data['write_node'] = write_name
    data['file_path'] = script_path
    if params:
      data.update(params)
    #
    #   Fire Job.submit() to submit the job.
    #
    return super(NukeJob, self).submit(data)


class MayaJob(Job):
  """
  Encapsulates Maya-specific job functions.
  """
  def __init__(self, *args, **kwargs):
    #
    #   Just run Job.__init__(), and set the job_type.
    #
    super(MayaJob, self).__init__(*args, **kwargs)
    self.job_type = 'maya'

  def submit(self, file, params=None):
    """
    Submits a Maya job to ZYNC.

    Maya-specific submit parameters. * == required.

    * camera: The name of the render camera.

    * xres: The output image x resolution.

    * yres: The output image y resolution.

    * chunk_size: The number of frames to render per task.

    * renderer: The renderer to use. A list of available renderers
        can be retrieved with Zync.get_maya_renderers().

    * out_path: The path to which output frames will be downloaded to.
        Use a local path as it appears to you.

    * project: The local path of your Maya project. Used to resolve all
        relative paths.

    * frange: The frame range to render.

    * scene_info: A dict of information about your Maya scene to help
        ZYNC prepare its environment properly.

            Required:

                files: A list of files required to render your scene.

                extension: The file extension of your rendered frames.

                version: The Maya version in use.

                render_layers: A list of ALL render layers in your scene, not just
                    those being rendered.

            Optional:

                references: A list of references in use in your scene. Default: []

                unresolved_references: A list of unresolved references in your scene.
                    Helps ZYNC find all references. Default: []

                plugins: A list of plugins in use in your scene. Default: ['Mayatomr']

                arnold_version: If rendering with the Arnold renderer, the Arnold
                    version in use. Required for Arnold jobs. Default: None

                vray_version: If rendering with the Vray renderer, the Vray version in use.
                    Required for Vray jobs. Default: None

                file_prefix: The file name prefix used in your scene. Default: ['', {}]
                    The structure is a two-element list, where the first element is the
                    global prefix and the second element is a dict of each layer override.
                    Example:
                        ['global_scene_prefix', {
                            layer1: 'layer1_prefix',
                            layer2: 'layer2_prefix'
                        }]

                padding: The frame padding in your scene. Default: None

                bake_sets: A dict of all Bake Sets in your scene. Required for Bake
                    jobs. Bake jobs are in beta and are probably not available for
                    your site. Default: {}

                render_passes: A dict of render passes being renderered, by render layer.
                    Default: {}
                    Example: {'render_layer1': ['refl', 'beauty'], 'render_layer2': ['other_pass']}

        layers: A list of render layers to be rendered. Not required, but either layers or
            bake_sets must be provided. Default: []

        bake_sets: A list of Bake Sets to be baked out. Not required, but either layers or
            bake_sets must be provided. Bake jobs are currently in beta and are probably not
            available to your site yet. Default: []

        step: The frame step to render, i.e. a step of 1 will render very frame,
            a step of 2 will render every other frame. Setting step > 1
            will cause chunk_size to be set to 1. Default: 1

        use_mi: Whether to use Mental Ray Standalone to render. Only used for Mental Ray jobs.
            This option is required for most sites. Default: 0

        use_vrscene: Whether to use Vray Standalone to render. Only used for Vray jobs.
            for Vray jobs. Default: 0

        vray_nightly: When rendering Vray, whether to use the latest Vray nightly build to render.
            Only used for Vray jobs. Default: 0

        ignore_plugin_errors: Whether to ignore errors about missing plugins. WARNING: if you
            set this to 1 and the missing plugins are doing anything important in your scene,
            it is extremely likely your job will render incorrectly, or not at all. USE CAUTION.

        use_ass: Whether to use Arnold Standalone (kick) to render. Only used for Arnold jobs. Default: 0

    """
    #
    #   Set some default params, and update them with what's been passed in.
    #
    data = {}
    data['job_type'] = 'maya'
    data['file_path'] = file
    if params:
      data.update(params)
    #
    #   Fire Job.submit() to submit the job.
    #
    return super(MayaJob, self).submit(data)


class ArnoldJob(Job):
  """
  Encapsulates Arnold-specific job functions.
  """
  def __init__(self, *args, **kwargs):
    #
    #   Just run Job.__init__(), and set the job_type.
    #
    super(ArnoldJob, self).__init__(*args, **kwargs)
    self.job_type = 'arnold'

  def submit(self, file, params=None):
    """
    Submits an Arnold job to ZYNC.

    Arnold-specific submit parameters. * == required.

    NOTE: the "file" param can contain a wildcard to render multiple Arnold
      scenes as part of the same job. E.g. "/path/to/render_scene.*.ass"

    * xres: The output image x resolution.

    * yres: The output image y resolution.

    project_dir: Path to the 3d project directory, if one exists. For example,
      your Maya project. This will help Zync to resolve relative file paths.

    * output_dir: The directory into which to download all output frames.

    * output_filename: The name of the output files. Can be a path, i.e.
        can include slashes.

    * scene_info: A dict of information about your Arnold scene to help
        ZYNC prepare its environment properly.

          Required:

            arnold_version: The Arnold version in use.

            padding: The frame padding in your scene.

          Optional:

            files: A list of files required to render your scene. This is not
              required as ZYNC will scan your scene to determine a file list.
              But, you can use this element to force extra elements to be added.
    """
    #
    #   Build default params, and update with what's been passed in.
    #
    data = {}
    data['job_type'] = 'arnold'
    data['file_path'] = file
    if params:
      data.update(params)
    #
    #   Fire Job.submit() to submit the job.
    #
    return super(ArnoldJob, self).submit(data)


class VrayJob(Job):
  """
  Encapsulates Vray-specific job functions.
  """
  def __init__(self, *args, **kwargs):
    #
    #   Just run Job.__init__(), and set the job_type.
    #
    super(VrayJob, self).__init__(*args, **kwargs)
    self.job_type = 'vray'

  def submit(self, file, params=None):
    """
    Submits an Vray job to ZYNC.

    Vray-specific submit parameters. * == required.

    * frange: The frame range to render.

    * chunk_size: The number of frames to render per task.

    project_dir: Path to the 3d project directory, if one exists. For example,
      your Maya project. This will help Zync to resolve relative file paths.

    * output_dir: The directory to store output frames in.

    * output_filename: The name of the output files. Can contain subdirectories.

    * xres: The output image x resolution.

    * yres: The output image y resolution.

    * scene_info: A dict of information about your Arnold scene to help
        ZYNC prepare its environment properly.

          Required:

            vray_version: The Vray version in use.

            padding: The frame padding in your scene.

            files: A list of files required to render your scene. This is not
              required as ZYNC will scan your scene to determine a file list.
              But, you can use this element to force extra elements to be added.
    """
    #
    #   Build default params, and update with what's been passed in.
    #
    data = {}
    data['job_type'] = 'vray'
    data['file_path'] = file
    if params:
      data.update(params)
    #
    #   Fire Job.submit() to submit the job.
    #
    return super(VrayJob, self).submit(data)


class AEJob(Job):
  """
  Encapsulates AE-specific job functions.

  Typically you would launch AE jobs directly from After-Effects, which uses a
  JavaScript environment. This class is provided mostly for Zync team's internal
  use.
  """
  def __init__(self, *args, **kwargs):
    #
    #   Just run Job.__init__(), and set the job_type.
    #
    super(AEJob, self).__init__(*args, **kwargs)
    self.job_type = 'ae'

  def submit(self, file, params=None):
    """
    Submits an AE job to ZYNC.
    """
    #
    #   Build default params, and update with what's been passed in.
    #
    data = {}
    data['job_type'] = 'ae'
    data['file_path'] = file
    if params:
      data.update(params)
    #
    #   Fire Job.submit() to submit the job.
    #
    return super(AEJob, self).submit(data)


class HoudiniJob(Job):
  """
  Encapsulates Houdini-specific job functions.
  """
  def __init__(self, *args, **kwargs):
    #
    #   Just run Job.__init__(), and set the job_type.
    #
    super(HoudiniJob, self).__init__(*args, **kwargs)
    self.job_type = 'houdini'

  def submit(self, file, params=None):
    """
    Submits an Houdini job to ZYNC.
    """
    #
    #   Build default params, and update with what's been passed in.
    #
    data = {}
    data['job_type'] = 'houdini'
    data['file_path'] = file
    if params:
      data.update(params)
    #
    #   Fire Job.submit() to submit the job.
    #
    return super(HoudiniJob, self).submit(data)


class C4dJob(Job):
  """
  Encapsulates Cinema 4D-specific job functions.
  """
  def __init__(self, *args, **kwargs):
    #
    #   Just run Job.__init__(), and set the job_type.
    #
    super(C4dJob, self).__init__(*args, **kwargs)
    self.job_type = 'c4d'

  def submit(self, file, params=None):
    """
    Submits an Cinema 4D job to ZYNC.
    """
    #
    #   Build default params, and update with what's been passed in.
    #
    data = {}
    data['job_type'] = 'c4d'
    data['file_path'] = file
    if params:
      data.update(params)
    #
    #   Fire Job.submit() to submit the job.
    #
    return super(C4dJob, self).submit(data)


def is_latest_version(versions_to_check, check_zync_python=True):
  """Checks if version of the plugins are up to date with published ones.

  Args:
    versions_to_check: [(str, str)], List of pairs representing name of the
        plugin and it's current version

  Returns:
    bool, True if asked version is up to date
  """
  version_api_template = 'https://api.zyncrender.com/%s/version'
  if check_zync_python:
    versions_to_check.append(('zync_python', __version__))
  http = httplib2.Http()
  for plugin_name, local_version in versions_to_check:
    publish_url = version_api_template % plugin_name
    response, published_version = http.request(publish_url, 'GET')
    if StrictVersion(local_version) < StrictVersion(published_version):
      # Update is needed
      return False
  return True
