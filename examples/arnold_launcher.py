
#
#   Go two levels up and add that directory to the PATH, so we can find zync.py.
#
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#
#   Import ZYNC Python API.
#
import zync

#
#   Connect to ZYNC. This will start the browser to perform an Oauth2
#   authorization if needed.
#
z = zync.Zync()

#
#   The path to your Arnold scene. Use a wildcard to indicate multiple files.
#
scene_path = '/path/to/project/scene.ass'
#scene_path = '/path/to/project/scene.*.ass'

#
#   Other job parameters.
#
params = {
  #
  # GENERAL OPTIONS
  #
  #
  # job_subtype = Job subtype. Will currently always be "render".
  #
  'job_subtype': 'render', 
  #
  # num_instances = Number of render nodes to assign to this job.
  #
  'num_instances': 1,
  #
  # priority = The job's priority. 1-100, lower numbers = more priority.
  #
  'priority': 50, 
  #
  # upload_only = Whether to run an "upload-only" job. 0 will perform a full render
  #   render job, 1 will just upload files - no rendering will take place.
  #
  'upload_only': 0, 
  #
  # proj_name = ZYNC project.
  #
  'proj_name': 'ARNOLD_LAUNCHER', 
  #
  # skip_check = Whether to skip the file check / upload. Only use this if you're
  #   absolutely sure all files have already been uploaded to ZYNC.
  #
  'skip_check': 0, 
  #
  # instance_type = The machine type to use to render the job.
  #
  'instance_type': 'n1-standard-8', 
  #
  # ARNOLD OPTIONS
  #
  # output_dir = Path to a local directory for output frames to be downloaded to.
  #
  'output_dir': '/path/to/output/folder',
  #
  # output_filename = How output frames should be named. Can contain slashes
  #   to create subdirectories. Use a double dot '..' to indicate where the
  #   frame number should be inserted.
  #
  'output_filename': 'subdirectory/for/frames..png',
  #
  # xres = The output image x resolution.
  #
  'xres': 1280, 
  #
  # yres = The output image y resolution.
  #
  'yres': 720,
  #
  # scene_info = A collection of information about your Arnold scene(s).
  #
  'scene_info': {
    #
    # files = A list of files needed to render. Use local paths. ZYNC
    #   will also do its own scan prior to render, to supplement
    #   this list.
    #
    'files': [
      '/path/to/project/sourceimages/probe.hdr', 
      '/path/to/project/sourceimages/eyes.jpg', 
      '/path/to/project/sourceimages/wood-flooring-041_d.jpg', 
      '/path/to/project/sourceimages/wood-flooring-041_b.png', 
      '/path/to/project/sourceimages/wood-flooring-041_r.jpg'
    ], 
    #
    #   arnold_version = The Arnold version in use in your scene.
    #
    'arnold_version': '1.2.3.1', 
    #
    #   padding = The frame padding.
    #
    'padding': 3 
  } 
}

#
#   Launch the job. submit_job() returns the ID of the new job.
#
new_job = z.submit_job('arnold', scene_path, params=params)

print 'Job Launched.'

