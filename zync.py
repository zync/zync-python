"""
Zync Python API

A Python wrapper around the Zync HTTP API.
"""

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from urllib import urlencode

import zync_lib.httplib2 as httplib2
import zync_lib.oauth2client as oauth2client 

class ZyncAuthenticationError(Exception):
    pass

class ZyncError(Exception):
    pass

class ZyncConnectionError(Exception):
    pass

class ZyncPreflightError(Exception):
    pass

if os.environ.get('ZYNC_URL'):
  ZYNC_URL = os.environ.get('ZYNC_URL')
else:
  # FIXME: maintained for backwards compatibility
  current_dir = os.path.dirname(os.path.abspath(__file__))
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
  if platform.system().lower() == 'win32':
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

class HTTPBackend(object):
  """
  Methods for talking to services over HTTP.
  """
  def __init__(self, script_name, token, timeout=30.0, 
               disable_ssl_certificate_validation=False,
               url=None):
    """
    
    Args:
      disable_ssl_certificate_validation: bool, if True, will disable SSL
        certificate validation (for Zync integration tests).
      script_name: str, the Zync API script name
      token: str, token of the API script
      url: str, URL to the site.
    """
    self.script_name = script_name
    self.token = token
    if not url:
      url = ZYNC_URL
    self.url = url
    self.timeout = timeout
    self.disable_ssl_certificate_validation = disable_ssl_certificate_validation
    # access_token holds the user's current OAuth access token. Not used
    # if using a standard Zync login rather than a Google OAuth login.
    self.access_token = None
    if self.up():
      # cookie holds the current session cookie which is needed to 
      # make authenticated requests to the Zync REST API. This creates
      # a session with script-level permissions, which allow most read-only
      # functionality. A subsequent call to __auth() must be made to elevate
      # permissions to user-level, which will allow write access for operations
      # such as submitting jobs.
      self.cookie = self.__auth(self.script_name, self.token)
    else:
      raise ZyncConnectionError('ZYNC is down at URL: %s' % (self.url,))

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
      response, content = http.request(self.url, 'GET')
    except httplib2.ServerNotFoundError:
      return False
    except AttributeError:
      return False
    else:
      status = str(response['status'])
      return status.startswith('2') or status.startswith('3')

  def set_cookie(self, headers={}):
    """
    Adds the auth cookie to the given headers, raises
    ZyncAuthenticationError if cookie doesn't exist.
    """
    if self.cookie:
      headers['Cookie'] = self.cookie
      return headers
    else:
      raise ZyncAuthenticationError('Zync authentication failed.')

  def __auth(self, script_name, token, username=None, password=None, 
    access_token=None, email=None):
    """
    Authenticate with Zync.
    """
    http = self.__get_http()
    url = '%s/api/validate' % (self.url,)
    args = {
      'script_name': script_name,
      'token': token
    }
    if access_token is not None:
      args['access_token'] = access_token
      args['email'] = email
    elif username != None:
      args['user'] = username
      args['pass'] = password
    data = urlencode(args)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response, content = http.request(url, 'POST', data, headers=headers)
    if response['status'] == '200':
      return response['set-cookie']
    else:
      raise ZyncAuthenticationError(content)

  def login(self, username=None, password=None):
    """
    Elevate your session's permission level by authenticating with your username
    and password. This is not required for most methods in the class - the main
    exception is submit_job(), which does require user/pass authentication.
    """
    if self.up():
      self.cookie = self.__auth(self.script_name, self.token, username=username, password=password)
    else:
      raise ZyncConnectionError('ZYNC is down at URL: %s' % (self.url,))

  def __google_api(self, api_path, params={}):
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

  def login_with_google(self):
    """Performs the Google OAuth flow, which will open the user's browser
    for authorization if necessary, then retrieves the user's account info
    and authorizes with Zync.

    Returns:
      str, the user's email address

    Raises:
      ZyncAuthenticationError if user info is invalid or the login fails
      ZyncConnectionError if the Zync site is down
    """
    if self.up():
      storage = oauth2client.file.Storage(OAUTH2_STORAGE)
      credentials = storage.get()
      if credentials is None or credentials.invalid:
        flow = oauth2client.client.flow_from_clientsecrets(
          CLIENT_SECRET,
          scope=(
            'https://www.googleapis.com/auth/userinfo.profile '
            'https://www.googleapis.com/auth/userinfo.email'
          )
        )
        parser = argparse.ArgumentParser(parents=[oauth2client.tools.argparser])
        flags = parser.parse_args([])
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
          credentials.access_token, self.script_name, self.token, primary_email)
      return primary_email
    else:
      raise ZyncConnectionError('ZYNC is down at URL: %s' % (self.url,))
    
  def _save_oauth_credentials(self, access_token, script_name, token, email):
    """Saves credentials for oauth authentication.
    
    Used by Zync integration tests.
    
    Args:
      access_token: str, the OAuth access token.
      script_name: str, the Zync API script name
      token: str, token of the API script
      email: str, email address of the user authenticating with oauth
    """
    self.access_token = access_token
    self.cookie = self.__auth(script_name, token, access_token=access_token, email=email)

  def request(self, url, operation, data={}, headers={}):
    http = self.__get_http()
    headers = self.set_cookie(headers=headers)
    headers['X-Zync-Header'] = '1'
    if operation == 'GET':
      if len(data) > 0:
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
    else:
      raise ZyncError('%s: %s: %s' % (url.split('?')[0], resp['status'], content))

class Zync(HTTPBackend):
  """
  The entry point to the Zync service. Initialize this with your script name
  and token to use most API methods.
  """

  def __init__(self, script_name, token, timeout=30.0, application=None, 
               disable_ssl_certificate_validation=False, url=None):
    """
    Create a Zync object, for interacting with the Zync service.
    
    Args:
      disable_ssl_certificate_validation: bool, if True, will disable SSL
        certificate validation (for Zync integration tests).
      script_name: str, the Zync API script name
      token: str, token of the API script
      url: str, URL to the site, defaults to ZYNC_URL in config.py.
    """
    #
    #   Call the HTTPBackend.__init__() method.
    #
    super(Zync, self).__init__(
        script_name, token, timeout=timeout, 
        disable_ssl_certificate_validation=disable_ssl_certificate_validation,
        url=url)
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
    url = '%s/api/config' % (self.url,)
    if var != None:
      url += '/%s' % (var,)
    result = self.request(url, 'GET')
    if var == None:
      return result
    elif var in result:
      return result[var]
    else:
      return None

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

  def get_instance_types(self):
    """
    Get a list of instance types available to your site.
    """
    url = '%s/api/instance_types' % (self.url,)
    return self.request(url, 'GET')

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
    The projects queued for deletion are filtered out.
    """
    url = '%s/api/projects' % (self.url,)
    result = self.request(url, 'GET')
    return [project for project in result if (project['delete'] == 0)]

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

  def submit(self, script_path, write_name, params={}):
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

  def submit(self, file, params={}):
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

  def submit(self, file, params={}):
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

  def submit(self, file, params={}):
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
    data.update(params)
    #
    #   Fire Job.submit() to submit the job.
    #
    return super(VrayJob, self).submit(data)
